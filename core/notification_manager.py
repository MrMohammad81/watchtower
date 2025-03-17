from helpers.helpers import Helpers
from utils import logger

# Thresholds
MAX_DISPLAY_NEW = 10
MAX_DISPLAY_UPDATE = 5
MAX_DISPLAY_BRUTEFORCE = 5
ALLOWED_STATUS_CODES = ['200', '403', '404']

class NotificationManager:
    def __init__(self , domain, notification_sender):
        self.domain = domain
        self.notification_sender = notification_sender
        
    def notify_first_scan(self, count_results, httpx_results):
        bruteforce_filtered = self._get_filtered_bruteforce()

        msg_lines = [
            f"✅ *First Scan Completed* for `{self.domain}`",
            f"🔎 Discovered `{count_results}` unique subdomains."
        ]

        if bruteforce_filtered:
            msg_lines.append("")
            msg_lines.append(f"🛡️ *DNS Bruteforce Subdomains* ({len(bruteforce_filtered)}):")
            for item in bruteforce_filtered[:MAX_DISPLAY_BRUTEFORCE]:
                msg_lines.append(Helpers.subdomain_filter(item))

            if len(bruteforce_filtered) > MAX_DISPLAY_BRUTEFORCE:
                msg_lines.append(f"...and `{len(bruteforce_filtered) - MAX_DISPLAY_BRUTEFORCE}` more found by bruteforce.")

        final_msg = "\n".join(msg_lines)
        logger.info("✅ First scan notification composed.")

        # Send notification + CSV always
        self.notification_sender.send_notifications(final_msg, httpx_results, is_first_scan=True)

    def notify_changes(self, changes):
        if not changes:
            logger.info(f"No changes detected in {self.domain}")
            return

        new_items = [c for c in changes if c["type"] == "new"]
        updated_items = [c for c in changes if c["type"] == "update"]
        new_bruteforce_items = [c for c in new_items if c.get("data", {}).get("bruteforce", False)]

        msg_lines = [f"🔔 *Scan Updates* for `{self.domain}`"]

        if new_items:
            msg_lines.append("")
            msg_lines.append(f"🆕 *New Subdomains* ({len(new_items)}):")
            for item in new_items[:MAX_DISPLAY_NEW]:
                subdomain = item.get("data", {})
                msg_lines.append(Helpers.subdomain_filter(subdomain))

            if len(new_items) > MAX_DISPLAY_NEW:
                msg_lines.append(f"...and `{len(new_items) - MAX_DISPLAY_NEW}` more new subdomains.")

        if updated_items:
            msg_lines.append("")
            msg_lines.append(f"🔄 *Updated Subdomains* ({len(updated_items)}):")
            for item in updated_items[:MAX_DISPLAY_UPDATE]:
                url = item["url"]
                diff = item["diff"]
                msg_lines.append(f"- [{url}]({url})")

                for field in ["status", "title", "tech", "bruteforce"]:
                    if field in diff:
                        old = diff[field].get('old', '-')
                        new = diff[field].get('new', '-')
                        msg_lines.append(f"   • *{field.capitalize()}*: `{old}` ➜ `{new}`")

            if len(updated_items) > MAX_DISPLAY_UPDATE:
                msg_lines.append(f"...and `{len(updated_items) - MAX_DISPLAY_UPDATE}` more updated subdomains.")

        if new_bruteforce_items:
            msg_lines.append("")
            msg_lines.append(f"🛡️ *New DNS Bruteforce Subdomains* ({len(new_bruteforce_items)}):")
            for item in new_bruteforce_items[:MAX_DISPLAY_BRUTEFORCE]:
                subdomain = item.get("data", {})
                msg_lines.append(Helpers.subdomain_filter(subdomain))

            if len(new_bruteforce_items) > MAX_DISPLAY_BRUTEFORCE:
                msg_lines.append(f"...and `{len(new_bruteforce_items) - MAX_DISPLAY_BRUTEFORCE}` more bruteforce subdomains.")

        msg_lines.append("")
        msg_lines.append(f"📊 *Summary*: New: `{len(new_items)}` | Updated: `{len(updated_items)}` | New Bruteforce: `{len(new_bruteforce_items)}`")

        final_msg = "\n".join(msg_lines)
        logger.info("✅ Change notification composed.")

        # Send notification + CSV always
        self.notification_sender.send_notifications(final_msg, changes)
