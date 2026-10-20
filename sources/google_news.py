from urllib.parse import quote_plus, urlparse

from config import (
    FILTER_PROFILES,
    SEARCH_WINDOWS_DAYS,
)
from sources.common import make_item, parse_date, score_section_item, should_keep_section_item


GOOGLE_NEWS_RSS_URL = (
    "https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"
)


def fetch_google_news_items(search_queries, existing_items=None, cache=None, article_cache=None,
                            targets=None, wechat_needed=0):
    """Search a declared query scope; never stop or trim by article counts."""
    from sources.http_feed import fetch_unique, enrich_items
    from intelligence.report_quality import eligible, canonical_link
    from config import SEARCH_QUERIES_PER_SECTION
    cache = cache if cache is not None else {}
    article_cache = article_cache if article_cache is not None else {}
    existing_items = existing_items or []
    seen = {canonical_link(i['link']) for i in existing_items if i.get('link')}
    sections = dict(_iter_section_queries(search_queries))
    selected = {s: [] for s in sections}
    queues = {s: list(dict.fromkeys(' '.join(q.split()) for q in queries[:SEARCH_QUERIES_PER_SECTION]))
              for s, queries in sections.items()}

    def read_batch(batch):
        feeds = fetch_unique([entry[2] for entry in batch], cache)
        seeds = []
        for (section, query, url), feed in zip(batch, feeds):
            if feed is None:
                continue
            profile = FILTER_PROFILES.get(section, {})
            for entry in feed.entries:
                title, summary = entry.get('title', ''), entry.get('summary', '')
                if should_keep_section_item(title, summary, profile):
                    item = _make_google_news_item(entry, query, section, max(SEARCH_WINDOWS_DAYS),
                                                 score_section_item(title, summary, profile), 2, False)
                    publisher = entry.get('source') or {}
                    item['source'] = (publisher.get('title') if isinstance(publisher, dict) else str(publisher)) or urlparse(item['link']).hostname or 'Web source'
                    seeds.append(item)
        added = set()
        for item in enrich_items(seeds, article_cache):
            if not eligible(item):
                continue
            key = canonical_link(item['link'])
            if key not in seen:
                seen.add(key)
                selected[item['domain']].append(item)
                added.add(item['domain'])
        return added

    while any(queues.values()):
        batch = []
        for section, queries in queues.items():
            for _ in range(min(2, len(queries))):
                query = queries.pop(0)
                batch.append((section, query, GOOGLE_NEWS_RSS_URL.format(query=quote_plus(query + ' when:14d'))))
        added = read_batch(batch)
        alternate = [(s, q, 'https://www.bing.com/search?format=rss&q=' + quote_plus(q + ' past 14 days'))
                     for s, q, _ in batch if s not in added]
        if alternate:
            read_batch(alternate)
    print('[search] cached requests=' + str(len(cache)) + ', usable=' + str({s: len(v) for s, v in selected.items()}), flush=True)
    return [item for s in sections for item in sorted(selected[s], key=lambda i: i.get('relevance_score', 0), reverse=True)]


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

