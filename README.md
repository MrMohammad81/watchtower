# 🛡️ Watchtower - Subdomain Recon & Monitoring Tool

**Watchtower** is an automated subdomain reconnaissance tool designed to discover, scan, and monitor subdomains for changes.  
It notifies you via **Telegram** and **Discord** when new subdomains are discovered or existing ones are updated.

---

## 🚀 Features

- Multi-source subdomain enumeration (crt.sh, RapidDNS, Chaos, Subfinder, WebArchive, Shodan, GitHub Subdomains, etc.)
- DNS resolution via `massdns` and bruteforce DNS discovery with `PureDNS`
- Live subdomain discovery using `dnsx` and `httpx`
- Technology detection, status code checking, and title grabbing
- MongoDB storage for subdomains and change tracking
- **BruteForce subdomain detection** flagging and notifications
- Telegram & Discord notifications (message + CSV if too large)
- Multi-threading for faster scans
- YAML-based target management
- Advanced filters to query MongoDB results (status, title, tech, URL, bruteforce flag)
- CSV export for large scan results and notifications
- GitHub Subdomain discovery using `github-subdomains`

---

## 🏗️ Project Structure

```
watchtower/
├── cli/                # CLI argument handler
├── config/             # Configuration files (resolvers, settings)
├── core/               # Core logic (scanner, fetchers, mongo, processor)
├── utils/              # Logging & utility functions
├── data/               # Target YAML files directory
├── main.py             # Main entry point
├── requirements.txt    # Python dependencies
└── Dockerfile          # Optional Docker support
```

---

## 📦 Requirements

### Python Packages

```
requests
pymongo
PyYAML
colorama
tldextract
dnsgen
```

### External Tools (Installed on Your Server)

| Tool                  | Install Command                                                                                       |
|-----------------------|-------------------------------------------------------------------------------------------------------|
| **subfinder**         | `go install github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest`                           |
| **chaos**             | `go install github.com/projectdiscovery/chaos-client/cmd/chaos@latest`                               |
| **dnsx**              | `go install github.com/projectdiscovery/dnsx/cmd/dnsx@latest`                                        |
| **httpx**             | `go install github.com/projectdiscovery/httpx/cmd/httpx@latest`                                      |
| **massdns**           | `git clone https://github.com/blechschmidt/massdns.git && cd massdns && make && cp bin/massdns /usr/local/bin` |
| **shosubgo**          | `go install github.com/incogbyte/shosubgo@latest`                                                    |
| **puredns**           | `go install github.com/d3mondev/puredns@latest`                                                      |
| **github-subdomains** | `go install github.com/gwen001/github-subdomains@latest`                                             |

---

## 📝 Installation (Without Docker)

1. **Clone the repository**
   ```bash
   git clone https://github.com/MrMohammad81/watchtower.git
   cd watchtower
   ```

2. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Create an alias to run Watchtower easily**
   Add this function to your `~/.bashrc` or `~/.zshrc`:
   ```bash
   watchtower() {
       python3 /app/main.py "$@"
   }
   ```

4. **Reload your shell config**
   ```bash
   source ~/.bashrc
   ```

---

## 🐛 Docker Support (Optional)

### Build Docker Image
```bash
docker build -t watchtower .
```

### Run Single Domain Scan
```bash
docker run --rm watchtower -u example.com --threads 10
```

### Run Target YAML File Scan
```bash
docker run --rm -v $(pwd)/data:/app/data watchtower --targets-file data/targets.yaml --threads 10
```

---

## ⚙️ Configuration

### Example `data/targets.yaml`

```yaml
targets:
  - name: company1
    domains:
      - example.com
      - example.org
  - name: company2
    domains:
      - test.com
```

### Example `config/settings.py`

```python
MONGO_URI = "mongodb://admin:password@localhost:27017/admin?authSource=admin"
TELEGRAM_BOT_TOKEN = "your_bot_token"
TELEGRAM_CHAT_ID = "your_chat_id"
DISCORD_WEBHOOK_URL = "your_discord_webhook_url"
RESOLVER_PATH = "config/resolver.txt"
THREADS = 5
SHODAN_API_KEY = "your_shodan_api_key"
CHAOS_API_KEY = "your_chaos_api_key"
GITHUB_TOKEN = "your_github_token"
WORDLIST_PATH = "data/wordlist.txt"
```

---

## 📄 MongoDB Integration

Watchtower uses **MongoDB** to store and track discovered subdomains and scan results over time.

### 🔧 MongoDB Setup (Quick Start)

#### 1. Install MongoDB (Ubuntu Example)
```bash
sudo apt update
sudo apt install -y mongodb
sudo systemctl enable mongodb
sudo systemctl start mongodb
```

#### 2. Access MongoDB Shell (Optional)
```bash
mongo
```

#### 3. Create Admin User (Optional but Recommended)
```javascript
use admin
db.createUser({
  user: "admin",
  pwd: "yourStrongPassword",
  roles: [{ role: "userAdminAnyDatabase", db: "admin" }]
})
```

### ⚙️ MongoDB Configuration in Watchtower

In the `config/settings.py` file, set your MongoDB connection:
```python
MONGO_URI = "mongodb://admin:yourStrongPassword@localhost:27017/admin?authSource=admin"
```

### 📂 Database Structure

For each company (defined in `targets.yaml`), Watchtower creates a separate MongoDB database named `<company>_db`.
Inside each database, it stores subdomain scan results in the `httpx_results` collection.

Document example stored in MongoDB:
```json
{
    "url": "https://subdomain.example.com",
    "status": "200",
    "title": "Example Title",
    "tech": ["nginx", "php"],
    "bruteforce": true,
    "created_at": "2024-03-12T09:00:00"
}
```

---

## 🛠️ Usage Examples

### Run Single Domain Scan
```bash
watchtower -u example.com
```

### Batch Scan with YAML Targets
```bash
watchtower --targets-file data/targets.yaml --threads 10
```

### Show Stored httpx Results for a Company
```bash
watchtower --show-httpx company1
```

#### With Filters
```bash
watchtower --show-httpx company1 --status 200 --title admin
```

#### Filter for DNS BruteForce Subdomains Only
```bash
watchtower --show-httpx company1 --dns-check true
```

### Show Newly Added Subdomains (Last 24 Hours)
```bash
watchtower --show-new company1
```

#### With Filters
```bash
watchtower --show-new company1 --status 200 --dns-check true
```

### Show Updated Subdomains (With Filters)
```bash
watchtower --show-updates company1 --dns-check true
```

### Update Project From GitHub
```bash
watchtower --update
```

---

## 📢 Notifications

### 🔹 Telegram Notifications
- First-time scan summaries
- New subdomains discovered
- Subdomain status/title/tech changes
- DNS BruteForce discovered subdomains with specific status codes (200, 403, 404)
- CSV file attachment when results are large

### 🔹 Discord Notifications
- Same as Telegram but via Discord webhook

---

## 🤖 Telegram Bot Setup

### 🔹 Step 1 - Create Your Bot
1. Open Telegram and search for `@BotFather`
2. Send `/start` and then `/newbot`
3. Give it a name and username (e.g., `watchtower_bot`)
4. Copy the provided **Bot Token**

### 🔹 Step 2 - Add Bot to Your Group
1. Create a Telegram group or use an existing one
2. Add your bot as a member of the group
3. Make sure the bot has **permission to send messages**

### 🔹 Step 3 - Get the Chat ID
1. Forward any message from the group to `@userinfobot` or use [this tool](https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates)
2. Note the **chat ID**, usually starts with `-100`

### 🔹 Step 4 - Update `settings.py`
```python
TELEGRAM_BOT_TOKEN = "your_bot_token"
TELEGRAM_CHAT_ID = "-1001234567890"
```

---

## 👨‍💻 Author

Made with ❤️ by **MohammadHossein Mohit**

