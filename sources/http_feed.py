"""Fetch independent feeds concurrently, without a report/stage deadline."""
from concurrent.futures import ThreadPoolExecutor
import requests
import feedparser

NETWORK_WORKERS = 6


def fetch_feed(url):
    # Connection/read inactivity protection only, not a report completion deadline.
    # Retry a failed read once; never silently treat a failed fetch as an empty feed.
    for attempt in range(2):
        try:
            response = requests.get(url, timeout=(5, 30), headers={'User-Agent': 'WeeklyIntelligence/1.0'})
            response.raise_for_status()
            parsed = feedparser.parse(response.content)
            if parsed.get('bozo') and not parsed.entries:
                raise ValueError('Invalid feed response')
            return parsed
        except (requests.RequestException, ValueError) as exc:
            if attempt == 1:
                print(f'[fetch failed] {url}: {type(exc).__name__}', flush=True)
                return None


def fetch_unique(urls, cache):
    missing = list(dict.fromkeys(url for url in urls if url not in cache))
    with ThreadPoolExecutor(max_workers=NETWORK_WORKERS) as executor:
        for url, result in zip(missing, executor.map(fetch_feed, missing)):
            cache[url] = result
    return [cache[url] for url in urls]
