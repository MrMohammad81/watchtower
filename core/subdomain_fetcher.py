import subprocess
import requests
import json
import re
from utils import logger
from config import settings
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class SubdomainFetcher:
    def __init__(self):
        self.shodan_api_key = settings.SHODAN_API_KEY
        self.chaos_api_key = settings.CHAOS_API_KEY
        self.session = self.create_session_with_retries()

    def create_session_with_retries(self):
        session = requests.Session()
        retries = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            raise_on_status=False
        )
        adapter = HTTPAdapter(max_retries=retries)
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        return session

    def from_crtsh(self, domain):
        logger.info(f"[crt.sh] Fetching subdomains for {domain}")
        url = f"https://crt.sh/?q={domain}&output=json"
        try:
            response = self.session.get(url, timeout=30)
            if response.status_code != 200:
                logger.warning(f"[crt.sh] returned status {response.status_code} for {domain}")
                return []
            data = response.json()
            subdomains = set()
            for entry in data:
                name_value = entry.get('name_value', '')
                for sub in name_value.split("\n"):
                    if "*" not in sub:
                        subdomains.add(sub.strip())
            logger.success(f"[crt.sh] Found {len(subdomains)} subdomains")
            return list(subdomains)
        except Exception as e:
            logger.error(f"[crt.sh] Error: {e}")
            return []

    def from_subfinder(self, domain):
        logger.info(f"[subfinder] Running for {domain}")
        try:
            cmd = f"subfinder -d {domain} -silent -all"
            output = subprocess.check_output(cmd, shell=True, text=True)
            subdomains = [line.strip() for line in output.splitlines() if line.strip()]
            logger.success(f"[subfinder] Found {len(subdomains)} subdomains")
            return subdomains
        except Exception as e:
            logger.error(f"[subfinder] Error: {e}")
            return []

    def from_shodan(self, domain):
        logger.info(f"[shosubgo] Running for {domain}")
        try:
            cmd = f"shosubgo -d {domain} -s {self.shodan_api_key}"
            output = subprocess.check_output(cmd, shell=True, text=True)
            subdomains = [line.strip() for line in output.splitlines() if line.strip()]
            logger.success(f"[shosubgo] Found {len(subdomains)} subdomains")
            return subdomains
        except subprocess.CalledProcessError as e:
            logger.error(f"[shosubgo] Command failed: {e}")
            return []
        except Exception as e:
            logger.error(f"[shosubgo] Error: {e}")
            return []

    def from_urlscan(self, domain):
        logger.info(f"[urlscan.io] Fetching subdomains for {domain}")
        url = f"https://urlscan.io/api/v1/search/?q=domain:{domain}"
        try:
            response = self.session.get(url, timeout=30)
            if response.status_code != 200:
                logger.warning(f"[urlscan.io] returned status {response.status_code} for {domain}")
                return []
            data = response.json()
            subdomains = set()
            for result in data.get('results', []):
                task = result.get('task', {})
                subdomain = task.get('domain')
                if subdomain:
                    subdomains.add(subdomain)
            logger.success(f"[urlscan.io] Found {len(subdomains)} subdomains")
            return list(subdomains)
        except Exception as e:
            logger.error(f"[urlscan.io] Error: {e}")
            return []

    def from_rapiddns(self, domain):
        logger.info(f"[RapidDNS] Fetching subdomains for {domain}")
        url = f"https://rapiddns.io/s/{domain}?full=1&down=1#result"
        try:
            response = self.session.get(url, timeout=30)
            if response.status_code != 200:
                logger.warning(f"[RapidDNS] returned status {response.status_code} for {domain}")
                return []
            html = response.text
            matches = re.findall(r'<td>([^<]*\.[^<]*\.[^<]*)</td>', html)
            clean_subdomains = set()
            for match in matches:
                cleaned = re.sub(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', '', match).strip()
                if cleaned:
                    clean_subdomains.add(cleaned)
            logger.success(f"[RapidDNS] Found {len(clean_subdomains)} subdomains")
            return list(clean_subdomains)
        except Exception as e:
            logger.error(f"[RapidDNS] Error: {e}")
            return []

    def from_subdomain_center(self, domain):
        logger.info(f"[subdomain.center] Fetching subdomains for {domain}")
        url = f"https://api.subdomain.center/?domain={domain}"
        try:
            response = self.session.get(url, timeout=30)
            if response.status_code != 200:
                logger.warning(f"[subdomain.center] returned status {response.status_code} for {domain}")
                return []
            data = response.json()
            subdomains = [d for d in data]
            logger.success(f"[subdomain.center] Found {len(subdomains)} subdomains")
            return subdomains
        except Exception as e:
            logger.error(f"[subdomain.center] Error: {e}")
            return []

    def from_chaos(self, domain):
        logger.info(f"[Chaos] Running for {domain}")
        try:
            cmd = f"chaos -key {self.chaos_api_key} -d {domain} -silent"
            output = subprocess.check_output(cmd, shell=True, text=True)
            subdomains = [line.strip() for line in output.splitlines() if line.strip()]
            logger.success(f"[Chaos] Found {len(subdomains)} subdomains")
            return subdomains
        except Exception as e:
            logger.error(f"[Chaos] Error: {e}")
            return []

    def from_wayback(self, domain):
        logger.info(f"[Wayback Machine] Fetching subdomains for {domain}")
        url = f"https://web.archive.org/cdx/search/cdx?url=*.{domain}&collaps=urlkey&fl=original"
        try:
            response = self.session.get(url, timeout=30)
            if response.status_code != 200:
                logger.warning(f"[Wayback Machine] returned status {response.status_code} for {domain}")
                return []
            lines = response.text.strip().split("\n")
            subdomains = set()
            for line in lines:
                parts = line.split("/")
                if len(parts) >= 3:
                    host = parts[2].split(":")[0]
                    if host and domain in host:
                        subdomains.add(host)
            logger.success(f"[Wayback Machine] Found {len(subdomains)} subdomains")
            return list(subdomains)
        except Exception as e:
            logger.error(f"[Wayback Machine] Error: {e}")
            return []

    def run_all(self, domain):
        logger.info(f"Fetching subdomains from all sources for {domain}")
        all_subdomains = set()

        all_subdomains.update(self.from_crtsh(domain))
        all_subdomains.update(self.from_subfinder(domain))
        all_subdomains.update(self.from_shodan(domain))
        all_subdomains.update(self.from_urlscan(domain))
        all_subdomains.update(self.from_rapiddns(domain))
        all_subdomains.update(self.from_subdomain_center(domain))
        all_subdomains.update(self.from_chaos(domain))
        all_subdomains.update(self.from_wayback(domain))

        logger.success(f"Total unique subdomains found: {len(all_subdomains)}")
        return list(all_subdomains)

    def filter_in_scope(self, subdomains, domain):
        filtered = []
        domain = domain.lower()

        for sub in subdomains:
            sub = sub.strip().lower()
            if sub == domain or sub.endswith(f".{domain}"):
                filtered.append(sub)

        logger.info(f"Filtered {len(filtered)} in-scope subdomains out of {len(subdomains)} total")
        return filtered
