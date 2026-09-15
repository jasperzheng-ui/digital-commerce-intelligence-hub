from urllib.parse import quote_plus, urlparse

from config import (
    EXPANDED_SEARCH_QUERIES,
    FILTER_PROFILES,
    MAX_SECTION_CANDIDATES,
    MIN_SECTION_CANDIDATES,
    SEARCH_WINDOWS_DAYS,
)
from sources.common import make_item, parse_date, score_section_item, should_keep_section_item


GOOGLE_NEWS_RSS_URL = (
    "https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"
)


def fetch_google_news_items(search_queries, existing_items=None, cache=None, article_cache=None,
                            targets=None, wechat_needed=0):
    from sources.http_feed import fetch_unique, enrich_items
    from intelligence.report_quality import eligible, canonical_link
    from config import PREFERRED_WECHAT_CHANNELS
    cache = cache if cache is not None else {}
    article_cache = article_cache if article_cache is not None else {}
    targets = targets or MIN_SECTION_CANDIDATES
    existing_items = existing_items or []
    sections = dict(_iter_section_queries(search_queries))
    selected = {s: [] for s in sections}
    # Small prioritized batches, not the entire keyword catalogue. This limits work,
    # never interrupts a running request or fabricates completeness.
    queues = {}
    for s, queries in sections.items():
        channels = PREFERRED_WECHAT_CHANNELS.get(s, [])[:2]
        targeted = ['site:mp.weixin.qq.com ' + channel for channel in channels]
        queries = targeted + list(queries)[:2] if wechat_needed else list(queries)[:4]
        queues[s] = list(dict.fromkeys(' '.join(q.split()).casefold() for q in queries))
    def enough(s):
        pool = [i for i in existing_items + selected[s] if i.get('domain') == s]
        return (len({canonical_link(i['link']) for i in pool}) >= targets.get(s, 8)
                and len({canonical_link(i['link']) for i in pool if i.get('source_type') == 'wechat'}) >= wechat_needed)
    def read_batch(batch, feeds):
        seeds = []
        for (s, query, url), feed in zip(batch, feeds):
            if feed is None:
                continue
            profile = FILTER_PROFILES.get(s, {})
            for entry in feed.entries[:4]:
                title, summary = entry.get('title', ''), entry.get('summary', '')
                if should_keep_section_item(title, summary, profile):
                    item = _make_google_news_item(entry, query, s, max(SEARCH_WINDOWS_DAYS),
                                                  score_section_item(title, summary, profile), 2, False)
                    publisher = entry.get('source') or {}
                    item['source'] = (publisher.get('title') if isinstance(publisher, dict) else str(publisher)) or urlparse(item['link']).hostname or 'Web source'
                    seeds.append(item)
        verified = enrich_items(seeds, article_cache)
        for item in verified:
            if eligible(item):
                s = item['domain']
                key = canonical_link(item['link'])
                if key not in {canonical_link(i['link']) for i in existing_items + selected[s]}:
                    selected[s].append(item)
    while queues:
        batch = []
        for s in list(queues):
            if enough(s) or not queues[s]:
                del queues[s]
                continue
            for _ in range(min(2, len(queues[s]))):
                query = queues[s].pop(0)
                url = GOOGLE_NEWS_RSS_URL.format(query=quote_plus(query + ' when:14d'))
                if url not in cache:
                    batch.append((s, query, url))
        if not batch:
            continue
        read_batch(batch, fetch_unique([x[2] for x in batch], cache))
        alternate = [(s, q, 'https://www.bing.com/search?format=rss&q=' + quote_plus(q))
                     for s, q, _ in batch if not enough(s)]
        alternate = [b for b in alternate if b[2] not in cache]
        if alternate:
            read_batch(alternate, fetch_unique([x[2] for x in alternate], cache))
    print('[search] cached requests=' + str(len(cache)) + ', usable=' + str({s: len(v) for s,v in selected.items()}), flush=True)
    return [i for s in sections for i in sorted(selected[s], key=lambda i: i.get('relevance_score',0), reverse=True)[:MAX_SECTION_CANDIDATES.get(s,12)]]


def _make_google_news_item(entry, query, section, window_days, score, priority, fallback):
    item = make_item(
        source=f"Google News: {query}",
        title=entry.get("title", ""),
        summary=entry.get("summary", "") or entry.get("description", ""),
        link=entry.get("link", ""),
        published_date=parse_date(entry),
        domain=section,
        origin_type="google_news",
        priority=priority,
        search_window_days=window_days,
    )
    item["relevance_score"] = score
    if fallback:
        item["fallback_reason"] = "highest_scored_recent_candidate"
    return item


def _dedupe_key(title, link):
    normalized_title = " ".join(str(title).lower().split())
    normalized_link = str(link).strip()
    return normalized_title, normalized_link


def _iter_section_queries(search_queries):
    if isinstance(search_queries, dict):
        for section, queries in search_queries.items():
            yield section, queries
        return

    # Backward compatibility with old [{query, domain}] shape.
    grouped = {}
    for query_config in search_queries:
        grouped.setdefault(query_config.get("domain", "retail"), []).append(query_config["query"])
    for section, queries in grouped.items():
        yield section, queries
