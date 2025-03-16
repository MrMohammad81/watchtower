import os
import csv
import tempfile
from database.mongo_manager import MongoManager
from core.scanner import Scanner
from services.notifier import TelegramNotifier, DiscordNotifier
from utils import logger
from config import settings

# Thresholds
MAX_DISPLAY_NEW = 10
MAX_DISPLAY_UPDATE = 5
MAX_DISPLAY_BRUTEFORCE = 5
ALLOWED_STATUS_CODES = ['200', '403', '404']

# Platform message limits
DISCORD_CHAR_LIMIT = 1000
TELEGRAM_CHAR_LIMIT = 1000

class DomainProcessor:
    def __init__(self, domain, program_name):
        self.domain = domain
        self.program_name = program_name
        self.mongo = MongoManager(settings.MONGO_URI, program_name, domain)
        self.scanner = Scanner(settings.RESOLVER_PATH)
        self.telegram_notifier = TelegramNotifier()
        self.discord_notifier = DiscordNotifier()

    def process(self, fetcher_results):
        logger.info(f"🔎 Processing domain: {self.domain}")

        # Run scan chain
        httpx_results = self.scanner.run_scan_chain(fetcher_results, self.domain)
        count_results = len(httpx_results)

        # First scan check
        is_first_scan = self.mongo.httpx.count_documents({}) == 0

        # Update Mongo with changes
        changes = self.mongo.update_httpx(httpx_results)

        # Notify based on first scan or updates
        if is_first_scan:
            self._notify_first_scan(count_results)
            logger.success(f"✅ First scan for {self.domain} completed. Subdomains found: {count_results}")
        else:
            self._notify_changes(changes)

        # Close DB connection
        self.mongo.close()

    def _notify_first_scan(self, count_results):
        bruteforce_filtered = self._get_filtered_bruteforce()

        msg_lines = [
            f"✅ *First Scan Completed* for `{self.domain}`",
            f"🔎 Discovered `{count_results}` unique subdomains."
        ]

        if bruteforce_filtered:
            msg_lines.append("")
            msg_lines.append(f"🛡️ *DNS Bruteforce Subdomains* ({len(bruteforce_filtered)}):")
            for item in bruteforce_filtered[:MAX_DISPLAY_BRUTEFORCE]:
                msg_lines.append(self._format_subdomain_entry(item))

            if len(bruteforce_filtered) > MAX_DISPLAY_BRUTEFORCE:
                msg_lines.append(f"...and `{len(bruteforce_filtered) - MAX_DISPLAY_BRUTEFORCE}` more found by bruteforce.")

        final_msg = "\n".join(msg_lines)
        logger.info("✅ First scan notification composed.")

        # Send notification or CSV based on message size or data size
        self._send_notifications(final_msg, bruteforce_filtered, is_first_scan=True)

    def _notify_changes(self, changes):
        if not changes:
            logger.info(f"No changes detected in {self.domain}")
            return

        new_items = [c for c in changes if c["type"] == "new"]
        updated_items = [c for c in changes if c["type"] == "update"]
        new_bruteforce_items = [c for c in new_items if c.get("data", {}).get("bruteforce", False)]

        msg_lines = [f"🔔 *Scan Updates* for `{self.domain}`"]

        # New Subdomains
        if new_items:
            msg_lines.append("")
            msg_lines.append(f"🆕 *New Subdomains* ({len(new_items)}):")
            for item in new_items[:MAX_DISPLAY_NEW]:
                subdomain = item.get("data", {})
                msg_lines.append(self._format_subdomain_entry(subdomain))

            if len(new_items) > MAX_DISPLAY_NEW:
                msg_lines.append(f"...and `{len(new_items) - MAX_DISPLAY_NEW}` more new subdomains.")

        # Updated Subdomains
        if updated_items:
            msg_lines.append("")
            msg_lines.append(f"🔄 *Updated Subdomains* ({len(updated_items)}):")
            for item in updated_items[:MAX_DISPLAY_UPDATE]:
                url = item["url"]
                diff = item["diff"]
                msg_lines.append(f"- [{url}]({url})")

                for field in ["status", "title", "tech", "bruteforce"]:
                    if field in diff:
                        old = diff[field]['old'] if diff[field]['old'] is not None else '-'
                        new = diff[field]['new'] if diff[field]['new'] is not None else '-'
                        msg_lines.append(f"   • *{field.capitalize()}*: `{old}` ➜ `{new}`")

            if len(updated_items) > MAX_DISPLAY_UPDATE:
                msg_lines.append(f"...and `{len(updated_items) - MAX_DISPLAY_UPDATE}` more updated subdomains.")

        # New DNS Bruteforce Subdomains
        if new_bruteforce_items:
            msg_lines.append("")
            msg_lines.append(f"🛡️ *New DNS Bruteforce Subdomains* ({len(new_bruteforce_items)}):")
            for item in new_bruteforce_items[:MAX_DISPLAY_BRUTEFORCE]:
                subdomain = item.get("data", {})
                msg_lines.append(self._format_subdomain_entry(subdomain))

            if len(new_bruteforce_items) > MAX_DISPLAY_BRUTEFORCE:
                msg_lines.append(f"...and `{len(new_bruteforce_items) - MAX_DISPLAY_BRUTEFORCE}` more bruteforce subdomains.")

        # Summary
        msg_lines.append("")
        msg_lines.append(f"📊 *Summary*: New: `{len(new_items)}` | Updated: `{len(updated_items)}` | New Bruteforce: `{len(new_bruteforce_items)}`")

        final_msg = "\n".join(msg_lines)
        logger.info("✅ Change notification composed.")

        self._send_notifications(final_msg, changes)

    def _send_notifications(self, message, data, is_first_scan=True):
        """
        Send notifications to both Telegram and Discord.
        If message is too long, send CSV instead.
        """
        message_length = len(message)

        if message_length <= DISCORD_CHAR_LIMIT and message_length <= TELEGRAM_CHAR_LIMIT:
            self.telegram_notifier.send(message)
            self.discord_notifier.send(message)
            logger.info("✅ Notifications sent successfully (Text Mode).")
            return

        logger.warning("⚠️ Message too long, sending CSV instead...")

        if is_first_scan:
            csv_file = self._create_csv_first_scan(data, self.domain)
            caption = f"📂 Full BruteForce Results for `{self.domain}` (CSV attached)"
        else:
            csv_file = self._create_csv(data, self.domain)
            caption = f"📂 Full Scan Results for `{self.domain}` (CSV attached)"

        # Send CSV to both platforms
        self.telegram_notifier.send_file(csv_file, caption=caption)
        self.discord_notifier.send_file(csv_file, message=caption)

        os.remove(csv_file)
        logger.info(f"🗑️ Temporary CSV file {csv_file} deleted after sending.")

    def _format_subdomain_entry(self, item):
        url = item.get('url', '-')
        status = item.get('status', '-')
        title = item.get('title', '-') or '-'
        tech_list = item.get('tech', [])
        tech_display = ', '.join(tech_list) if tech_list else '-'

        # Return formatted string
        return f"- [{url}]({url})\n  status: {status}\n  title: {title}\n  tech: {tech_display}"

    def _create_csv(self, changes, domain):
        tmp_dir = tempfile.gettempdir()
        file_path = os.path.join(tmp_dir, f"{domain}_changes.csv")

        with open(file_path, mode='w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['Type', 'URL', 'Status', 'Title', 'BruteForce', 'Tech', 'Changes']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            for change in changes:
                row = {
                    'Type': change.get('type', ''),
                    'URL': change.get('data', {}).get('url') or change.get('url', ''),
                    'Status': change.get('data', {}).get('status', ''),
                    'Title': change.get('data', {}).get('title', ''),
                    'BruteForce': change.get('data', {}).get('bruteforce', False),
                    'Tech': ', '.join(change.get('data', {}).get('tech', [])) if change.get('data') else '',
                    'Changes': str(change.get('diff', '')) if change.get('diff') else ''
                }
                writer.writerow(row)

        logger.success(f"✅ CSV file created: {file_path}")
        return file_path

    def _create_csv_first_scan(self, bruteforce_items, domain):
        tmp_dir = tempfile.gettempdir()
        file_path = os.path.join(tmp_dir, f"{domain}_bruteforce_first_scan.csv")

        with open(file_path, mode='w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['URL', 'Status', 'Title', 'BruteForce', 'Tech']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            for item in bruteforce_items:
                row = {
                    'URL': item.get('url', ''),
                    'Status': item.get('status', ''),
                    'Title': item.get('title', ''),
                    'BruteForce': item.get('bruteforce', False),
                    'Tech': ', '.join(item.get('tech', [])) if item.get('tech') else ''
                }
                writer.writerow(row)

        logger.success(f"✅ CSV file (first scan) created: {file_path}")
        return file_path

    def _get_filtered_bruteforce(self):
        """
        Get only bruteforce subdomains with allowed status codes.
        """
        bruteforce_items = self.mongo.get_bruteforce_only()
        return [item for item in bruteforce_items if item.get("status") in ALLOWED_STATUS_CODES]
