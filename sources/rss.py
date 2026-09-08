import feedparser

from config import FILTER_PROFILES, RSS_ITEMS_PER_FEED, SEARCH_WINDOWS_DAYS
from sources.common import is_within_days, make_item, parse_date, should_keep_section_item


def fetch_rss_items(feeds):
    items = []

    from sources.http_feed import fetch_unique
    parsed_feeds = fetch_unique([feed['url'] for feed in feeds], {})
    for feed_config, parsed_feed in zip(feeds, parsed_feeds):
        source = feed_config["source"]
        section = feed_config.get("domain", "retail")
        profile = FILTER_PROFILES.get(section)
        if not profile:
            continue

        if parsed_feed is None:
            continue

        for entry in parsed_feed.entries[:RSS_ITEMS_PER_FEED]:
            title = entry.get("title", "")
            summary = entry.get("summary", "") or entry.get("description", "")

            published_date = parse_date(entry)
            if not is_within_days(published_date, max(SEARCH_WINDOWS_DAYS)):
                continue

            if not should_keep_section_item(title=title, summary=summary, profile=profile):
                continue

            items.append(
                make_item(
                    source=source,
                    title=title,
                    summary=summary,
                    link=entry.get("link", ""),
                    published_date=published_date,
                    domain=section,
                    origin_type="rss",
                    priority=1,
                    search_window_days=max(SEARCH_WINDOWS_DAYS),
                )
            )

    return items

