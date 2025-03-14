import os
import csv
import tempfile
from core.mongo_manager import MongoManager
from core.scanner import Scanner
from core.notifier import TelegramNotifier, DiscordNotifier
from utils import logger
from config import settings

# Thresholds
MAX_DISPLAY_NEW = 10
MAX_DISPLAY_UPDATE = 5
MAX_DISPLAY_BRUTEFORCE = 5
ALLOWED_STATUS_CODES = ['200', '403', '404']

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

        # 4. Notifications based on first scan or updates
        if is_first_scan:
            self._notify_first_scan(count_results)
            logger.success(f"✅ First scan for {self.domain} completed. Subdomains found: {count_results}")
        else:
            self._notify_changes(changes)

        # 5. Close MongoDB connection
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
        self._send_notifications(final_msg)

        # Send CSV if necessary
        if len(bruteforce_filtered) > MAX_DISPLAY_BRUTEFORCE or count_results > MAX_DISPLAY_NEW:
            csv_file = self._create_csv_first_scan(bruteforce_filtered, self.domain)
            caption = f"📂 Full BruteForce Results for `{self.domain}` attached (CSV)"

            self.telegram_notifier.send_file(csv_file, caption=caption)
            self.discord_notifier.send_file(csv_file, message=caption)

            os.remove(csv_file)
            logger.info(f"🗑️ Temporary CSV file {csv_file} deleted.")

    def _notify_changes(self, changes):
        if not changes:
            logger.info(f"No changes detected in {self.domain}")
            return

        new_items = [c for c in changes if c["type"] == "new"]
        updated_items = [c for c in changes if c["type"] == "update"]

        # فقط new هایی که با dns bruteforce اومدن
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
                for field in ["status", "title", "tech"]:
                    if field in diff:
                        old = diff[field]['old'] or '-'
                        new = diff[field]['new'] or '-'
                        msg_lines.append(f"   • *{field.capitalize()}*: `{old}` ➜ `{new}`")

            if len(updated_items) > MAX_DISPLAY_UPDATE:
                msg_lines.append(f"...and `{len(updated_items) - MAX_DISPLAY_UPDATE}` more updated subdomains.")

        # فقط new bruteforce items رو نشون بده
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
        self._send_notifications(final_msg)

        # Send CSV if necessary
        if len(new_items) > MAX_DISPLAY_NEW or len(updated_items) > MAX_DISPLAY_UPDATE:
            csv_file = self._create_csv(changes, self.domain)
            caption = f"📂 Full Scan Results for `{self.domain}` attached (CSV)"

            self.telegram_notifier.send_file(csv_file, caption=caption)
            self.discord_notifier.send_file(csv_file, message=caption)

            os.remove(csv_file)
            logger.info(f"🗑️ Temporary CSV file {csv_file} deleted.")

    def _format_subdomain_entry(self, item):
        url = item.get('url')
        status = item.get('status', '-')
        title = item.get('title', '-') or '-'
        tech_list = item.get('tech', [])
        tech_display = ', '.join(tech_list) if tech_list else '-'

        telegram_link = f"[{url}]({url})"
        return f"- {telegram_link}\n  status: {status}\n  title: {title}\n  tech: {tech_display}"

    def _create_csv(self, changes, domain):
        tmp_dir = tempfile.gettempdir()
        file_path = os.path.join(tmp_dir, f"{domain}_changes.csv")

        with open(file_path, mode='w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['Type', 'URL', 'Status', 'Title', 'BruteForce', 'Tech', 'Changes']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            for change in changes:
                row = {
                    'Type': change['type'],
                    'URL': change.get('data', {}).get('url') or change.get('url'),
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
                    'URL': item.get('url'),
                    'Status': item.get('status', ''),
                    'Title': item.get('title', ''),
                    'BruteForce': item.get('bruteforce', False),
                    'Tech': ', '.join(item.get('tech', []))
                }
                writer.writerow(row)

        logger.success(f"✅ CSV file (first scan) created: {file_path}")
        return file_path

    def _get_filtered_bruteforce(self):
        bruteforce_items = self.mongo.get_bruteforce_only()
        return [item for item in bruteforce_items if item.get("status") in ALLOWED_STATUS_CODES]

    def _send_notifications(self, message):
        self.telegram_notifier.send(message)
        self.discord_notifier.send(message)
