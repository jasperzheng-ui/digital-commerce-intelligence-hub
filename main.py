from datetime import datetime
import json
import os

from config import (
    HTML_OUTPUT_PATH,
    MAX_ITEMS_FOR_GEMINI,
    MIN_SECTION_CANDIDATES,
    PREVIEW_DATA_PATH,
    PREVIEW_OUTPUT_PATH,
    PROJECT_NAME,
    SECTION_ORDER,
)


REPORT_MODES = {"preview", "manual_preview", "deploy_only", "publish"}


def collect_information_pool(search_cache=None, article_cache=None):
    from config import FEEDS, MANUAL_INPUT_PATH, SEARCH_QUERIES
    from sources.google_news import fetch_google_news_items
    from sources.manual import fetch_manual_items, validate_manual_source_mix
    from sources.rss import fetch_rss_items
    from sources.http_feed import enrich_items
    from intelligence.report_quality import eligible
    manual_items = fetch_manual_items(MANUAL_INPUT_PATH)
    validate_manual_source_mix(manual_items)
    rss = fetch_rss_items(FEEDS)  # Always runs, independently of manual count.
    automatic = enrich_items(prepare_information_pool(rss, limit=24), article_cache)
    items = [i for i in manual_items + automatic if eligible(i)]
    print(f'[collect] manual={len(manual_items)}, rss_filtered={len(rss)}, rss_readable={len(automatic)}, usable={len(items)}', flush=True)
    items.extend(fetch_google_news_items(SEARCH_QUERIES, existing_items=items,
                 cache=search_cache, article_cache=article_cache, wechat_needed=4))
    return prepare_information_pool(items)


def _item_key(item):
    from intelligence.report_quality import canonical_link
    link = canonical_link(item.get('link'))
    return ('link', link) if link else ('title', str(item.get('title', '')).strip().lower())



def prepare_information_pool(items, limit=MAX_ITEMS_FOR_GEMINI):
    from config import SECTION_ORDER
    pools = {s: [] for s in SECTION_ORDER}
    seen = set()
    for item in items:
        key = _item_key(item)
        if key in seen or not item.get('title') or not item.get('summary'):
            continue
        seen.add(key)
        pools.get(item.get('domain'), []).append(item)
    # Equal section capacity; alternate WeChat/other to preserve quota options.
    for s, pool in pools.items():
        ranked = sorted(pool, key=lambda i: (i.get('relevance_score', 0), i.get('published_date', '')), reverse=True)
        wechat = [i for i in ranked if i.get('source_type') == 'wechat']
        other = [i for i in ranked if i.get('source_type') != 'wechat']
        ordered = []
        while wechat or other:
            for group in (wechat, other):
                if group:
                    ordered.append(group.pop(0))
        pools[s] = ordered
    chosen = []
    while any(pools.values()) and len(chosen) < limit:
        for s in SECTION_ORDER:
            if pools[s] and len(chosen) < limit:
                chosen.append(pools[s].pop(0))
    return chosen


def build_empty_message():
    today = datetime.now().strftime("%Y-%m-%d")
    return (
        f"{PROJECT_NAME}\n"
        f"Date: {today}\n\n"
        "本期信息源未返回可用于分析的数字商业 / 电商情报。"
    )


def build_empty_dashboard_data():
    today = datetime.now().strftime("%Y-%m-%d")
    return {
        "date": today,
        "headline": "本期信息源未返回高置信度外部情报",
        "platform_intelligence": [],
        "ai_technology": [],
        "sports_outdoor": [],
        "retail_innovation": [],
        "one_thing_worth_watching": "本期信息源未返回高置信度外部情报，页面已正常更新。",
    }


def build_dashboard_notification(data, page_url):
    headline = data.get("headline") or data.get("one_thing_worth_watching") or "今日信号已更新"
    return (
        "Digital Commerce Intelligence 已更新\n"
        f"今日重点：{headline}\n"
        f"查看完整页面：{page_url}"
    )


def send_optional_feishu_test_message(data, page_url):
    if os.getenv("ENABLE_FEISHU_TEST") != "true":
        return
    from output.feishu import send_text_message

    send_text_message(build_dashboard_notification(data, page_url))


def get_report_mode():
    mode = (os.getenv("REPORT_MODE") or "publish").strip().lower()
    if mode not in REPORT_MODES:
        raise ValueError(f"REPORT_MODE must be one of {sorted(REPORT_MODES)}, got: {mode}")
    return mode


def get_dashboard_url(mode):
    configured_url = os.getenv("DASHBOARD_URL") or os.getenv("PAGES_URL")
    if configured_url:
        return configured_url

    base_url = (os.getenv("DASHBOARD_BASE_URL") or "").strip()
    if base_url:
        base_url = base_url.rstrip("/") + "/"
        if mode == "preview":
            return base_url + "preview/index.html"
        return base_url + "index.html"

    if mode == "preview":
        return "output/preview/index.html"
    return "output/index.html"


def generate_dashboard_data():
    from intelligence.gemini import generate_dashboard_data as generate_with_gemini
    from intelligence.report_quality import finalize_report
    from config import TARGET_SECTION_SIGNALS, EXPANDED_SEARCH_QUERIES, MIN_SECTION_CANDIDATES
    from sources.google_news import fetch_google_news_items
    from time import monotonic
    started = monotonic()
    search_cache, article_cache = {}, {}
    pool = collect_information_pool(search_cache, article_cache)
    generated = generate_with_gemini(pool) if pool else {'parse_warning': '没有可审核素材'}
    result = finalize_report(generated, pool)
    # One targeted supplementary batch after actual quality review; cache is shared.
    if pool and not generated.get('parse_warning'):
        from intelligence.gemini import _canonical_section_key
        gaps = [s for s in SECTION_ORDER if len(result[_canonical_section_key(s)]) < TARGET_SECTION_SIGNALS[s]]
        mix_gap = result['source_mix']['shortfall']
        if mix_gap:
            gaps = list(SECTION_ORDER)
        queries = {s: EXPANDED_SEARCH_QUERIES.get(s, [])[3:6] for s in gaps}
        if queries:
            extra = fetch_google_news_items(queries, existing_items=pool, cache=search_cache,
                article_cache=article_cache, targets={s: sum(i['domain']==s for i in pool)+3 for s in gaps},
                wechat_needed=6 if mix_gap else 0)
            if extra:
                # Preserve previously reviewed options while giving new candidates room.
                reviewed_links = {c['link'] for section in SECTION_ORDER for c in generated.get(_canonical_section_key(section), [])}
                base = [i for i in pool if i['link'] in reviewed_links]
                pool = prepare_information_pool(base + extra)
                result = finalize_report(generate_with_gemini(pool), pool)
    print(f'[report] {result["quality_status"]}, total={monotonic()-started:.1f}s', flush=True)
    return result


def save_preview_data(data):
    PREVIEW_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    PREVIEW_DATA_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_preview_data():
    if not PREVIEW_DATA_PATH.exists():
        return None
    return json.loads(PREVIEW_DATA_PATH.read_text(encoding="utf-8"))


def run_preview_mode():
    from output.email import send_brief_email
    from output.html import render_dashboard

    dashboard_data = generate_dashboard_data()
    render_dashboard(dashboard_data, PREVIEW_OUTPUT_PATH, archive_href="../archive/")
    save_preview_data(dashboard_data)

    page_url = get_dashboard_url("preview")
    send_brief_email(dashboard_data, page_url)
    send_optional_feishu_test_message(dashboard_data, page_url)
    print(f"Preview dashboard generated: {PREVIEW_OUTPUT_PATH}")


def validate_preview_data(data):
    """Validate editable draft structure without selection rules or AI calls."""
    if not isinstance(data, dict):
        raise ValueError("output/preview/data.json 必须是 JSON 对象。")
    try:
        datetime.strptime(data.get("date", ""), "%Y-%m-%d")
    except (TypeError, ValueError) as exc:
        raise ValueError("草稿 date 必须是有效的 YYYY-MM-DD 日期。") from exc
    total = 0
    for section in ("platform_intelligence", "ai_technology", "sports_outdoor", "retail_innovation"):
        cards = data.get(section)
        if not isinstance(cards, list):
            raise ValueError(f"{section} 必须是文章数组。")
        for card in cards:
            if not isinstance(card, dict):
                raise ValueError(f"{section} 中的文章必须是 JSON 对象。")
            title = card.get("title") or card.get("name")
            link = card.get("link")
            points = card.get("summary_points")
            if not isinstance(title, str) or not title.strip():
                raise ValueError(f"{section} 文章缺少标题。")
            if not isinstance(link, str) or not link.startswith(("https://", "http://")):
                raise ValueError(f"{section} 文章缺少有效链接。")
            if not isinstance(points, list) or not points or not all(isinstance(x, str) and x.strip() for x in points):
                raise ValueError(f"{section} 的 summary_points 必须是非空文本数组。")
            keywords = card.get("keywords", [])
            if not isinstance(keywords, list) or not all(isinstance(x, str) for x in keywords):
                raise ValueError(f"{section} 的 keywords 必须是文本数组。")
            total += 1
    if not total:
        raise ValueError("草稿没有文章，停止生成和发送空白周报。")
    if data.get("parse_warning"):
        raise ValueError("草稿含 parse_warning，请先检查并修正数据。")
    return data


def run_saved_preview_mode(send_email=False):
    """Render checked-in JSON; never collect, invoke AI, or publish archives."""
    from output.html import render_dashboard

    data = load_preview_data()
    if data is None:
        raise FileNotFoundError("缺少 output/preview/data.json，请先提交草稿 JSON。")
    validate_preview_data(data)
    render_dashboard(data, PREVIEW_OUTPUT_PATH, archive_href="../archive/")
    if send_email:
        from output.email import send_brief_email
        send_brief_email(data, get_dashboard_url("preview"))
    print(f"Saved preview rendered: {PREVIEW_OUTPUT_PATH}; email={send_email}")


def prepare_manual_publish(data):
    """Check file structure only; editorial selection belongs to Preview."""
    from intelligence.report_quality import report_shortfalls, source_mix
    if not isinstance(data, dict):
        raise ValueError("终稿必须是 JSON 对象，请检查 output/preview/data.json。")
    try:
        datetime.strptime(data.get("date", ""), "%Y-%m-%d")
    except (TypeError, ValueError) as exc:
        raise ValueError("终稿 date 必须是有效的 YYYY-MM-DD 日期。") from exc
    sections = ("platform_intelligence", "ai_technology",
                "sports_outdoor", "retail_innovation")
    for section in sections:
        cards = data.get(section)
        if not isinstance(cards, list):
            raise ValueError(f"终稿 {section} 必须是文章数组；空板块请填写 []。")
        for card in cards:
            if not isinstance(card, dict):
                raise ValueError(f"终稿 {section} 中的文章必须是 JSON 对象。")
            points = card.get("summary_points")
            if points is not None and (not isinstance(points, list)
                    or not all(isinstance(p, str) for p in points)):
                raise ValueError(f"终稿 {section} 的 summary_points 必须是文本数组。")
    # Refresh stale counters after manual deletion without enforcing quotas,
    # scores, freshness, review_version, or AI review fields.
    result = dict(data)
    result["source_mix"] = source_mix(result)
    result["quality_shortfalls"] = report_shortfalls(result)
    result["quality_status"] = "manually_approved"
    result["editorial_notice"] = ""
    result.pop("parse_warning", None)
    return result


def run_publish_mode():
    from output.archive import save_dashboard_history
    from output.email import send_brief_email
    from output.html import render_dashboard

    dashboard_data = load_preview_data()
    if dashboard_data is None:
        raise FileNotFoundError("缺少 output/preview/data.json，请先准备并审核终稿；Publish 不会重新采集或调用 AI。")
    else:
        print(f"Publishing reviewed preview data: {PREVIEW_DATA_PATH}")

    dashboard_data = prepare_manual_publish(dashboard_data)
    render_dashboard(dashboard_data, HTML_OUTPUT_PATH)
    save_dashboard_history(dashboard_data, HTML_OUTPUT_PATH.parent)
    save_preview_data(dashboard_data)

    page_url = get_dashboard_url("publish")
    send_brief_email(dashboard_data, page_url)
    send_optional_feishu_test_message(dashboard_data, page_url)
    print(f"Published dashboard generated: {HTML_OUTPUT_PATH}")


def main():
    mode = get_report_mode()
    if mode == "preview":
        run_preview_mode()
        return
    if mode in {"manual_preview", "deploy_only"}:
        run_saved_preview_mode(send_email=mode == "manual_preview")
        return
    run_publish_mode()


if __name__ == "__main__":
    main()

