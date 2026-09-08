from datetime import datetime, timezone
import re

from sources.common import clean_text, make_item


FIELD_ALIASES = {
    "title": "title",
    "标题": "title",
    "category": "category",
    "分类": "category",
    "company": "company",
    "公司": "company",
    "平台": "company",
    "topic": "company",
    "主题": "company",
    "link": "link",
    "url": "link",
    "链接": "link",
    "原文": "link",
    "content": "content",
    "正文": "content",
    "内容": "content",
    "summary": "content",
    "摘要": "content",
    "keywords": "keywords",
    "关键词": "keywords",
    "source": "source",
    "来源": "source",
    "date": "date",
    "日期": "date",
}


def fetch_manual_items(path):
    if not path.exists():
        return []

    content = path.read_text(encoding="utf-8").strip()
    if not content:
        return []

    entries = _parse_manual_entries(content)
    items = []
    for entry in entries:
        if _is_placeholder_entry(entry):
            continue
        title = entry.get("title") or _extract_title(entry.get("content", ""))
        body = _format_manual_summary(entry)
        source = entry.get("source")
        item = make_item(
            source=f"Manual Input - {source}" if source else "Manual Input",
            title=title,
            summary=body,
            link=entry.get("link", ""),
            published_date=_parse_manual_date(entry.get("date")) or datetime.now(timezone.utc),
            domain=_infer_domain(
                entry.get("category", ""),
                entry.get("company", ""),
                f"{entry.get('keywords', '')} {body}",
            ),
            origin_type="manual",
            priority=3,
        )
        item["summary"] = body
        item["manual_category"] = entry.get("category", "")
        item["manual_company"] = entry.get("company", "")
        items.append(item)

    return items


def _extract_title(content):
    for line in content.splitlines():
        cleaned = clean_text(line).lstrip("#").strip()
        if cleaned:
            return cleaned[:120]
    return "Manual Digital Commerce Signal"


def _clean_manual_content(value):
    lines = []
    blank_seen = False
    for raw_line in str(value).splitlines():
        line = clean_text(raw_line)
        if not line:
            if not blank_seen and lines:
                lines.append("")
            blank_seen = True
            continue
        lines.append(line)
        blank_seen = False
    return "\n".join(lines).strip()


def _parse_manual_entries(content):
    chunks = [
        chunk.strip()
        for chunk in re.split(r"\n\s*(?:---+|###\s+|##\s+)\s*\n?", content)
        if chunk.strip()
    ]
    return [_parse_manual_entry(chunk) for chunk in chunks] or [_parse_manual_entry(content)]


def _parse_manual_entry(chunk):
    entry = {}
    content_lines = []
    current_field = None

    for raw_line in chunk.splitlines():
        line = raw_line.strip()
        if not line:
            if current_field == "content":
                content_lines.append("")
            continue

        if current_field and current_field != "content" and not entry.get(current_field):
            entry[current_field] = clean_text(line)
            current_field = None
            continue

        match = re.match(r"^[-*]?\s*([^:：]{1,24})\s*[:：]\s*(.*)$", line)
        if match:
            key = FIELD_ALIASES.get(match.group(1).strip().lower())
            value = match.group(2).strip()
            if key == "content":
                current_field = "content"
                if value:
                    content_lines.append(value)
            elif key:
                entry[key] = clean_text(value)
                current_field = key
            else:
                content_lines.append(line)
                current_field = None
            continue

        content_lines.append(line)

    if content_lines:
        entry["content"] = _clean_manual_content("\n".join(content_lines))
    if not entry.get("title"):
        entry["title"] = _extract_title(chunk)
    return entry


def _is_placeholder_entry(entry):
    title = clean_text(entry.get("title", "")).lower()
    content = clean_text(entry.get("content", "")).lstrip("#").strip().lower()
    has_signal_fields = any(entry.get(key) for key in ["link", "source", "date", "keywords", "category", "company"])
    return not has_signal_fields and title == "manual intelligence input" and content in {"", "manual intelligence input"}


def _format_manual_summary(entry):
    parts = []
    if entry.get("category"):
        parts.append(f"Category: {entry['category']}")
    if entry.get("keywords"):
        parts.append(f"Keywords: {entry['keywords']}")
    if entry.get("company"):
        parts.append(f"Company: {entry['company']}")
    if entry.get("source"):
        parts.append(f"Source: {entry['source']}")
    if entry.get("date"):
        parts.append(f"Date: {entry['date']}")
    if entry.get("content"):
        parts.append(f"Content: {entry['content']}")
    return "\n".join(parts) or entry.get("title", "")


def _parse_manual_date(value):
    if not value:
        return None
    cleaned = clean_text(value)
    for pattern in ["%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d"]:
        try:
            return datetime.strptime(cleaned, pattern).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def _infer_domain(category, company, content):
    text = f"{category} {company} {content}".lower()
    if any(word in text for word in ["platform", "平台", "internet giants", "阿里", "alibaba", "淘宝", "天猫", "京东", "jd", "字节", "bytedance", "腾讯", "tencent", "美团", "meituan", "拼多多", "pdd", "小红书"]):
        return "platform"
    if any(word in text for word in ["openai", "deepmind", "anthropic", "deepseek", "豆包", "通义", "kimi", "manus", "nvidia", "agent", "模型", "多模态"]):
        return "ai"
    if any(word in text for word in ["sports", "outdoor", "体育", "户外", "运动", "decathlon", "nike", "adidas", "lululemon", "anta", "li ning", "salomon"]):
        return "sports"
    return "retail"
