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

