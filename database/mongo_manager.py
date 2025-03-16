import pymongo
import re
from utils import logger
from datetime import datetime

class MongoManager:
    def __init__(self, mongo_uri, program_name, domain_name):
        """
        دیتابیس به اسم ProgramName_db
        کالکشن به اسم DomainName1_httpx_results و DomainName1_update_logs
        """
        self.mongo_uri = mongo_uri
        self.program_name = program_name.replace('.', '_').replace('-', '_')
        self.domain_name = domain_name.replace('.', '_').replace('-', '_')

        # Connect to MongoDB client and database (Program Name)
        self.client = pymongo.MongoClient(mongo_uri)
        self.db = self.client[f"{self.program_name}_db"]

        # Collections per domain
        self.httpx = self.db[f"{self.domain_name}_httpx_results"]
        self.updates = self.db[f"{self.domain_name}_update_logs"]

    def update_httpx(self, httpx_data):
        changes = []
        logger.info(f"🔧 Starting httpx processing for `{self.domain_name}`... Total entries: {len(httpx_data)}")

        for item in httpx_data:
            # Detect whether input is a line (string) or dict (parsed)
            if isinstance(item, str):
                line = item
                is_bruteforce = False
            else:
                line = item.get("line", "")
                is_bruteforce = item.get("bruteforce", False)

            logger.debug(f"⚙️ Processing line: {line}")

            # Extract fields from the httpx output
            brackets = re.findall(r'\[(.*?)\]', line)
            url_match = re.match(r'(\S+)', line)

            if not url_match:
                logger.warning(f"[SKIPPED] Invalid httpx output: {line}")
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

            # Check for existing entry
            existing = self.httpx.find_one({"url": url})

            if not existing:
                # New entry found
                doc["created_at"] = datetime.utcnow()
                self.httpx.insert_one(doc)
                changes.append({"type": "new", "data": doc})
                logger.success(f"🆕 New URL added: {url} (bruteforce: {is_bruteforce})")
            else:
                # Compare and update existing entry
                diff = {}
                for field in ["status", "title", "tech"]:
                    if existing.get(field) != doc[field]:
                        diff[field] = {"old": existing.get(field), "new": doc[field]}

                # Compare bruteforce flag
                if existing.get("bruteforce") != is_bruteforce:
                    diff["bruteforce"] = {"old": existing.get("bruteforce", False), "new": is_bruteforce}

                if not diff:
                    logger.info(f"No changes for: {url}")
                    continue

                # Update existing document
                doc["created_at"] = existing.get("created_at", datetime.utcnow())
                self.httpx.update_one({"url": url}, {"$set": doc})

                # Log the update diffs
                self.updates.insert_one({
                    "url": url,
                    "diff": diff,
                    "updated_at": datetime.utcnow()
                })

                changes.append({"type": "update", "url": url, "diff": diff})
                logger.success(f"🔄 URL updated: {url} Changes: {diff}")

        logger.success(f"✅ Done processing `{self.domain_name}`. Total changes: {len(changes)}")
        return changes

    def get_httpx_data(self, query=None):
        """Get data from domain's httpx_results collection."""
        query = query or {}
        return list(self.httpx.find(query, {"_id": 0}))

    def get_update_logs(self):
        """Get update logs for this domain."""
        return list(self.updates.find({}, {"_id": 0}))

    def get_bruteforce_only(self):
        """Get only bruteforce subdomains."""
        query = {"bruteforce": True}
        return list(self.httpx.find(query, {"_id": 0}))

    def get_domains(self):
        """List all domains in this program (collections)."""
        collections = self.db.list_collection_names()
        domains = []
        for col in collections:
            if col.endswith('_httpx_results'):
                domain_name = col.replace('_httpx_results', '')
                domains.append(domain_name)
        return domains

    def close(self):
        """Close Mongo connection."""
        self.client.close()

    @staticmethod
    def list_programs(mongo_uri):
        """List all program databases."""
        client = pymongo.MongoClient(mongo_uri)
        dbs = client.list_database_names()
        # Filter only program databases ending with _db
        programs = [db.replace('_db', '') for db in dbs if db.endswith('_db')]
        client.close()
        return programs

    @staticmethod
    def drop_program(mongo_uri, program_name):
        """Drop an entire program (database)."""
        client = pymongo.MongoClient(mongo_uri)
        db_name = f"{program_name}_db"
        client.drop_database(db_name)
        logger.success(f"🗑️ Program `{program_name}` dropped successfully.")
        client.close()
