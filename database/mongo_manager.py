import pymongo
import re
from utils import logger
from datetime import datetime

class MongoManager:
    def __init__(self, mongo_uri, program_name, domain_name):
        self.mongo_uri = mongo_uri
        self.program_name = program_name.replace('.', '_').replace('-', '_')
        self.domain_name = domain_name.replace('.', '_').replace('-', '_')

        # Connect with program name
        self.client = pymongo.MongoClient(mongo_uri)
        self.db = self.client[f"{self.program_name}_db"]

        self.httpx = self.db[f"{self.domain_name}_httpx_results"]
        self.updates = self.db[f"{self.domain_name}_update_logs"]

    def update_httpx(self, httpx_data):
        changes = []
        logger.info(f"🔧 Starting httpx results processing for `{self.domain_name}`... Total: {len(httpx_data)}")

        for item in httpx_data:
            if isinstance(item, str):
                line = item
                is_bruteforce = False
            else:
                line = item.get("line", "")
                is_bruteforce = item.get("bruteforce", False)

            logger.info(f"⚙️ Processing line: {line}")

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
                logger.success(f"🆕 New entry inserted for URL: {url} | bruteforce: {is_bruteforce}")

            else:
                diff = {}

                for field in ["status", "title", "tech"]:
                    if existing.get(field) != doc[field]:
                        diff[field] = {"old": existing.get(field), "new": doc[field]}

                if existing.get("bruteforce") != is_bruteforce:
                    diff["bruteforce"] = {"old": existing.get("bruteforce", False), "new": is_bruteforce}

                if not diff:
                    logger.info(f"No changes for URL: {url}")
                    continue

                doc["created_at"] = existing.get("created_at", datetime.utcnow())
                self.httpx.update_one({"url": url}, {"$set": doc})

                self.updates.insert_one({
                    "url": url,
                    "diff": diff,
                    "updated_at": datetime.utcnow()
                })

                changes.append({"type": "update", "url": url, "diff": diff})
                logger.success(f"🔄 Updated entry for URL: {url} with changes: {diff}")

        logger.success(f"✅ Finished processing httpx results. Changes detected: {len(changes)}")
        return changes

    def get_httpx_data(self, query=None):
        if query is None:
            query = {}
        return list(self.httpx.find(query, {"_id": 0}))

    def get_update_logs(self):
        return list(self.updates.find({}, {"_id": 0}))

    def get_bruteforce_only(self):
        query = {"bruteforce": True}
        return list(self.httpx.find(query, {"_id": 0}))

    def close(self):
        self.client.close()
