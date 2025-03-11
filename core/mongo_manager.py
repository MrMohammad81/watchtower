import pymongo
import re
from utils import logger
from datetime import datetime

class MongoManager:
    def __init__(self, mongo_uri, company_name):
        self.mongo_uri = mongo_uri
        self.company_name = company_name.replace('.', '_').replace('-', '_')
        self.client = pymongo.MongoClient(mongo_uri)
        self.db = self.client[f"{self.company_name}_db"]
        self.httpx = self.db["httpx_results"]

    def update_httpx(self, httpx_data):
        changes = []
        logger.info(f"Starting httpx results processing... Total lines: {len(httpx_data)}")

        for line in httpx_data:
            logger.info(f"Processing line: {line}")

            brackets = re.findall(r'\[(.*?)\]', line)
            url_match = re.match(r'(\S+)', line)

            if not url_match:
                logger.warning(f"[SKIPPED] Invalid httpx output line: {line}")
                continue

            url = url_match.group(1)
            status = brackets[0] if len(brackets) >= 1 else ""
            title = brackets[1] if len(brackets) >= 2 else ""
            tech_raw = brackets[2] if len(brackets) >= 3 else ""
            tech = [t.strip() for t in tech_raw.split(",") if t.strip()] if tech_raw else []

            doc = {
                "url": url,
                "status": status,
                "title": title,
                "tech": tech,
                "updated_at": datetime.utcnow()
            }

            existing = self.httpx.find_one({"url": url})

            if not existing:
                # New record
                doc["created_at"] = datetime.utcnow()
                self.httpx.insert_one(doc)
                changes.append({"type": "new", "data": doc})
                logger.success(f"New entry inserted for URL: {url}")

            else:
                diff = {}
                for field in ["status", "title", "tech"]:
                    if existing.get(field) != doc[field]:
                        diff[field] = {"old": existing.get(field), "new": doc[field]}

                if diff:
                    self.httpx.update_one({"url": url}, {"$set": doc})
                    changes.append({"type": "update", "url": url, "diff": diff})
                    logger.success(f"Updated entry for URL: {url} with changes: {diff}")

        logger.success(f"Finished processing httpx results. Changes detected: {len(changes)}")
        return changes

    def get_httpx_data(self, query=None):
        if query is None:
            query = {}
        return list(self.httpx.find(query, {"_id": 0}))

    def close(self):
        self.client.close()
