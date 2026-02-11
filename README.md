# Discord Co-op Game Deals Bot

A Discord webhook bot that posts **co-op PC game deals under $10** from multiple stores (via CheapShark), **verified via Steam** co-op categories, and runs automatically using **GitHub Actions**.

## Features
- Finds deals under a price threshold
- Verifies co-op support via Steam categories
- Posts clean Discord embeds via webhook
- Prevents reposts using a cached `posted_deals.json`

## Quick Start
1. Create a Discord webhook in your channel
2. Add it to GitHub Secrets:
   - `DISCORD_WEBHOOK_URL` (required)
   - `DISCORD_WEBHOOK_USERNAME` (optional)

3. GitHub Actions runs on a schedule (see `.github/workflows/coop-deals.yml`)

## Optional Environment Variables
- `MAX_PRICE` (default: `10.00`)
- `MAX_POSTS_PER_RUN` (default: `10`)
- `ONLY_STEAM_REDEEMABLE` (default: `true`)
- `ALLOWED_STORE_IDS` (example: `1,7,8,11`)
- `EXCLUDE_KEYWORDS` (example: `hentai,nsfw,sex,porn,simulator`)
