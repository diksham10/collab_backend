import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from src.config  import settings


async def send_email(to_mail: str, subject: str, body:str):
    
    msg=MIMEMultipart()
    msg["From"] = settings.EMAIL_FROM
    msg["To"] = to_mail
    msg["Subject"] = subject
    
    msg.attach(MIMEText(body, "plain"))

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
        server.starttls()
        server.login(settings.SMTP_USER, settings.SMTP_PASS)
        server.send_message(msg)
    



