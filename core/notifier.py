import requests
from utils import logger
from config import settings

class Notifier:
    def __init__(self):
        self.telegram_bot_token = settings.TELEGRAM_BOT_TOKEN
        self.telegram_chat_id = settings.TELEGRAM_CHAT_ID
        self.discord_webhook = settings.DISCORD_WEBHOOK_URL

    def send_telegram(self, message):
        url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage"
        payload = {
            "chat_id": self.telegram_chat_id,
            "text": message,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True
        }

        try:
            response = requests.post(url, json=payload, timeout=10)
            if response.status_code == 200:
                logger.success("Telegram notification sent!")
            else:
                logger.error(f"Telegram failed with status {response.status_code}: {response.text}")
        except Exception as e:
            logger.error(f"Telegram notification error: {e}")

    def send_discord(self, message):
        payload = {
            "content": message
        }

        try:
            response = requests.post(self.discord_webhook, json=payload, timeout=10)
            if response.status_code == 204:
                logger.success("Discord notification sent!")
            else:
                logger.error(f"Discord failed with status {response.status_code}: {response.text}")
        except Exception as e:
            logger.error(f"Discord notification error: {e}")

    def format_changes(self, company_name, new_entries, updates):
        message_lines = []
        message_lines.append(f"🛡️ *Watchtower Update* for *{company_name}*\n")

        # New subdomains
        if new_entries:
            message_lines.append(f"✅ *New Subdomains Found ({len(new_entries)})*:")
            for entry in new_entries[:10]:
                url = entry['data']['url']
                status = entry['data']['status']
                title = entry['data']['title']
                tech = ', '.join(entry['data']['tech']) if entry['data']['tech'] else 'None'
                message_lines.append(f"- `{url}` [{status}] [{title}] [{tech}]")

            if len(new_entries) > 10:
                message_lines.append(f"... and {len(new_entries) - 10} more.\n")

        # Updated subdomains
        if updates:
            message_lines.append(f"\n🔄 *Updated Subdomains ({len(updates)})*:")
            for update in updates[:5]:
                url = update['url']
                diff = update['diff']
                message_lines.append(f"- `{url}`")
                for field, change in diff.items():
                    message_lines.append(f"    ➤ *{field}*: `{change['old']}` ➜ `{change['new']}`")

            if len(updates) > 5:
                message_lines.append(f"... and {len(updates) - 5} more.")

        message_lines.append(f"\n📊 *Total New*: {len(new_entries)} | *Updated*: {len(updates)}")

        return '\n'.join(message_lines)

    def notify(self, company_name, changes):
        new_entries = [c for c in changes if c['type'] == 'new']
        updates = [c for c in changes if c['type'] == 'update']

        if not new_entries and not updates:
            logger.info("No changes to notify.")
            return

        message = self.format_changes(company_name, new_entries, updates)

        self.send_telegram(message)
        self.send_discord(message)
