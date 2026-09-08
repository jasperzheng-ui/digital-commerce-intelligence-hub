import os
from html import escape

import requests

from output.html import safe_text
from utils.date_utils import report_date_parts


RESEND_API_URL = "https://api.resend.com/emails"
DEFAULT_EMAIL_FROM = "Digital Commerce Intelligence <onboarding@resend.dev>"


SECTIONS = [
    ("Platform Intelligence", "platform_intelligence", "standard"),
    ("AI Capability", "ai_technology", "ai"),
    ("Sports & Outdoor", "sports_outdoor", "standard"),
    ("Retail Innovation", "retail_innovation", "standard"),
]


def send_brief_email(data, dashboard_url=""):
    api_key = os.getenv("EMAIL_API_KEY")
    email_to = os.getenv("EMAIL_TO")
    if not api_key:
        raise RuntimeError("Missing EMAIL_API_KEY environment variable.")
    if not email_to:
        raise RuntimeError("Missing EMAIL_TO environment variable.")

    date_parts = report_date_parts(data.get("date"))
    payload = {
        "from": os.getenv("EMAIL_FROM") or DEFAULT_EMAIL_FROM,
        "to": _split_recipients(email_to),
        "subject": (
            f"Weekly Industry Intelligence | {date_parts['iso_week']} "
            f"({date_parts['formatted_date']})"
        ),
        "html": build_email_html(data, dashboard_url),
        "text": build_email_text(data, dashboard_url),
    }

    response = requests.post(
        RESEND_API_URL,
        headers={"Authorization": f"Bearer {api_key}"},
        json=payload,
        timeout=30,
    )
    response.raise_for_status()
    print(f"Email response: {response.status_code} {response.text}")


def build_email_html(data, dashboard_url=""):
    date_parts = report_date_parts(data.get("date"))
    sections_html = "\n".join(
        _render_section(title, data.get(key, []) or [], section_type)
        for title, key, section_type in SECTIONS
    )

    return f"""<!doctype html>
<html>
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Weekly Industry Intelligence</title>
  </head>
  <body style="margin:0; padding:0; background:#f7f8fb; color:#172033; font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif;">
    <div style="display:none; max-height:0; overflow:hidden; opacity:0;">
      Weekly Industry Intelligence · {date_parts['iso_week']} · {date_parts['formatted_date']}
    </div>
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#f7f8fb; border-collapse:collapse;">
      <tr>
        <td align="center" style="padding:28px 12px;">
          <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:760px; background:#ffffff; border-collapse:separate; border-spacing:0; border-radius:18px; overflow:hidden; border:1px solid #e5e9f2;">
            <tr>
              <td style="padding:34px 34px 26px 34px; background:#ffffff; border-bottom:1px solid #e8edf5;">
                <div style="font-size:12px; line-height:1.4; color:#667085; letter-spacing:.08em; text-transform:uppercase; font-weight:700; margin-bottom:10px;">
                  Decathlon China Digital Commerce
                </div>
                <h1 style="margin:0; color:#111827; font-size:26px; line-height:1.15; font-weight:760;">
                  Weekly Industry Intelligence
                </h1>
                <div style="margin-top:10px; color:#5b6475; font-size:15px; line-height:1.6;">
                  {date_parts['iso_week']} · {date_parts['formatted_date']}
                </div>
                {_render_dashboard_button(dashboard_url)}
              </td>
            </tr>
            <tr>
              <td style="padding:28px 34px 34px 34px;">
                {sections_html}
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>"""


def build_email_text(data, dashboard_url=""):
    date_parts = report_date_parts(data.get("date"))
    lines = [
        "Weekly Industry Intelligence",
        f"{date_parts['iso_week']} · {date_parts['formatted_date']}",
    ]
    if dashboard_url:
        lines.extend(["", f"Open Dashboard: {safe_text(dashboard_url)}"])

    for title, key, section_type in SECTIONS:
        lines.extend(["", title])
        cards = data.get(key, []) or []
        if not cards:
            lines.append("No reliable signal returned from real sources.")
            continue
        for index, card in enumerate(cards, start=1):
            lines.extend(_format_text_card(index, card, section_type))

    return "\n".join(safe_text(line) for line in lines).strip() + "\n"


def build_email_body(data, dashboard_url=""):
    return build_email_text(data, dashboard_url)


def _render_dashboard_button(dashboard_url):
    url = safe_text(dashboard_url).strip()
    if not url:
        return ""
    return f"""
                <div style="margin-top:22px;">
                  <a href="{_e(url)}" style="display:inline-block; background:#0055ff; color:#ffffff; text-decoration:none; font-size:14px; font-weight:700; line-height:1; padding:13px 18px; border-radius:999px;">
                    Open Dashboard
                  </a>
                </div>"""


def _render_section(title, cards, section_type):
    cards = _safe_cards(cards)
    if cards:
        cards_html = "\n".join(_render_card(card, section_type) for card in cards)
    else:
        cards_html = """
                  <tr>
                    <td style="padding:18px 20px; color:#667085; font-size:14px; line-height:1.6; background:#fafbff; border:1px solid #e8edf5; border-radius:14px;">
                      No reliable signal returned from real sources.
                    </td>
                  </tr>"""

    return f"""
                <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="border-collapse:separate; border-spacing:0; margin:0 0 30px 0;">
                  <tr>
                    <td style="padding:0 0 12px 0;">
                      <h2 style="margin:0; color:#111827; font-size:20px; line-height:1.3; font-weight:760;">
                        {_e(title)}
                      </h2>
                    </td>
                  </tr>
                  {cards_html}
                </table>"""


def _render_card(card, section_type):
    title = _card_title(card, section_type)
    summary_html = _render_summary_points(card, section_type)
    link_html = _render_original_link(card.get("link") if isinstance(card, dict) else "")

    return f"""
                  <tr>
                    <td style="padding:0 0 14px 0;">
                      <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#ffffff; border:1px solid #e5e9f2; border-radius:14px; border-collapse:separate; border-spacing:0;">
                        <tr>
                          <td style="padding:20px 20px 18px 20px;">
                            <h3 style="margin:0; color:#111827; font-size:17px; line-height:1.45; font-weight:750;">
                              {_e(title)}
                            </h3>
                            {summary_html}
                            {link_html}
                          </td>
                        </tr>
                      </table>
                    </td>
                  </tr>"""


def _render_summary_points(card, section_type):
    points = _summary_points(card, section_type)
    if not points:
        return ""
    items = "".join(
        f"""<li style="margin:0 0 8px 0; color:#263244; font-size:14px; line-height:1.75;">{_e(point)}</li>"""
        for point in points
    )
    return f"""
                            <div style="margin-top:14px;">
                              <div style="color:#6b7280; font-size:11px; line-height:1.4; letter-spacing:.08em; text-transform:uppercase; font-weight:800; margin-bottom:8px;">
                                摘要要点
                              </div>
                              <ul style="margin:0; padding-left:18px;">{items}</ul>
                            </div>"""


def _render_original_link(value):
    url = safe_text(value).strip()
    if not url:
        return ""
    return f"""
                            <div style="margin-top:16px;">
                              <a href="{_e(url)}" style="display:inline-block; color:#0055ff; text-decoration:none; font-size:13px; line-height:1; font-weight:750; padding:9px 12px; border:1px solid #c7d7fe; border-radius:999px;">
                                Read Original
                              </a>
                            </div>"""


def _format_text_card(index, card, section_type):
    if not isinstance(card, dict):
        return [f"{index}. {safe_text(card)}"]

    lines = [f"{index}. {_card_title(card, section_type)}"]
    for point in _summary_points(card, section_type):
        lines.append(f"   - {safe_text(point)}")
    link = safe_text(card.get("link")).strip()
    if link:
        lines.append(f"   Read Original: {link}")
    return lines


def _card_title(card, section_type):
    if not isinstance(card, dict):
        return safe_text(card) or "Signal"
    if section_type == "ai":
        return safe_text(card.get("title") or card.get("name") or "AI Capability")
    return safe_text(card.get("name") or card.get("title") or "Industry Signal")


def _card_body_fields(card, section_type):
    if not isinstance(card, dict):
        return [("NEWS", card), ("WHY THIS MATTERS", "")]
    if section_type == "ai":
        return [
            ("NEWS", card.get("capability") or card.get("news") or ""),
            ("WHY THIS MATTERS", card.get("industry_impact") or card.get("why_this_matters") or ""),
        ]
    return [
        ("NEWS", card.get("news") or ""),
        ("WHY THIS MATTERS", card.get("why_this_matters") or ""),
    ]


def _summary_points(card, section_type):
    if not isinstance(card, dict):
        return [safe_text(card)]
    value = card.get("summary_points")
    if isinstance(value, list):
        return [safe_text(item).strip() for item in value if safe_text(item).strip()]
    if value:
        return [safe_text(value).strip()]
    return [
        safe_text(field_value).strip()
        for _, field_value in _card_body_fields(card, section_type)
        if safe_text(field_value).strip()
    ]


def _trend_values(value):
    if isinstance(value, list):
        return [safe_text(item).strip() for item in value if safe_text(item).strip()]
    text = safe_text(value).strip()
    if not text:
        return []
    separators = ["，", ",", "、", "|"]
    for separator in separators:
        if separator in text:
            return [item.strip() for item in text.split(separator) if item.strip()]
    return [text]


def _safe_cards(cards):
    if isinstance(cards, list):
        return cards
    if cards:
        return [cards]
    return []


def _split_recipients(value):
    recipients = [item.strip() for item in value.replace(";", ",").split(",")]
    return [item for item in recipients if item]


def _e(value):
    return escape(safe_text(value), quote=True)
