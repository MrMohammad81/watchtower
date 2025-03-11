import argparse
import yaml
import tldextract
import subprocess
import sys
from datetime import datetime, timedelta
from core.domain_processor import DomainProcessor
from core.subdomain_fetcher import SubdomainFetcher
from utils import logger
from config import settings
from concurrent.futures import ThreadPoolExecutor

def parse_targets_file(yaml_file):
    try:
        with open(yaml_file, 'r') as file:
            data = yaml.safe_load(file)
            return data.get('targets', [])
    except Exception as e:
        logger.error(f"Failed to load targets file: {e}")
        return []

def run_update():
    logger.info("Checking for updates from GitHub...")
    try:
        result = subprocess.run(["git", "pull"], cwd="/usr/local/watchtower", capture_output=True, text=True)
        if result.returncode == 0:
            logger.success("Project updated successfully!")
            print(result.stdout)
        else:
            logger.error("Failed to update project:")
            print(result.stderr)
    except Exception as e:
        logger.error(f"Error during update: {e}")

def process_domain(domain, company_name):
    fetcher = SubdomainFetcher()
    fetcher_results = fetcher.run_all(domain)
    if not fetcher_results:
        logger.warning(f"No subdomains found for {domain}")
        return

    processor = DomainProcessor(domain, company_name)
    processor.process(fetcher_results)

def process_company_targets(company):
    company_name = company['name']
    domains = company.get('domains', [])
    if not domains:
        logger.warning(f"No domains found for company: {company_name}")
        return

    logger.info(f"Processing company: {company_name}")
    with ThreadPoolExecutor(max_workers=settings.THREADS) as executor:
        executor.map(lambda domain: process_domain(domain, company_name), domains)

def main_cli():
    parser = argparse.ArgumentParser(description="Watchtower Subdomain Recon Tool")

    parser.add_argument("-u", "--domain", help="Single domain to scan")
    parser.add_argument("--targets-file", help="Path to targets YAML file")
    parser.add_argument("--threads", type=int, help="Number of threads")
    parser.add_argument("--update", action="store_true", help="Update Watchtower from GitHub")

    # Filters
    parser.add_argument("--show-httpx", metavar="COMPANY", help="Show all httpx results for a company")
    parser.add_argument("--status", type=str, help="Filter by status code (e.g., 200)")
    parser.add_argument("--title", type=str, help="Filter by title keyword (e.g., admin)")
    parser.add_argument("--tech", type=str, help="Filter by technology (e.g., wordpress)")
    parser.add_argument("--url", type=str, help="Filter by URL keyword (e.g., login)")

    # New feature for newly added & updated items
    parser.add_argument("--show-new", metavar="COMPANY", help="Show newly added/updated subdomains for a company")

    args = parser.parse_args()

    if args.threads:
        settings.THREADS = args.threads
        logger.info(f"Threads set to {settings.THREADS} from CLI argument")

    if args.update:
        run_update()
        sys.exit(0)

    # Show HTTPX results with optional filters
    if args.show_httpx:
        company_name = args.show_httpx
        processor = DomainProcessor("", company_name)
        query = {}

        if args.status:
            query["status"] = str(args.status)
        if args.title:
            query["title"] = {"$regex": args.title, "$options": "i"}
        if args.tech:
            query["tech"] = {"$elemMatch": {"$regex": args.tech, "$options": "i"}}
        if args.url:
            query["url"] = {"$regex": args.url, "$options": "i"}

        results = processor.mongo.get_httpx_data(query=query)

        if not results:
            logger.warning("No results found with the given filters.")
        else:
            for res in results:
                logger.info(f"[{res['status']}] {res['url']} | {res['title']} | {res['tech']}")

        processor.mongo.close()
        sys.exit(0)

    # Show NEW/UPDATED items in the last 24 hours
    if args.show_new:
        company_name = args.show_new
        processor = DomainProcessor("", company_name)

        since = datetime.utcnow() - timedelta(days=1)
        query = {
            "$or": [
                {"created_at": {"$gte": since}},
                {"updated_at": {"$gte": since}}
            ]
        }

        new_results = processor.mongo.get_httpx_data(query=query)

        if not new_results:
            logger.warning(f"No new/updated subdomains found in the last 24 hours for {company_name}.")
        else:
            logger.success(f"Found {len(new_results)} NEW/UPDATED subdomains for {company_name}:")
            for res in new_results:
                label = "NEW" if res.get("created_at", None) and res["created_at"] >= since else "UPDATE"
                logger.info(f"[{label}] {res['url']} [{res['status']}] {res['title']} | {res['tech']}")

        processor.mongo.close()
        sys.exit(0)

    # Single domain scan
    if args.domain:
        extracted = tldextract.extract(args.domain)
        company_name = extracted.domain
        logger.info(f"Running single domain scan: {args.domain} (company name: {company_name})")
        process_domain(args.domain, company_name)
        logger.success("Single scan completed!")
        sys.exit(0)

    # Batch scan via targets file
    if args.targets_file:
        companies = parse_targets_file(args.targets_file)
        with ThreadPoolExecutor(max_workers=settings.THREADS) as executor:
            executor.map(process_company_targets, companies)

        logger.success("Batch scan completed!")
        sys.exit(0)

    parser.error("You must provide --targets-file or -u or --show-httpx or --show-new")
    sys.exit(1)
