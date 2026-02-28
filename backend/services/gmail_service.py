"""
Gmail API Integration
- send_call_summary()  — rich HTML email after a call completes
- send_threat_alert()  — automated alert when monitor detects price changes

Auth: OAuth2 refresh-token flow via httpx — no extra pip packages needed.

Setup (one-time, local):
  1. Google Cloud Console → Enable Gmail API
  2. Create OAuth 2.0 credentials (Desktop app)
  3. Download credentials.json, run:
       python -c "
       from google_auth_oauthlib.flow import InstalledAppFlow
       flow = InstalledAppFlow.from_client_secrets_file('credentials.json', ['https://www.googleapis.com/auth/gmail.send'])
       creds = flow.run_local_server(port=0)
       print('CLIENT_ID:', creds.client_id)
       print('CLIENT_SECRET:', creds.client_secret)
       print('REFRESH_TOKEN:', creds.refresh_token)
       "
  4. Store CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN in Render env vars.

  OR simply use GMAIL_APP_PASSWORD (Gmail → Settings → App Passwords).
  Both paths are supported — App Password is tried first if set.
"""

import base64
import logging
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

import httpx

import config

logger = logging.getLogger(__name__)

GMAIL_TOKEN_URL = "https://oauth2.googleapis.com/token"
GMAIL_SEND_URL = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"


# ── Auth helpers ─────────────────────────────────────────────

async def _get_oauth_token() -> Optional[str]:
    """Exchange refresh token for a short-lived access token."""
    if not all([config.GMAIL_CLIENT_ID, config.GMAIL_CLIENT_SECRET, config.GMAIL_REFRESH_TOKEN]):
        return None
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(GMAIL_TOKEN_URL, data={
                "client_id": config.GMAIL_CLIENT_ID,
                "client_secret": config.GMAIL_CLIENT_SECRET,
                "refresh_token": config.GMAIL_REFRESH_TOKEN,
                "grant_type": "refresh_token",
            })
            resp.raise_for_status()
            return resp.json().get("access_token")
    except Exception as e:
        logger.error("Gmail token refresh failed: %s", e)
        return None


# ── Core send ────────────────────────────────────────────────

async def send_email(to: str, subject: str, html_body: str) -> dict:
    """
    Send an HTML email. Tries App Password SMTP first (simpler), then OAuth API.
    Falls back silently if neither is configured.
    """
    recipient = to or config.GMAIL_RECIPIENT_EMAIL
    sender = config.GMAIL_SENDER_EMAIL

    if not recipient or not sender:
        logger.debug("Gmail recipient/sender not configured — email skipped")
        return {"status": "skipped"}

    # Path 1: App Password via SMTP (simpler for hackathon)
    if config.GMAIL_APP_PASSWORD:
        return _send_via_smtp(sender, recipient, subject, html_body)

    # Path 2: OAuth2 via Gmail API
    access_token = await _get_oauth_token()
    if not access_token:
        logger.warning("Gmail not configured (no APP_PASSWORD or OAuth tokens) — skipped")
        return {"status": "gmail_unavailable"}

    return await _send_via_api(sender, recipient, subject, html_body, access_token)


def _send_via_smtp(sender: str, recipient: str, subject: str, html_body: str) -> dict:
    """Send via Gmail SMTP using an App Password."""
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"Haggle <{sender}>"
        msg["To"] = recipient
        msg.attach(MIMEText(html_body, "html"))

        ctx = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ctx) as server:
            server.login(sender, config.GMAIL_APP_PASSWORD)
            server.sendmail(sender, recipient, msg.as_string())

        logger.info("Email sent via SMTP to %s: %s", recipient, subject)
        return {"status": "sent", "method": "smtp"}
    except Exception as e:
        logger.error("Gmail SMTP send failed: %s", e)
        return {"error": str(e)}


async def _send_via_api(
    sender: str, recipient: str, subject: str, html_body: str, access_token: str
) -> dict:
    """Send via Gmail REST API using OAuth2 access token."""
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"Haggle <{sender}>"
        msg["To"] = recipient
        msg.attach(MIMEText(html_body, "html"))

        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                GMAIL_SEND_URL,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                json={"raw": raw},
            )
            resp.raise_for_status()
            data = resp.json()
            logger.info("Email sent via API to %s: id=%s subject=%s", recipient, data.get("id"), subject)
            return {"status": "sent", "id": data.get("id"), "method": "api"}
    except Exception as e:
        logger.error("Gmail API send failed: %s", e)
        return {"error": str(e)}


# ── Email builders ───────────────────────────────────────────

async def send_call_summary(
    task,
    transcript: list[dict] | None = None,
    transcript_text: str | None = None,
    agent_summary: dict | None = None,
    upcoming_threats: list[dict] | None = None,
) -> dict:
    """
    Send a call outcome summary to the user.

    Args:
        task: Task object with outcome, savings, confirmation_number, etc.
        transcript: list of {role, text} dicts from demo simulation
        transcript_text: raw transcript string from Vapi end-of-call-report
    """
    action_label = task.action.value.replace("_", " ").title()
    savings = task.savings or 0
    outcome = task.outcome or "Call completed"
    conf = task.confirmation_number or ""

    subject = (
        f"Haggle: {'Saved $' + str(int(savings)) + '/mo on ' if savings > 0 else ''}"
        f"{task.company} {action_label}"
    )

    # Filter to imminent billing increases only (not informational competitor rates)
    imminent = [
        d for d in (upcoming_threats or [])
        if d.get("type") in ("BILLING_INCREASE", "RATE_INCREASE")
    ]

    html = _call_summary_html(
        company=task.company,
        action=action_label,
        user_name=task.user_name,
        outcome=outcome,
        savings=savings,
        confirmation=conf,
        transcript=transcript,
        transcript_text=transcript_text,
        dashboard_url=config.DASHBOARD_URL,
        agent_summary=agent_summary,
        upcoming_threats=imminent,
    )

    return await send_email(config.GMAIL_RECIPIENT_EMAIL, subject, html)


async def send_threat_alert(detections: list[dict]) -> dict:
    """
    Send an automated alert when the monitor detects price changes or threats.
    This is the proactive monitoring → email flow.
    """
    if not detections:
        return {"status": "no_detections"}

    billing_increases = [d for d in detections if d.get("type") in ("BILLING_INCREASE", "RATE_INCREASE")]
    count = len(detections)
    subject = (
        f"Haggle Alert: {count} financial threat{'s' if count > 1 else ''} detected"
        + (f" — {billing_increases[0]['company']} rate increase" if billing_increases else "")
    )

    html = _threat_alert_html(detections=detections, dashboard_url=config.DASHBOARD_URL)
    return await send_email(config.GMAIL_RECIPIENT_EMAIL, subject, html)


# ── HTML templates ───────────────────────────────────────────

def _upcoming_threats_html(threats: list[dict]) -> str:
    """Compact section showing imminent billing increases detected by the monitor."""
    source_labels = {
        "airbyte_stripe": ("Stripe", "#8b5cf6"),
        "overshoot_vision": ("Overshoot", "#3b82f6"),
        "tavily_search": ("Web", "#f59e0b"),
    }

    cards = []
    for d in threats:
        label, color = source_labels.get(d.get("source", ""), ("Monitor", "#6b7280"))
        company = d.get("company") or d.get("merchant", "Unknown")
        old = d.get("old_amount", d.get("old_value"))
        new = d.get("new_amount", d.get("new_value"))
        pct = d.get("increase_pct")
        summary = d.get("summary", "")

        price_row = ""
        if old is not None and new is not None:
            pct_badge = f'<span style="color:#ef4444;font-size:11px;margin-left:6px;">(+{pct}%)</span>' if pct else ""
            price_row = f'<span style="color:#ef4444;font-size:13px;font-weight:700;">${old} → ${new}{pct_badge}</span>'

        summary_row = f'<div style="color:#9ca3af;font-size:11px;margin-top:3px;">{summary}</div>' if summary else ""

        cards.append(f"""
        <div style="padding:10px 0;border-bottom:1px solid #2d1515;">
          <div style="display:flex;align-items:center;gap:8px;margin-bottom:4px;">
            <span style="background:{color}22;color:{color};font-size:9px;font-weight:700;padding:2px 7px;border-radius:99px;white-space:nowrap;text-transform:uppercase;">{label}</span>
            <span style="color:#f3f4f6;font-size:13px;font-weight:600;flex:1;">{company}</span>
            {price_row}
          </div>
          {summary_row}
        </div>""")

    # Remove bottom border on last card
    count = len(threats)
    return f"""
    <div style="background:#1c0a0a;border:1px solid #7f1d1d;border-radius:12px;padding:16px 20px;margin:16px 0;">
      <div style="display:flex;align-items:center;gap:8px;margin-bottom:10px;">
        <div style="width:6px;height:6px;background:#ef4444;border-radius:50%;"></div>
        <span style="color:#fca5a5;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:0.08em;">
          {count} Imminent Billing Increase{'s' if count > 1 else ''} Detected
        </span>
      </div>
      {''.join(cards)}
      <div style="color:#6b7280;font-size:11px;margin-top:10px;">
        Haggle is monitoring these — check your dashboard to take action.
      </div>
    </div>"""


def _call_summary_html(
    company: str,
    action: str,
    user_name: str,
    outcome: str,
    savings: float,
    confirmation: str,
    transcript: list[dict] | None,
    transcript_text: str | None,
    dashboard_url: str,
    agent_summary: dict | None = None,
    upcoming_threats: list[dict] | None = None,
) -> str:
    annual = savings * 12 if savings else 0

    savings_badge = ""
    if savings > 0:
        savings_badge = f"""
        <div style="background:#052e16;border:1px solid #166534;border-radius:8px;padding:16px 20px;margin:16px 0;text-align:center;">
          <div style="color:#4ade80;font-size:28px;font-weight:700;">${savings:.0f}<span style="font-size:16px;font-weight:400;">/month saved</span></div>
          <div style="color:#86efac;font-size:13px;margin-top:4px;">${annual:.0f}/year &middot; starts next billing cycle</div>
        </div>"""

    conf_row = ""
    if confirmation:
        conf_row = f"""
        <tr>
          <td style="padding:8px 0;color:#9ca3af;font-size:13px;border-bottom:1px solid #1f2937;">Confirmation</td>
          <td style="padding:8px 0;color:#f3f4f6;font-size:13px;font-family:monospace;font-weight:600;border-bottom:1px solid #1f2937;">{confirmation}</td>
        </tr>"""

    # Build transcript HTML
    transcript_html = ""
    if transcript:
        lines = []
        for entry in transcript:
            role = entry.get("role", "")
            text = entry.get("text", "")
            if not text:
                continue
            is_agent = role == "agent"
            bg = "#1e3a5f" if is_agent else "#1f2937"
            color = "#93c5fd" if is_agent else "#d1d5db"
            align = "left" if is_agent else "right"
            label = "Haggle Agent" if is_agent else "Customer Rep"
            lines.append(f"""
            <div style="margin:8px 0;text-align:{align};">
              <div style="display:inline-block;max-width:80%;background:{bg};border-radius:12px;padding:10px 14px;text-align:left;">
                <div style="color:{color};font-size:10px;font-weight:600;margin-bottom:4px;text-transform:uppercase;">{label}</div>
                <div style="color:#e5e7eb;font-size:13px;line-height:1.5;">{text}</div>
              </div>
            </div>""")
        if lines:
            transcript_html = f"""
            <div style="margin:24px 0;">
              <h3 style="color:#6b7280;font-size:11px;font-weight:600;letter-spacing:0.1em;text-transform:uppercase;margin:0 0 12px;">Call Transcript</h3>
              <div style="background:#0f0f14;border:1px solid #1f2937;border-radius:12px;padding:16px;max-height:600px;overflow:hidden;">
                {''.join(lines)}
              </div>
            </div>"""
    elif transcript_text:
        transcript_html = f"""
        <div style="margin:24px 0;">
          <h3 style="color:#6b7280;font-size:11px;font-weight:600;letter-spacing:0.1em;text-transform:uppercase;margin:0 0 12px;">Call Transcript</h3>
          <div style="background:#0f0f14;border:1px solid #1f2937;border-radius:12px;padding:16px;font-family:monospace;font-size:12px;color:#9ca3af;white-space:pre-wrap;line-height:1.6;">{transcript_text[:3000]}</div>
        </div>"""

    # Build upcoming threats block (imminent billing increases only)
    threats_html = _upcoming_threats_html(upcoming_threats) if upcoming_threats else ""

    # Build agent summary block
    summary_html = ""
    if agent_summary:
        narrative = agent_summary.get("narrative", "")
        key_points = agent_summary.get("key_points", [])
        points_html = "".join(
            f'<li style="padding:3px 0;color:#d1d5db;font-size:13px;">&#10003;&nbsp; {pt}</li>'
            for pt in key_points
        )
        summary_html = f"""
        <div style="background:#0c1a2e;border:1px solid #1e3a5f;border-radius:12px;padding:20px 24px;margin:16px 0;">
          <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;">
            <div style="width:6px;height:6px;background:#3b82f6;border-radius:50%;"></div>
            <span style="color:#93c5fd;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:0.08em;">Agent Summary</span>
          </div>
          <p style="color:#e5e7eb;font-size:14px;line-height:1.7;margin:0 0 14px;">{narrative}</p>
          <ul style="margin:0;padding:0;list-style:none;">
            {points_html}
          </ul>
        </div>"""

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"></head>
<body style="margin:0;padding:0;background:#111827;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
  <div style="max-width:600px;margin:0 auto;padding:24px 16px;">

    <!-- Header -->
    <div style="background:linear-gradient(135deg,#0f0f14 0%,#1a1a2e 100%);border:1px solid #1f2937;border-radius:16px;padding:24px;margin-bottom:16px;text-align:center;">
      <div style="font-size:22px;font-weight:800;color:#ffffff;letter-spacing:-0.5px;">
        Life<span style="color:#3b82f6;">Pilot</span>
      </div>
      <div style="color:#6b7280;font-size:12px;margin-top:4px;">Autonomous Consumer Advocacy Agent</div>
    </div>

    <!-- Result card -->
    <div style="background:#111827;border:1px solid #1f2937;border-radius:16px;padding:24px;margin-bottom:16px;">
      <div style="display:flex;align-items:center;margin-bottom:16px;">
        <div style="width:8px;height:8px;background:#4ade80;border-radius:50%;margin-right:8px;"></div>
        <span style="color:#4ade80;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:0.08em;">Call Completed</span>
      </div>

      <h2 style="color:#ffffff;font-size:20px;font-weight:700;margin:0 0 4px;">{company}</h2>
      <div style="color:#6b7280;font-size:13px;margin-bottom:16px;">{action} &middot; {user_name}'s account</div>

      {savings_badge}

      <table style="width:100%;border-collapse:collapse;margin:16px 0;">
        <tr>
          <td style="padding:8px 0;color:#9ca3af;font-size:13px;border-bottom:1px solid #1f2937;">Outcome</td>
          <td style="padding:8px 0;color:#f3f4f6;font-size:13px;border-bottom:1px solid #1f2937;">{outcome}</td>
        </tr>
        {conf_row}
        <tr>
          <td style="padding:8px 0;color:#9ca3af;font-size:13px;">Account holder</td>
          <td style="padding:8px 0;color:#f3f4f6;font-size:13px;">{user_name}</td>
        </tr>
      </table>
    </div>

    {summary_html}

    {threats_html}

    {transcript_html}

    <!-- CTA -->
    <div style="text-align:center;margin:24px 0;">
      <a href="{dashboard_url}" style="background:#3b82f6;color:#ffffff;text-decoration:none;padding:12px 32px;border-radius:8px;font-weight:600;font-size:14px;display:inline-block;">
        View Dashboard
      </a>
    </div>

    <p style="color:#374151;font-size:11px;text-align:center;margin-top:24px;">
      Haggle automatically made this call on your behalf.<br>
      You can review all call recordings and transcripts in your dashboard.
    </p>
  </div>
</body>
</html>"""


def _threat_alert_html(detections: list[dict], dashboard_url: str) -> str:
    source_labels = {
        "airbyte_stripe": ("Stripe", "#8b5cf6"),
        "overshoot_vision": ("Overshoot Vision", "#3b82f6"),
        "tavily_search": ("Web Monitor", "#f59e0b"),
    }

    detection_cards = []
    for d in detections:
        src = d.get("source", "monitor")
        label, color = source_labels.get(src, ("Monitor", "#6b7280"))
        company = d.get("company") or d.get("merchant", "Unknown")
        d_type = (d.get("type") or "").replace("_", " ").title()
        old = d.get("old_amount", d.get("old_value"))
        new = d.get("new_amount", d.get("new_value"))
        pct = d.get("increase_pct")
        summary = d.get("summary", "")
        relevance = d.get("relevance", "")

        price_change = ""
        if old is not None and new is not None:
            price_change = f"""
            <div style="margin:8px 0;">
              <span style="color:#ef4444;font-size:16px;font-weight:700;">${old} → ${new}</span>
              {f'<span style="color:#ef4444;font-size:12px;margin-left:8px;">(+{pct}%)</span>' if pct else ''}
            </div>"""

        detection_cards.append(f"""
        <div style="background:#111827;border:1px solid #ef4444;border-left:3px solid #ef4444;border-radius:12px;padding:16px;margin-bottom:12px;">
          <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
            <span style="background:{color}22;color:{color};font-size:10px;font-weight:700;padding:2px 8px;border-radius:99px;text-transform:uppercase;">{label}</span>
            <span style="color:#6b7280;font-size:10px;text-transform:uppercase;">{d_type}</span>
          </div>
          <div style="color:#ffffff;font-size:15px;font-weight:600;">{company}</div>
          {price_change}
          {f'<div style="color:#9ca3af;font-size:12px;margin-top:6px;">{summary}</div>' if summary else ''}
          {f'<div style="color:#f59e0b;font-size:11px;margin-top:4px;">→ {relevance}</div>' if relevance else ''}
        </div>""")

    count = len(detections)
    billing_count = sum(1 for d in detections if d.get("type") in ("BILLING_INCREASE", "RATE_INCREASE"))

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"></head>
<body style="margin:0;padding:0;background:#111827;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
  <div style="max-width:600px;margin:0 auto;padding:24px 16px;">

    <!-- Header -->
    <div style="background:linear-gradient(135deg,#0f0f14 0%,#1a1a2e 100%);border:1px solid #1f2937;border-radius:16px;padding:24px;margin-bottom:16px;text-align:center;">
      <div style="font-size:22px;font-weight:800;color:#ffffff;letter-spacing:-0.5px;">
        Life<span style="color:#3b82f6;">Pilot</span>
      </div>
      <div style="color:#6b7280;font-size:12px;margin-top:4px;">Autonomous Consumer Advocacy Agent</div>
    </div>

    <!-- Alert banner -->
    <div style="background:#1c0a0a;border:1px solid #7f1d1d;border-radius:12px;padding:16px 20px;margin-bottom:20px;display:flex;align-items:center;">
      <div style="background:#ef4444;width:8px;height:8px;border-radius:50%;margin-right:12px;flex-shrink:0;"></div>
      <div>
        <div style="color:#fca5a5;font-weight:700;font-size:14px;">
          {count} financial threat{'s' if count > 1 else ''} detected
        </div>
        <div style="color:#7f1d1d;font-size:12px;margin-top:2px;">
          {f'{billing_count} billing increase{"s" if billing_count > 1 else ""} require immediate action' if billing_count > 0 else 'Review and take action from your dashboard'}
        </div>
      </div>
    </div>

    <!-- Detections -->
    {''.join(detection_cards)}

    <!-- What Haggle can do -->
    <div style="background:#0c1a2e;border:1px solid #1e3a5f;border-radius:12px;padding:16px 20px;margin:20px 0;">
      <div style="color:#93c5fd;font-size:12px;font-weight:600;margin-bottom:8px;">What Haggle can do right now</div>
      <ul style="margin:0;padding-left:16px;color:#9ca3af;font-size:13px;line-height:1.8;">
        <li>Call {detections[0].get('company') or detections[0].get('merchant', 'your provider')} and negotiate your rate back down</li>
        <li>Research competitor rates and prepare leverage arguments</li>
        <li>Get a confirmation number and update your knowledge graph</li>
        <li>Send you a follow-up summary with exact savings</li>
      </ul>
    </div>

    <!-- CTA -->
    <div style="text-align:center;margin:24px 0;">
      <a href="{dashboard_url}" style="background:#ef4444;color:#ffffff;text-decoration:none;padding:14px 40px;border-radius:8px;font-weight:700;font-size:15px;display:inline-block;">
        Handle It Now →
      </a>
    </div>

    <p style="color:#374151;font-size:11px;text-align:center;margin-top:24px;">
      Haggle monitors your financial accounts and the web automatically.<br>
      These alerts are sent whenever a threat is detected. Unsubscribe in dashboard settings.
    </p>
  </div>
</body>
</html>"""
