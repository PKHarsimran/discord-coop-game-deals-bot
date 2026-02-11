# Discord Co-op Game Deals Bot 🎮
![GitHub Actions](https://github.com/PKHarsimran/discord-coop-game-deals-bot/actions/workflows/coop-deals.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.11-blue)
![License](https://img.shields.io/github/license/PKHarsimran/discord-coop-game-deals-bot)

A **Discord webhook bot** that automatically posts **co-op PC game deals under $10** from multiple stores (via **CheapShark**), **verifies co-op support using Steam categories**, and runs **daily** using **GitHub Actions** — no servers required.

Perfect for Discord servers that want **daily co-op game deals** without spam or duplicate posts.

---

## ✨ Features

- 🔍 Finds PC game deals under a configurable price threshold  
- 🤝 Verifies **co-op support** using Steam’s official categories  
- 🛒 Supports **multiple stores** (Steam, Humble, Fanatical, GMG, etc.)  
- 📬 Posts clean, rich **Discord embeds** via webhooks  
- 🧠 Prevents reposts using a cached `posted_deals.json`  
- ⏱️ Runs **automatically once per day** using GitHub Actions  
- 🔒 Webhook is kept **100% private** using GitHub Secrets  

---

## 🚀 How It Works

1. GitHub Actions runs the bot on a daily schedule  
2. Deals are fetched from CheapShark  
3. Each game is checked against Steam to confirm co-op support  
4. Matching deals under the price limit are posted to Discord  
5. Previously posted deals are skipped automatically  

---

## 🧰 Tech Stack

- Python 3.11  
- CheapShark API  
- Steam Store API  
- Discord Webhooks  
- GitHub Actions  

---

## 🖼️ Preview

![Discord Preview](docs/preview.png)


## ⚡ Quick Start

### 1️⃣ Create a Discord Webhook
- Go to **Server Settings → Integrations → Webhooks**
- Copy the webhook URL

### 2️⃣ Add GitHub Secrets
In your GitHub repo:
- Go to **Settings → Secrets and variables → Actions**
- Add:
  - `DISCORD_WEBHOOK_URL` (required)
  - `DISCORD_WEBHOOK_USERNAME` (optional)

### 3️⃣ Done 🎉
GitHub Actions will now run the bot automatically based on the schedule defined in:

```
.github/workflows/coop-deals.yml
```

You can also trigger it manually from the **Actions** tab.

---

## ⏰ Schedule

By default, the bot runs **once per day** using this cron schedule (UTC):

```yaml
cron: "0 9 * * *"
```

---

## ⚙️ Configuration (Optional)

| Variable | Description | Default |
|--------|------------|---------|
| `MAX_PRICE` | Maximum deal price | `10.00` |
| `MAX_POSTS_PER_RUN` | Max deals per run | `10` |
| `ONLY_STEAM_REDEEMABLE` | Steamworks-only deals | `true` |
| `ALLOWED_STORE_IDS` | Limit to specific stores | all |
| `EXCLUDE_KEYWORDS` | Filter out unwanted titles | `hentai, nsfw, sex, porn, simulator` |

---

## 🔐 Security

- Webhook URL is never committed  
- Stored securely using GitHub Secrets  
- Safe for public repositories  

---

## 📜 License

MIT License

---

⭐ If this bot helps your server, consider starring the repo!
