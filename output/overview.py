"""Shared, optional weekly overview for web, HTML email and plain text email."""
from html import escape
from urllib.parse import urlsplit


SECTION_TITLES = {
    "platform_intelligence": "国内电商平台",
    "ai_technology": "AI 能力与行业影响",
    "sports_outdoor": "体育与户外行业",
    "retail_innovation": "传统零售创新",
}


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
    for field in ("macro_analysis", "core_signals", "keywords", "sources"):
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
    for index, paragraph in enumerate(overview.get("macro_analysis", [])):
        path = f"weekly_overview.macro_analysis[{index}]"
        if not isinstance(paragraph, dict):
            raise ValueError(f"{path} 必须是对象。")
        _text(paragraph.get("text"), f"{path}.text", required=True)
        refs = paragraph.get("source_ids", [])
        if not isinstance(refs, list) or not all(isinstance(r, str) for r in refs):
            raise ValueError(f"{path}.source_ids 必须是来源 ID 文本数组。")
        for ref in refs:
            if ref not in sources:
                raise ValueError(f"{path}.source_ids 引用了不存在的来源：{ref}")
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
    used = list(dict.fromkeys(ref for p in overview.get("macro_analysis", [])
                             for ref in p.get("source_ids", [])))
    return overview, sources, {ref: n for n, ref in enumerate(used, 1)}


def render_overview_html(data, email=False):
    overview, sources, numbers = _content(data)
    headline = data.get("headline") or data.get("today_focus") or data.get("one_thing_worth_watching") or ""
    if not overview and not headline:
        return ""
    e = lambda value: escape(str(value), quote=True)
    title_style = "margin:0 0 8px;color:#3643BA;font-size:14px;font-weight:750;"
    blocks = ['<h2 style="margin:0 0 4px;font-size:22px;color:#172033;">本周核心概览</h2>',
              '<div style="color:#687386;font-size:12px;margin-bottom:20px;">Weekly Overview</div>',
              f'<h3 style="{title_style}">核心总结</h3>']
    if headline:
        blocks.append(f'<p style="margin:0 0 10px;font-size:20px;line-height:1.5;font-weight:750;">{e(headline)}</p>')
    if overview.get("summary"):
        blocks.append(f'<p style="margin:0;line-height:1.75;">{e(overview["summary"])}</p>')
    if overview.get("macro_analysis"):
        paragraphs = []
        for paragraph in overview["macro_analysis"]:
            refs = " ".join(
                f'<a href="{e(sources[ref]["url"])}" target="_blank" rel="noopener noreferrer" '
                f'aria-label="来源 {numbers[ref]}：{e(sources[ref]["title"])}" '
                f'style="color:#3643BA;text-decoration:underline;font-size:13px;">[{numbers[ref]}]</a>'
                for ref in dict.fromkeys(paragraph.get("source_ids", [])))
            paragraphs.append(f'<p style="margin:0 0 8px;line-height:1.75;">{e(paragraph["text"])} {refs}</p>')
        blocks.append('<div style="margin-top:20px;padding:16px;background:#f3f4fc;border-radius:8px;">'
                      f'<h3 style="{title_style}">宏观环境分析</h3>' + "".join(paragraphs) + '</div>')
    if numbers:
        rows = []
        for ref, number in numbers.items():
            source = sources[ref]
            meta = " · ".join(source.get(k, "") for k in ("source", "date") if source.get(k))
            rows.append(f'<li style="margin:6px 0;overflow-wrap:anywhere;">'
                        f'<a href="{e(source["url"])}" target="_blank" rel="noopener noreferrer" '
                        f'style="color:#3643BA;text-decoration:underline;">[{number}] {e(source["title"])}</a>'
                        + (f' <span style="color:#687386;">· {e(meta)}</span>' if meta else '') + '</li>')
        blocks.append('<div style="margin-top:12px;padding-top:12px;border-top:1px solid #e6e9ef;font-size:12px;">'
                      '<strong style="color:#687386;">参考来源</strong><ul style="list-style:none;padding:0;margin:6px 0 0;">'
                      + "".join(rows) + '</ul></div>')
    if overview.get("core_signals"):
        rows = []
        for signal in overview["core_signals"]:
            section = signal.get("section")
            label = f'<strong>{e(SECTION_TITLES[section])}：</strong>' if section else ''
            rows.append(f'<li style="margin:8px 0;line-height:1.7;">{label}{e(signal["text"])}</li>')
        blocks.append(f'<div style="margin-top:20px;"><h3 style="{title_style}">核心信号</h3>'
                      '<ul style="margin:0;padding-left:20px;">' + ''.join(rows) + '</ul></div>')
    if overview.get("keywords"):
        tags = ''.join(f'<span style="display:inline-block;margin:4px 6px 0 0;padding:4px 10px;'
                       f'background:#eef0fc;color:#3643BA;border-radius:12px;font-size:12px;">{e(word)}</span>'
                       for word in overview["keywords"])
        blocks.append(f'<div style="margin-top:18px;"><h3 style="{title_style}">核心关键词</h3>{tags}</div>')
    body = ''.join(blocks)
    if email:
        return '<div style="margin:0 0 30px;padding:20px;border:1px solid #e6e9ef;border-radius:8px;font-size:14px;">' + body + '</div>'
    return '<section class="section overview" id="weekly-overview" aria-label="本周核心概览">' + body + '</section>'


def render_overview_text(data):
    overview, sources, numbers = _content(data)
    headline = data.get("headline") or data.get("today_focus") or data.get("one_thing_worth_watching") or ""
    if not overview and not headline:
        return ""
    lines = ["本周核心概览", "核心总结", str(headline)]
    if overview.get("summary"):
        lines.append(overview["summary"])
    if overview.get("macro_analysis"):
        lines.extend(["", "宏观环境分析"])
        for paragraph in overview["macro_analysis"]:
            refs = ''.join(f'[{numbers[ref]}]' for ref in dict.fromkeys(paragraph.get("source_ids", [])))
            lines.append(paragraph["text"] + refs)
    if numbers:
        lines.extend(["", "参考来源"])
        for ref, number in numbers.items():
            source = sources[ref]
            meta = ' · '.join(source.get(k, '') for k in ('source', 'date') if source.get(k))
            lines.extend([f'[{number}] {source["title"]}' + (f' · {meta}' if meta else ''), source["url"]])
    if overview.get("core_signals"):
        lines.extend(["", "核心信号"] + ["- " + (SECTION_TITLES[s["section"]] + "：" if s.get("section") else "")
                     + s["text"] for s in overview["core_signals"]])
    if overview.get("keywords"):
        lines.extend(["", "核心关键词：" + " / ".join(overview["keywords"])])
    return '\n'.join(lines)
