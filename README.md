# Discord Co-op Game Deals Bot 🎮

![GitHub Actions](https://github.com/PKHarsimran/discord-coop-game-deals-bot/actions/workflows/coop-deals.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.11-blue)
![License](https://img.shields.io/github/license/PKHarsimran/discord-coop-game-deals-bot)

A Discord webhook bot that finds co-op PC game deals under a configurable budget, verifies co-op support using Steam metadata, enriches deals with review context, ranks them, and posts a curated digest.

---

## Features

- Pulls deals from CheapShark and optionally from Steam featured specials.
- Verifies co-op support from Steam category metadata.
- Enriches deals with Steam review score summary.
- Smart ranking based on discount, affordability, co-op depth, and sentiment.
- Structured run metrics and logging for easier troubleshooting.
- Duplicate protection:
  - avoids reposting previously posted deal IDs
  - avoids posting multiple entries for the same Steam app in one run
  - optional franchise dedupe to reduce near-duplicate series entries
- HTTP retry/backoff client for resilience.
- Local JSON cache for Steam metadata to reduce repeated API calls.
- Optional role ping with safe `allowed_mentions` usage.
- Multiple digest modes (`daily`, `weekend`, `budget`).
- New quality guard: minimum discount threshold (`MIN_DISCOUNT_PERCENT`).

---

## Repository Layout

```text
bot/
  main.py             # Orchestration pipeline
  config.py           # Environment parsing and validation
  cheapshark.py       # CheapShark store/deal API client
  steam_store.py      # Steam featured specials API client
  steam.py            # Steam appdetails + appreviews + cache
  discord_webhook.py  # Discord payload composition + sending
  http_client.py      # Shared requests session with retries
  models.py           # Deal dataclass
```

---

## Quick Start

### 1) Install dependencies

```bash
pip install -r requirements.txt
```

### 2) Configure environment

Create a `.env` file (or export vars in CI):

```bash
DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/..."
DISCORD_WEBHOOK_USERNAME="Co-op Deals Bot"

MAX_PRICE="10.00"
MAX_POSTS_PER_RUN="10"
ONLY_STEAM_REDEEMABLE="true"
INCLUDE_STEAM_DIRECT_SPECIALS="true"
MIN_DISCOUNT_PERCENT="0"

ALLOWED_STORE_IDS=""
ALLOWED_STORE_NAMES=""
EXCLUDED_STORE_IDS=""
EXCLUDED_STORE_NAMES=""
EXCLUDE_KEYWORDS="hentai,nsfw,sex,porn,simulator"

EMBED_COLOR="0x57F287"
PING_ROLE_ON_POST="false"
DISCORD_ROLE_ID=""

DIGEST_MODE="daily"
PROFILE_NAME="default"
PRICE_SWEET_SPOT="5.0"
MIN_REVIEW_PERCENT="0"
MIN_REVIEW_COUNT="0"
FRANCHISE_DEDUPE_ENABLED="true"
FRANCHISE_DEDUPE_WORDS="2"
LOG_LEVEL="INFO"

POSTED_CACHE_FILE="data/posted_deals.json"
STEAM_COOP_CACHE_FILE="data/steam_coop_cache.json"
```

### 3) Run locally

```bash
python -m bot.main
```

---

## Configuration Reference

| Variable | Type | Default | Description |
|---|---:|---:|---|
| `DISCORD_WEBHOOK_URL` | string | empty | Discord webhook endpoint (required for posting). |
| `DISCORD_WEBHOOK_USERNAME` | string | `Co-op Deals Bot` | Display name for webhook posts. |
| `MAX_PRICE` | float | `10.00` | Strict upper price bound. |
| `MAX_POSTS_PER_RUN` | int | `10` | Maximum deals posted each run (min 1). |
| `ONLY_STEAM_REDEEMABLE` | bool | `true` | Ask CheapShark for Steamworks/redeemable deals only. |
| `INCLUDE_STEAM_DIRECT_SPECIALS` | bool | `true` | Include Steam featured specials as an additional source. |
| `MIN_DISCOUNT_PERCENT` | float | `0` | Filter out deals below this discount % (0–100). |
| `ALLOWED_STORE_IDS` | CSV | empty | Optional store ID allow-list. |
| `ALLOWED_STORE_NAMES` | CSV | empty | Optional normalized store name allow-list. |
| `EXCLUDED_STORE_IDS` | CSV | empty | Optional store ID block-list. |
| `EXCLUDED_STORE_NAMES` | CSV | empty | Optional normalized store name block-list. |
| `EXCLUDE_KEYWORDS` | CSV | `hentai,nsfw,sex,porn,simulator` | Title keyword filter. |
| `EMBED_COLOR` | int/hex | `0x57F287` | Discord embed color. |
| `PING_ROLE_ON_POST` | bool | `false` | Enables role pinging. |
| `DISCORD_ROLE_ID` | string | empty | Role ID used when ping is enabled. |
| `DIGEST_MODE` | enum | `daily` | `daily`, `weekend`, or `budget` (invalid values fall back to `daily`). |
| `PROFILE_NAME` | string | `default` | Optional profile tag added to digest title (normalized to lowercase `a-z0-9_-`, max 32 chars). |
| `PRICE_SWEET_SPOT` | float | `5.0` | Price threshold used in ranking/reasoning. |
| `MIN_REVIEW_PERCENT` | int | `0` | Optional minimum Steam review score percentage for filtering (0–100). |
| `MIN_REVIEW_COUNT` | int | `0` | Optional minimum number of Steam reviews for filtering. |
| `FRANCHISE_DEDUPE_ENABLED` | bool | `true` | Skip multiple picks from the same normalized franchise/title prefix in one run. |
| `FRANCHISE_DEDUPE_WORDS` | int | `2` | Number of leading normalized title words used to build franchise dedupe keys (1–5). |
| `LOG_LEVEL` | string | `INFO` | Runtime logging verbosity (`DEBUG`, `INFO`, etc.). |
| `POSTED_CACHE_FILE` | path | `data/posted_deals.json` | Posted deal cache path. |
| `STEAM_COOP_CACHE_FILE` | path | `data/steam_coop_cache.json` | Steam metadata cache path. |

---

## How Ranking Works

Each candidate receives a score composed from:

- base discount (`savings_pct`)
- bonus if below `PRICE_SWEET_SPOT`
- bonus for multiple co-op tags
- bonus from review percentage
- penalty for previously posted items

Then the bot:

1. removes already-posted IDs
2. deduplicates by Steam app ID for this run
3. keeps top `MAX_POSTS_PER_RUN`

---

## Running in GitHub Actions

Typical schedule:

- Daily: `0 9 * * *`
- Friday bonus run: `0 16 * * 5`

You can also trigger manually and pass digest mode as workflow input (if your workflow file supports it).

---

## Troubleshooting

- `Missing DISCORD_WEBHOOK_URL`: set it in your environment or GitHub Secrets.
- Empty results:
  - increase `MAX_PRICE`
  - lower `MIN_DISCOUNT_PERCENT`
  - loosen store allow/exclude filters
- Wrong digest label: only `daily`, `weekend`, and `budget` are valid.
- Too many repeated API calls: ensure `STEAM_COOP_CACHE_FILE` is persisted between runs.

---

## Development

### Lint/format suggestions

Runtime dependency is `requests`; `pytest` is used for local/CI tests. For local quality checks:

```bash
python -m compileall bot tests
pytest -q
```

---

## License

MIT.
