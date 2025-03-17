import pymongo
import re
from utils import logger
from datetime import datetime
from config import settings

class MongoManager:
    def __init__(self, mongo_uri, program_name, domain_name=None):
        self.mongo_uri = mongo_uri
        self.program_name = program_name.replace('.', '_').replace('-', '_')
        self.domain_name = domain_name.replace('.', '_').replace('-', '_') if domain_name else None

        self.client = pymongo.MongoClient(self.mongo_uri)
        self.db = self.client[f"{self.program_name}_db"]

        if self.domain_name:
            self.httpx = self.db[f"{self.domain_name}_httpx_results"]
            self.updates = self.db[f"{self.domain_name}_update_logs"]
        else:
            self.httpx = None
            self.updates = None

    # ---------- STATIC METHODS ----------
    
    @staticmethod
    def get_client():
        logger.debug("🔌 Getting MongoDB client")
        return pymongo.MongoClient(settings.MONGO_URI)

    @staticmethod
    def list_programs():
        logger.debug("🔎 Listing all programs in MongoDB...")
        client = MongoManager.get_client()

        dbs = client.list_database_names()
        programs = [db.replace('_db', '') for db in dbs if db.endswith('_db')]

        if not programs:
            logger.warning("⚠️ No programs found in MongoDB.")
        else:
            logger.success(f"✅ Found {len(programs)} programs:")
            for p in programs:
                logger.info(f"- {p}")

        client.close()
        return programs

    # ---------- INSTANCE METHODS ----------

    def list_domains(self):
        logger.debug(f"🔎 Listing domains for program `{self.program_name}`")
        collections = self.db.list_collection_names()

        domains = []
        for coll in collections:
            if coll.endswith("_httpx_results"):
                domain = coll.replace("_httpx_results", "")
                domains.append(domain)

        return domains

    def drop_program(self):
        logger.warning(f"⚠️ Dropping entire program `{self.program_name}` and its data...")
        self.client.drop_database(f"{self.program_name}_db")
        logger.success(f"✅ Program `{self.program_name}` has been dropped.")

    def drop_domain(self, domain_name):
        domain_clean = domain_name.replace('.', '_').replace('-', '_')

        logger.warning(f"⚠️ Dropping domain `{domain_clean}` inside program `{self.program_name}`...")

        self.db.drop_collection(f"{domain_clean}_httpx_results")
        self.db.drop_collection(f"{domain_clean}_update_logs")

        logger.success(f"✅ Domain `{domain_clean}` has been dropped from program `{self.program_name}`.")

    # ---------- DATA OPERATIONS ----------

    def update_httpx(self, httpx_data):
        if not self.httpx:
            logger.error("❌ No domain selected. Cannot update HTTPX data.")
            return []

        changes = []
        logger.info(f"🔧 Processing httpx results for `{self.domain_name}`... Total: {len(httpx_data)}")

        for item in httpx_data:
            if isinstance(item, str):
                line = item
                is_bruteforce = False
            else:
                line = item.get("line", "")
                is_bruteforce = item.get("bruteforce", False)

            logger.debug(f"⚙️ Processing line: {line}")

            brackets = re.findall(r'\[(.*?)\]', line)
            url_match = re.match(r'(\S+)', line)

            if not url_match:
                logger.warning(f"[SKIPPED] Invalid httpx output line: {line}")
                continue

            url = url_match.group(1)
            status = brackets[0] if len(brackets) >= 1 else ""
            title = brackets[1] if len(brackets) >= 2 else ""
            tech_raw = brackets[2] if len(brackets) >= 3 else ""
            tech = [t.strip() for t in tech_raw.split(",")] if tech_raw else []

            doc = {
                "url": url,
                "status": status,
                "title": title,
                "tech": tech,
                "updated_at": datetime.utcnow(),
                "bruteforce": is_bruteforce
            }

            existing = self.httpx.find_one({"url": url})

            if not existing:
                doc["created_at"] = datetime.utcnow()
                self.httpx.insert_one(doc)
                changes.append({"type": "new", "data": doc})
                logger.success(f"🆕 Inserted: {url} (bruteforce: {is_bruteforce})")

            else:
                diff = {}
                for field in ["status", "title", "tech"]:
                    if existing.get(field) != doc[field]:
                        diff[field] = {"old": existing.get(field), "new": doc[field]}

                if existing.get("bruteforce") != is_bruteforce:
                    diff["bruteforce"] = {"old": existing.get("bruteforce", False), "new": is_bruteforce}

                if not diff:
                    logger.info(f"No changes detected for {url}")
                    continue

                doc["created_at"] = existing.get("created_at", datetime.utcnow())
                self.httpx.update_one({"url": url}, {"$set": doc})

                self.updates.insert_one({
                    "url": url,
                    "diff": diff,
                    "updated_at": datetime.utcnow()
                })

                changes.append({"type": "update", "url": url, "diff": diff})
                logger.success(f"🔄 Updated: {url} with changes: {diff}")

        logger.success(f"✅ Finished httpx processing. Total changes: {len(changes)}")
        return changes

    def get_httpx_data(self, query=None):
        if not self.httpx:
            logger.error("❌ No domain selected for fetching HTTPX data.")
            return []

        query = query or {}
        logger.debug(f"🔎 Fetching HTTPX data with query: {query}")
        return list(self.httpx.find(query, {"_id": 0}))

    def get_update_logs(self):
        if not self.updates:
            logger.error("❌ No domain selected for fetching update logs.")
            return []

        logger.debug("🔎 Fetching update logs")
        return list(self.updates.find({}, {"_id": 0}))

    def get_bruteforce_only(self):
        if not self.httpx:
            logger.error("❌ No domain selected for fetching bruteforce results.")
            return []

        query = {"bruteforce": True}
        logger.debug("🔎 Fetching bruteforce-only subdomains")
        return list(self.httpx.find(query, {"_id": 0}))

    def close(self):
        self.client.close()
        logger.debug("🔒 MongoDB connection closed")
