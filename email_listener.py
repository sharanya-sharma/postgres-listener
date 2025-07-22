import os
import psycopg2
import select
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env (Render sets them automatically)

# PostgreSQL connection
conn = psycopg2.connect(os.environ["DATABASE_URL"])
conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
cur = conn.cursor()

# Listen to channels
cur.execute("LISTEN new_community_member;")
cur.execute("LISTEN new_switch_story;")
print("📡 Listening for new inserts...")

def send_email(subject, content):
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

while True:
    if select.select([conn], [], [], None) == ([], [], []):
        continue
    conn.poll()
    while conn.notifies:
        notify = conn.notifies.pop(0)
        channel = notify.channel
        new_id = notify.payload

        if channel == "new_community_member":
            cur.execute("SELECT full_name, email_address, city FROM community_members WHERE id = %s", (new_id,))
            row = cur.fetchone()
            send_email("🧑‍🤝‍🧑 New Community Member",
                       f"Name: {row[0]}\nEmail: {row[1]}\nCity: {row[2]}")

        elif channel == "new_switch_story":
            cur.execute("SELECT name, email, current_status FROM switch_stories WHERE id = %s", (new_id,))
            row = cur.fetchone()
            send_email("📘 New Switch Story",
                       f"Name: {row[0]}\nEmail: {row[1]}\nCurrent Status: {row[2]}")
