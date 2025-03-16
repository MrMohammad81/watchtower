import argparse
import yaml
import tldextract
from core.domain_processor import DomainProcessor
from core.subdomain_fetcher import SubdomainFetcher
from utils import logger
from config import settings
from concurrent.futures import ThreadPoolExecutor
import subprocess
import sys
from datetime import datetime, timedelta
from infrastructure.mongo_manager import MongoManager

def parse_targets_file(yaml_file):
    try:
        with open(yaml_file, 'r') as file:
            data = yaml.safe_load(file)
            return data.get('targets', [])
    except Exception as e:
        logger.error(f"❌ Failed to load targets file: {e}")
        return []

def run_update():
    logger.info("🔄 Checking for updates from GitHub...")
    try:
        result = subprocess.run(["git", "pull"], cwd="/usr/local/watchtower", capture_output=True, text=True)
        if result.returncode == 0:
            logger.success("✅ Project updated successfully!")
            print(result.stdout)
        else:
            logger.error("❌ Failed to update project:")
            print(result.stderr)
    except Exception as e:
        logger.error(f"⚠️ Error during update: {e}")

def process_domain(domain, program_name):
    fetcher = SubdomainFetcher()
    fetcher_results = fetcher.run_all(domain)

    if not fetcher_results:
        logger.warning(f"⚠️ No subdomains found for {domain}")
        return

    processor = DomainProcessor(domain, program_name)
    processor.process(fetcher_results)

def process_company_targets(company):
    program_name = company['name']
    domains = company.get('domains', [])

    if not domains:
        logger.warning(f"⚠️ No domains found for program: {program_name}")
        return

    logger.info(f"🚀 Processing program: {program_name}")

    with ThreadPoolExecutor(max_workers=settings.THREADS) as executor:
        executor.map(lambda domain: process_domain(domain, program_name), domains)

def main_cli():
    parser = argparse.ArgumentParser(description="🛡️ Watchtower Subdomain Recon Tool")

    # Main commands
    parser.add_argument("-u", "--domain", help="Single domain to scan")
    parser.add_argument("--targets-file", help="Path to targets YAML file")
    parser.add_argument("--threads", type=int, help="Number of threads (override default)")
    parser.add_argument("--update", action="store_true", help="Update Watchtower from GitHub")

    # Query commands
    parser.add_argument("--show-httpx", metavar="PROGRAM", help="Show httpx results for a program (optional filters)")
    parser.add_argument("--show-new", metavar="PROGRAM", help="Show newly added subdomains for a program (optional filters)")
    parser.add_argument("--show-updates", metavar="PROGRAM", help="Show updated subdomains and their changes for a program")

    # Extra management commands
    parser.add_argument("--programs", action="store_true", help="List all programs")
    parser.add_argument("--drop", metavar="PROGRAM", help="Drop a program from database")

    # Filters
    parser.add_argument("--domain-name", metavar="DOMAIN", help="Filter results for a specific domain inside a program")
    parser.add_argument("--status", type=str, help="Filter by status code")
    parser.add_argument("--dns-check", type=str, help="Filter DNS bruteforce subdomains (true/false)")
    parser.add_argument("--title", type=str, help="Filter by title keyword")
    parser.add_argument("--tech", type=str, help="Filter by technology keyword")
    parser.add_argument("--url", type=str, help="Filter by URL keyword")

    args = parser.parse_args()

    if args.threads:
        settings.THREADS = args.threads

    if args.update:
        run_update()
        sys.exit(0)

    if args.programs:
        list_programs()
        sys.exit(0)

    if args.drop:
        drop_program(args.drop)
        sys.exit(0)

    if args.show_httpx:
        handle_show_httpx(args)
        sys.exit(0)

    if args.show_new:
        handle_show_new(args)
        sys.exit(0)

    if args.show_updates:
        handle_show_updates(args)
        sys.exit(0)

    if args.domain:
        extracted = tldextract.extract(args.domain)
        program_name = extracted.domain
        process_domain(args.domain, program_name)
        sys.exit(0)

    if args.targets_file:
        companies = parse_targets_file(args.targets_file)
        with ThreadPoolExecutor(max_workers=settings.THREADS) as executor:
            executor.map(process_company_targets, companies)
        sys.exit(0)

    parser.error("❌ You must provide --targets-file or -u or --show-* options")
    sys.exit(1)

def list_programs():
    client = MongoManager.get_client()
    db_list = client.list_database_names()

    logger.info("📚 Available Programs:")
    for db in db_list:
        if db.endswith("_db"):
            program_name = db.replace("_db", "")
            logger.info(f" - {program_name}")

    client.close()

def drop_program(program_name):
    client = MongoManager.get_client()
    db_name = f"{program_name}_db"

    if db_name in client.list_database_names():
        client.drop_database(db_name)
        logger.success(f"🗑️ Program `{program_name}` dropped successfully.")
    else:
        logger.warning(f"❌ Program `{program_name}` not found.")

    client.close()

def handle_show_httpx(args):
    program_name = args.show_httpx
    processor = DomainProcessor("", program_name)

    query = build_query_from_filters(args)
    logger.info(f"📄 Query for program `{program_name}` with filters: {query}")

    results = processor.mongo.get_httpx_data(query=query, domain=args.domain_name)

    if not results:
        logger.warning("⚠️ No results found.")
    else:
        for res in results:
            logger.info(f"{res['url']} [{res['status']}] {res['title']} {res['tech']}")

    processor.mongo.close()

def handle_show_new(args):
    program_name = args.show_new
    processor = DomainProcessor("", program_name)

    yesterday = datetime.utcnow() - timedelta(days=1)
    query = {"created_at": {"$gte": yesterday}}
    query.update(build_query_from_filters(args))

    logger.info(f"📄 Query for new entries: {query}")

    results = processor.mongo.get_httpx_data(query=query, domain=args.domain_name)

    if not results:
        logger.warning("⚠️ No new subdomains found.")
    else:
        for res in results:
            logger.info(f"{res['url']} [{res['status']}] {res['title']} {res['tech']}")

    processor.mongo.close()

def handle_show_updates(args):
    program_name = args.show_updates
    processor = DomainProcessor("", program_name)

    updates = processor.mongo.get_update_logs(domain=args.domain_name)

    if not updates:
        logger.warning("⚠️ No updated subdomains found.")
    else:
        for upd in updates:
            url = upd.get("url", "N/A")
            diff = upd.get("diff", {})
            logger.info(f"- [{url}]({url})")
            for field, change in diff.items():
                old = change.get("old", "-")
                new = change.get("new", "-")
                logger.info(f"  • {field.capitalize()}: {old} ➜ {new}")

    processor.mongo.close()

def build_query_from_filters(args):
    query = {}

    if args.status:
        query["status"] = str(args.status)
    if args.title:
        query["title"] = {"$regex": args.title, "$options": "i"}
    if args.tech:
        query["tech"] = {"$elemMatch": {"$regex": args.tech, "$options": "i"}}
    if args.url:
        query["url"] = {"$regex": args.url, "$options": "i"}
    if args.dns_check:
        query["bruteforce"] = args.dns_check.lower() == "true"

    return query
