"""Preserve editorial quality and email metadata without execution deadlines."""
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import urlparse

from config import BASE_DIR, MANUAL_INPUT_PATH, MIN_SECTION_SIGNALS, SECTION_ORDER
from intelligence.gemini import normalize_dashboard_data, _canonical_section_key, _fallback_card_from_item

RD_TITLES = ('benchmark', 'leaderboard', 'model release', 'training method',
             '模型发布', '模型参数', '排行榜', '训练方法', '推理框架', '芯片', '研发', '研究论文')
APPLICATION_WORDS = ('购物', '客服', '库存', '订单', '销售', '门店', '供应链', '工作流',
                     '办公', '营销', '商品', 'shopping', 'customer service', 'workflow', 'inventory')


def original_link(value):
    parsed = urlparse(str(value or '').strip())
    return parsed.scheme in {'http', 'https'} and bool(parsed.hostname) and parsed.hostname != 'news.google.com'


def eligible(item, today=None):
    if not item.get('title') or not item.get('summary') or not original_link(item.get('link')):
        return False
    try:
        day = datetime.fromisoformat(str(item.get('published_date', '')).replace('Z', '+00:00')).date()
    except ValueError:
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
    return item.get('origin_type') == 'manual' and eligible(item)


def attach_metadata(card, item):
    for key in ('category', 'keywords', 'company', 'date'):
        value = item.get(key)
        if value:
            card[key] = value
    card['source'] = item.get('source', '')
    card.setdefault('date', str(item.get('published_date', ''))[:10])


def finalize_report(data, items):
    normalized = normalize_dashboard_data(data or {})
    normalized['date'] = datetime.now(timezone.utc).date().isoformat()
    by_link = {item['link']: item for item in items if eligible(item)}
    used = set()
    for domain in SECTION_ORDER:
        key = _canonical_section_key(domain)
        accepted = []
        for card in normalized[key]:
            link = card.get('link', '')
            item = by_link.get(link)
            if not item or link in used or not card.get('summary_points'):
                continue
            # Keep explicit editorial classification stable, even if Gemini moves it.
            if item.get('origin_type') == 'manual' and item.get('domain') != domain:
                continue
            if domain == 'ai' and not eligible(dict(item, domain='ai')):
                continue
            attach_metadata(card, item)
            accepted.append(card)
            used.add(link)
        normalized[key] = accepted
    supplemented = False
    for domain in SECTION_ORDER:
        key = _canonical_section_key(domain)
        for item in items:
            if item.get('domain') != domain or not manual_fallback_allowed(item) or item['link'] in used:
                continue
            if len(normalized[key]) >= 8:
                break
            card = _fallback_card_from_item(domain, item)
            attach_metadata(card, item)
            normalized[key].append(card)
            used.add(item['link'])
            supplemented = True
    if supplemented:
        normalized['editorial_notice'] = '部分或全部摘要直接采用已审核的人工素材，请在publish前核对。'
    if not data or data.get('parse_warning'):
        normalized['headline'] = 'AI生成未完成，本期采用人工素材备用摘要'
        normalized['parse_warning'] = (data or {}).get('parse_warning') or 'AI generation failed; manual source fallback.'
    shortfalls = report_shortfalls(normalized)
    normalized['quality_status'] = 'incomplete' if shortfalls else 'ready_for_review'
    normalized['quality_shortfalls'] = shortfalls
    return normalized


def report_shortfalls(data):
    return {domain: len({c.get('link') for c in data.get(_canonical_section_key(domain), [])
                        if original_link(c.get('link')) and c.get('summary_points')})
            for domain, minimum in MIN_SECTION_SIGNALS.items()
            if len({c.get('link') for c in data.get(_canonical_section_key(domain), [])
                    if original_link(c.get('link')) and c.get('summary_points')}) < minimum}


def validate_report(data):
    # Validate the normalized shape without discarding explicit email metadata.
    shortages = report_shortfalls(normalize_dashboard_data(data))
    if shortages:
        raise ValueError(f'发布中止，每类至少两篇；缺口={shortages}。补充合格素材并重新preview。')


