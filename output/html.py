from datetime import datetime
from html import escape

from output.overview import render_overview_html, render_section_overview_html
from output.digest import render_digest_html

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


SECTIONS = [
    {
        "key": "platform_intelligence",
        "title": "国内电商平台",
        "subtitle": "Platform Intelligence",
    },
    {
        "key": "ai_technology",
        "title": "AI 能力与行业影响",
        "subtitle": "AI Capabilities & Industry Impact",
    },
    {
        "key": "sports_outdoor",
        "title": "体育与户外行业",
        "subtitle": "Sports & Outdoor",
    },
    {
        "key": "retail_innovation",
        "title": "传统零售创新",
        "subtitle": "Retail Innovation",
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
      --blue: #3643BA;
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

    html {{ scroll-behavior: smooth; }}
    .section {{ scroll-margin-top: 24px; }}
    .sidebar {{ display: none; }}
    .sidebar-title {{ color: var(--blue); font-size: 13px; font-weight: 750; margin: 0 12px 22px; }}
    .report-nav {{ display: flex; flex-direction: column; gap: 6px; }}
    .report-nav a {{
      display: block; padding: 11px 12px; border-left: 3px solid transparent;
      border-radius: 0 6px 6px 0; color: var(--muted); text-decoration: none;
      font-size: 14px; line-height: 1.5;
    }}
    .report-nav a:hover {{ color: var(--blue); background: #f4f5fc; }}
    .report-nav a[aria-current="location"] {{
      color: var(--blue); background: #eef0fc; border-left-color: var(--blue); font-weight: 750;
    }}
    .report-nav a:focus-visible, .mobile-directory summary:focus-visible {{ outline: 2px solid var(--blue); outline-offset: 3px; }}
    .mobile-directory {{ margin-bottom: 18px; padding: 12px; border: 1px solid var(--line); border-radius: 8px; background: #fff; }}
    .mobile-directory summary {{ cursor: pointer; color: var(--blue); font-size: 14px; font-weight: 750; }}
    .mobile-directory .report-nav {{ margin-top: 12px; }}
    .overview {{ font-size: 15px; overflow-wrap: anywhere; }}
    @media (prefers-reduced-motion: reduce) {{ html {{ scroll-behavior: auto; }} }}

    .topbar {{
      display: flex;
      flex-wrap: wrap;
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
      overflow-wrap: anywhere;
    }}

    .header-actions {{
      display: flex;
      flex-wrap: wrap;
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


    }}

    /* A mouse-operated desktop keeps its left directory at every browser zoom.
       Touch devices retain the compact directory; article columns follow the
       space remaining beside the sidebar rather than the full window width. */
    @media (hover: hover) and (pointer: fine), (min-width: 1281px) {{
      :root {{
        --sidebar-width: clamp(100px, 18vw, 208px);
        --sidebar-left: max(8px, calc((100vw - 1600px) / 2));
      }}
      .sidebar {{
        display: block; position: fixed; top: 0; bottom: 0;
        left: var(--sidebar-left); width: var(--sidebar-width);
        padding: 40px 8px 24px 0; background: #fff;
        border-right: 1px solid var(--line); overflow-y: auto;
        overflow-wrap: anywhere;
      }}
      .page {{
        width: min(1120px, calc(100% - var(--sidebar-left) - var(--sidebar-width) - 48px));
        margin-left: max(calc(var(--sidebar-left) + var(--sidebar-width) + 24px), calc((100% - 1120px) / 2));
        margin-right: 24px; padding-top: 44px;
        min-width: 0; overflow-wrap: anywhere;
      }}
      .mobile-directory {{ display: none; }}
      .section {{ padding: clamp(10px, 2vw, 22px); }}

    }}
  </style>
</head>
<body>
  <aside class="sidebar" aria-label="周报导航">
    <p class="sidebar-title">Digital Commerce<br>Intelligence Hub</p>
    {_render_navigation(data)}
  </aside>
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

    <details class="mobile-directory">
      <summary>本期目录</summary>
      {_render_navigation(data)}
    </details>

    {_render_warning(data)}

    {render_overview_html(data)}

    {_render_sections(data)}
  </main>
  <script>
    (() => {{
      const links = Array.from(document.querySelectorAll('.report-nav a'));
      const sections = Array.from(document.querySelectorAll('main > .section[id]'));
      let scheduled = false;
      function updateNavigation() {{
        scheduled = false;
        let active = sections[0];
        for (const section of sections) {{
          if (section.getBoundingClientRect().top <= 140) active = section;
        }}
        if (window.scrollY > 0 && window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 2) {{
          active = sections[sections.length - 1];
        }}
        for (const link of links) {{
          if (active && link.hash === '#' + active.id) link.setAttribute('aria-current', 'location');
          else link.removeAttribute('aria-current');
        }}
      }}
      window.addEventListener('scroll', () => {{
        if (!scheduled) {{ scheduled = true; requestAnimationFrame(updateNavigation); }}
      }}, {{ passive: true }});
      window.addEventListener('resize', updateNavigation);
      for (const link of links) link.addEventListener('click', () => {{
        const directory = link.closest('details');
        if (directory) directory.open = false;
      }});
      updateNavigation();
    }})();
  </script>
</body>
</html>
"""


def _render_navigation(data):
    items = [(section["key"], section["title"]) for section in SECTIONS]
    items.insert(0, ("weekly-overview", "本周行业观察"))
    return '<nav class="report-nav" aria-label="本期目录">' + ''.join(
        f'<a href="#{safe_escape(key)}">{safe_escape(title)}</a>' for key, title in items) + '</nav>'


def _render_sections(data):
    return "\n".join(_render_section(section, data) for section in SECTIONS)


def _render_section(section, data):
    return f"""
    <section class="section" id="{safe_escape(section['key'])}">
      <div class="section-head">
        <div>
          <h2>{safe_escape(section["title"])}</h2>
          <div class="subtitle">{safe_escape(section["subtitle"])}</div>
        </div>
      </div>
      {render_section_overview_html(data, section['key'])}
      <div class="digest-content">
        {render_digest_html(data, section['key'])}
      </div>
    </section>
    """


def _render_warning(data):
    warning = data.get("parse_warning") or data.get("editorial_notice")
    if not warning:
        return ""
    return f'<div class="warning">{safe_escape(warning)}</div>'


