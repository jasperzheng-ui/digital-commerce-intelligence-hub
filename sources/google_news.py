from urllib.parse import quote_plus

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


def fetch_google_news_items(search_queries, existing_items=None):
    # Query once for the widest window. All recency selection below is local.
    from sources.http_feed import fetch_unique
    from sources.common import coerce_datetime
    from datetime import datetime, timezone, timedelta

    sections = dict(_iter_section_queries(search_queries))
    cache = {}
    raw = {section: [] for section in sections}
    seen_queries = {section: set() for section in sections}
    now = datetime.now(timezone.utc)
    widest = max(SEARCH_WINDOWS_DAYS)
    existing_links = {s: {i.get('link') for i in (existing_items or [])
                         if i.get('domain') == s and i.get('link')}
                      for s in sections}

    def enough(section):
        links = existing_links[section] | {i['link'] for i in select(section)}
        return len(links) >= MIN_SECTION_CANDIDATES.get(section, 2)

    def select(section):
        by_key = {}
        profile = FILTER_PROFILES.get(section, {})
        for entry, query in raw[section]:
            published = parse_date(entry)
            parsed = coerce_datetime(published)
            if parsed is None or parsed > now or parsed < now - timedelta(days=widest):
                continue
            title = entry.get('title', '')
            summary = entry.get('summary', '') or entry.get('description', '')
            if not should_keep_section_item(title, summary, profile):
                continue
            score = score_section_item(title, summary, profile)
            item = _make_google_news_item(entry, query, section, widest, score, 2, False)
            key = _dedupe_key(item['title'], item['link'])
            by_key.setdefault(key, item)
        values = list(by_key.values())
        for window in sorted(SEARCH_WINDOWS_DAYS):
            recent = [dict(i, search_window_days=window) for i in values
                      if coerce_datetime(i['published_date']) >= now - timedelta(days=window)]
            recent.sort(key=lambda i: (i.get('relevance_score', 0), i.get('published_date', '')), reverse=True)
            if len(recent) >= MIN_SECTION_CANDIDATES.get(section, 2) or window == widest:
                return recent[:MAX_SECTION_CANDIDATES.get(section, 8)]
        return []

    def collect(queries_by_section):
        queues = {s: iter(q) for s, q in queries_by_section.items()}
        while queues:
            batch = []
            for section in list(queues):
                if enough(section):
                    del queues[section]
                    continue
                # Two per section per wave: prioritize early queries, avoid
                # launching an entire catalogue after the pool is sufficient.
                for _ in range(2):
                    query = next(queues[section], None)
                    if query is None:
                        del queues[section]
                        break
                    normalized = ' '.join(query.split()).casefold()
                    if normalized in seen_queries[section]:
                        continue
                    seen_queries[section].add(normalized)
                    url = GOOGLE_NEWS_RSS_URL.format(query=quote_plus(f'{normalized} when:{widest}d'))
                    batch.append((section, query, url))
            if not batch:
                continue
            feeds = fetch_unique([url for _, _, url in batch], cache)
            for (section, query, _), feed in zip(batch, feeds):
                if feed is not None:
                    # Keep the returned feed, not only its first five entries:
                    # a 14-day response must also support local 3/7-day selection.
                    raw[section].extend((entry, query) for entry in feed.entries)
        return {s: select(s) for s in sections}

    selected = collect(sections)
    deficient = {s: EXPANDED_SEARCH_QUERIES.get(s, []) for s in sections
                 if not enough(s)}
    if deficient:
        selected = collect(deficient)
    print(f'[search] unique requests={len(cache)}, candidates=' + str({s: len(v) for s, v in selected.items()}), flush=True)
    return [item for section in sections for item in selected[section]]


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
