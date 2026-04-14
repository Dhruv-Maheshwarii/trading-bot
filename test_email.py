import smtplib
import os
from dotenv import load_dotenv
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Load .env file
load_dotenv()
EMAIL_SENDER   = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_RECEIVER = os.getenv("EMAIL_RECEIVER")

def send_email(subject, body):
    msg = MIMEMultipart()
    msg['From']    = EMAIL_SENDER
    msg['To']      = EMAIL_RECEIVER
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'html'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.sendmail(EMAIL_SENDER, EMAIL_RECEIVER, msg.as_string())
        server.quit()
        print("✅ Email sent successfully!")
    except Exception as e:
        print(f"❌ Email failed: {e}")

# Test
send_email(
    subject="🤖 AlgoTrade Bot — Test Email",
    body="""
    <h2 style='color:green'>✅ AlgoTrade Bot Connected!</h2>
    <p>Your trading bot email alerts are working!</p>
    <p><b>Strategy:</b> MA + RSI + MACD + ATR</p>
    <p><b>Pair:</b> BTC/USDT</p>
    """
)