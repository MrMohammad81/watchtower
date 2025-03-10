import subprocess
import tempfile
import os
from utils import logger
from core.subdomain_fetcher import SubdomainFetcher

class Scanner:
    def __init__(self, resolver_path):
        self.resolver_path = resolver_path
        self.fetcher = SubdomainFetcher()

    def _run_massdns(self, input_list):
        logger.info("Running massdns...")
        with tempfile.NamedTemporaryFile(mode='w+', delete=False) as temp_in:
            temp_in.write('\n'.join(input_list))
            temp_in.flush()

        out_file = tempfile.NamedTemporaryFile(delete=False).name
        cmd = (
            f"massdns -r {self.resolver_path} -q -t A {temp_in.name} -o S | "
            f"cut -d ' ' -f1 | sed 's/\\.$//g' | sort -u > {out_file}"
        )
        subprocess.run(cmd, shell=True, executable='/bin/bash', check=True)

        with open(out_file, 'r') as f:
            results = [line.strip() for line in f]

        os.remove(temp_in.name)
        os.remove(out_file)
        logger.success(f"massdns found {len(results)} results")
        return results

    def _run_dnsgen(self, subdomains):
        logger.info("Running dnsgen...")
        with tempfile.NamedTemporaryFile(mode='w+', delete=False) as temp_in:
            temp_in.write('\n'.join(subdomains))
            temp_in.flush()

        out_file = tempfile.NamedTemporaryFile(delete=False).name
        cmd = f"cat {temp_in.name} | dnsgen -f - | sort -u > {out_file}"
        subprocess.run(cmd, shell=True, executable='/bin/bash', check=True)

        with open(out_file, 'r') as f:
            results = [line.strip() for line in f]

        os.remove(temp_in.name)
        os.remove(out_file)
        logger.success(f"dnsgen produced {len(results)} domains")
        return results

    def _run_dnsx(self, subdomains):
        logger.info("Running dnsx...")
        with tempfile.NamedTemporaryFile(mode='w+', delete=False) as temp_in:
            temp_in.write('\n'.join(subdomains))
            temp_in.flush()

        cmd = f"cat {temp_in.name} | dnsx -silent -a"
        output = subprocess.check_output(cmd, shell=True, text=True, executable='/bin/bash')

        os.remove(temp_in.name)
        results = output.strip().splitlines()
        logger.success(f"dnsx found {len(results)} live subdomains")
        return results

    def _run_httpx(self, subdomains):
        logger.info("Running httpx...")
        with tempfile.NamedTemporaryFile(mode='w+', delete=False) as temp_in:
            temp_in.write('\n'.join(subdomains))
            temp_in.flush()

        cmd = f"cat {temp_in.name} | httpx --status-code --title --tech-detect -silent -random-agent -no-color"
        output = subprocess.check_output(cmd, shell=True, text=True, executable='/bin/bash')

        os.remove(temp_in.name)
        results = output.strip().splitlines()
        logger.success(f"httpx produced {len(results)} results")
        return results

    def run_scan_chain(self, fetcher_results, domain):
        massdns_1 = self._run_massdns(fetcher_results)
        massdns_1_filtered = self.fetcher.filter_in_scope(massdns_1, domain)

        dnsgen_out = self._run_dnsgen(massdns_1_filtered)
        dnsgen_filtered = self.fetcher.filter_in_scope(dnsgen_out, domain)

        massdns_2 = self._run_massdns(dnsgen_filtered)
        massdns_2_filtered = self.fetcher.filter_in_scope(massdns_2, domain)

        dnsx_out = self._run_dnsx(massdns_2_filtered)
        httpx_out = self._run_httpx(dnsx_out)

        return httpx_out