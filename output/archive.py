import json
import re
from datetime import datetime
from html import escape
from pathlib import Path

from output.html import render_dashboard


DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def save_dashboard_history(data, output_dir):
    brief_date = get_brief_date(data)
    archive_dir = output_dir / "archive"
    data_dir = output_dir / "data"
    daily_dir = archive_dir / brief_date

    daily_dir.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)

    daily_html = daily_dir / "index.html"
    daily_json = data_dir / f"{brief_date}.json"

    render_dashboard(data, daily_html, archive_href="../")
    daily_json.write_text(
        json.dumps(build_archive_json(data, brief_date), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    render_archive_index(archive_dir, output_dir)

    return {
        "date": brief_date,
        "daily_html": daily_html,
        "daily_json": daily_json,
        "archive_index": archive_dir / "index.html",
    }


def get_brief_date(data):
    value = str(data.get("date") or "").strip()
    if DATE_RE.match(value):
        return value
    return datetime.now().strftime("%Y-%m-%d")


def build_archive_json(data, brief_date):
    archived = {
        "date": brief_date,
        "today_focus": data.get("headline", ""),
        "platform": data.get("platform_intelligence", []),
        "ai": data.get("ai_technology", []),
        "sports": data.get("sports_outdoor", []),
        "retail": data.get("retail_innovation", []),
        "one_thing_worth_watching": data.get("one_thing_worth_watching", ""),
    }
    if data.get("weekly_overview") is not None:
        archived["weekly_overview"] = data["weekly_overview"]
    return archived


def scan_archive_dates(archive_dir):
    if not archive_dir.exists():
        return []

    dates = []
    for path in archive_dir.iterdir():
        if path.is_dir() and DATE_RE.match(path.name) and (path / "index.html").exists():
            dates.append(path.name)
    return sorted(dates, reverse=True)


def render_archive_index(archive_dir, output_dir):
    archive_dir.mkdir(parents=True, exist_ok=True)
    dates = scan_archive_dates(archive_dir)
    (archive_dir / "index.html").write_text(build_archive_index_html(dates), encoding="utf-8")
    return archive_dir / "index.html"


def build_archive_index_html(dates):
    cards = "\n".join(_render_date_card(date) for date in dates)
    if not cards:
        cards = '<div class="empty">还没有历史周报。</div>'

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>历史周报 | Digital Commerce Intelligence</title>
  <style>
    :root {{
      --bg: #f7f8fb;
      --card: #ffffff;
      --ink: #172033;
      --muted: #687386;
      --line: #e6e9ef;
      --blue: #2357d9;
      --blue-soft: #edf3ff;
      --dark: #111827;
    }}

    * {{ box-sizing: border-box; }}

    body {{
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC",
        "Hiragino Sans GB", "Microsoft YaHei", Arial, sans-serif;
      line-height: 1.5;
    }}

    .page {{
      width: min(960px, calc(100% - 32px));
      margin: 0 auto;
      padding: 44px 0;
    }}

    .topbar {{
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 20px;
      margin-bottom: 28px;
    }}

    .eyebrow {{
      margin: 0 0 8px;
      color: var(--blue);
      font-size: 13px;
      font-weight: 760;
      letter-spacing: .08em;
      text-transform: uppercase;
    }}

    h1 {{
      margin: 0;
      font-size: clamp(34px, 5vw, 52px);
      line-height: 1;
      letter-spacing: 0;
    }}

    .home-link {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-height: 38px;
      padding: 8px 13px;
      border-radius: 8px;
      background: var(--dark);
      color: #fff;
      text-decoration: none;
      font-size: 14px;
      font-weight: 760;
      white-space: nowrap;
    }}

    .list {{
      display: grid;
      gap: 14px;
    }}

    .card {{
      display: flex;
      justify-content: space-between;
      gap: 18px;
      align-items: center;
      padding: 20px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--card);
      color: var(--ink);
      text-decoration: none;
    }}

    .date {{
      font-size: 22px;
      font-weight: 760;
      margin-bottom: 4px;
    }}

    .label {{
      color: var(--muted);
      font-size: 14px;
    }}

    .arrow {{
      color: var(--blue);
      font-weight: 760;
      white-space: nowrap;
    }}

    .empty {{
      color: var(--muted);
      border: 1px dashed var(--line);
      border-radius: 8px;
      padding: 20px;
      background: var(--card);
    }}

    @media (max-width: 680px) {{
      .page {{ width: min(100% - 24px, 960px); padding-top: 28px; }}
      .topbar {{ display: block; }}
      .home-link {{ margin-top: 16px; }}
      .card {{ display: block; }}
      .arrow {{ display: inline-block; margin-top: 12px; }}
    }}
  </style>
</head>
<body>
  <main class="page">
    <section class="topbar">
      <div>
        <p class="eyebrow">Weekly Intelligence Archive</p>
        <h1>历史周报</h1>
      </div>
      <a class="home-link" href="../">返回今日首页</a>
    </section>
    <section class="list">
      {cards}
    </section>
  </main>
</body>
</html>
"""


def _render_date_card(date):
    return f"""
      <a class="card" href="{escape(date, quote=True)}/">
        <div>
          <div class="date">{escape(format_week_label(date))}</div>
          <div class="label">Digital Commerce Intelligence Brief</div>
        </div>
        <div class="arrow">查看周报 →</div>
      </a>
    """


def format_week_label(date):
    try:
        parsed = datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        return date
    return f"Week {parsed.isocalendar()[1]}"

