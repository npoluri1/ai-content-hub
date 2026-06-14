import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate
from typing import Optional

from ..core.config import settings
from ..core.models import ContentItem, ClassifiedItem

logger = logging.getLogger(__name__)


class NewsletterSender:
    def __init__(
        self,
        smtp_host: str = None,
        smtp_port: int = None,
        smtp_user: str = None,
        smtp_pass: str = None,
    ):
        self.smtp_host = smtp_host or getattr(settings, "SMTP_HOST", None)
        self.smtp_port = smtp_port or getattr(settings, "SMTP_PORT", 587)
        self.smtp_user = smtp_user or getattr(settings, "SMTP_USER", None)
        self.smtp_pass = smtp_pass or getattr(settings, "SMTP_PASS", None)
        self.from_email = getattr(settings, "FROM_EMAIL", "noreply@aicontenthub.local")

    def _connect(self) -> Optional[smtplib.SMTP]:
        if not self.smtp_host:
            logger.warning("SMTP not configured: no host set")
            return None
        try:
            server = smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=10)
            server.ehlo()
            if server.has_extn("STARTTLS"):
                server.starttls()
                server.ehlo()
            if self.smtp_user and self.smtp_pass:
                server.login(self.smtp_user, self.smtp_pass)
            return server
        except Exception as e:
            logger.error("SMTP connection failed: %s", e)
            return None

    def send_digest(
        self, to_email: str, digest_text: str, subject: str = None
    ) -> bool:
        subject = subject or "AI Content Hub - Your Daily Digest"
        server = self._connect()
        if not server:
            logger.info("Digest email not sent (no SMTP): %s chars to %s", len(digest_text), to_email)
            return False
        try:
            msg = MIMEText(digest_text, "plain", "utf-8")
            msg["Subject"] = subject
            msg["From"] = self.from_email
            msg["To"] = to_email
            msg["Date"] = formatdate(localtime=True)
            server.sendmail(self.from_email, [to_email], msg.as_string())
            logger.info("Digest email sent to %s", to_email)
            return True
        except Exception as e:
            logger.error("Failed to send digest email: %s", e)
            return False
        finally:
            try:
                server.quit()
            except Exception:
                pass

    def send_html_digest(
        self, to_email: str, html_content: str, subject: str = None
    ) -> bool:
        subject = subject or "AI Content Hub - Your Daily Digest"
        server = self._connect()
        if not server:
            logger.info("HTML digest not sent (no SMTP) to %s", to_email)
            return False
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.from_email
            msg["To"] = to_email
            msg["Date"] = formatdate(localtime=True)
            msg.attach(MIMEText("Please view this email in an HTML-compatible client.", "plain", "utf-8"))
            msg.attach(MIMEText(html_content, "html", "utf-8"))
            server.sendmail(self.from_email, [to_email], msg.as_string())
            logger.info("HTML digest email sent to %s", to_email)
            return True
        except Exception as e:
            logger.error("Failed to send HTML digest email: %s", e)
            return False
        finally:
            try:
                server.quit()
            except Exception:
                pass

    def send_alert(self, to_email: str, topic: str, item: ContentItem) -> bool:
        subject = f"AI Content Hub Alert: {topic}"
        html = self._build_html_template([item], [topic])
        return self.send_html_digest(to_email, html, subject=subject)

    def send_weekly_newsletter(
        self, to_email: str, items: list[ContentItem], topics: list[str]
    ) -> bool:
        subject = "AI Content Hub - Weekly Newsletter"
        html = self._build_html_template(items, topics)
        # Prepend a trends section
        trends_section = "<h2 style='color: #00d4aa; margin-top: 30px;'>Trending This Week</h2><p>Curated AI highlights from across the web.</p>"
        html = html.replace("<body>", f"<body>{trends_section}")
        return self.send_html_digest(to_email, html, subject=subject)

    def _build_html_template(
        self, items: list[ContentItem], topics: list[str]
    ) -> str:
        topic_items = {t: [] for t in topics}
        untagged = []
        for item in items:
            matched = False
            for t in topics:
                if t.lower().replace(" ", "_") in [x.lower().replace(" ", "_") for x in item.topics]:
                    topic_items[t].append(item)
                    matched = True
                    break
            if not matched:
                untagged.append(item)

        source_counts = {}
        for item in items:
            source_counts[item.source] = source_counts.get(item.source, 0) + 1

        sections_html = ""
        for topic in topics:
            topic_items_list = topic_items.get(topic, [])
            if not topic_items_list:
                continue
            display_name = topic.replace("_", " ").title()
            items_html = ""
            for item_item in topic_items_list[:10]:
                snippet = (item_item.content_cleaned or item_item.content)[:200]
                if len(snippet) == 200:
                    snippet = snippet.rsplit(" ", 1)[0] + "..."
                source_badge = f"<span style='background:#333;color:#00d4aa;padding:2px 8px;border-radius:4px;font-size:12px;'>{item_item.source}</span>"
                items_html += f"""
                <div style="margin-bottom:20px;padding:15px;background:#1e1e1e;border-radius:8px;border-left:3px solid #00d4aa;">
                    <div style="margin-bottom:6px;">{source_badge}</div>
                    <h3 style="margin:0 0 8px;font-size:16px;"><a href="{item_item.url}" style="color:#e0e0e0;text-decoration:none;">{item_item.title}</a></h3>
                    <p style="margin:0;color:#aaa;font-size:13px;line-height:1.4;">{snippet}</p>
                    <a href="{item_item.url}" style="display:inline-block;margin-top:8px;color:#00d4aa;font-size:13px;text-decoration:none;">Read more &rarr;</a>
                </div>"""
            sections_html += f"""
            <div style="margin-bottom:30px;">
                <div style="border-bottom:2px solid #333;padding-bottom:8px;margin-bottom:16px;">
                    <h2 style="color:#00d4aa;margin:0;font-size:20px;">{display_name}</h2>
                </div>
                {items_html}
            </div>"""

        footer_stats = " | ".join(f"{src}: {cnt}" for src, cnt in sorted(source_counts.items()))

        html = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;background-color:#121212;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background-color:#121212;"><tr><td align="center">
<table width="600" cellpadding="0" cellspacing="0" style="background-color:#1a1a1a;border-radius:12px;margin:20px 0;">
<tr><td style="padding:30px 30px 20px;text-align:center;border-bottom:1px solid #333;">
    <h1 style="color:#00d4aa;margin:0;font-size:28px;">AI Content Hub</h1>
    <p style="color:#888;margin:8px 0 0;font-size:14px;">Curated AI Intelligence</p>
</td></tr>
<tr><td style="padding:30px;">
    {sections_html}
</td></tr>
<tr><td style="padding:20px 30px;border-top:1px solid #333;text-align:center;">
    <p style="color:#666;font-size:12px;margin:0 0 8px;">{footer_stats}</p>
    <p style="color:#666;font-size:12px;margin:0;">
        <a href="#" style="color:#555;text-decoration:none;">Unsubscribe</a> &middot;
        <a href="#" style="color:#555;text-decoration:none;">Preferences</a>
    </p>
</td></tr>
</table>
</td></tr></table>
</body>
</html>"""
        return html
