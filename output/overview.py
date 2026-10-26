"""Shared, optional weekly overview for web, HTML email and plain text email."""
from html import escape
from urllib.parse import urlsplit


SECTION_TITLES = {
    "platform_intelligence": "国内电商平台",
    "ai_technology": "AI 能力与行业影响",
    "sports_outdoor": "体育与户外行业",
    "retail_innovation": "传统零售创新",
}

ANALYSIS_GROUPS = (
    ("macro_analysis", "宏观经济与政策"),
    ("consumer_insights", "消费需求与支出变化"),
    ("channel_competition", "渠道与竞争格局"),
)

LEGACY_ANALYSIS_GROUPS = (
    ("macro_analysis", "宏观环境"),
    ("industry_trends", "行业趋势"),
    ("consumer_insights", "消费者洞察"),
)


def analysis_groups(overview):
    """Old saved editions keep their original headings and citation order."""
    if "industry_trends" in overview and "channel_competition" not in overview:
        return LEGACY_ANALYSIS_GROUPS
    return ANALYSIS_GROUPS


def original_url(value):
    if not isinstance(value, str) or any(c.isspace() for c in value):
        return False
    try:
        url = urlsplit(value)
        return bool(url.scheme in {"https", "http"} and url.hostname
                    and not url.username and not url.password
                    and url.hostname.lower() != "news.google.com")
    except ValueError:
        return False


def _text(value, path, required=False):
    if not isinstance(value, str) or (required and not value.strip()):
        raise ValueError(f"{path} 必须是{'非空' if required else ''}文本。")


def validate_overview(data):
    """Validate only supplied fields; old drafts do not need an overview."""
    overview = data.get("weekly_overview")
    if overview is None:
        return
    if not isinstance(overview, dict):
        raise ValueError("weekly_overview 必须是对象。")
    _text(overview.get("summary", ""), "weekly_overview.summary")
    for field in ("macro_analysis", "consumer_insights", "channel_competition", "industry_trends", "core_signals", "keywords", "sources"):
        if not isinstance(overview.get(field, []), list):
            raise ValueError(f"weekly_overview.{field} 必须是数组。")
    sources = {}
    for index, source in enumerate(overview.get("sources", [])):
        path = f"weekly_overview.sources[{index}]"
        if not isinstance(source, dict):
            raise ValueError(f"{path} 必须是对象。")
        for field in ("id", "title", "url"):
            _text(source.get(field), f"{path}.{field}", required=True)
        for field in ("source", "date"):
            _text(source.get(field, ""), f"{path}.{field}")
        if source["id"] in sources:
            raise ValueError(f"{path}.id 重复：{source['id']}")
        if not original_url(source["url"]):
            raise ValueError(f"{path}.url 必须是有效的 HTTP(S) 原文链接。")
        sources[source["id"]] = source
    if "channel_competition" in overview and "industry_trends" in overview:
        raise ValueError("新版渠道与竞争格局和旧版行业趋势不能同时填写。")
    for field, _ in analysis_groups(overview):
        for index, paragraph in enumerate(overview.get(field, [])):
            path = f"weekly_overview.{field}[{index}]"
            if not isinstance(paragraph, dict):
                raise ValueError(f"{path} 必须是对象。")
            _text(paragraph.get("title", ""), f"{path}.title")
            _text(paragraph.get("text"), f"{path}.text", required=True)
            refs = paragraph.get("source_ids", [])
            if not isinstance(refs, list) or not all(isinstance(r, str) for r in refs):
                raise ValueError(f"{path}.source_ids 必须是来源 ID 文本数组。")
            for ref in refs:
                if ref not in sources:
                    raise ValueError(f"{path}.source_ids 引用了不存在的来源：{ref}")
    summaries = overview.get("section_overviews", {})
    if not isinstance(summaries, dict):
        raise ValueError("weekly_overview.section_overviews 必须是对象。")
    for section, text in summaries.items():
        if section not in SECTION_TITLES:
            raise ValueError(f"weekly_overview.section_overviews.{section} 不是有效板块。")
        _text(text, f"weekly_overview.section_overviews.{section}", required=True)
    for index, signal in enumerate(overview.get("core_signals", [])):
        path = f"weekly_overview.core_signals[{index}]"
        if not isinstance(signal, dict):
            raise ValueError(f"{path} 必须是对象。")
        _text(signal.get("text"), f"{path}.text", required=True)
        if signal.get("section", "") not in ("", *SECTION_TITLES):
            raise ValueError(f"{path}.section 不是有效板块。")
    for index, word in enumerate(overview.get("keywords", [])):
        _text(word, f"weekly_overview.keywords[{index}]", required=True)


def _content(data):
    validate_overview(data)
    overview = data.get("weekly_overview") or {}
    sources = {s["id"]: s for s in overview.get("sources", [])}
    used = list(dict.fromkeys(ref for field, _ in analysis_groups(overview)
                             for p in overview.get(field, [])
                             for ref in p.get("source_ids", [])))
    from output.digest import citation_catalog
    catalog = citation_catalog(data)
    return overview, sources, {ref: catalog[sources[ref]['url']]['number'] for ref in used}


def section_overview(data, section):
    """New block summaries take precedence; preserve manually edited legacy signals."""
    overview = data.get("weekly_overview") or {}
    summary = overview.get("section_overviews", {}).get(section, "").strip()
    if summary:
        return summary
    legacy = [s["text"].strip() for s in overview.get("core_signals", [])
              if s.get("section") == section and s.get("text", "").strip()]
    if legacy:
        return " ".join(legacy)
    if not data.get(section):
        return "本期未筛出高价值行业情报。"
    return "本期尚未填写板块总览。"


def render_section_overview_html(data, section):
    text = escape(section_overview(data, section), quote=True)
    return ('<div class="section-overview" style="margin:0 0 18px;padding:16px 18px;'
            'background:#f3f4fc;border-left:3px solid #3643BA;border-radius:0 8px 8px 0;'
            'overflow-wrap:anywhere;">'
            '<div style="margin:0 0 7px;color:#3643BA;font-size:13px;font-weight:750;">本周板块总览</div>'
            f'<p style="margin:0;color:#263244;font-size:15px;line-height:1.8;">{text}</p></div>')


def _point_content(point):
    title = point.get("title", "").strip()
    text = point["text"]
    # Older hand-edited drafts put the subheading at the start of the paragraph.
    if not title:
        first, separator, remainder = text.partition("。")
        if separator and remainder.strip() and "：" in first and len(first.split("：", 1)[0]) <= 10:
            return first, remainder.strip()
        title = "综合观察"
    return title, text


def render_overview_html(data, email=False):
    overview, sources, numbers = _content(data)
    e = lambda value: escape(str(value), quote=True)
    blocks = ['<h2 style="margin:0 0 24px;font-size:24px;color:#172033;">本周行业观察</h2>']
    groups = analysis_groups(overview)
    for index, (field, label) in enumerate(groups, 1):
        blocks.append('<div style="margin-top:22px;">'
                      f'<h3 style="margin:0 0 18px;padding-left:10px;border-left:3px solid #3643BA;'
                      f'color:#3643BA;font-size:19px;line-height:1.5;">{index}. {label}</h3>')
        paragraphs = overview.get(field, [])
        if not paragraphs:
            blocks.append('<p style="margin:0;color:#687386;font-size:14px;line-height:1.8;">'
                          '本期暂无足够素材支持该维度分析。</p>')
        for paragraph in paragraphs:
            title, body_text = _point_content(paragraph)
            if title:
                blocks.append(f'<h4 style="margin:18px 0 8px;color:#172033;font-size:16px;'
                              f'line-height:1.65;font-weight:750;">{e(title)}</h4>')
            refs = " ".join(
                f'<a href="{e(sources[ref]["url"])}" target="_blank" rel="noopener noreferrer" '
                f'title="{e(sources[ref]["title"])}" aria-label="来源 {numbers[ref]}：{e(sources[ref]["title"])}" '
                f'style="color:#3643BA;text-decoration:underline;font-size:13px;">[{numbers[ref]}]</a>'
                for ref in dict.fromkeys(paragraph.get("source_ids", [])))
            blocks.append(f'<p style="margin:0 0 12px;color:#263244;font-size:15px;line-height:1.85;">'
                          f'{e(body_text)} {refs}</p>')
        blocks.append('</div>')
        if index < len(groups):
            blocks.append('<div style="margin-top:24px;border-top:1px solid #edf0f5;"></div>')
    body = ''.join(blocks)
    if email:
        return ('<div style="margin:0 0 30px;padding:20px;border:1px solid #e6e9ef;'
                'border-radius:8px;">' + body + '</div>')
    return '<section class="section overview" id="weekly-overview" aria-label="本周行业观察">' + body + '</section>'


def render_overview_text(data):
    overview, sources, numbers = _content(data)
    lines = ["本周行业观察"]
    for index, (field, label) in enumerate(analysis_groups(overview), 1):
        lines.extend(["", f"{index}. {label}"])
        paragraphs = overview.get(field, [])
        if not paragraphs:
            lines.append("本期暂无足够素材支持该维度分析。")
        for paragraph in paragraphs:
            title, body_text = _point_content(paragraph)
            lines.append(title)
            refs = " ".join(f'[{numbers[ref]}] {sources[ref]["url"]}'
                            for ref in dict.fromkeys(paragraph.get("source_ids", [])))
            lines.append(body_text + (" " + refs if refs else ""))
    return "\n".join(lines)

