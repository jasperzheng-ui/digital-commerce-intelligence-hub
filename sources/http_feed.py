"""Fetch independent feeds concurrently, without a report/stage deadline."""
from concurrent.futures import ThreadPoolExecutor
import requests
import feedparser

NETWORK_WORKERS = 8


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


# Reuse the existing module for article verification; no new runtime dependency.
from html.parser import HTMLParser
from urllib.parse import urlparse, urljoin
import re
import json
from sources.editorial_policy import auto_exclusion_reason


class ArticleText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.skip = 0
        self.parts = []
        self.canonical = ''
        self.published = ''
        self.description = ''

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in {'script', 'style', 'nav', 'footer', 'noscript'}:
            self.skip += 1
        if tag == 'link' and 'canonical' in attrs.get('rel', '').split():
            self.canonical = attrs.get('href', '')
        if tag == 'meta':
            key = attrs.get('property') or attrs.get('name') or attrs.get('itemprop')
            if key in {'article:published_time', 'datePublished', 'pubdate', 'publishdate'}:
                self.published = attrs.get('content', '')
            if key in {'description', 'og:description'}:
                self.description = attrs.get('content', '')
        if tag == 'time' and attrs.get('itemprop') == 'datePublished':
            self.published = attrs.get('datetime', '') or self.published

    def handle_endtag(self, tag):
        if tag in {'script', 'style', 'nav', 'footer', 'noscript'} and self.skip:
            self.skip -= 1
        if tag in {'p', 'div', 'section', 'article', 'h1', 'h2', 'li'}:
            self.parts.append('\n')

    def handle_data(self, text):
        if not self.skip:
            self.parts.append(text)


def _jsonld_publication(text):
    def article_date(value):
        if isinstance(value, list):
            for item in value:
                found = article_date(item)
                if found:
                    return found
        if isinstance(value, dict):
            types = value.get('@type', [])
            types = types if isinstance(types, list) else [types]
            if any(str(t).split('/')[-1] in {'Article', 'NewsArticle', 'BlogPosting', 'Report', 'TechArticle'} for t in types):
                if isinstance(value.get('datePublished'), str):
                    return value['datePublished']
            return article_date(value.get('@graph', []))
        return ''
    for block in re.findall(r'<script\b[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', text, re.S | re.I):
        try:
            found = article_date(json.loads(block))
            if found:
                return found
        except (ValueError, TypeError):
            continue
    return ''


def fetch_article(url):
    """Read public HTML and follow normal redirects; never bypass access controls."""
    try:
        reason = auto_exclusion_reason(url)
        if reason:
            print(f'[source reject] {reason}: {url}', flush=True)
            return None
        response = requests.get(url, timeout=(5, 20), headers={'User-Agent': 'WeeklyIntelligence/1.0'})
        response.raise_for_status()
        if 'html' not in response.headers.get('Content-Type', '').lower():
            return None
        if response.encoding in {None, 'ISO-8859-1'}:
            response.encoding = response.apparent_encoding
        parser = ArticleText()
        body = re.search(r'<article\b[^>]*>(.*?)</article>', response.text, flags=re.S | re.I)
        parser.feed(response.text)
        parser.published = parser.published or _jsonld_publication(response.text)
        if body:
            body_parser = ArticleText()
            body_parser.feed(body.group(1))
            if len(''.join(body_parser.parts)) > 300:
                parser.parts = body_parser.parts
        link = response.url
        reason = auto_exclusion_reason(link)
        if reason:
            print(f'[source reject] {reason}: {link}', flush=True)
            return None
        canonical = urljoin(link, parser.canonical)
        # An unresolved Google redirect is not a publisher article.
        if urlparse(link).hostname == 'news.google.com':
            if parser.canonical and urlparse(canonical).hostname not in {'news.google.com', 'www.google.com'}:
                return fetch_article(canonical) if urlparse(canonical).scheme in {'http', 'https'} else None
            return None
        text = '\n'.join(line.strip() for line in ''.join(parser.parts).splitlines() if line.strip())
        if len(text) < 300 or any(x in text[:1500].lower() for x in
                                  ('verify you are human', 'enable javascript and cookies', '环境异常', '访问过于频繁', '完成验证', '该内容已被发布者删除', 'captcha', '访问验证')):
            return None
        return {'link': link, 'text': text[:6000], 'published': parser.published}
    except (requests.RequestException, ValueError, RecursionError):
        return None


def enrich_items(items, cache=None):
    """Only full-content automatic candidates enter the model's review pool."""
    from sources.common import coerce_datetime
    cache = cache if cache is not None else {}
    urls = list(dict.fromkeys(i['link'] for i in items if i.get('link') and i['link'] not in cache))
    with ThreadPoolExecutor(max_workers=NETWORK_WORKERS) as executor:
        for url, content in zip(urls, executor.map(fetch_article, urls)):
            cache[url] = content
    results = []
    for item in items:
        article = cache.get(item.get('link'))
        if not article:
            continue
        reason = auto_exclusion_reason(article['link'], item.get('title', ''))
        if reason:
            print(f'[source reject] {reason}: {article["link"]}', flush=True)
            continue
        item = dict(item)
        item['link'] = article['link']
        item['provenance_url'] = article['link']
        item['summary'] = article['text']
        item['content_verified'] = True
        if item.get('source') in {'news.google.com', 'www.bing.com', 'Web source'}:
            item['source'] = urlparse(item['link']).hostname
        parsed = coerce_datetime(article.get('published'))
        if parsed:
            item['published_date'] = parsed.isoformat()
            item['publication_date_basis'] = 'publisher_metadata'
        elif item.get('origin_type') == 'rss' and coerce_datetime(item.get('published_date')):
            item['publication_date_basis'] = 'publisher_rss'
        else:
            print(f'[source reject] unverified_publication_date: {item["link"]}', flush=True)
            continue
        item['publication_date_verified'] = True
        item['source_type'] = 'wechat' if urlparse(item['link']).hostname == 'mp.weixin.qq.com' else 'other'
        results.append(item)
    print(f'[content] attempted={len(items)}, readable={len(results)}, unreadable={len(items)-len(results)}', flush=True)
    return results

