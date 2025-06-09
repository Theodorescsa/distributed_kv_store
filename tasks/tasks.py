import requests
import smtplib
from email.mime.text import MIMEText
import redis
from django.conf import settings

redis_client = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT)

def mark_node_down(url):
    node_id = url.split("//")[1].split(":")[0]        # 'node2'
    redis_client.set(f"node_status:{node_id}", "down")

def sync_replica(key, value, replica_url):
    try:
        if value is not None:
            requests.post(
                f"{replica_url}/kv/?replica=true",
                json={"key": key, "value": value},
                timeout=3,
            )
        else:
            requests.delete(
                f"{replica_url}/kv/",
                params={"key": key, "replica": "true"},
                timeout=3,
            )
    except requests.exceptions.RequestException as e:
        print("[Replica Error]", e)
        mark_node_down(replica_url)

def send_email_notification(key, value):
    try:
        msg = MIMEText(f"Key: {key}, Value: {value}")
        msg['Subject'] = 'Key-Value Operation Notification'
        msg['From'] = settings.EMAIL_HOST_USER
        msg['To'] = 'dinhthai0312@gmail.com'

        with smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT) as server:
            server.starttls()
            server.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
            server.send_message(msg)
    except Exception as e:
        print(f"[Email Error] {e}")
