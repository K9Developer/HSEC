import smtplib, ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv
import os
load_dotenv()

PLAINTEXT_BODY = """\
HSEC Password Reset Code

You requested to reset your HSEC password.

Your reset code: {RESET_CODE}

This code is valid for {TIME_LEFT} minutes.
If you didn’t request this, you can ignore this message.

© 2025 HSEC
"""

HTML_BODY = """\
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>Password Reset Code</title>
</head>
<body style="margin:0;padding:0;font-family:Arial,sans-serif;background-color:#f2f4f6;">
  <table width="100%" cellpadding="0" cellspacing="0">
    <tr>
      <td align="center" style="padding:40px 0;">
        <table width="600" style="background-color:#ffffff;border-radius:8px;box-shadow:0 0 10px rgba(0,0,0,0.05);">
          <tr>
            <td align="center" style="background-color:#0f62fe;padding:24px;">
              <img src="https://i.ibb.co/9kZpQMLx/hsec.png" width="120" alt="HSEC Logo" />
            </td>
          </tr>
          <tr>
            <td style="padding:40px;color:#333333;font-size:16px;">
              <p style="margin-top:0;">Hi there,</p>
              <p>You recently requested to reset your <strong>HSEC</strong> account password.</p>
              <p>Use the following code to reset it. This code is valid for <strong>{TIME_LEFT} minutes</strong>.</p>

              <div style="margin:30px 0; text-align:center;">
                <div style="display:inline-block;padding:16px 32px;font-size:28px;font-weight:bold;color:#0f62fe;background:#f0f4ff;border-radius:8px;letter-spacing:4px;">
                  {RESET_CODE}
                </div>
              </div>

              <p>If you didn’t request this, you can safely ignore this email.</p>
              <p style="margin-top:40px;font-size:12px;color:#888888;">© 2025 HSEC. All rights reserved.</p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""

def send_reset_password_email(reset_code, recipient_email, time_left, logger):
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "Your HSEC Password Reset Code"
        msg["From"] = "HSEC <tim14321234124@gmail.com>"
        msg["To"] = recipient_email

        msg.attach(MIMEText(PLAINTEXT_BODY.replace("{RESET_CODE}", str(reset_code)).replace("{TIME_LEFT}", str(time_left//60)), "plain"))
        msg.attach(MIMEText(HTML_BODY.replace("{RESET_CODE}", str(reset_code)).replace("{TIME_LEFT}", str(time_left//60)), "html"))

        context = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as smtp:
            smtp.login("tim14321234124@gmail.com", os.environ['GMAIL_PASS'])
            smtp.send_message(msg)

        logger.info(f"Sent reset password email to {recipient_email} with code {reset_code}")
        return True
    except Exception as e:
        logger.error(f"Failed to send reset password email to {recipient_email}: {e}")
        return False