from core.mongo_manager import MongoManager
from core.scanner import Scanner
from core.notifier import TelegramNotifier, DiscordNotifier
from utils import logger
from config import settings

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

        # 1. Run scan chain -> get httpx results
        httpx_results = self.scanner.run_scan_chain(fetcher_results, self.domain)
        count_results = len(httpx_results)

        # 2. Check if this is the first scan
        is_first_scan = self.mongo.httpx.count_documents({}) == 0

        # 3. Update MongoDB and get changes
        changes = self.mongo.update_httpx(httpx_results)

        # 4. Handle first scan (no need to check changes)
        if is_first_scan:
            self._notify_first_scan(count_results)
            logger.success(f"First scan for {self.domain} finished. Subdomains found: {count_results}")
        else:
            self._notify_changes(changes)

        # 5. Close Mongo connection
        self.mongo.close()

    def _notify_first_scan(self, count_results):
        msg = (
            f"✅ *First Scan Completed* for `{self.domain}`\n\n"
            f"🔍 Discovered `{count_results}` unique subdomains."
        )
        self._send_notifications(msg)

    def _notify_changes(self, changes):
        if not changes:
            logger.info(f"No changes detected in {self.domain}")
            return

        new_items = [c for c in changes if c["type"] == "new"]
        updated_items = [c for c in changes if c["type"] == "update"]

        msg_lines = [f"🔔 *Scan Updates* for `{self.domain}`\n"]

        # 1. New URLs
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

        # 2. Updated URLs
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

        # 3. Final Stats
        msg_lines.append(f"📊 *Total New*: `{len(new_items)}` | *Updated*: `{len(updated_items)}`")

        final_msg = "\n".join(msg_lines)
        self._send_notifications(final_msg)

        logger.success(f"Changes detected and notified for {self.domain}")

    def _send_notifications(self, message):
        self.telegram_notifier.send(message)
        self.discord_notifier.send(message)
