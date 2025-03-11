import os
import csv
import tempfile
from core.mongo_manager import MongoManager
from core.scanner import Scanner
from core.notifier import TelegramNotifier, DiscordNotifier
from utils import logger
from config import settings

# Threshold for number of items to display in notification before attaching CSV
MAX_DISPLAY_NEW = 10
MAX_DISPLAY_UPDATE = 5

class DomainProcessor:
    def __init__(self, domain, company_name):
        self.domain = domain
        self.company_name = company_name
        self.mongo = MongoManager(settings.MONGO_URI, company_name)
        self.scanner = Scanner(settings.RESOLVER_PATH)
        self.telegram_notifier = TelegramNotifier()
        self.discord_notifier = DiscordNotifier()

    def process(self, fetcher_results):
        logger.info(f"🔎 Processing domain: {self.domain}")

        # 1. Run scan chain and get httpx results
        httpx_results = self.scanner.run_scan_chain(fetcher_results, self.domain)
        count_results = len(httpx_results)

        # 2. Check if it's the first scan for this domain/company
        is_first_scan = self.mongo.httpx.count_documents({}) == 0

        # 3. Update MongoDB with the new httpx results and get detected changes
        changes = self.mongo.update_httpx(httpx_results)

        # 4. First scan behavior (summary only)
        if is_first_scan:
            self._notify_first_scan(count_results)
            logger.success(f"First scan for {self.domain} completed. Subdomains found: {count_results}")
        else:
            # 5. Handle changes (if any)
            self._notify_changes(changes)

        # 6. Close MongoDB connection
        self.mongo.close()

    def _notify_first_scan(self, count_results):
        msg = (
            f"✅ *First Scan Completed* for `{self.domain}`\n\n"
            f"🔎 Discovered `{count_results}` unique subdomains."
        )
        self._send_notifications(msg)

    def _notify_changes(self, changes):
        if not changes:
            logger.info(f"No changes detected in {self.domain}")
            return

        new_items = [c for c in changes if c["type"] == "new"]
        updated_items = [c for c in changes if c["type"] == "update"]

        msg_lines = [f"🔔 *Scan Updates* for `{self.domain}`\n"]

        # New Subdomains Section
        if new_items:
            msg_lines.append(f"🆕 *New Subdomains Found ({len(new_items)})*:")
            for item in new_items[:MAX_DISPLAY_NEW]:
                url = item["data"]["url"]
                status = item["data"]["status"]
                title = item["data"]["title"] or "-"
                msg_lines.append(f"- `{url}` [{status}] \"{title}\"")
            if len(new_items) > MAX_DISPLAY_NEW:
                msg_lines.append(f"...and `{len(new_items) - MAX_DISPLAY_NEW}` more new items.")
            msg_lines.append("")

        # Updated Subdomains Section
        if updated_items:
            msg_lines.append(f"🔄 *Updated Subdomains ({len(updated_items)})*:")
            for item in updated_items[:MAX_DISPLAY_UPDATE]:
                url = item["url"]
                msg_lines.append(f"- `{url}`")
                for field, vals in item["diff"].items():
                    old_val = vals["old"] or "-"
                    new_val = vals["new"] or "-"
                    msg_lines.append(f"   • *{field.capitalize()}*: `{old_val}` ➜ `{new_val}`")
            if len(updated_items) > MAX_DISPLAY_UPDATE:
                msg_lines.append(f"...and `{len(updated_items) - MAX_DISPLAY_UPDATE}` more updated items.")
            msg_lines.append("")

        # Summary stats
        msg_lines.append(f"📊 *Total New*: `{len(new_items)}` | *Updated*: `{len(updated_items)}`")

        # Send the formatted message
        final_msg = "\n".join(msg_lines)
        self._send_notifications(final_msg)

        # If there are too many changes, send the full CSV
        if len(new_items) > MAX_DISPLAY_NEW or len(updated_items) > MAX_DISPLAY_UPDATE:
            csv_file = self._create_csv(changes, self.domain)
            caption = f"📂 Full Scan Results for `{self.domain}` attached (CSV)"

            self.telegram_notifier.send_file(csv_file, caption=caption)
            self.discord_notifier.send_file(csv_file, message=caption)

            os.remove(csv_file)
            logger.info(f"Temporary CSV file {csv_file} deleted.")

    def _create_csv(self, changes, domain):
        # Temporary directory for CSV file
        tmp_dir = tempfile.gettempdir()
        file_path = os.path.join(tmp_dir, f"{domain}_changes.csv")

        with open(file_path, mode='w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['Type', 'URL', 'Status', 'Title', 'Tech', 'Changes']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            for change in changes:
                row = {
                    'Type': change['type'],
                    'URL': change.get('data', {}).get('url') or change.get('url'),
                    'Status': change.get('data', {}).get('status', ''),
                    'Title': change.get('data', {}).get('title', ''),
                    'Tech': ', '.join(change.get('data', {}).get('tech', [])) if change.get('data') else '',
                    'Changes': str(change.get('diff', '')) if change.get('diff') else ''
                }
                writer.writerow(row)

        logger.success(f"CSV file created: {file_path}")
        return file_path

    def _send_notifications(self, message):
        """Send notifications to both Telegram and Discord."""
        self.telegram_notifier.send(message)
        self.discord_notifier.send(message)
