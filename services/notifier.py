import requests
import os
from utils import logger
from config import settings

class TelegramNotifier:
    def __init__(self):
        self.bot_token = settings.TELEGRAM_BOT_TOKEN
        self.chat_id = settings.TELEGRAM_CHAT_ID

    def send(self, message):
        """Send text message to Telegram."""
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True
        }
        try:
            response = requests.post(url, json=payload, timeout=10)
            if response.status_code == 200:
                logger.success("✅ Telegram message sent!")
            else:
                logger.error(f"❌ Telegram error {response.status_code}: {response.text}")
        except Exception as e:
            logger.error(f"❌ Telegram send error: {e}")

    def send_file(self, file_path, caption=""):
        """Send a file (CSV) to Telegram."""
        url = f"https://api.telegram.org/bot{self.bot_token}/sendDocument"

        if not os.path.exists(file_path):
            logger.error(f"❌ File not found: {file_path}")
            return

        with open(file_path, 'rb') as file:
            files = {'document': file}
            data = {
                "chat_id": self.chat_id,
                "caption": caption
            }
            try:
                response = requests.post(url, data=data, files=files, timeout=30)
                if response.status_code == 200:
                    logger.success(f"✅ Telegram file '{file_path}' sent!")
                else:
                    logger.error(f"❌ Telegram file error {response.status_code}: {response.text}")
            except Exception as e:
                logger.error(f"❌ Telegram file send error: {e}")

class DiscordNotifier:
    def __init__(self):
        self.webhook_url = settings.DISCORD_WEBHOOK_URL

    def send(self, message):
        """Send text message to Discord."""
        payload = {"content": message}
        try:
            response = requests.post(self.webhook_url, json=payload, timeout=10)
            if response.status_code in [200, 204]:
                logger.success("✅ Discord message sent!")
            else:
                logger.error(f"❌ Discord error {response.status_code}: {response.text}")
        except Exception as e:
            logger.error(f"❌ Discord send error: {e}")

    def send_file(self, file_path, message=""):
        """Send a file (CSV) to Discord."""
        if not os.path.exists(file_path):
            logger.error(f"❌ File not found: {file_path}")
            return

        with open(file_path, 'rb') as file:
            files = {'file': file}
            data = {'content': message}
            try:
                response = requests.post(self.webhook_url, data=data, files=files, timeout=30)
                if response.status_code in [200, 204]:
                    logger.success(f"✅ Discord file '{file_path}' sent!")
                else:
                    logger.error(f"❌ Discord file error {response.status_code}: {response.text}")
            except Exception as e:
                logger.error(f"❌ Discord file send error: {e}")
