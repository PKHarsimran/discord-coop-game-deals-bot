# Discord Co-op Game Deals Bot 🎮
![GitHub Actions](https://github.com/PKHarsimran/discord-coop-game-deals-bot/actions/workflows/coop-deals.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.11-blue)
![License](https://img.shields.io/github/license/PKHarsimran/discord-coop-game-deals-bot)

A **Discord webhook bot** that posts curated **co-op PC game deals under your target price** from CheapShark + Steam, verifies co-op support with Steam categories, enriches posts with review context, and runs on GitHub Actions.

---

## ✨ What’s Better Now

- 🔍 Smart ranking (not first-come): discounts + price sweet spot + co-op depth + review quality
- 🤝 Co-op metadata in post (online/LAN/split-screen tags when available)
- ⭐ Steam review summary enrichment
- 🧠 “Why this deal” explanation per game
- ♻️ Retry/backoff HTTP client for better reliability
- ⚡ Steam metadata cache (`data/steam_coop_cache.json`) to reduce repeated API calls
- 📬 Digest modes: `daily`, `weekend`, `budget`
- 🧱 Duplicate prevention cache (`data/posted_deals.json`)

---

## 🚀 Quick Start

1. Create a Discord webhook
2. Add GitHub secrets:
   - `DISCORD_WEBHOOK_URL` (required)
   - `DISCORD_WEBHOOK_USERNAME` (optional)
   - `DISCORD_ROLE_ID` (optional; needed only when role ping is enabled)
3. Enable Actions and run workflow manually once

---

## ⚙️ Configuration

| Variable | Description | Default |
|---|---|---|
| `MAX_PRICE` | Maximum deal price (strict upper bound) | `10.00` |
| `MAX_POSTS_PER_RUN` | Max deals per run | `10` |
| `ONLY_STEAM_REDEEMABLE` | Steamworks-only deals from CheapShark | `true` |
| `INCLUDE_STEAM_DIRECT_SPECIALS` | Include Steam Store specials source | `true` |
| `ALLOWED_STORE_IDS` | Allow-list store IDs | all |
| `ALLOWED_STORE_NAMES` | Allow-list store names | all |
| `EXCLUDED_STORE_IDS` | Block-list store IDs | none |
| `EXCLUDED_STORE_NAMES` | Block-list store names | none |
| `EXCLUDE_KEYWORDS` | Filter title keywords | `hentai, nsfw, sex, porn, simulator` |
| `EMBED_COLOR` | Discord embed color | `0x57F287` |
| `PING_ROLE_ON_POST` | Ping a role when posting | `false` |
| `DISCORD_ROLE_ID` | Role ID to mention | empty |
| `DIGEST_MODE` | `daily`, `weekend`, or `budget` | `daily` |
| `PRICE_SWEET_SPOT` | Bonus scoring threshold for low prices | `5.0` |
| `POSTED_CACHE_FILE` | Posted deal cache path | `data/posted_deals.json` |
| `STEAM_COOP_CACHE_FILE` | Steam metadata cache path | `data/steam_coop_cache.json` |

---

## ⏰ Schedule

Workflow runs:
- Daily: `0 9 * * *`
- Friday bonus run: `0 16 * * 5`

You can also trigger manually and pass a digest mode input.

---

## 🔐 Security

- Webhook stays in GitHub Secrets
- Safe mention policy (`allowed_mentions`) prevents broad mention abuse

---

## 📜 License

MIT License
