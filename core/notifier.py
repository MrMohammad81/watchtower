import requests
from utils import logger
from config import settings

class TelegramNotifier:
    def __init__(self):
        self.base_url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
        self.chat_id = settings.TELEGRAM_CHAT_ID

    def send(self, message):
        payload = {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": "Markdown"
        }
        try:
            res = requests.post(self.base_url, data=payload)
            if res.status_code != 200:
                logger.error(f"[Telegram] Error: {res.status_code} - {res.text}")
            else:
                logger.success("[Telegram] Notification sent!")
        except Exception as e:
            logger.error(f"[Telegram] Exception: {e}")

class DiscordNotifier:
    def __init__(self):
        self.webhook_url = settings.DISCORD_WEBHOOK_URL

    def send(self, message):
        payload = {
            "content": message
        }
        try:
            res = requests.post(self.webhook_url, json=payload)
            if res.status_code != 204:
                logger.error(f"[Discord] Error: {res.status_code} - {res.text}")
            else:
                logger.success("[Discord] Notification sent!")
        except Exception as e:
            logger.error(f"[Discord] Exception: {e}")
