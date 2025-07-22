import os
import psycopg2
import select
import smtplib
import threading
from email.message import EmailMessage
from dotenv import load_dotenv
from flask import Flask
import time

load_dotenv()

app = Flask(__name__)

@app.route("/")
def home():
    return "📡 Listener is running and alive!"

def send_email(subject, content):
    try:
        msg = EmailMessage()
        msg.set_content(content)
        msg["Subject"] = subject
        msg["From"] = os.environ["SMTP_EMAIL"]
        msg["To"] = os.environ["ALERT_EMAIL"]

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(os.environ["SMTP_EMAIL"], os.environ["SMTP_PASSWORD"])
            server.send_message(msg)
            print("✅ Email sent")
    except Exception as e:
        print("❌ Error sending email:", e)

def listen_to_db():
    while True:
        try:
            conn = psycopg2.connect(os.environ["DATABASE_URL"])
            conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
            cur = conn.cursor()

            cur.execute("LISTEN new_community_member;")
            print("📡 Listening for new inserts...")

            while True:
                if select.select([conn], [], [], 5) == ([], [], []):
                    continue
                conn.poll()
                while conn.notifies:
                    notify = conn.notifies.pop(0)
                    channel = notify.channel
                    new_id = notify.payload

                    if channel == "new_community_member":
                        cur.execute("SELECT full_name, email_address, whatsapp_number, city FROM community_members WHERE id = %s", (new_id,))
                        row = cur.fetchone()
                        send_email("🧑‍🤝‍🧑 New Community Member", f"Name: {row[0]}\nEmail: {row[1]}\nWhatsapp_number: {row[2]}\nCity: {row[3]}")
        except Exception as e:
            print("❌ Error in listener:", e)
            time.sleep(10)  # Retry after 10 seconds if failure

# Start listener in background
threading.Thread(target=listen_to_db, daemon=True).start()

# Start Flask server
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
