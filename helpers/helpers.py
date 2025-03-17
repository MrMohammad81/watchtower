from utils import logger

class Helpers:
    def __init__(self):
        pass
    
    
    def subdomain_filter(self, item):
        
        line = item.get('line', '')
        parts = line.split(' [')
    
        url = parts[0].strip() if len(parts) > 0 else '-'
        status = parts[1].replace(']', '').strip() if len(parts) > 1 else '-'
        title = parts[2].replace(']', '').strip() if len(parts) > 2 else '-'
        tech_display = parts[3].replace(']', '').strip() if len(parts) > 3 else '-'

        return (
            f"- [{url}]({url})\n"
           f"  status: {status}\n"
           f"  title: {title}\n"
           f"  tech: {tech_display}"
        )


    def bruteforce_filter(self, item):
        
        url = item.get('url', '-')
        status = item.get('status', '-')
        title = item.get('title', '-') or '-'
        tech_list = item.get('tech', [])
        tech_display = ', '.join(tech_list) if tech_list else '-'

        return (
            f"- [{url}]({url})\n"
           f"  status: {status}\n"
           f"  title: {title}\n"
           f"  tech: {tech_display}"
        )
        
    def auto_subdomain_filter(self, item):
       
        logger.error(f"Auto filtering item: {item}")

        if 'line' in item:
            return self.subdomain_filter(item)
        elif 'url' in item:
            return self.bruteforce_filter(item)
        else:
            return "- Unknown item format -"