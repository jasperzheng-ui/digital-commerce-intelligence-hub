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


REPORT_MODES = {"preview", "publish"}


def collect_information_pool():
    from config import FEEDS, MANUAL_INPUT_PATH, SEARCH_QUERIES
    from sources.google_news import fetch_google_news_items
    from sources.manual import fetch_manual_items
    from sources.rss import fetch_rss_items

    items = []
    items.extend(fetch_manual_items(MANUAL_INPUT_PATH))
    items.extend(fetch_rss_items(FEEDS))
    items.extend(fetch_google_news_items(SEARCH_QUERIES))
    return prepare_information_pool(items)


def prepare_information_pool(items, limit=MAX_ITEMS_FOR_GEMINI):
    cleaned_items = []
    seen = set()

    for item in items:
        title = item.get("title", "").strip()
        summary = item.get("summary", "").strip()

        if not title or not summary:
            continue

        dedupe_key = (title.lower(), item.get("link", "").strip())
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        cleaned_items.append(item)

    section_rank = {section: index for index, section in enumerate(SECTION_ORDER)}
    cleaned_items.sort(
        key=lambda item: (
            item.get("priority", 1),
            -section_rank.get(item.get("domain", "retail"), len(section_rank)),
            -(item.get("search_window_days") or 0),
            item.get("published_date", ""),
        ),
        reverse=True,
    )

    selected_items = []
    selected_keys = set()

    manual_items = [item for item in cleaned_items if item.get("origin_type") == "manual"]
    for item in manual_items:
        if len(selected_items) >= limit:
            break
        key = (item.get("title", "").lower(), item.get("link", "").strip())
        if key in selected_keys:
            continue
        selected_keys.add(key)
        selected_items.append(item)

    for section in SECTION_ORDER:
        minimum = MIN_SECTION_CANDIDATES.get(section, 0)
        section_items = [item for item in cleaned_items if item.get("domain") == section]
        for item in section_items[:minimum]:
            key = (item.get("title", "").lower(), item.get("link", "").strip())
            if key in selected_keys:
                continue
            selected_keys.add(key)
            selected_items.append(item)

    for item in cleaned_items:
        if len(selected_items) >= limit:
            break
        key = (item.get("title", "").lower(), item.get("link", "").strip())
        if key in selected_keys:
            continue
        selected_keys.add(key)
        selected_items.append(item)

    return selected_items[:limit]


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

    information_pool = collect_information_pool()
    if not information_pool:
        return build_empty_dashboard_data()
    return generate_with_gemini(information_pool)


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


def run_publish_mode():
    from output.archive import save_dashboard_history
    from output.email import send_brief_email
    from output.html import render_dashboard

    dashboard_data = load_preview_data()
    if dashboard_data is None:
        print("No preview data found. Generating a fresh publish version.")
        dashboard_data = generate_dashboard_data()
    else:
        print(f"Publishing reviewed preview data: {PREVIEW_DATA_PATH}")

    render_dashboard(dashboard_data, HTML_OUTPUT_PATH)
    save_dashboard_history(dashboard_data, HTML_OUTPUT_PATH.parent)

    page_url = get_dashboard_url("publish")
    send_brief_email(dashboard_data, page_url)
    send_optional_feishu_test_message(dashboard_data, page_url)
    print(f"Published dashboard generated: {HTML_OUTPUT_PATH}")


def main():
    mode = get_report_mode()
    if mode == "preview":
        run_preview_mode()
        return
    run_publish_mode()


if __name__ == "__main__":
    main()
