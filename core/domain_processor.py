from core.mongo_manager import MongoManager
from core.scanner import Scanner
from core.notifier import TelegramNotifier, DiscordNotifier
from utils import logger
from config import settings

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

        # Run the scanning chain and collect httpx results
        httpx_results = self.scanner.run_scan_chain(fetcher_results, self.domain)

        # Count the number of httpx results
        count_results = len(httpx_results)

        # Check if it's the first scan for this company/domain
        is_first_scan = self.mongo.httpx.count_documents({}) == 0

        # Update MongoDB with new httpx results and detect changes
        changes = self.mongo.update_httpx(httpx_results)

        # Handle first scan - only notify about the total number of found URLs
        if is_first_scan:
            msg = (
                f"✅ First scan completed for `{self.domain}`\n\n"
                f"🔎 Discovered `{count_results}` unique subdomains."
            )

            # Send notification
            self.telegram_notifier.send(msg)
            self.discord_notifier.send(msg)

            logger.success(f"First scan for {self.domain} finished. Subdomains found: {count_results}")
            return

        # Handle subsequent scans with detected changes
        if changes:
            # Compose notification message
            msg_lines = [f"🔔 Scan Updates for: `{self.domain}`\n"]

            # New URLs block
            new_items = [c for c in changes if c["type"] == "new"]
            if new_items:
                msg_lines.append("🆕 New URLs:")
                for item in new_items:
                    url = item["data"]["url"]
                    status = item["data"]["status"]
                    title = item["data"]["title"] or "-"
                    msg_lines.append(f"- `{url}` [{status}] - \"{title}\"")
                msg_lines.append("")  # Empty line for separation

            # Updated URLs block
            updated_items = [c for c in changes if c["type"] == "update"]
            if updated_items:
                msg_lines.append("🔄 Updated URLs:")
                for item in updated_items:
                    url = item["url"]
                    msg_lines.append(f"- `{url}`")
                    for field, vals in item["diff"].items():
                        old_val = vals["old"]
                        new_val = vals["new"]
                        msg_lines.append(f"  • {field.capitalize()}: `{old_val}` ➜ `{new_val}`")
                msg_lines.append("")  # Empty line for separation

            # Combine all message lines
            final_msg = "\n".join(msg_lines)

            # Send notification
            self.telegram_notifier.send(final_msg)
            self.discord_notifier.send(final_msg)

            logger.success(f"Changes detected and notified for {self.domain}")

        else:
            logger.info(f"No changes detected in {self.domain}")

        # Close MongoDB connection after processing
        self.mongo.close()
