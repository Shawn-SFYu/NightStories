import smtplib
from email.mime.text import MIMEText
import os
import json

def notification(message):
    try:
        message = json.loads(message)
        mp3_fid = message["mp3_fid"]
        sender_email = os.getenv('EMAIL_USER')
        password = os.getenv('EMAIL_PASSWORD')
        receiver_address = message["username"]

        msg = MIMEText("MP3 ready for download: {}".format(mp3_fid))
        msg['Subject'] = "MP3 ready for download"
        msg['From'] = sender_email
        msg['To'] = receiver_address

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender_email, password)
            server.send_message(msg)
            
        print("Email sent successfully")
        return True, None
    except Exception as e:
        print(e)
        return False, str(e)