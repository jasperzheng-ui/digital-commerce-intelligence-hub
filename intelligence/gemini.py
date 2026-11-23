import json
import re
from urllib.parse import urlparse

from intelligence.prompt import build_dashboard_prompt


GEMINI_MODEL = "gemini-3.5-flash-lite"


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


def _review_schema():
    fields = {key: {"type": "STRING"} for key in
              ("name", "title", "company", "subcategory", "topic", "link", "quality_reason", "event_key")}
    fields["summary_points"] = {"type": "ARRAY", "items": {"type": "STRING"}}
    fields["quality_score"] = {"type": "INTEGER"}
    card = {"type": "OBJECT", "properties": fields,
            "required": ["link", "summary_points", "quality_score", "quality_reason", "event_key"]}
    properties = {key: {"type": "ARRAY", "items": card} for key in ("platform", "ai", "sports", "retail")}
    properties["headline"] = {"type": "STRING"}
    properties["date"] = {"type": "STRING"}
    properties["rejected_candidates"] = {"type": "ARRAY", "items": {
        "type": "OBJECT", "properties": {"link": {"type": "STRING"}, "reason": {"type": "STRING"}},
        "required": ["link", "reason"]}}
    return {"type": "OBJECT", "properties": properties,
            "required": ["platform", "ai", "sports", "retail", "rejected_candidates"]}


def _validate_review_response(data):
    for key in ("platform", "ai", "sports", "retail", "rejected_candidates"):
        if not isinstance(data.get(key), list):
            raise ValueError(f"审核JSON缺少 {key} 数组")
        for item in data[key]:
            if not isinstance(item, dict) or not isinstance(item.get("link"), str) or not item["link"]:
                raise ValueError(f"{key} 每条结果都必须有原始link")
            if key != "rejected_candidates":
                if (not isinstance(item.get("summary_points"), list) or not item["summary_points"]
                        or not all(isinstance(p, str) and p.strip() for p in item["summary_points"])
                        or not isinstance(item.get("quality_score"), int)
                        or not isinstance(item.get("quality_reason"), str)
                        or not isinstance(item.get("event_key"), str)):
                    raise ValueError(f"{key} 的摘要或审核字段无效")


def _generate_dashboard_batch(items):
    from intelligence.batches import generate_json
    result = generate_json(build_dashboard_prompt(items), "新闻审核",
                           response_schema=_review_schema(), validator=_validate_review_response)
    return normalize_dashboard_data(result)


def generate_dashboard_data(items):
    from intelligence.batches import batches
    from intelligence.report_quality import canonical_link
    result = {section: [] for section in SECTION_ALIASES}
    result['rejected_candidates'] = []
    queue = list(batches(items))
    index = 0
    while queue:
        batch = queue.pop(0)
        index += 1
        print(f'[review batch] {index}: {len(batch)} source articles', flush=True)
        from intelligence.batches import JsonGenerationError
        try:
            reviewed = _generate_dashboard_batch(batch)
            if reviewed.get('parse_warning'):
                raise JsonGenerationError('本批AI审核JSON无效')
        except JsonGenerationError:
            if len(batch) <= 1:
                raise
            middle = len(batch) // 2
            print(f'[review split] {len(batch)} -> {middle}+{len(batch)-middle}; no source dropped', flush=True)
            queue[0:0] = [batch[:middle], batch[middle:]]
            continue
        known = {canonical_link(i['link']) for i in batch}
        accepted = {canonical_link(c.get('link')) for section in SECTION_ALIASES for c in reviewed[section]}
        rejected = {canonical_link(c.get('link')) for c in reviewed.get('rejected_candidates', [])}
        if known - accepted - rejected:
            raise RuntimeError('AI审核遗漏部分输入文章，请重新Preview；没有按数量截断素材。')
        if (accepted | rejected) - known:
            raise RuntimeError('AI审核引用了本批素材之外的链接，已停止生成。')
        for section in SECTION_ALIASES:
            result[section].extend(reviewed[section])
        result['rejected_candidates'].extend(reviewed.get('rejected_candidates', []))
        if reviewed.get('headline'):
            result['headline'] = reviewed['headline']
    return result


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
    for key in ("weekly_overview", "parse_warning", "quality_status", "quality_shortfalls", "source_mix",
                "editorial_notice", "review_version", "rejected_candidates"):
        if key in data:
            normalized[key] = data[key]
    return _sanitize_dashboard_terms(normalized)


def _first_section(data, canonical_key):
    for key in SECTION_ALIASES[canonical_key]:
        if data.get(key):
            return data[key]
    return []


def _card_metadata(item):
    fields = ("title", "company", "category", "keywords", "date", "source", "source_type",
              "origin_type", "quality_score", "quality_reason", "event_key", "review_status",
              "provenance_url", "subcategory", "topic", "references", "text")
    return {key: item[key] for key in fields if key in item}


def _normalize_cards(items):
    cards = []
    for item in items:
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
                **_card_metadata(item),
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
    for item in items:
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
                **_card_metadata(item),
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


def _canonical_section_key(domain):
    return {
        "platform": "platform_intelligence",
        "ai": "ai_technology",
        "sports": "sports_outdoor",
        "retail": "retail_innovation",
    }[domain]


def _strip_json_fence(raw_text):
    text = raw_text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


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
    return points


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


