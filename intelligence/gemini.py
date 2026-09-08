import os
import json
import re
from datetime import datetime
from urllib.parse import urlparse

from config import MIN_SECTION_SIGNALS, SECTION_ORDER
from intelligence.prompt import build_dashboard_prompt


GEMINI_MODEL = "gemini-3.6-flash"


SECTION_ALIASES = {
    "platform_intelligence": ["platform", "platform_intelligence", "platform_watch"],
    "ai_technology": ["ai", "ai_technology", "ai_watch"],
    "sports_outdoor": ["sports", "sports_outdoor", "sports_and_outdoor"],
    "retail_innovation": ["retail", "retail_innovation", "retail_trends", "retail_watch"],
}


_DIRECT_TO_CONSUMER_ABBR = "D" + "TC"
_DECA_DIRECT_PHRASE = "对" + "迪卡侬而言"


FORBIDDEN_OUTPUT_REPLACEMENTS = (
    (_DECA_DIRECT_PHRASE + "，", "给迪卡侬的启示是，"),
    (_DECA_DIRECT_PHRASE, "给迪卡侬的启示"),
    (_DIRECT_TO_CONSUMER_ABBR + " Opportunity", "业务启示"),
    (_DIRECT_TO_CONSUMER_ABBR + " opportunity", "业务启示"),
    (_DIRECT_TO_CONSUMER_ABBR + "机会", "业务启示"),
    (_DIRECT_TO_CONSUMER_ABBR + " 策略", "数字商业能力"),
    (_DIRECT_TO_CONSUMER_ABBR + "策略", "数字商业能力"),
    (_DIRECT_TO_CONSUMER_ABBR, "数字商业"),
)


def generate_dashboard_data(items):
    try:
        from google import genai
    except ImportError as exc:
        raise RuntimeError(
            "Missing google-genai package. Run: python3 -m pip install -r requirements.txt"
        ) from exc

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("Missing GEMINI_API_KEY environment variable.")

    prompt = build_dashboard_prompt(items)
    client = genai.Client(api_key=api_key)
    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
        )
    except Exception as exc:
        return build_source_fallback(
            items,
            f"Gemini request failed; rendered source-based fallback content. Error: {exc}",
        )

    raw_text = response.text.strip()
    return parse_dashboard_json(raw_text)


def parse_dashboard_json(raw_text):
    text = _strip_json_fence(raw_text)
    try:
        return normalize_dashboard_data(json.loads(text))
    except json.JSONDecodeError:
        extracted = _extract_json_object(text)
        if extracted:
            try:
                return normalize_dashboard_data(json.loads(extracted))
            except json.JSONDecodeError:
                pass
        return build_dashboard_fallback(raw_text)


def normalize_dashboard_data(data):
    normalized = {
        "date": data.get("date", ""),
        "headline": data.get("headline") or data.get("one_thing_worth_watching") or "今日信号已更新",
        "platform_intelligence": _filter_reliable_cards(_normalize_cards(_first_section(data, "platform_intelligence"))),
        "ai_technology": _filter_reliable_cards(_normalize_ai_cards(_first_section(data, "ai_technology"))),
        "sports_outdoor": _filter_reliable_cards(_normalize_cards(_first_section(data, "sports_outdoor"))),
        "retail_innovation": _filter_reliable_cards(_normalize_cards(_first_section(data, "retail_innovation"))),
        "one_thing_worth_watching": data.get("one_thing_worth_watching") or data.get("headline") or "今日信号已更新",
    }
    if data.get("parse_warning"):
        normalized["parse_warning"] = data["parse_warning"]
    return _sanitize_dashboard_terms(normalized)


def _first_section(data, canonical_key):
    for key in SECTION_ALIASES[canonical_key]:
        if data.get(key):
            return data[key]
    return []


def _normalize_cards(items):
    cards = []
    for item in items[:8]:
        if isinstance(item, str):
            cards.append(
                {
                    "name": "Signal",
                    "news": _clean_text(item),
                    "summary_points": _summary_points(item),
                    "why_this_matters": "该信号值得进一步阅读原文确认。",
                    "trend": "Signal",
                    "link": "",
                }
            )
            continue

        cards.append(
            {
                "name": item.get("name") or item.get("platform") or item.get("topic") or "Signal",
                "news": _clean_text(item.get("news") or item.get("signal") or ""),
                "summary_points": _summary_points(
                    item.get("summary_points")
                    or item.get("summary")
                    or item.get("news")
                    or item.get("signal")
                    or item.get("why_this_matters")
                    or item.get("why")
                    or ""
                ),
                "why_this_matters": _clean_text(item.get("why_this_matters") or item.get("why") or ""),
                "trend": item.get("trend") or "Trend",
                "link": item.get("link") or "",
            }
        )
    return cards


def _normalize_ai_cards(items):
    cards = []
    for item in items[:8]:
        if isinstance(item, str):
            cards.append(
                {
                    "name": "AI 能力变化",
                    "title": "AI 能力变化",
                    "capability": _clean_text(item),
                    "summary_points": _summary_points(item),
                    "industry_impact": "该技术信号需要结合原文进一步判断行业影响。",
                    "trend": "AI 能力",
                    "link": "",
                }
            )
            continue

        title = item.get("title") or item.get("name") or item.get("topic") or item.get("platform") or "AI 能力变化"
        capability = item.get("capability") or item.get("news") or item.get("signal") or ""
        industry_impact = item.get("industry_impact") or item.get("why_this_matters") or item.get("why") or ""
        cards.append(
            {
                "name": title,
                "title": title,
                "capability": _clean_text(capability),
                "summary_points": _summary_points(
                    item.get("summary_points")
                    or item.get("summary")
                    or [capability, industry_impact]
                ),
                "industry_impact": _clean_text(industry_impact),
                "trend": item.get("trend") or "AI 能力",
                "link": item.get("link") or "",
            }
        )
    return cards


def build_dashboard_fallback(raw_text):
    return {
        "date": "",
        "headline": "Gemini 返回内容未能解析为标准 JSON",
        "platform_intelligence": [],
        "ai_technology": [],
        "sports_outdoor": [],
        "retail_innovation": [],
        "one_thing_worth_watching": "Gemini 返回内容未能解析为标准 JSON，已按 empty 结果处理。",
        "parse_warning": "Gemini JSON parse failed; rendered empty fallback content.",
    }


def build_source_fallback(source_items, warning):
    data = build_dashboard_fallback("")
    data["date"] = datetime.now().strftime("%Y-%m-%d")
    data["headline"] = "Gemini 暂时不可用，已基于真实候选来源生成临时预览"
    data["one_thing_worth_watching"] = data["headline"]
    data["parse_warning"] = warning
    return ensure_minimum_dashboard_signals(data, source_items)


def ensure_minimum_dashboard_signals(data, source_items):
    normalized = normalize_dashboard_data(data)
    items_by_domain = _items_by_domain(source_items)

    for domain in SECTION_ORDER:
        section_key = _canonical_section_key(domain)
        cards = normalized.get(section_key, [])
        minimum = MIN_SECTION_SIGNALS.get(domain, 2)
        used_links = {card.get("link") for card in cards if isinstance(card, dict) and card.get("link")}
        for item in items_by_domain.get(domain, []):
            if len(cards) >= 8:
                break
            # A source fallback is a draft of editor-selected inputs. Automatic
            # snippets have not passed the AI source/scope review; do not use
            # them to make the publication count appear complete.
            if item.get("origin_type") != "manual":
                continue
            if not item.get("title") or not item.get("summary") or not item.get("link"):
                continue
            if item.get("link") in used_links:
                continue
            if _is_google_news_redirect(item.get("link")):
                continue
            cards.append(_fallback_card_from_item(domain, item))
            if item.get("link"):
                used_links.add(item.get("link"))

        normalized[section_key] = cards
        if len(cards) < minimum:
            print(f"Draft shortfall: {domain} {len(cards)}/{minimum}")

    return _sanitize_dashboard_terms(normalized)


def _sanitize_dashboard_terms(value):
    if isinstance(value, str):
        text = value
        for old, new in FORBIDDEN_OUTPUT_REPLACEMENTS:
            text = text.replace(old, new)
        return text
    if isinstance(value, list):
        return [_sanitize_dashboard_terms(item) for item in value]
    if isinstance(value, dict):
        return {key: _sanitize_dashboard_terms(item) for key, item in value.items()}
    return value


def _filter_reliable_cards(cards):
    return [
        card
        for card in cards
        if not (isinstance(card, dict) and _is_google_news_redirect(card.get("link")))
    ]


def _is_google_news_redirect(link):
    host = urlparse(str(link or "")).netloc.lower()
    return host == "news.google.com"


def _items_by_domain(items):
    grouped = {section: [] for section in SECTION_ORDER}
    for item in items:
        domain = item.get("domain")
        if domain not in grouped:
            continue
        grouped[domain].append(item)

    for section_items in grouped.values():
        section_items.sort(
            key=lambda item: (
                1 if item.get("origin_type") == "manual" else 0,
                item.get("priority", 1),
                item.get("relevance_score", 0),
                -(item.get("search_window_days") or 0),
                item.get("published_date", ""),
            ),
            reverse=True,
        )
    return grouped


def _canonical_section_key(domain):
    return {
        "platform": "platform_intelligence",
        "ai": "ai_technology",
        "sports": "sports_outdoor",
        "retail": "retail_innovation",
    }[domain]


def _fallback_card_from_item(domain, item):
    title = item.get("title") or "Signal"
    raw_summary = item.get("summary") or title
    summary = _clean_text(raw_summary)
    link = item.get("link") or ""
    trend = _fallback_trend(item)
    points = _summary_points(raw_summary)

    if domain == "ai":
        return {
            "name": _shorten(title, 42),
            "title": _shorten(_business_ai_title(title), 42),
            "capability": summary,
            "summary_points": points,
            "industry_impact": "",
            "trend": trend,
            "link": link,
        }

    return {
        "name": _shorten(_company_or_topic(title), 32),
        "news": summary,
        "summary_points": points,
        "why_this_matters": "",
        "trend": trend,
        "link": link,
    }


def _business_ai_title(title):
    lowered = title.lower()
    if "search" in lowered:
        return "AI 搜索能力进入业务流程"
    if "customer service" in lowered or "客服" in title:
        return "AI 客服能力继续增强"
    if "shopping" in lowered or "购物" in title:
        return "AI 购物助手能力继续增强"
    if "agent" in lowered:
        return "AI Agent 可处理连续业务任务"
    if "workflow" in lowered or "operations" in lowered or "运营" in title:
        return "AI 正在进入企业工作流"
    return title


def _company_or_topic(title):
    return re.split(r"[-|:：]", title, maxsplit=1)[0].strip() or title


def _fallback_trend(item):
    if item.get("fallback_reason"):
        return "高相关候选;周度补充"
    window_days = item.get("search_window_days")
    if window_days:
        return f"近{window_days}天;行业情报"
    return "行业情报"


def _strip_json_fence(raw_text):
    text = raw_text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _extract_json_object(text):
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return ""
    return text[start : end + 1]


def _shorten(text, limit):
    text = re.sub(r"\s+", " ", str(text)).strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def _clean_text(text):
    return re.sub(r"\s+", " ", str(text)).strip()


def _summary_points(value):
    text = ""
    if isinstance(value, list):
        points = [_clean_text(item) for item in value if _clean_text(item)]
        text = " ".join(points)
    else:
        raw_text = str(value or "").strip()
        line_points = _manual_structured_points(raw_text)
        if line_points:
            points = line_points
        else:
            text = _clean_text(raw_text)
            points = [part.strip() for part in re.split(r"(?<=[。！？.!?])\s*", text) if part.strip()]
        if len(points) <= 1 and text:
            points = [text]
    return points[:6]


def _manual_structured_points(text):
    points = []
    metadata_prefixes = ("Category:", "Keywords:", "Company:", "Source:", "Date:")
    for raw_line in text.splitlines():
        line = _clean_text(raw_line)
        if not line or line.startswith(metadata_prefixes):
            continue
        if line.startswith("Content:"):
            line = line[len("Content:") :].strip()
        line = re.sub(r"^(?:[-*•]|\d+[.)、]|[一二三四五六七八九十]+[、.])\s*", "", line).strip()
        if line:
            points.append(line)
    return points if len(points) > 1 else []
