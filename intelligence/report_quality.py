"""Source quality and deduplication without article counts or source-share quotas."""
from datetime import datetime, timezone, timedelta
import re
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse
from config import MIN_QUALITY_SCORE, SECTION_ORDER
from intelligence.gemini import normalize_dashboard_data, _canonical_section_key


def canonical_link(value):
    p = urlparse(str(value or '').strip())
    query = [(k, v) for k, v in parse_qsl(p.query, keep_blank_values=True)
             if not k.startswith('utm_') and k not in {'scene', 'xtrack', 'chksm', 'from', 'isappinstalled'}]
    return urlunparse((p.scheme, p.netloc.lower(), p.path.rstrip('/'), '', urlencode(sorted(query)), ''))


def original_link(value):
    from output.digest import safe_url
    return safe_url(value)


def eligible(item, today=None):
    if not item.get('title') or not item.get('summary') or not original_link(item.get('link')):
        return False
    try:
        day = datetime.fromisoformat(str(item.get('published_date', '')).replace('Z', '+00:00')).date()
    except (TypeError, ValueError):
        return False
    today = today or datetime.now(timezone.utc).date()
    return today - timedelta(days=14) <= day <= today


def manual_fallback_allowed(item):
    return False


def attach_metadata(card, item):
    from output.digest import infer_subcategory
    for key in ('company', 'keywords'):
        if not card.get(key) and item.get(key):
            card[key] = item[key]
    if item.get('subcategory'):
        card['subcategory'] = item['subcategory']
    section = _canonical_section_key(item['domain'])
    card['subcategory'] = infer_subcategory(section, card)
    card.update(category=item['domain'], date=str(item.get('published_date', ''))[:10],
                source=re.sub(r'^Manual Input\s*-\s*', '', item.get('source', ''), flags=re.I),
                origin_type=item.get('origin_type', ''), source_type=item.get('source_type', 'other'),
                provenance_url=item.get('provenance_url') or item['link'])


def _score(card):
    try:
        return max(0, min(100, int(card.get('quality_score', 0))))
    except (TypeError, ValueError):
        return 0


def _cards(data):
    return [c for s in SECTION_ORDER for c in data.get(_canonical_section_key(s), [])]


def source_mix(data):
    from output.digest import references
    by_link = {}
    for card in _cards(data):
        for ref in references(card):
            by_link[canonical_link(ref['link'])] = ref['link']
    wechat = sum(urlparse(url).hostname == 'mp.weixin.qq.com' for url in by_link.values())
    return {'total': len(by_link), 'wechat': wechat, 'required_wechat': 0, 'shortfall': 0}


def report_shortfalls(data):
    return {}  # Empty sections are allowed; no filling or article-count gate.


def finalize_report(data, items):
    normalized = normalize_dashboard_data(data or {})
    normalized['date'] = datetime.now(timezone.utc).date().isoformat()
    by_link = {canonical_link(i['link']): i for i in items if eligible(i)}
    rejected = list(normalized.get('rejected_candidates', []))
    candidates = []
    for domain in SECTION_ORDER:
        for card in normalized[_canonical_section_key(domain)]:
            item = by_link.get(canonical_link(card.get('link')))
            points = card.get('summary_points', [])
            valid = (item and item.get('domain') == domain and _score(card) >= MIN_QUALITY_SCORE
                     and card.get('quality_reason') and card.get('event_key') and points
                     and all(isinstance(p, str) and p.strip() for p in points)
                     and (item.get('origin_type') == 'manual' or item.get('content_verified')))
            if not valid:
                rejected.append({'link': card.get('link', ''), 'reason': '正文、来源、分类或审核证据未通过校验'})
                continue
            card['link'] = item['link']
            card['quality_score'] = _score(card)
            card['review_status'] = 'accepted'
            attach_metadata(card, item)
            candidates.append(card)
    selected = {domain: [] for domain in SECTION_ORDER}
    links, events = set(), set()
    for card in sorted(candidates, key=_score, reverse=True):
        link = canonical_link(card['link'])
        event = re.sub(r'\s+', '', str(card['event_key'])).casefold()
        if link in links or event in events:
            rejected.append({'link': card['link'], 'reason': '同一原文或同一事件的重复报道'})
            continue
        links.add(link)
        events.add(event)
        selected[card['category']].append(card)
    for domain in SECTION_ORDER:
        normalized[_canonical_section_key(domain)] = selected[domain]
    normalized.update(review_version=3, quality_shortfalls={}, source_mix=source_mix(normalized),
                      quality_status='ready_for_review' if links else 'empty',
                      rejected_candidates=rejected, editorial_notice='')
    if normalized.get('parse_warning'):
        normalized['quality_status'] = 'incomplete'
        normalized['editorial_notice'] = 'AI审核未完成，请重新Preview。'
    print('[selection] ' + str({s: len(v) for s, v in selected.items()}), flush=True)
    return normalized


def validate_report(data):
    from output.digest import validate_digest
    if data.get('parse_warning'):
        raise ValueError('AI审核未完成，请检查草稿。')
    validate_digest(data)

