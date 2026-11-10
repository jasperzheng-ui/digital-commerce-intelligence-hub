"""Deterministic source exclusions and explicit manual background markers."""
import re
from urllib.parse import urlsplit, unquote


def background_requested(entry):
    explicit = str(entry.get('material_type', '')).strip().casefold()
    if explicit:
        return (explicit in {'background', '背景', '背景补充', '窗口外补充', '历史补充'}
                or explicit.startswith(('窗口外补充，', '窗口外补充,', '背景补充，', '背景补充,')))
    keywords = re.split(r'[,，、;；|\n]+', str(entry.get('keywords', '')).casefold())
    return any(word.strip() in {'background', '背景补充', '窗口外补充', '历史补充'} for word in keywords)


def auto_exclusion_reason(url, title=''):
    try:
        parsed = urlsplit(str(url or ''))
    except ValueError:
        return 'invalid_url'
    host = (parsed.hostname or '').casefold()
    path = unquote(parsed.path).casefold().rstrip('/')
    if (host == 'wikipedia.org' or host.endswith('.wikipedia.org')
            or host == 'wikidata.org' or host.endswith('.wikidata.org')
            or host in {'baike.baidu.com', 'baike.com', 'www.baike.com'}):
        return 'encyclopedia'
    # Locale roots are still homepages, not independent news articles.
    if not path or re.fullmatch(r'/(?:[a-z]{2}(?:-[a-z]{2})?|index\.(?:html?|php)|home)', path):
        return 'homepage'
    if re.fullmatch(r'/(?:[a-z]{2}(?:-[a-z]{2})?/)?(?:index|news|newsroom|blog|press|press-releases)', path):
        return 'article_index'
    if re.search(r'/(?:[a-z]{2}(?:-[a-z]{2})?/)?(?:about(?:-us|-alibaba)?|company|company-profile|our-company|company-history|corporate-profile)$', path):
        return 'company_profile'
    if (re.search(r'/(?:learn|learning|glossary|encyclopedia|wiki)(?:/|$)', path)
            or re.search(r'/what-is[-/]', path)
            or '/ways-to-search/' in path):
        return 'evergreen_or_product_guide'
    if re.search(r'(?:公司|集团|品牌).{0,8}(?:简介|介绍|上市历程|发展历程)$', str(title)):
        return 'company_profile'
    return ''
