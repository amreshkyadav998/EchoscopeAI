"""Alert email (HLD §4.6).

Renders an HTML alert with a Jinja2 template and sends it via the SendGrid HTTP API.
If no SENDGRID_API_KEY is configured, it logs the email instead (dev stub) so the
pipeline runs without external credentials.
"""

from __future__ import annotations

import httpx
from jinja2 import Template
from loguru import logger as log

from config import get_settings

_TEMPLATE = Template(
    """
    <html><body style="font-family:Arial,sans-serif">
      <h2 style="color:#b91c1c">🚨 Alert: {{ keyword }}</h2>
      <p>{{ trigger_reason }}</p>
      <table style="border-collapse:collapse">
        <tr><td style="padding:4px 12px"><b>Mentions</b></td><td>{{ mention_count }}</td></tr>
        <tr><td style="padding:4px 12px"><b>Rule</b></td><td>{{ rule_name }}</td></tr>
        <tr><td style="padding:4px 12px"><b>When</b></td><td>{{ triggered_at }}</td></tr>
      </table>
      <p style="color:#6b7280;font-size:12px">EchoscopeAI · automated alert</p>
    </body></html>
    """
)


def render_alert_html(**ctx) -> str:
    return _TEMPLATE.render(**ctx)


async def send_alert_email(to_addresses: list[str], subject: str, html: str) -> bool:
    """Send via SendGrid if configured, else log a stub. Returns True if 'sent'."""
    settings = get_settings()
    if not to_addresses:
        return False

    if not settings.sendgrid_api_key:
        log.info("alert email (stub — no SENDGRID_API_KEY)", to=to_addresses, subject=subject)
        return True

    payload = {
        "personalizations": [{"to": [{"email": a} for a in to_addresses]}],
        "from": {"email": settings.email_from_address or "alerts@echoscope.local"},
        "subject": subject,
        "content": [{"type": "text/html", "value": html}],
    }
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                "https://api.sendgrid.com/v3/mail/send",
                headers={"Authorization": f"Bearer {settings.sendgrid_api_key}"},
                json=payload,
            )
            resp.raise_for_status()
        log.info("alert email sent via SendGrid", to=to_addresses, subject=subject)
        return True
    except Exception:
        log.exception("failed to send alert email")
        return False
