import argparse
import yaml
import tldextract
from core.domain_processor import DomainProcessor
from core.subdomain_fetcher import SubdomainFetcher
from utils import logger
from config import settings
from concurrent.futures import ThreadPoolExecutor
import subprocess

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
    parser.add_argument("--show-httpx", metavar="COMPANY", help="Show all httpx results for a company")
    parser.add_argument("--update", action="store_true", help="Update Watchtower from GitHub")

    args = parser.parse_args()

    # Dynamic thread override
    if args.threads:
        settings.THREADS = args.threads
        logger.info(f"Threads set to {settings.THREADS} from CLI argument")

    # Handle --update option
    if args.update:
        run_update()
        return

    if args.show_httpx:
        company_name = args.show_httpx
        processor = DomainProcessor("", company_name)
        results = processor.mongo.get_httpx_data()
        for res in results:
            logger.info(f"{res['url']} [{res['status']}] {res['title']} {res['tech']}")
        processor.mongo.close()
        return

    if args.domain:
        extracted = tldextract.extract(args.domain)
        company_name = extracted.domain
        logger.info(f"Running single domain scan: {args.domain} (company name: {company_name})")
        process_domain(args.domain, company_name)
        logger.success("Single scan completed!")
        return

    if args.targets_file:
        companies = parse_targets_file(args.targets_file)

        with ThreadPoolExecutor(max_workers=settings.THREADS) as executor:
            executor.map(process_company_targets, companies)

        logger.success("Batch scan completed!")
        return

    parser.error("You must provide --targets-file or -u or --show-httpx")
