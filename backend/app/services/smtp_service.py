import smtplib
from email.mime.text import MIMEText

from app.config import settings
from app.models import UserSmtpSetting


def send_email(to_email: str, subject: str, body: str, smtp_setting: UserSmtpSetting | None = None) -> None:
    host = smtp_setting.smtp_host if smtp_setting and smtp_setting.is_enabled else settings.smtp_host
    port = smtp_setting.smtp_port if smtp_setting and smtp_setting.is_enabled else settings.smtp_port
    username = smtp_setting.smtp_username if smtp_setting and smtp_setting.is_enabled else settings.smtp_username
    password = smtp_setting.smtp_password if smtp_setting and smtp_setting.is_enabled else settings.smtp_password
    use_ssl = smtp_setting.smtp_use_ssl if smtp_setting and smtp_setting.is_enabled else settings.smtp_use_ssl
    from_email = (
        smtp_setting.smtp_from_email
        if smtp_setting and smtp_setting.is_enabled and smtp_setting.smtp_from_email
        else (settings.smtp_from_email or username)
    )

    if not host or not username:
        raise ValueError("SMTP 配置不完整，请先在设置页保存 SMTP 参数")

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = from_email
    msg["To"] = to_email

    if use_ssl:
        with smtplib.SMTP_SSL(host, port) as server:
            server.login(username, password)
            server.sendmail(msg["From"], [to_email], msg.as_string())
    else:
        with smtplib.SMTP(host, port) as server:
            server.starttls()
            server.login(username, password)
            server.sendmail(msg["From"], [to_email], msg.as_string())
