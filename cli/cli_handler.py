import argparse
import yaml
import tldextract
import subprocess
import sys
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor

from core.domain_processor import DomainProcessor
from core.subdomain_fetcher import SubdomainFetcher
from database.mongo_manager import MongoManager
from utils import logger
from config import settings


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
        result = subprocess.run(
            ["git", "pull"],
            cwd="/usr/local/watchtower",
            capture_output=True,
            text=True
        )
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


def process_program_targets(program):
    program_name = program['name']
    domains = program.get('domains', [])

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
    parser.add_argument("--programs", action="store_true", help="List all programs")
    parser.add_argument("--domains", metavar="PROGRAM", help="List all domains for a program")
    parser.add_argument("--drop", metavar="PROGRAM", help="Delete a program, or domain inside a program (use --domain-name)")
    
    parser.add_argument("--show-httpx", metavar="PROGRAM", help="Show httpx results for a program (optional filters)")
    parser.add_argument("--show-new", metavar="PROGRAM", help="Show newly added subdomains for a program (optional filters)")
    parser.add_argument("--show-updates", metavar="PROGRAM", help="Show updated subdomains and their changes for a program")

    # Filters
    parser.add_argument("--domain-name", metavar="DOMAIN", help="Specify domain inside program (for queries or deletion)")
    parser.add_argument("--status", type=str, help="Filter by status code")
    parser.add_argument("--dns-check", type=str, help="Filter DNS bruteforce subdomains (true/false)")
    parser.add_argument("--title", type=str, help="Filter by title keyword")
    parser.add_argument("--tech", type=str, help="Filter by technology keyword")
    parser.add_argument("--url", type=str, help="Filter by URL keyword")

    args = parser.parse_args()

    # Threads
    if args.threads:
        settings.THREADS = args.threads
        logger.info(f"🧵 Threads set to {settings.THREADS} from CLI argument")

    # Update
    if args.update:
        run_update()
        sys.exit(0)

    # Program listings and actions
    if args.programs:
        MongoManager.list_programs()
        sys.exit(0)

    if args.domains:
        handle_domains(args.domains)
        sys.exit(0)

    if args.drop:
        handle_drop(args.drop, args.domain_name)
        sys.exit(0)

    # Show httpx results with filters
    if args.show_httpx:
        handle_show_httpx(args)
        sys.exit(0)

    # Show new subdomains
    if args.show_new:
        handle_show_new(args)
        sys.exit(0)

    # Show updated subdomains
    if args.show_updates:
        handle_show_updates(args)
        sys.exit(0)

    # Single domain scan
    if args.domain:
        extracted = tldextract.extract(args.domain)
        program_name = extracted.domain
        process_domain(args.domain, program_name)
        sys.exit(0)

    # Batch scan from targets file
    if args.targets_file:
        programs = parse_targets_file(args.targets_file)
        with ThreadPoolExecutor(max_workers=settings.THREADS) as executor:
            executor.map(process_program_targets, programs)
        sys.exit(0)

    parser.error("❌ You must provide --targets-file, -u, --programs, --domains, --show-* or --drop")
    sys.exit(1)


# ----------------- HANDLER FUNCTIONS ----------------- #

def handle_domains(program_name):
    mongo = MongoManager(settings.MONGO_URI, program_name=program_name)

    domains = mongo.list_domains()
    mongo.close()

    if not domains:
        logger.warning(f"⚠️ No domains found for program `{program_name}`.")
    else:
        logger.success(f"✅ Found {len(domains)} domains in program `{program_name}`:")
        for d in domains:
            logger.info(f"- {d}")


def handle_drop(program_name, domain_name=None):
    mongo = MongoManager(settings.MONGO_URI, program_name)

    if domain_name:
        mongo.drop_domain(domain_name)
    else:
        mongo.drop_program()

    mongo.close()


def handle_show_httpx(args):
    program_name = args.show_httpx
    domain_name = args.domain_name
    mongo = MongoManager(settings.MONGO_URI, program_name, domain_name)

    query = build_query_from_filters(args)
    logger.info(f"📄 Querying program `{program_name}`, domain `{domain_name or 'ALL'}` with filters: {query}")

    results = mongo.get_httpx_data(query=query)

    if not results:
        logger.warning("⚠️ No results found.")
    else:
        logger.success(f"✅ Found {len(results)} entries:")
        for res in results:
            logger.info(f"{res['url']} [{res['status']}] {res['title']} {res['tech']}")

    mongo.close()


def handle_show_new(args):
    program_name = args.show_new
    domain_name = args.domain_name
    mongo = MongoManager(settings.MONGO_URI, program_name, domain_name)

    yesterday = datetime.utcnow() - timedelta(days=1)
    query = {"created_at": {"$gte": yesterday}}
    query.update(build_query_from_filters(args))

    logger.info(f"📄 Querying NEW entries for `{program_name}`, domain `{domain_name or 'ALL'}`...")
    results = mongo.get_httpx_data(query=query)

    if not results:
        logger.warning("⚠️ No new subdomains found.")
    else:
        logger.success(f"✅ Found {len(results)} new subdomains:")
        for res in results:
            logger.info(f"{res['url']} [{res['status']}] {res['title']} {res['tech']}")

    mongo.close()


def handle_show_updates(args):
    program_name = args.show_updates
    domain_name = args.domain_name
    mongo = MongoManager(settings.MONGO_URI, program_name, domain_name)

    logger.info(f"📄 Fetching update logs for `{program_name}`, domain `{domain_name or 'ALL'}`...")
    updates = mongo.get_update_logs()

    if not updates:
        logger.warning("⚠️ No updated subdomains found.")
    else:
        logger.success(f"✅ Found {len(updates)} updated subdomains:")
        for upd in updates:
            url = upd.get("url", "N/A")
            diff = upd.get("diff", {})
            logger.info(f"- {url}")
            for field, change in diff.items():
                old_val = change.get("old", "-")
                new_val = change.get("new", "-")
                logger.info(f"  • {field.capitalize()}: {old_val} ➜ {new_val}")

    mongo.close()


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
