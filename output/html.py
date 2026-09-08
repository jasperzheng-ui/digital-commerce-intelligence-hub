from datetime import datetime
from html import escape

from utils.date_utils import report_date_parts


_DIRECT_TO_CONSUMER_ABBR = "D" + "TC"
_DECA_DIRECT_PHRASE = "对" + "迪卡侬而言"


TEXT_REPLACEMENTS = (
    (_DECA_DIRECT_PHRASE + "，", "给迪卡侬的启示是，"),
    (_DECA_DIRECT_PHRASE, "给迪卡侬的启示"),
    (_DIRECT_TO_CONSUMER_ABBR + " Opportunity", "业务启示"),
    (_DIRECT_TO_CONSUMER_ABBR + " opportunity", "业务启示"),
    (_DIRECT_TO_CONSUMER_ABBR + "机会", "业务启示"),
    (_DIRECT_TO_CONSUMER_ABBR + " 策略", "数字商业能力"),
    (_DIRECT_TO_CONSUMER_ABBR + "策略", "数字商业能力"),
    (_DIRECT_TO_CONSUMER_ABBR, "数字商业"),
)


def safe_text(value):
    if value is None:
        return ""
    if isinstance(value, str):
        return sanitize_text(value)
    if isinstance(value, list):
        return ", ".join(part for part in (safe_text(item) for item in value) if part)
    if isinstance(value, dict):
        return ", ".join(
            f"{safe_text(key)}: {safe_text(item)}"
            for key, item in value.items()
            if safe_text(key) or safe_text(item)
        )
    return str(value)


def sanitize_text(text):
    for old, new in TEXT_REPLACEMENTS:
        text = text.replace(old, new)
    return text


def safe_escape(value, quote=True):
    return escape(safe_text(value), quote=quote)


def safe_cards(value):
    return value if isinstance(value, list) else []


SECTIONS = [
    {
        "key": "platform_intelligence",
        "title": "国内电商平台",
        "subtitle": "Platform Intelligence",
        "tone": "blue",
    },
    {
        "key": "ai_technology",
        "title": "AI 能力与行业影响",
        "subtitle": "AI Capabilities & Industry Impact",
        "tone": "violet",
    },
    {
        "key": "sports_outdoor",
        "title": "体育与户外行业",
        "subtitle": "Sports & Outdoor",
        "tone": "orange",
    },
    {
        "key": "retail_innovation",
        "title": "传统零售创新",
        "subtitle": "Retail Innovation",
        "tone": "green",
    },
]


def render_dashboard(data, output_path, archive_href="./archive/"):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(build_dashboard_html(data, archive_href=archive_href), encoding="utf-8")
    return output_path


def build_dashboard_html(data, archive_href="./archive/"):
    date = data.get("date") or datetime.now().strftime("%Y-%m-%d")
    date_parts = report_date_parts(date)
    report_date_label = f"{date_parts['iso_week']} · {date_parts['formatted_date']}"

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Weekly Industry Intelligence</title>
  <style>
    :root {{
      --bg: #f7f8fb;
      --card: #ffffff;
      --ink: #172033;
      --muted: #687386;
      --line: #e6e9ef;
      --soft-line: #f0f2f6;
      --blue: #2357d9;
      --blue-soft: #edf3ff;
      --green: #078365;
      --green-soft: #eaf8f2;
      --orange: #b25a00;
      --orange-soft: #fff3e6;
      --violet: #6f52d4;
      --violet-soft: #f2effc;
      --dark: #111827;
    }}

    * {{
      box-sizing: border-box;
    }}

    body {{
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC",
        "Hiragino Sans GB", "Microsoft YaHei", Arial, sans-serif;
      line-height: 1.5;
    }}

    .page {{
      width: min(1120px, calc(100% - 32px));
      margin: 0 auto;
      padding: 44px 0 44px;
    }}

    .topbar {{
      display: flex;
      justify-content: space-between;
      gap: 24px;
      align-items: flex-start;
      margin-bottom: 28px;
    }}

    .eyebrow {{
      margin: 0 0 8px;
      color: var(--blue);
      font-size: 13px;
      font-weight: 750;
      letter-spacing: .08em;
      text-transform: uppercase;
    }}

    h1 {{
      margin: 0;
      font-size: clamp(30px, 4.4vw, 48px);
      line-height: 1;
      letter-spacing: 0;
    }}

    .header-actions {{
      display: flex;
      align-items: center;
      gap: 12px;
      flex: 0 0 auto;
      padding-top: 2px;
    }}

    .date {{
      color: var(--muted);
      font-size: 15px;
    }}

    .archive-link {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-height: 36px;
      padding: 7px 12px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--card);
      color: var(--ink);
      text-decoration: none;
      font-size: 14px;
      font-weight: 760;
      white-space: nowrap;
    }}

    .archive-link:hover {{
      border-color: #c8ced8;
    }}

    .section {{
      margin-top: 22px;
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 22px;
    }}

    .section-head {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      padding-bottom: 16px;
      border-bottom: 1px solid var(--soft-line);
      margin-bottom: 18px;
    }}

    h2 {{
      margin: 0;
      font-size: 24px;
      letter-spacing: 0;
    }}

    .subtitle {{
      margin-top: 2px;
      color: var(--muted);
      font-size: 14px;
      font-weight: 650;
    }}

    .section-badge {{
      border-radius: 999px;
      padding: 6px 11px;
      font-size: 12px;
      font-weight: 760;
      white-space: nowrap;
    }}

    .blue {{ color: var(--blue); background: var(--blue-soft); }}
    .violet {{ color: var(--violet); background: var(--violet-soft); }}
    .green {{ color: var(--green); background: var(--green-soft); }}
    .orange {{ color: var(--orange); background: var(--orange-soft); }}

    .cards {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 16px;
      align-items: start;
    }}

    .card {{
      display: flex;
      flex-direction: column;
      gap: 14px;
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 18px;
      background: #fff;
      min-height: 0;
    }}

    .card-title {{
      margin: 0;
      font-size: 20px;
      line-height: 1.25;
      letter-spacing: 0;
    }}

    .field {{
      padding-top: 12px;
      border-top: 1px solid var(--soft-line);
    }}

    .field-label {{
      color: var(--muted);
      font-size: 12px;
      font-weight: 780;
      letter-spacing: .04em;
      text-transform: uppercase;
      margin-bottom: 4px;
    }}

    .field p {{
      margin: 0;
      font-size: 15.5px;
      line-height: 1.62;
    }}

    .summary-list {{
      margin: 0;
      padding-left: 1.15em;
      font-size: 15.5px;
      line-height: 1.72;
    }}

    .summary-list li {{
      margin: 0 0 8px;
    }}

    .summary-list li:last-child {{
      margin-bottom: 0;
    }}

    .trend {{
      display: inline-flex;
      width: fit-content;
      border-radius: 999px;
      padding: 6px 10px;
      background: #f3f5f8;
      color: #344054;
      font-size: 13px;
      font-weight: 720;
    }}

    .read-button {{
      margin-top: auto;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: fit-content;
      min-height: 38px;
      padding: 8px 13px;
      border-radius: 8px;
      background: var(--dark);
      color: #fff;
      text-decoration: none;
      font-size: 14px;
      font-weight: 760;
    }}

    .read-button.disabled {{
      background: #eef1f5;
      color: #8792a2;
      pointer-events: none;
    }}

    .empty {{
      color: var(--muted);
      border: 1px dashed var(--line);
      border-radius: 8px;
      padding: 18px;
      background: #fbfcfe;
    }}

    .warning {{
      margin-top: 14px;
      color: #8a5a00;
      background: #fff7e6;
      border: 1px solid #ffe1a6;
      border-radius: 8px;
      padding: 12px 14px;
      font-size: 13px;
    }}

    @media (max-width: 760px) {{
      .page {{
        width: min(100% - 24px, 1120px);
        padding-top: 28px;
      }}

      .topbar {{
        display: block;
        margin-bottom: 20px;
      }}

      .header-actions {{
        margin-top: 14px;
        justify-content: space-between;
      }}

      .section {{
        padding: 18px;
      }}

      .section-head {{
        display: block;
      }}

      .section-badge {{
        display: inline-flex;
        margin-top: 10px;
      }}

      .cards {{
        grid-template-columns: 1fr;
      }}

      .card {{
        min-height: auto;
      }}
    }}
  </style>
</head>
<body>
  <main class="page">
    <section class="topbar">
      <div>
        <p class="eyebrow">Digital Commerce Intelligence Hub</p>
        <h1>Weekly Industry Intelligence</h1>
      </div>
      <div class="header-actions">
        <div class="date">{safe_escape(report_date_label)}</div>
        <a class="archive-link" href="{safe_escape(archive_href, quote=True)}">历史周报</a>
      </div>
    </section>

    {_render_sections(data)}

    {_render_warning(data)}
  </main>
</body>
</html>
"""


def _render_sections(data):
    return "\n".join(_render_section(section, safe_cards(data.get(section["key"], []))) for section in SECTIONS)


def _render_section(section, cards):
    rendered_cards = "\n".join(_render_card(card, section["key"]) for card in cards[:8])
    if not rendered_cards:
        rendered_cards = '<div class="empty">本期未筛出高价值行业情报。</div>'

    return f"""
    <section class="section">
      <div class="section-head">
        <div>
          <h2>{safe_escape(section["title"])}</h2>
          <div class="subtitle">{safe_escape(section["subtitle"])}</div>
        </div>
        <span class="section-badge {safe_escape(section["tone"])}">{len(cards[:8])} Signals</span>
      </div>
      <div class="cards">
        {rendered_cards}
      </div>
    </section>
    """


def _render_card(card, section_key):
    if isinstance(card, str):
        card = {"name": "Signal", "news": card, "summary_points": [card], "link": ""}

    link = safe_text(card.get("link", ""))
    button = (
        f'<a class="read-button" href="{safe_escape(link, quote=True)}" target="_blank" rel="noopener noreferrer">阅读全文</a>'
        if link
        else '<span class="read-button disabled">暂无原文链接</span>'
    )

    return f"""
    <article class="card">
      <h3 class="card-title">{safe_escape(_card_title(card, section_key))}</h3>
      <div class="field">
        <div class="field-label">摘要要点</div>
        {_render_summary_points(card, section_key)}
      </div>
      {button}
    </article>
    """


def _card_title(card, section_key):
    if not isinstance(card, dict):
        return card or "Signal"
    if section_key == "ai_technology":
        return card.get("title") or card.get("name") or "AI 能力变化"
    return card.get("name") or card.get("title") or "Signal"


def _render_summary_points(card, section_key):
    points = _summary_points(card, section_key)
    if not points:
        return "<p></p>"
    if len(points) == 1:
        return f"<p>{safe_escape(points[0])}</p>"
    rendered = "\n".join(f"<li>{safe_escape(point)}</li>" for point in points)
    return f'<ul class="summary-list">{rendered}</ul>'


def _summary_points(card, section_key):
    if not isinstance(card, dict):
        return [safe_text(card)]

    raw_points = card.get("summary_points")
    if isinstance(raw_points, list):
        return [safe_text(point).strip() for point in raw_points if safe_text(point).strip()]
    if raw_points:
        return _split_points(raw_points)

    if section_key == "ai_technology":
        values = [
            card.get("capability") or card.get("news") or "",
            card.get("industry_impact") or card.get("why_this_matters") or "",
        ]
    else:
        values = [
            card.get("news") or "",
            card.get("why_this_matters") or "",
        ]
    return [safe_text(value).strip() for value in values if safe_text(value).strip()]


def _split_points(value):
    text = safe_text(value).strip()
    if not text:
        return []
    if isinstance(value, str):
        parts = [part.strip(" -•\t") for part in text.splitlines() if part.strip(" -•\t")]
        if len(parts) > 1:
            return parts
    return [text]


def _render_warning(data):
    warning = data.get("parse_warning")
    if not warning:
        return ""
    return f'<div class="warning">{safe_escape(warning)}</div>'
