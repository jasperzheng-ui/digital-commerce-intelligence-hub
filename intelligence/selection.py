"""Select at most 30 distinct sources across the overview and four sections."""
from datetime import date
from urllib.parse import urlsplit

from config import MAX_REPORT_SOURCES
from intelligence.gemini import SECTION_ALIASES
from intelligence.report_quality import canonical_link


def select_report_sources(data, research):
    """Prefer recent quality, then balance available editorial directions.

    Selection happens after candidate review and before synthesis. Reviewed
    complementary reports remain independent sources and may be merged later.
    """
    report_date = date.fromisoformat(data['date'])
    candidates = []
    for section in SECTION_ALIASES:
        for card in data.get(section, []):
            candidates.append({
                'section': section, 'item': card, 'url': canonical_link(card['link']),
                'date': card['date'], 'score': card['quality_score'],
                'bucket': (section, card.get('subcategory', 'unclassified')),
                'topic': card.get('topic', ''),
            })
    for item in research.get('sources', []):
        candidates.append({
            'section': 'overview', 'item': item, 'url': canonical_link(item['url']),
            'date': item['date'], 'score': 85,
            'bucket': ('overview', item.get('subcategory', 'overview')),
            'topic': '',
        })
    def rank(candidate):
        age = (report_date - date.fromisoformat(candidate['date'])).days
        return (candidate['score'] + (10 if age <= 6 else 0), candidate['date'])

    candidates.sort(key=rank, reverse=True)
    chosen_urls, selected, coverage = set(), [], set()
    # First retain one quality source for each available section/ecosystem/origin.
    for candidate in candidates:
        if candidate['bucket'] in coverage or candidate['url'] in chosen_urls:
            continue
        if len(chosen_urls) >= MAX_REPORT_SOURCES:
            break
        selected.append(candidate)
        chosen_urls.add(candidate['url'])
        coverage.add(candidate['bucket'])
    # Among remaining sources prefer new topics before repeating a direction.
    covered_topics = {(c['bucket'], c['topic']) for c in selected}
    remainder = [c for c in candidates if c['url'] not in chosen_urls]
    while remainder and len(chosen_urls) < MAX_REPORT_SOURCES:
        best = max(remainder, key=lambda c: (
            rank(c)[0] + (5 if (c['bucket'], c['topic']) not in covered_topics else 0),
            c['date']))
        selected.append(best)
        chosen_urls.add(best['url'])
        covered_topics.add((best['bucket'], best['topic']))
        remainder = [c for c in remainder if c['url'] != best['url']]
    result = dict(data)
    # A source can be retained by the overview or one news section, never twice.
    ownership = {c['url']: c['section'] for c in selected}
    for section in SECTION_ALIASES:
        result[section] = [c for c in data.get(section, [])
                           if ownership.get(canonical_link(c['link'])) == section]
    result['rejected_candidates'] = list(data.get('rejected_candidates', []))
    for candidate in candidates:
        if candidate['section'] != 'overview' and candidate['url'] not in chosen_urls:
            result['rejected_candidates'].append({
                'link': candidate['item']['link'], 'reason': '全局质量、时效与方向平衡精选',
            })
    bundle = dict(research, sources=[c['item'] for c in selected if c['section'] == 'overview'])
    result['source_mix'] = {
        'total': len(chosen_urls),
        'wechat': sum(urlsplit(url).hostname == 'mp.weixin.qq.com' for url in chosen_urls),
        'required_wechat': 0, 'shortfall': 0,
    }
    return result, bundle
