import smtplib, os
from email.message import EmailMessage
import json
def notification(message):
    try:
        message = json.loads(message)
        mp3_fid = message["mp3_fid"]
        sender_address = os.environ.get("GMAIL_ADDRESS")
        sender_password = os.environ.get("GMAIL_PASSWORD")
        receiver_address = message["username"]

        msg = EmailMessage()
        msg.set_content("MP3 ready for download: {}".format(mp3_fid)) 
        msg["Subject"] = "MP3 ready for download"
        msg["From"] = sender_address
        msg["To"] = receiver_address

        smtp_server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
        smtp_server.login(sender_address, os.environ.get("GMAIL_PASSWORD"))
        smtp_server.sendmail(sender_address, receiver_address, msg.as_string())
        smtp_server.quit() 
        print("Email sent successfully")
    except Exception as e:
        print(e) 
        return e