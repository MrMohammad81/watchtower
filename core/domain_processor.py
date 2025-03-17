from database.mongo_manager import MongoManager
from core.scanner import Scanner
from core.notification_manager import NotificationManager
from services.notification_sender import NotificationSender
from utils import logger
from config import settings

# Thresholds
MAX_DISPLAY_NEW = 10
MAX_DISPLAY_UPDATE = 5
MAX_DISPLAY_BRUTEFORCE = 5
ALLOWED_STATUS_CODES = ['200', '403', '404']

# Platform message limits (not restricting anymore for CSV)
DISCORD_CHAR_LIMIT = 1900
TELEGRAM_CHAR_LIMIT = 4000

class DomainProcessor:
    def __init__(self, domain, program_name):
        self.domain = domain
        self.program_name = program_name
        self.mongo = MongoManager(settings.MONGO_URI, program_name, domain)
        self.scanner = Scanner(settings.RESOLVER_PATH)
        self.notification_sender = NotificationSender(domain)
        self.notification_manager = NotificationManager(domain=self.domain, program_name=program_name, notification_sender=self.notification_sender)

    def process(self, fetcher_results):
        logger.info(f"🔎 Processing domain: {self.domain}")
        # Run scan chain
        httpx_results = self.scanner.run_scan_chain(fetcher_results, self.domain)
        count_results = len(httpx_results)

       
        # Check if this is the first scan
        is_first_scan = self.mongo.httpx.count_documents({}) == 0

        # Update MongoDB and get changes
        changes = self.mongo.update_httpx(httpx_results)

        if is_first_scan:
            self.notification_manager.notify_first_scan(count_results, httpx_results)
            logger.success(f"✅ First scan for {self.domain} completed. Subdomains found: {count_results}")
        else:
            self.notification_manager.notify_changes(changes)

        self.mongo.close()

