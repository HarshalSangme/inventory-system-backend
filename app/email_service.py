"""
Email Service for Jot Auto Parts W.L.L
Centralized email sending with branded HTML templates.
Uses the same static assets as invoice_pdf.py (Invoice_Header.png, shop_footer_board.jpg).
"""
import os
import base64
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage

logger = logging.getLogger(__name__)

# Static assets directory (same as invoice_pdf.py)
STATIC_DIR = os.path.join(os.path.dirname(__file__), '..', 'static')


class EmailService:
    """Centralized email service with branded templates."""

    def __init__(self):
        self.smtp_host = os.environ["SMTP_HOST"]
        self.smtp_port = int(os.environ["SMTP_PORT"])
        self.smtp_user = os.environ["SMTP_USER"]
        self.smtp_password = os.environ["SMTP_PASSWORD"]
        self.verification_base_url = os.getenv("VERIFICATION_BASE_URL", "https://yourdomain.com")

    def _send(self, to_email: str, subject: str, html_body: str, embed_images: dict | None = None):
        """Send an email with optional CID-embedded images."""
        msg = MIMEMultipart("related")
        msg["Subject"] = subject
        msg["From"] = self.smtp_user
        msg["To"] = to_email

        # Attach HTML body
        msg.attach(MIMEText(html_body, "html"))

        # Embed images as CID attachments (for universal email client support)
        if embed_images:
            for cid, filepath in embed_images.items():
                if os.path.exists(filepath):
                    with open(filepath, "rb") as f:
                        img_data = f.read()
                    ext = os.path.splitext(filepath)[1].lstrip(".").lower()
                    if ext == "jpg":
                        ext = "jpeg"
                    img = MIMEImage(img_data, _subtype=ext)
                    img.add_header("Content-ID", f"<{cid}>")
                    img.add_header("Content-Disposition", "inline", filename=os.path.basename(filepath))
                    msg.attach(img)

        with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(self.smtp_user, self.smtp_password)
            server.sendmail(self.smtp_user, to_email, msg.as_string())

        logger.info(f"Email sent to {to_email}: {subject}")

    # ──────────────────────────────────────────────
    #  Base Template
    # ──────────────────────────────────────────────

    def _wrap_in_template(self, content_html: str, preheader: str = "") -> str:
        """Wrap content in the branded Jot Auto Parts email template."""
        return f"""\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Jot Auto Parts W.L.L</title>
  <!--[if mso]><noscript><xml><o:OfficeDocumentSettings><o:PixelsPerInch>96</o:PixelsPerInch></o:OfficeDocumentSettings></xml></noscript><![endif]-->
</head>
<body style="margin:0; padding:0; background-color:#f4f4f7; font-family:Arial, Helvetica, sans-serif; -webkit-font-smoothing:antialiased;">
  <!-- Preheader (hidden preview text) -->
  <span style="display:none !important; visibility:hidden; mso-hide:all; font-size:1px; line-height:1px; max-height:0; max-width:0; opacity:0; overflow:hidden;">
    {preheader}
  </span>

  <!-- Outer wrapper -->
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:#f4f4f7;">
    <tr>
      <td align="center" style="padding:24px 16px;">

        <!-- Main card -->
        <table role="presentation" width="600" cellpadding="0" cellspacing="0" style="max-width:600px; width:100%; background-color:#ffffff; border-radius:12px; overflow:hidden; box-shadow:0 4px 24px rgba(0,0,0,0.08);">

          <!-- Header with logo -->
          <tr>
            <td style="background: linear-gradient(135deg, #4a4a4a 0%, #5e5e5e 50%, #4a4a4a 100%); padding:0;">
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
                <tr>
                  <td align="center" style="padding:24px 32px 16px;">
                    <img src="cid:header_logo" alt="Jot Auto Parts W.L.L" style="max-width:420px; width:100%; height:auto;" />
                  </td>
                </tr>
                <tr>
                  <td style="height:4px; background:linear-gradient(90deg, #E8571E 0%, #D96B00 50%, #E8571E 100%);"></td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- Body content -->
          <tr>
            <td style="padding:32px 40px 16px;">
              {content_html}
            </td>
          </tr>

          <!-- Divider -->
          <tr>
            <td style="padding:0 40px;">
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
                <tr><td style="border-top:1px solid #e8e8e8; height:1px; font-size:1px;">&nbsp;</td></tr>
              </table>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="padding:20px 40px 12px;">
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
                <tr>
                  <td align="center">
                    <p style="margin:0 0 6px; font-size:13px; font-weight:bold; color:#4a4a4a;">
                      JOT AUTO PARTS W.L.L
                    </p>
                    <p style="margin:0 0 4px; font-size:11px; color:#888888; direction:rtl;">
                      جـوت لقطع غيار السيارات ذ.م.م
                    </p>
                    <p style="margin:0 0 4px; font-size:11px; color:#888888;">
                      Shop 128, Road 6, Block 604 &bull; Kingdom of Bahrain
                    </p>
                    <p style="margin:0 0 4px; font-size:11px; color:#888888;">
                      CR.NO 174260-1
                    </p>
                    <p style="margin:0 0 4px; font-size:11px; color:#888888;">
                      &#9742; 36341106, 36024064 &nbsp;&bull;&nbsp;
                      &#9993; jotautopartswll@gmail.com
                    </p>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- Footer brands banner -->
          <tr>
            <td style="padding:0;">
              <img src="cid:footer_banner" alt="Toyota | Hyundai | Nissan" style="width:100%; height:auto; display:block; border-radius:0 0 12px 12px;" />
            </td>
          </tr>

        </table>

        <!-- Sub-footer -->
        <table role="presentation" width="600" cellpadding="0" cellspacing="0" style="max-width:600px; width:100%;">
          <tr>
            <td align="center" style="padding:16px 0 0;">
              <p style="margin:0; font-size:10px; color:#aaaaaa;">
                &copy; {self._current_year()} Jot Auto Parts W.L.L &mdash; All rights reserved.
              </p>
            </td>
          </tr>
        </table>

      </td>
    </tr>
  </table>
</body>
</html>"""

    @staticmethod
    def _current_year() -> str:
        from datetime import datetime
        return str(datetime.now().year)

    def _get_embedded_images(self) -> dict:
        """Return the standard image CIDs used by the base template."""
        return {
            "header_logo": os.path.join(STATIC_DIR, "Invoice_Header.png"),
            "footer_banner": os.path.join(STATIC_DIR, "shop_footer_board.jpg"),
        }

    # ──────────────────────────────────────────────
    #  Email Types
    # ──────────────────────────────────────────────

    def send_verification_email(self, username: str, email: str, token: str):
        """Send email verification with branded template."""
        verification_link = f"{self.verification_base_url}/verify-email/{token}"

        content = f"""\
<h2 style="margin:0 0 8px; font-size:22px; color:#4a4a4a; font-weight:700;">
  Verify Your Email Address
</h2>
<p style="margin:0 0 20px; font-size:14px; color:#888;">
  Account Verification &bull; Jot Auto Parts Inventory System
</p>

<p style="margin:0 0 12px; font-size:15px; color:#333333; line-height:1.6;">
  Hello <strong>{username}</strong>,
</p>
<p style="margin:0 0 24px; font-size:15px; color:#333333; line-height:1.6;">
  Thank you for registering. Please verify your email address to activate your account
  and access the Jot Auto Parts inventory system.
</p>

<!-- CTA Button -->
<table role="presentation" cellpadding="0" cellspacing="0" style="margin:0 auto 24px;">
  <tr>
    <td align="center" style="border-radius:8px; background:linear-gradient(135deg, #E8571E 0%, #D96B00 100%);">
      <a href="{verification_link}"
         target="_blank"
         style="display:inline-block; padding:14px 40px; font-size:16px; font-weight:700;
                color:#ffffff; text-decoration:none; border-radius:8px; letter-spacing:0.5px;">
        &#10003;&nbsp; Verify My Email
      </a>
    </td>
  </tr>
</table>

<p style="margin:0 0 8px; font-size:12px; color:#999999; text-align:center;">
  Or copy and paste this link into your browser:
</p>
<p style="margin:0 0 24px; font-size:12px; color:#E8571E; text-align:center; word-break:break-all;">
  <a href="{verification_link}" style="color:#E8571E; text-decoration:underline;">{verification_link}</a>
</p>

<!-- Info box -->
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin:0 0 8px;">
  <tr>
    <td style="background-color:#fef8f4; border-left:4px solid #E8571E; padding:12px 16px; border-radius:0 6px 6px 0;">
      <p style="margin:0; font-size:12px; color:#666666; line-height:1.5;">
        <strong>&#9888; This link expires in 24 hours.</strong><br/>
        If you did not request this verification, you can safely ignore this email.
      </p>
    </td>
  </tr>
</table>"""

        html = self._wrap_in_template(content, preheader="Verify your email to access Jot Auto Parts inventory system")
        images = self._get_embedded_images()

        self._send(
            to_email=email,
            subject="Verify Your Email — Jot Auto Parts W.L.L",
            html_body=html,
            embed_images=images,
        )

    def send_welcome_email(self, username: str, email: str):
        """Send a welcome email after successful verification."""
        content = f"""\
<h2 style="margin:0 0 8px; font-size:22px; color:#4a4a4a; font-weight:700;">
  Welcome to Jot Auto Parts! &#127881;
</h2>
<p style="margin:0 0 20px; font-size:14px; color:#888;">
  Your account is now active
</p>

<p style="margin:0 0 12px; font-size:15px; color:#333333; line-height:1.6;">
  Hello <strong>{username}</strong>,
</p>
<p style="margin:0 0 24px; font-size:15px; color:#333333; line-height:1.6;">
  Your email has been verified successfully! You now have full access to the
  Jot Auto Parts inventory management system.
</p>

<!-- Features list -->
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin:0 0 24px;">
  <tr>
    <td style="padding:8px 0; font-size:14px; color:#333;">&#9989; &nbsp;Manage products &amp; inventory</td>
  </tr>
  <tr>
    <td style="padding:8px 0; font-size:14px; color:#333;">&#9989; &nbsp;Create invoices &amp; transactions</td>
  </tr>
  <tr>
    <td style="padding:8px 0; font-size:14px; color:#333;">&#9989; &nbsp;View reports &amp; dashboard analytics</td>
  </tr>
</table>

<p style="margin:0 0 8px; font-size:13px; color:#666666; line-height:1.5;">
  If you have any questions, contact us at
  <a href="mailto:jotautopartswll@gmail.com" style="color:#E8571E;">jotautopartswll@gmail.com</a>.
</p>"""

        html = self._wrap_in_template(content, preheader="Your Jot Auto Parts account is now active!")
        images = self._get_embedded_images()

        self._send(
            to_email=email,
            subject="Welcome to Jot Auto Parts W.L.L!",
            html_body=html,
            embed_images=images,
        )

    def send_customer_notification(self, customer_email: str, customer_name: str, subject: str, message: str):
        """Send a generic branded notification to a customer."""
        content = f"""\
<h2 style="margin:0 0 8px; font-size:22px; color:#4a4a4a; font-weight:700;">
  {subject}
</h2>
<p style="margin:0 0 20px; font-size:14px; color:#888;">
  Notification from Jot Auto Parts W.L.L
</p>

<p style="margin:0 0 12px; font-size:15px; color:#333333; line-height:1.6;">
  Dear <strong>{customer_name}</strong>,
</p>
<div style="margin:0 0 24px; font-size:15px; color:#333333; line-height:1.7;">
  {message}
</div>

<p style="margin:0; font-size:13px; color:#666666; line-height:1.5;">
  Thank you for choosing Jot Auto Parts W.L.L. For enquiries, reach us at
  <a href="mailto:jotautopartswll@gmail.com" style="color:#E8571E;">jotautopartswll@gmail.com</a>
  or call <strong>36341106 / 36024064</strong>.
</p>"""

        html = self._wrap_in_template(content, preheader=f"{subject} — Jot Auto Parts W.L.L")
        images = self._get_embedded_images()

        self._send(
            to_email=customer_email,
            subject=f"{subject} — Jot Auto Parts W.L.L",
            html_body=html,
            embed_images=images,
        )
