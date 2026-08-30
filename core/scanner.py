import subprocess
import tempfile
import os
import re
from utils import logger
from core.subdomain_fetcher import SubdomainFetcher
from config import settings

class Scanner:
    def __init__(self, resolver_path):
        self.resolver_path = resolver_path
        self.fetcher = SubdomainFetcher()

    def clean_domains(self, subdomains):
        """
        Clean and filter subdomains before running tools like massdns, dnsx, etc.
        """
        clean_list = []

        for d in subdomains:
            if not d:
                continue

            d = d.strip().lower()

            # Skip invalid entries
            if '.' not in d:
                continue

            # Skip URLs
            if d.startswith('http'):
                continue

            # Allow valid DNS characters only
            if not re.match(r'^[a-z0-9.-]+$', d):
                continue

            clean_list.append(d)

        unique_domains = list(set(clean_list))
        logger.info(f"Cleaned {len(unique_domains)} valid subdomains out of {len(subdomains)} total")
        return unique_domains

    def _run_massdns(self, input_list):
        logger.info("Running massdns...")

        input_list = self.clean_domains(input_list)

        if not input_list:
            logger.warning("No valid subdomains to run massdns on!")
            return []

        with tempfile.NamedTemporaryFile(mode='w+', delete=False) as temp_in:
            temp_in.write('\n'.join(input_list))
            temp_in.flush()

        out_file = tempfile.NamedTemporaryFile(delete=False).name
        cmd = (
            f"massdns -r {self.resolver_path} -q -t A {temp_in.name} -o S | "
            f"cut -d ' ' -f1 | sed 's/\\.$//g' | sort -u > {out_file}"
        )

        try:
            subprocess.run(cmd, shell=True, executable='/bin/bash', check=True)
        except subprocess.CalledProcessError as e:
            logger.error(f"massdns failed: {e}")
            return []

        with open(out_file, 'r') as f:
            results = [line.strip() for line in f]

        os.remove(temp_in.name)
        os.remove(out_file)

        logger.success(f"massdns found {len(results)} results")
        return results

    def _run_puredns_bruteforce(self, wordlist_path, domain):
        logger.info(f"Running puredns bruteforce for {domain}...")

        with tempfile.NamedTemporaryFile(mode='w+', delete=False) as temp_out:
            output_file = temp_out.name

            cmd = (
                f"puredns bruteforce {wordlist_path} {domain} "
                f"-q -r {self.resolver_path} -w {output_file}"
            )

            try:
                subprocess.run(cmd, shell=True, executable='/bin/bash', check=True)

                with open(output_file, 'r') as f:
                    results = [line.strip() for line in f.readlines()]

                logger.success(f"puredns found {len(results)} subdomains (bruteforce).")

            except subprocess.CalledProcessError as e:
                logger.error(f"puredns bruteforce failed: {e}")
                results = []

            os.remove(output_file)

        return results

    def _run_dnsx(self, subdomains):
        logger.info("Running dnsx...")

        subdomains = self.clean_domains(subdomains)

        if not subdomains:
            logger.warning("No valid subdomains to run dnsx on!")
            return []

        with tempfile.NamedTemporaryFile(mode='w+', delete=False) as temp_in:
            temp_in.write('\n'.join(subdomains))
            temp_in.flush()

        cmd = f"cat {temp_in.name} | dnsx -silent -a"

        try:
            output = subprocess.check_output(cmd, shell=True, text=True, executable='/bin/bash')
            results = output.strip().splitlines()

        except subprocess.CalledProcessError as e:
            logger.error(f"dnsx failed: {e}")
            results = []

        os.remove(temp_in.name)

        logger.success(f"dnsx found {len(results)} live subdomains")
        return results

    def _run_httpx(self, subdomains):
        logger.info("Running httpx...")

        subdomains = self.clean_domains(subdomains)

        if not subdomains:
            logger.warning("No valid subdomains to run httpx on!")
            return []

        with tempfile.NamedTemporaryFile(mode='w+', delete=False) as temp_in:
            temp_in.write('\n'.join(subdomains))
            temp_in.flush()

        cmd = (
            f"cat {temp_in.name} | httpx --status-code --title --tech-detect "
            f"-silent -random-agent -no-color"
        )

        try:
            output = subprocess.check_output(cmd, shell=True, text=True, executable='/bin/bash')
            results = output.strip().splitlines()

        except subprocess.CalledProcessError as e:
            logger.error(f"httpx failed: {e}")
            results = []

        os.remove(temp_in.name)

        logger.success(f"httpx produced {len(results)} results")
        return results

    def run_scan_chain(self, fetcher_results, domain):
        logger.info(f"Starting scan chain for {domain}")

        # Step 1: Run puredns bruteforce
        wordlist_path = settings.WORDLIST_PATH
        puredns_results = self._run_puredns_bruteforce(wordlist_path, domain)

        # Step 2: Combine fetcher and puredns results
        combined_subdomains = list(set(fetcher_results + puredns_results))
        logger.success(f"Combined subdomains count: {len(combined_subdomains)}")

        # Step 3: massdns resolution on combined results
        massdns_filtered = self.fetcher.filter_in_scope(self._run_massdns(combined_subdomains), domain)

        # Step 4: dnsx live subdomain discovery
        dnsx_out = self._run_dnsx(massdns_filtered)

        # Step 5: httpx probing on live subdomains
        httpx_out = self._run_httpx(dnsx_out)

        # Step 6: Flag httpx results that came from puredns
        puredns_set = set(self.clean_domains(puredns_results))

        flagged_httpx = []
        for line in httpx_out:
            # Extract URL to check the domain
            url = line.split()[0]
            domain_part = url.replace("https://", "").replace("http://", "").split("/")[0]

            is_bruteforce = domain_part in puredns_set

            flagged_httpx.append({
                "line": line,
                "bruteforce": is_bruteforce
            })

        logger.info(f"Flagged {len([h for h in flagged_httpx if h['bruteforce']])} subdomains from dnsbruteforce")

        logger.success(f"Completed scan chain for {domain}")

        return flagged_httpx
