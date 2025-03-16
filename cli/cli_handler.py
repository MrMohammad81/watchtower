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

def process_domain(domain, company_name):
    fetcher = SubdomainFetcher()
    fetcher_results = fetcher.run_all(domain)
    if not fetcher_results:
        logger.warning(f"⚠️ No subdomains found for {domain}")
        return
    processor = DomainProcessor(domain, company_name)
    processor.process(fetcher_results)

def process_company_targets(company):
    company_name = company['name']
    domains = company.get('domains', [])
    if not domains:
        logger.warning(f"⚠️ No domains found for company: {company_name}")
        return
    logger.info(f"🚀 Processing company: {company_name}")
    with ThreadPoolExecutor(max_workers=settings.THREADS) as executor:
        executor.map(lambda domain: process_domain(domain, company_name), domains)

def main_cli():
    parser = argparse.ArgumentParser(description="🛡️ Watchtower Subdomain Recon Tool")

    # Main arguments
    parser.add_argument("-u", "--domain", help="Single domain to scan")
    parser.add_argument("--targets-file", help="Path to targets YAML file")
    parser.add_argument("--threads", type=int, help="Number of threads (override default)")
    parser.add_argument("--update", action="store_true", help="Update Watchtower from GitHub")

    # Filters & Queries
    parser.add_argument("--show-httpx", metavar="COMPANY", help="Show httpx results for a company")
    parser.add_argument("--show-new", metavar="COMPANY", help="Show newly added subdomains for a company")
    parser.add_argument("--show-updates", metavar="COMPANY", help="Show updated subdomains and their changes")
    parser.add_argument("--domain-filter", metavar="DOMAIN", help="Domain to filter results in multi-domain companies")
    
    # Filters on result display
    parser.add_argument("--status", type=str, help="Filter by status code (e.g., 200)")
    parser.add_argument("--dns-check", type=str, help="Filter by DNS bruteforce subdomains (true/false)")
    parser.add_argument("--title", type=str, help="Filter by title keyword (e.g., admin)")
    parser.add_argument("--tech", type=str, help="Filter by technology (e.g., wordpress)")
    parser.add_argument("--url", type=str, help="Filter by URL keyword (e.g., login)")

    args = parser.parse_args()

    # Threads
    if args.threads:
        settings.THREADS = args.threads
        logger.info(f"🧵 Threads set to {settings.THREADS} from CLI argument")

    # Git Update
    if args.update:
        run_update()
        sys.exit(0)

    # Queries
    if args.show_httpx:
        handle_show_httpx(args)
        sys.exit(0)

    if args.show_new:
        handle_show_new(args)
        sys.exit(0)

    if args.show_updates:
        handle_show_updates(args)
        sys.exit(0)

    # Scan a single domain
    if args.domain:
        extracted = tldextract.extract(args.domain)
        company_name = extracted.domain
        logger.info(f"🚀 Running single domain scan: {args.domain} (company: {company_name})")
        process_domain(args.domain, company_name)
        logger.success("✅ Single scan completed!")
        sys.exit(0)

    # YAML Batch scan
    if args.targets_file:
        companies = parse_targets_file(args.targets_file)
        with ThreadPoolExecutor(max_workers=settings.THREADS) as executor:
            executor.map(process_company_targets, companies)
        logger.success("✅ Batch scan completed!")
        sys.exit(0)

    # If nothing matches
    parser.error("❌ You must provide --targets-file or -u or --show-httpx or --show-new or --show-updates")
    sys.exit(1)

def handle_show_httpx(args):
    company_name = args.show_httpx
    domain_filter = args.domain_filter
    processor = DomainProcessor(domain_filter or "", company_name)

    query = build_query_from_filters(args)
    logger.info(f"📄 Running httpx query for company `{company_name}` with filters: {query}")

    results = processor.mongo.get_httpx_data(query=query)

    if not results:
        logger.warning(f"⚠️ No results found for `{company_name}` with the given filters.")
    else:
        logger.success(f"✅ {len(results)} results found for `{company_name}`")
        for res in results:
            logger.info(f"{res['url']} [{res['status']}] {res['title']} {res['tech']}")

    processor.mongo.close()

def handle_show_new(args):
    company_name = args.show_new
    domain_filter = args.domain_filter
    processor = DomainProcessor(domain_filter or "", company_name)

    logger.info(f"🆕 Fetching new subdomains for `{company_name}`...")
    yesterday = datetime.utcnow() - timedelta(days=1)
    query = {"created_at": {"$gte": yesterday}}

    extra_filters = build_query_from_filters(args)
    query.update(extra_filters)

    logger.info(f"📄 Querying new entries with filters: {query}")

    new_results = processor.mongo.get_httpx_data(query=query)

    if not new_results:
        logger.warning("⚠️ No new subdomains found matching your filters.")
    else:
        logger.success(f"✅ Found {len(new_results)} new subdomains for `{company_name}`:")
        for res in new_results:
            logger.info(f"{res['url']} [{res['status']}] {res['title']} {res['tech']}")

    processor.mongo.close()

def handle_show_updates(args):
    company_name = args.show_updates
    domain_filter = args.domain_filter
    processor = DomainProcessor(domain_filter or "", company_name)

    logger.info(f"🔄 Fetching updates for `{company_name}`...")

    updates = processor.mongo.get_update_logs()

    if not updates:
        logger.warning(f"⚠️ No updated subdomains found for `{company_name}`.")
    else:
        logger.success(f"✅ Found {len(updates)} updates for `{company_name}`:")
        for upd in updates:
            url = upd.get("url", "N/A")
            diff = upd.get("diff", {})
            logger.info(f"- [{url}]({url})")
            for field, change in diff.items():
                old_val = change.get("old", "-")
                new_val = change.get("new", "-")
                logger.info(f"  • {field.capitalize()}: {old_val} ➜ {new_val}")
            logger.info("")

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

    if args.dns_check and args.dns_check.lower() == "true":
        query["bruteforce"] = True
    elif args.dns_check and args.dns_check.lower() == "false":
        query["bruteforce"] = False

    return query
