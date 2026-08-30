import os
import tempfile
import csv
import re
from utils import logger

class CsvFileCreator:
    def __init__(self, domain):
        self.domain = domain
    
    def create_csv(self, changes, domain):
        tmp_dir = tempfile.gettempdir()
        file_path = os.path.join(tmp_dir, f"{domain}_changes.csv")

        with open(file_path, mode='w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['Type', 'URL', 'Status', 'Title', 'BruteForce', 'Tech', 'Changes']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            for change in changes:
                row = {
                    'Type': change.get('type', ''),
                    'URL': change.get('data', {}).get('url') or change.get('url', ''),
                    'Status': change.get('data', {}).get('status', ''),
                    'Title': change.get('data', {}).get('title', ''),
                    'BruteForce': change.get('data', {}).get('bruteforce', False),
                    'Tech': ', '.join(change.get('data', {}).get('tech', [])) if change.get('data') else '',
                    'Changes': str(change.get('diff', '')) if change.get('diff') else ''
                }
                writer.writerow(row)

        logger.success(f"✅ CSV file created: {file_path}")
        return file_path
    
    def create_csv_first_scan(self, httpx_results, domain):
        tmp_dir = tempfile.gettempdir()
        file_path = os.path.join(tmp_dir, f"{domain}_first_scan.csv")

        with open(file_path, mode='w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['URL', 'Status', 'Title', 'BruteForce', 'Tech']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            for item in httpx_results:
                line = item.get('line', '')

                # Regex for parsing line into components
                match = re.match(r'^(https?://[^\s]+)\s\[(\d{3})\]\s\[(.*?)\]', line)
                if match:
                    url = match.group(1) 
                    status = match.group(2)  
                    title_and_tech = match.group(3)  

                    tech = []
                    title = ''
                    if ',' in title_and_tech:
                        parts = title_and_tech.split(',')
                        title = parts[0].strip() 
                        tech = [tech_item.strip() for tech_item in parts[1:]]  
                    else:
                        title = title_and_tech.strip()

                    row = {
                        'URL': url,
                        'Status': status,
                        'Title': title,
                        'BruteForce': item.get('bruteforce', False),
                        'Tech': ', '.join(tech)
                    }
                    writer.writerow(row)

        logger.success(f"✅ CSV file (first scan) created: {file_path}")
        return file_path
