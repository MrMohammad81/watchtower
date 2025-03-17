from utils import logger
import os
from services.notifier import TelegramNotifier, DiscordNotifier
from core.csv_file_creator import CsvFileCreator


class NotificationSender:
    def __init__(self, domain):
        self.domain = domain
        self.telegram_notifier = TelegramNotifier()
        self.discord_notifier = DiscordNotifier()
        self.csv_file_creator = CsvFileCreator(domain)
    
    def send_notifications(self, message, data, is_first_scan=False):
        """
        Always send text message + CSV to Telegram and Discord.
        """
        logger.info("📤 Sending notifications...")

        # Send message text
        self.telegram_notifier.send(message)
        self.discord_notifier.send(message)

        # Prepare CSV file
        if is_first_scan:
            csv_file = self.csv_file_creator.create_csv_first_scan(data, self.domain)
            caption = f"📂 Full BruteForce Results for `{self.domain}` (CSV attached)"
        else:
            csv_file = self.csv_file_creator.create_csv(data, self.domain)
            caption = f"📂 Full Scan Results for `{self.domain}` (CSV attached)"

        # Send CSV files
        self.telegram_notifier.send_file(csv_file, caption=caption)
        self.discord_notifier.send_file(csv_file, message=caption)

        # Clean up
        os.remove(csv_file)
        logger.info(f"🗑️ Temporary CSV file {csv_file} deleted after sending.")