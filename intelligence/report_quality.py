"""Editorial selection and publish gates; no report deadline or automatic filler."""
from datetime import datetime, timezone, timedelta
from math import ceil
import re
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse
from config import (MIN_SECTION_SIGNALS, SECTION_ORDER, MIN_WECHAT_SHARE,
                    MIN_QUALITY_SCORE, MAX_SECTION_SIGNALS)
from intelligence.gemini import normalize_dashboard_data, _canonical_section_key

RD_TITLES = ('benchmark', 'leaderboard', 'model release', 'training method',
             '模型发布', '模型参数', '排行榜', '训练方法', '推理框架', '芯片', '研发', '研究论文')
APPLICATION_WORDS = ('购物', '客服', '库存', '订单', '销售', '门店', '供应链', '工作流',
                     '办公', '营销', '商品', 'shopping', 'customer service', 'workflow', 'inventory')


def canonical_link(value):
    p = urlparse(str(value or '').strip())
    query = [(k, v) for k, v in parse_qsl(p.query, keep_blank_values=True)
             if not k.startswith('utm_') and k not in {'scene', 'xtrack', 'chksm', 'from', 'isappinstalled'}]
    return urlunparse((p.scheme, p.netloc.lower(), p.path.rstrip('/'), '', urlencode(sorted(query)), ''))


def original_link(value):
    p = urlparse(str(value or '').strip())
    return p.scheme in {'http', 'https'} and bool(p.hostname) and p.hostname not in {'news.google.com', 'www.bing.com'}


def eligible(item, today=None):
    if not item.get('title') or not item.get('summary') or not original_link(item.get('link')):
        return False
    try:
        day = datetime.fromisoformat(str(item.get('published_date', '')).replace('Z', '+00:00')).date()
    except (TypeError, ValueError):
        return False
    today = today or datetime.now(timezone.utc).date()
    if not today - timedelta(days=14) <= day <= today:
        return False
    if item.get('domain') == 'ai':
        title = item['title'].lower()
        text = (title + ' ' + item['summary']).lower()
        if any(word in title for word in RD_TITLES) or not any(word in text for word in APPLICATION_WORDS):
            return False
    return True


def manual_fallback_allowed(item):
    return False  # Missing model review must not silently promote manual material.


def attach_metadata(card, item):
    for key in ('company', 'keywords'):
        if not card.get(key) and item.get(key):
            card[key] = item[key]
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


def _wechat(card):
    return card.get('source_type') == 'wechat'


def source_mix(data):
    cards = _cards(data)
    count = sum(_wechat(c) for c in cards)
    required = ceil(len(cards) * MIN_WECHAT_SHARE)
    return {'total': len(cards), 'wechat': count, 'required_wechat': required,
            'shortfall': max(0, required - count)}


def report_shortfalls(data):
    return {s: {'actual': len(data.get(_canonical_section_key(s), [])), 'required': minimum}
            for s, minimum in MIN_SECTION_SIGNALS.items()
            if len(data.get(_canonical_section_key(s), [])) < minimum}


def finalize_report(data, items):
    normalized = normalize_dashboard_data(data or {})
    normalized['date'] = datetime.now(timezone.utc).date().isoformat()
    by_link = {canonical_link(i['link']): i for i in items if eligible(i)}
    candidates, used_links, used_events = [], set(), set()
    for domain in SECTION_ORDER:
        for card in normalized[_canonical_section_key(domain)]:
            item = by_link.get(canonical_link(card.get('link')))
            points = card.get('summary_points', [])
            if (not item or item.get('domain') != domain or _score(card) < MIN_QUALITY_SCORE
                    or not card.get('quality_reason') or not card.get('event_key')
                    or not 3 <= len(points) <= 6 or not all(isinstance(p, str) and p.strip() for p in points)):
                continue
            if item.get('origin_type') != 'manual' and not item.get('content_verified'):
                continue
            card['link'] = item['link']
            card['quality_score'] = _score(card)
            card['review_status'] = 'accepted'
            attach_metadata(card, item)
            candidates.append(card)
    candidates.sort(key=lambda c: (_score(c), _wechat(c)), reverse=True)
    pools = {s: [] for s in SECTION_ORDER}
    for card in candidates:
        link = canonical_link(card['link'])
        event = re.sub(r'\s+', '', str(card['event_key'])).casefold()
        if link in used_links or event in used_events:
            continue
        used_links.add(link)
        used_events.add(event)
        pools[card['category']].append(card)
    selected = {s: pool[:MAX_SECTION_SIGNALS] for s, pool in pools.items()}
    # Swap qualifying alternatives before reducing article counts to meet the share.
    def deficit():
        cards = [c for v in selected.values() for c in v]
        return ceil(len(cards) * MIN_WECHAT_SHARE) - sum(_wechat(c) for c in cards)
    while deficit() > 0:
        swaps = []
        for s in SECTION_ORDER:
            unused = [c for c in pools[s] if _wechat(c) and c not in selected[s]]
            other = [c for c in selected[s] if not _wechat(c)]
            if unused and other:
                incoming, outgoing = unused[0], min(other, key=_score)
                swaps.append((_score(incoming) - _score(outgoing), s, incoming, outgoing))
        if swaps:
            _, s, incoming, outgoing = max(swaps, key=lambda x: x[0])
            selected[s].remove(outgoing)
            selected[s].append(incoming)
            continue
        removable = [(s, c) for s in SECTION_ORDER if len(selected[s]) > MIN_SECTION_SIGNALS[s]
                     for c in selected[s] if not _wechat(c)]
        if not removable:
            break
        s, card = min(removable, key=lambda pair: _score(pair[1]))
        selected[s].remove(card)
    for s in SECTION_ORDER:
        normalized[_canonical_section_key(s)] = sorted(selected[s], key=_score, reverse=True)
    normalized['review_version'] = 2
    normalized['quality_shortfalls'] = report_shortfalls(normalized)
    normalized['source_mix'] = source_mix(normalized)
    incomplete = bool(normalized['quality_shortfalls'] or normalized['source_mix']['shortfall'] or normalized.get('parse_warning'))
    normalized['quality_status'] = 'incomplete' if incomplete else 'ready_for_review'
    normalized['editorial_notice'] = (
        f"本期尚未达到发布条件。板块缺口：{normalized['quality_shortfalls']}；"
        f"公众号：{normalized['source_mix']['wechat']}/{normalized['source_mix']['total']}，"
        f"至少需要{normalized['source_mix']['required_wechat']}篇。请补充合格素材后重新Preview。"
        if incomplete else '')
    if normalized.get('parse_warning'):
        normalized['headline'] = 'AI审核未完成，本期暂不可发布'
    print('[selection] ' + str({'sections': {s: len(selected[s]) for s in SECTION_ORDER},
                              'sources': normalized['source_mix'],
                              'origins': {o: sum(c.get('origin_type') == o for c in _cards(normalized))
                                          for o in ('manual', 'rss', 'google_news')},
                              'model_rejections': normalized.get('rejected_candidates', [])}), flush=True)
    return normalized


def validate_report(data):
    normalized = normalize_dashboard_data(data)
    shortages = report_shortfalls(normalized)
    cards = _cards(normalized)
    if normalized.get('review_version') != 2 or normalized.get('parse_warning'):
        raise ValueError('请先按新规则运行Preview并审核，旧预览或AI审核失败的数据不能直接Publish。')
    if shortages or any(len(normalized[_canonical_section_key(s)]) > MAX_SECTION_SIGNALS for s in SECTION_ORDER):
        raise ValueError(f'发布中止：每类要求3-5篇，缺口={shortages}')
    if source_mix(normalized)['shortfall']:
        raise ValueError(f'发布中止：公众号至少占一半，当前={source_mix(normalized)}')
    links, events = set(), set()
    for c in cards:
        link = canonical_link(c.get('link'))
        event = re.sub(r'\s+', '', str(c.get('event_key', ''))).casefold()
        item = dict(title=c.get('title') or c.get('name'), summary=' '.join(c.get('summary_points', [])),
                    link=c.get('link'), published_date=c.get('date'), domain=c.get('category'))
        if (c.get('review_status') != 'accepted' or _score(c) < MIN_QUALITY_SCORE
                or not c.get('quality_reason') or not event or not eligible(item)
                or not 3 <= len(c.get('summary_points', [])) <= 6 or c.get('source_type') not in {'wechat', 'other'}
                or link in links or event in events):
            raise ValueError('发布中止：文章审核字段、时效性或去重检查未通过，请重新Preview。')
        links.add(link)
        events.add(event)
