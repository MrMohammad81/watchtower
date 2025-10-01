import requests
import os
import time
from utils import logger
from config import settings

class TelegramNotifier:
    def __init__(self):
        self.bot_token = settings.TELEGRAM_BOT_TOKEN
        self.chat_id = settings.TELEGRAM_CHAT_ID
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"

    def send(self, message, retries=3, timeout=30, delay=5):
        """Send text message to Telegram with retries."""
        url = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True
        }

        for attempt in range(1, retries + 1):
            try:
                response = requests.post(url, json=payload, timeout=timeout)
                if response.status_code == 200:
                    logger.success("✅ Telegram message sent!")
                    return True
                else:
                    logger.error(f"❌ Telegram error {response.status_code}: {response.text}")
            except requests.exceptions.ReadTimeout:
                logger.warning(f"⏳ Telegram read timeout, attempt {attempt}/{retries}")
            except requests.exceptions.RequestException as e:
                logger.error(f"❌ Telegram send error: {e}")

            if attempt < retries:
                time.sleep(delay)

        logger.error("❌ Failed to send Telegram message after multiple attempts.")
        return False

    def send_file(self, file_path, caption="", retries=3, timeout=60, delay=5):
        """Send a file (CSV) to Telegram with retries."""
        url = f"{self.base_url}/sendDocument"

        if not os.path.exists(file_path):
            logger.error(f"❌ File not found: {file_path}")
            return False

        for attempt in range(1, retries + 1):
            try:
                with open(file_path, 'rb') as file:
                    files = {'document': file}
                    data = {
                        "chat_id": self.chat_id,
                        "caption": caption
                    }
                    response = requests.post(url, data=data, files=files, timeout=timeout)
                    if response.status_code == 200:
                        logger.success(f"✅ Telegram file '{file_path}' sent!")
                        return True
                    else:
                        logger.error(f"❌ Telegram file error {response.status_code}: {response.text}")
            except requests.exceptions.ReadTimeout:
                logger.warning(f"⏳ Telegram file read timeout, attempt {attempt}/{retries}")
            except requests.exceptions.RequestException as e:
                logger.error(f"❌ Telegram file send error: {e}")

            if attempt < retries:
                time.sleep(delay)

        logger.error("❌ Failed to send Telegram file after multiple attempts.")
        return False

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
