"""Email notification via SMTP."""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict

from ..config import Config


def send_email(config: Config, subject: str, html_body: str) -> bool:
    """Send an email notification. Returns True on success."""
    if not config.email_enabled:
        return False

    msg = MIMEMultipart("alternative")
    msg["From"] = config.email_sender
    msg["To"] = config.email_receiver
    msg["Subject"] = subject
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        if config.email_use_ssl:
            with smtplib.SMTP_SSL(config.email_smtp_server, config.email_smtp_port) as server:
                server.login(config.email_sender, config.email_password)
                server.sendmail(config.email_sender, config.email_receiver, msg.as_string())
        else:
            with smtplib.SMTP(config.email_smtp_server, config.email_smtp_port) as server:
                server.starttls()
                server.login(config.email_sender, config.email_password)
                server.sendmail(config.email_sender, config.email_receiver, msg.as_string())
        return True
    except Exception as e:
        print(f"[Email] Failed to send: {e}")
        return False


def build_paper_summary_html(papers: List[Dict]) -> str:
    """Build HTML email body from a list of papers."""
    rows = ""
    for p in papers:
        rows += f"""
        <tr>
            <td style="padding:10px;border-bottom:1px solid #eee;">
                <a href="{p['link']}" style="font-size:14px;font-weight:bold;color:#1a73e8;text-decoration:none;">
                    {p['title']}
                </a>
                <p style="font-size:12px;color:#666;margin:4px 0;">{p['authors']}</p>
                <p style="font-size:13px;color:#333;margin:4px 0;">{p['summary_zh']}</p>
                {("<p style=\"font-size:12px;color:#888;margin:4px 0;\">- " + p['relevance_reason'] + "</p>") if p.get('relevance_reason') else ""}
            </td>
        </tr>"""

    return f"""<html><body style="font-family:sans-serif;max-width:700px;margin:0 auto;">
    <h2 style="color:#333;">arXiv 论文日报</h2>
    <table style="width:100%;border-collapse:collapse;">{rows}</table>
    <p style="font-size:12px;color:#999;margin-top:20px;">由 auto-arXiv 自动生成</p>
</body></html>"""
