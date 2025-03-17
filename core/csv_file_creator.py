import os
import tempfile
import csv
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
        file_path = os.path.join(tmp_dir, f"{domain}_bruteforce_first_scan.csv")

        logger.error(f"Bruteforce items for CSV: {httpx_results}")  # Log to ensure data structure

        with open(file_path, mode='w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['URL', 'Status', 'Title', 'BruteForce', 'Tech']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()

                for item in httpx_results:
                    row = {
                        'URL': item.get('url', ''),
                        'Status': item.get('status', ''),
                        'Title': item.get('title', ''),
                        'BruteForce': item.get('bruteforce', False),
                        'Tech': ', '.join(item.get('tech', [])) if item.get('tech') else ''
                    }
                writer.writerow(row)

        logger.success(f"✅ CSV file (first scan) created: {file_path}")
        return file_path
