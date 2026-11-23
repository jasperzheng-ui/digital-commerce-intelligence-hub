import os
from html import escape

import requests

from output.html import safe_text
from output.overview import render_overview_html, render_overview_text, render_section_overview_html, section_overview
from output.digest import render_digest_html, render_digest_text
from utils.date_utils import report_date_parts


RESEND_API_URL = "https://api.resend.com/emails"
DEFAULT_EMAIL_FROM = "Digital Commerce Intelligence <onboarding@resend.dev>"


SECTIONS = [
    ("Platform Intelligence", "platform_intelligence"),
    ("AI Capability", "ai_technology"),
    ("Sports & Outdoor", "sports_outdoor"),
    ("Retail Innovation", "retail_innovation"),
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
        _render_digest_section(title, data, key)
        for title, key in SECTIONS
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
                {render_overview_html(data, email=True)}
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

    overview = render_overview_text(data)
    if overview:
        lines.extend(["", overview])

    for title, key in SECTIONS:
        lines.extend(["", title, "本周板块总览", section_overview(data, key)])
        lines.append(render_digest_text(data, key))

    return "\n".join(safe_text(line) for line in lines).strip() + "\n"


def build_email_body(data, dashboard_url=""):
    return build_email_text(data, dashboard_url)


def _render_dashboard_button(dashboard_url):
    url = safe_text(dashboard_url).strip()
    if not url:
        return ""
    return f"""
                <div style="margin-top:22px;">
                  <a href="{_e(url)}" style="display:inline-block; background:#3643BA; color:#ffffff; text-decoration:none; font-size:14px; font-weight:700; line-height:1; padding:13px 18px; border-radius:999px;">
                    Open Dashboard
                  </a>
                </div>"""


def _render_digest_section(title, data, key):
    return (f'<table role="presentation" width="100%" cellspacing="0" cellpadding="0" '
            f'style="border-collapse:collapse;margin-bottom:32px;"><tr><td>'
            f'<h2 style="margin:0 0 16px;color:#172033;font-size:22px;line-height:1.5;">{_e(title)}</h2>'
            + render_section_overview_html(data, key) + render_digest_html(data, key) + '</td></tr></table>')


def _split_recipients(value):
    recipients = [item.strip() for item in value.replace(";", ",").split(",")]
    return [item for item in recipients if item]


def _e(value):
    return escape(safe_text(value), quote=True)


