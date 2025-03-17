from utils import logger

class Helpers:
    def __init__(self):
        pass
    
    def subdomain_filter(self, item):
        logger.info(f"Filtering item: {item}")
        url = item.get('url', '-')
        status = item.get('status', '-')
        title = item.get('title', '-') or '-'
        tech_list = item.get('tech', [])
        tech_display = ', '.join(tech_list) if tech_list else '-'

        return f"- [{url}]({url})\n  status: {status}\n  title: {title}\n  tech: {tech_display}"