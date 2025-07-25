from email.mime.image import MIMEImage
import smtplib, ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv
import os
load_dotenv()

PASS_RESET_PLAINTEXT_BODY = """HSEC Password Reset Code\nYou requested to reset your HSEC password.\nYour reset code: {RESET_CODE}\nThis code is valid for {TIME_LEFT} minutes.\nIf you didn’t request this, you can ignore this message.\n\n© 2025 HSEC"""
PASS_RESET_HTML_BODY = """<!doctypehtml><meta charset=UTF-8><title>Password Reset Code</title><body style=margin:0;padding:0;font-family:Arial,sans-serif;background-color:#f2f4f6><table width=100% cellpadding=0 cellspacing=0><tr><td style="padding:40px 0"align=center><table width=600 style="background-color:#fff;border-radius:8px;box-shadow:0 0 10px rgba(0,0,0,.05)"><tr><td style=background-color:#0f62fe;padding:24px align=center><img alt="HSEC Logo"src=https://raw.githubusercontent.com/K9Developer/HSEC/refs/heads/master/assets/hsec.png width=120><tr><td style=padding:40px;color:#333;font-size:16px><p style=margin-top:0>Hi there,<p>You recently requested to reset your <strong>HSEC</strong> account password.<p>Use the following code to reset it. This code is valid for <strong>{TIME_LEFT} minutes</strong>.<div style="margin:30px 0;text-align:center"><div style="display:inline-block;padding:16px 32px;font-size:28px;font-weight:700;color:#0f62fe;background:#f0f4ff;border-radius:8px;letter-spacing:4px">{RESET_CODE}</div></div><p>If you didn’t request this, you can safely ignore this email.<p style=margin-top:40px;font-size:12px;color:#888>© 2025 HSEC. All rights reserved.</table></table>"""

def send_reset_password_email(reset_code, recipient_email, time_left, logger):
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "Your HSEC Password Reset Code"
        msg["From"] = "HSEC <tim14321234124@gmail.com>"
        msg["To"] = recipient_email

        msg.attach(MIMEText(PASS_RESET_PLAINTEXT_BODY.replace("{RESET_CODE}", str(reset_code)).replace("{TIME_LEFT}", str(time_left//60)), "plain"))
        msg.attach(MIMEText(PASS_RESET_HTML_BODY.replace("{RESET_CODE}", str(reset_code)).replace("{TIME_LEFT}", str(time_left//60)), "html"))

        context = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as smtp:
            smtp.login("tim14321234124@gmail.com", os.environ['GMAIL_PASS'])
            smtp.send_message(msg)

        logger.info(f"Sent reset password email to {recipient_email} with code {reset_code}")
        return True
    except Exception as e:
        logger.error(f"Failed to send reset password email to {recipient_email}: {e}")
        return False



CAMERA_SHARE_PLAINTEXT_BODY = """HSEC Camera Shared With You\n{SHARER_EMAIL} just shared a camera with you.\nCamera MAC: {CAMERA_MAC}\nYou can now view this camera from your HSEC dashboard.\nIf you didn’t expect this, you can ignore this message.\n\n© 2025 HSEC"""
CAMERA_SHARE_HTML_BODY = """<!doctypehtml><meta charset=UTF-8><title>Camera Shared With You</title><body style=margin:0;padding:0;font-family:Arial,sans-serif;background-color:#f2f4f6><table width=100% cellpadding=0 cellspacing=0><tr><td style="padding:40px 0"align=center><table width=600 style="background-color:#fff;border-radius:8px;box-shadow:0 0 10px rgba(0,0,0,.05)"><tr><td style=background-color:#0f62fe;padding:24px align=center><img alt="HSEC Logo"src=https://raw.githubusercontent.com/K9Developer/HSEC/refs/heads/master/assets/hsec.png width=120><tr><td style=padding:40px;color:#333;font-size:16px><p style=margin-top:0>Hi there,<p><strong>{SHARER_EMAIL}</strong> just shared a camera with you on <strong>HSEC</strong>.<p>Camera MAC address:<div style="margin:30px 0;text-align:center"><div style="display:inline-block;padding:16px 32px;font-size:24px;font-weight:700;color:#0f62fe;background:#f0f4ff;border-radius:8px;letter-spacing:1px">{CAMERA_MAC}</div></div><p>Log in to your dashboard to start viewing the live feed.<p>If you didn’t expect this, you can safely ignore this email.<p style=margin-top:40px;font-size:12px;color:#888>© 2025 HSEC. All rights reserved.</table></table>"""

def send_camera_share_email(sharer, recipient_email, mac, logger):
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "HSEC Camera Shared With You"
        msg["From"] = "HSEC <tim14321234124@gmail.com>"
        msg["To"] = recipient_email

        msg.attach(MIMEText(CAMERA_SHARE_PLAINTEXT_BODY.replace("{SHARER_EMAIL}", sharer).replace("{CAMERA_MAC}", mac), "plain"))
        msg.attach(MIMEText(CAMERA_SHARE_HTML_BODY.replace("{SHARER_EMAIL}", sharer).replace("{CAMERA_MAC}", mac), "html"))

        context = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as smtp:
            smtp.login("tim14321234124@gmail.com", os.environ['GMAIL_PASS'])
            smtp.send_message(msg)

        logger.info(f"Sent reset password email to {recipient_email} with camera {mac} shared by {sharer}")
        return True
    except Exception as e:
        logger.error(f"Failed to send reset password email to {recipient_email}: {e}")
        return False


MOTION_ALERT_PLAINTEXT_BODY = """HSEC Motion Alert\n\nMotion was detected by your camera.\n\nCamera MAC: {CAMERA_MAC}\nDetected Objects: {CLASSES}\n\nCheck your HSEC dashboard to view recent activity.\n\n© 2025 HSEC"""
MOTION_ALERT_HTML_BODY = """<!doctypehtml><meta charset=UTF-8><title>Motion Detected</title><body style=margin:0;padding:0;font-family:Arial,sans-serif;background-color:#f2f4f6><table width=100% cellpadding=0 cellspacing=0><tr><td style="padding:40px 0"align=center><table width=600 style="background-color:#fff;border-radius:8px;box-shadow:0 0 10px rgba(0,0,0,.05)"><tr><td style=background-color:#d92e2e;padding:24px align=center><img src=https://raw.githubusercontent.com/K9Developer/HSEC/refs/heads/master/assets/hsec.png alt="HSEC Logo"width=120><tr><td style=padding:40px;color:#333;font-size:16px><p style=margin-top:0>Hi there,<p><strong>Motion was detected</strong> in a protected area by your camera.<p>Camera MAC address:<div style="margin:30px 0;text-align:center"><div style="display:inline-block;padding:16px 32px;font-size:24px;font-weight:700;color:#d92e2e;background:#fce8e6;border-radius:8px;letter-spacing:1px">{CAMERA_MAC}</div></div><p><strong>Detected objects:</strong> {CLASSES}<p>Below is a snapshot of the moment motion was detected:<div style=text-align:center;margin-top:20px><img src=cid:motion_image style=max-width:100%;border-radius:8px></div><p style=margin-top:30px>Visit your dashboard to view live footage or more alerts.<p style=margin-top:40px;font-size:12px;color:#888>© 2025 HSEC. All rights reserved.</table></table>"""
def send_motion_alert_email(email: str | list[str], classes: list[str], mac: str, frame: bytes, logger):
    try:
        if isinstance(email, str):
            recipients = [email]
        else:
            recipients = email

        msg = MIMEMultipart("related")
        msg["Subject"] = "HSEC Motion Detected Alert"
        msg["From"] = "HSEC <tim14321234124@gmail.com>"
        msg["To"] = ", ".join(recipients)

        alt_part = MIMEMultipart("alternative")
        plain = MOTION_ALERT_PLAINTEXT_BODY.replace("{CAMERA_MAC}", mac).replace("{CLASSES}", ", ".join(classes))
        html = MOTION_ALERT_HTML_BODY.replace("{CAMERA_MAC}", mac).replace("{CLASSES}", ", ".join(classes))

        alt_part.attach(MIMEText(plain, "plain"))
        alt_part.attach(MIMEText(html, "html"))
        msg.attach(alt_part)

        image = MIMEImage(frame, _subtype="jpeg")
        image.add_header("Content-ID", "<motion_image>")
        image.add_header("Content-Disposition", "inline", filename="motion.jpg")
        msg.attach(image)

        context = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as smtp:
            smtp.login("tim14321234124@gmail.com", os.environ["GMAIL_PASS"])
            smtp.sendmail(
                from_addr="tim14321234124@gmail.com",
                to_addrs=recipients,
                msg=msg.as_string()
            )

        logger.info(f"Motion alert email sent to {recipients} from camera {mac}")
        return True

    except Exception as e:
        logger.error(f"Failed to send motion alert email to {email}: {e}")
        return False