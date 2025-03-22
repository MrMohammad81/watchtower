import os
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

MONGO_URI = "mongodb://admin:password@localhost:27017/admin?authSource=admin"
TELEGRAM_BOT_TOKEN = "your_bot_token"
TELEGRAM_CHAT_ID = "your_chat_id"
DISCORD_WEBHOOK_URL = "your_discord_webhook_url"
THREADS = 5
SHODAN_API_KEY = "your_shodan_api_key"
CHAOS_API_KEY = "your_chaos_api_key"
GITHUB_TOKEN = "your_github_token"
WORDLIST_PATH = os.path.join(BASE_DIR, 'config', 'wordlist.txt')
RESOLVER_PATH = os.path.join(BASE_DIR, 'config', 'resolver.txt')