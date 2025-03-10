
# 🛡️ Watchtower - Subdomain Recon & Monitoring Tool

**Watchtower** is an automated subdomain reconnaissance tool designed to discover, scan, and monitor subdomains for changes.  
It notifies you via Telegram and Discord when new subdomains are discovered or existing ones are updated.

---

## 🚀 Features

- Multi-source subdomain enumeration (crt.sh, RapidDNS, Chaos, Subfinder, WebArchive, etc.)
- DNS resolution via `massdns` and permutations with `dnsgen`
- Live subdomain discovery using `dnsx` and `httpx`
- Technology detection, status code checking, and title grabbing
- MongoDB storage for subdomains and change tracking
- **Telegram & Discord notifications** for updates and alerts
- Multi-threading for faster scans
- YAML-based target management

---

## 🏗️ Project Structure

```
watchtower/
├── cli/                # CLI argument handler
├── config/             # Configuration files (resolvers, settings)
├── core/               # Core logic (scanner, fetchers, mongo)
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

| Tool         | Install Command                                      |
|--------------|------------------------------------------------------|
| **subfinder**    | `go install github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest` |
| **chaos**        | `go install github.com/projectdiscovery/chaos-client/cmd/chaos@latest` |
| **dnsx**         | `go install github.com/projectdiscovery/dnsx/cmd/dnsx@latest` |
| **httpx**        | `go install github.com/projectdiscovery/httpx/cmd/httpx@latest` |
| **massdns**      | `git clone https://github.com/blechschmidt/massdns.git && cd massdns && make && cp bin/massdns /usr/local/bin` |
| **shosubgo**     | `go install github.com/incogbyte/shosubgo@latest` |

---

## 📝 Installation (Without Docker)

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/watchtower.git
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
       python3 /usr/local/watchtower/main.py "$@"
   }
   ```

4. **Reload your shell config**
   ```bash
   source ~/.bashrc
   ```

---

## 🐳 Docker Support (Optional)

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
```

---

## 🗄️ MongoDB Integration

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

### 🗂️ Database Structure

For each company (defined in `targets.yaml`), Watchtower creates a separate MongoDB database named `<company>_db`.  
Inside each database, it stores subdomain scan results in the `httpx_results` collection.

Document example stored in MongoDB:
```json
{
    "url": "https://subdomain.example.com",
    "status": "200",
    "title": "Example Title",
    "tech": ["nginx", "php"]
}
```

---

## 🛠️ Usage Examples

### Run Single Domain Scan
```bash
watchtower -u example.com --threads 10
```

### Batch Scan with YAML Targets
```bash
watchtower --targets-file data/targets.yaml --threads 10
```

### Show Stored httpx Results for a Company
```bash
watchtower --show-httpx company1
```

---

## 📢 Notifications

### Telegram Notifications
- Get notified via Telegram Bot when:
  - A first-time scan is completed (domain summary)
  - New subdomains are discovered
  - Existing subdomains change (status code, title, technologies)

### Discord Notifications
- Discord notifications are sent to a configured webhook URL.
- You will be notified about:
  - New subdomains found
  - Changes in subdomain details (status, title, technologies)
  - Scan summaries (on first-time scans)

To enable Discord notifications:
1. Create a Discord webhook in your server settings.
2. Add the webhook URL in your `settings.py`:
   ```python
   DISCORD_WEBHOOK_URL = "your_discord_webhook_url"
   ```

---

## 👨‍💻 Author

Made with ❤️ by **Your Name**
