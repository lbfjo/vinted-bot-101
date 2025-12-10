# Vinted Bot

A bot that monitors Vinted for new listings matching your saved searches and sends notifications to Slack and/or Discord.

## Features

- **Multi-locale search**: Monitor Vinted across different countries (FR, DE, EN, IT, ES, etc.)
- **Rich notifications**: Get detailed alerts with title, price, size, brand, condition, and seller rating
- **Slack & Discord support**: Send to one or both platforms with per-search webhook overrides
- **Smart filtering**:
  - Price range (min/max)
  - Include/exclude keywords
  - Minimum seller rating
- **Duplicate suppression**: Never get alerted twice for the same listing
- **Cooldown windows**: Prevent notification spam with configurable cooldowns
- **Batch notifications**: Group multiple matches into a single message
- **State persistence**: Remembers seen listings between runs (via GitHub Actions artifacts)
- **Rate limiting**: Respects Vinted's rate limits with automatic backoff
- **Metrics & logging**: Track found/notified/skipped counts per run

## Getting Started

### 1. Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure your searches

```bash
cp config/searches.example.yaml config/searches.yaml
```

Edit `config/searches.yaml` with your search criteria and webhook URLs.

### 3. Run the bot

```bash
# Normal run
python -m src.cli

# With verbose logging
python -m src.cli -v

# Dry run (no notifications sent)
python -m src.cli --dry-run

# Custom config path
python -m src.cli -c /path/to/config.yaml
```

## Configuration

### Global Settings

| Setting | Description | Default |
|---------|-------------|---------|
| `poll_interval_seconds` | Polling interval (for local continuous mode) | 300 |
| `slack_webhook_url` | Slack webhook URL | - |
| `discord_webhook_url` | Discord webhook URL | - |
| `default_cooldown_minutes` | Default cooldown between notifications | 60 |
| `state_file` | Path to state file for duplicate suppression | `data/state.json` |
| `max_seen_ids_per_search` | Max listing IDs to remember per search | 1000 |
| `batch_notifications` | Group matches into single notification | false |
| `max_batch_size` | Max listings per batch notification | 10 |

### Search Configuration

| Option | Description | Required |
|--------|-------------|----------|
| `name` | Label for logs and notifications | Yes |
| `keywords` | List of search terms | Yes |
| `locales` | Vinted locales to search (e.g., `fr`, `de`, `en`) | No (default: `["en"]`) |
| `price_min` | Minimum price filter | No |
| `price_max` | Maximum price filter | No |
| `include_keywords` | At least one must match in title/brand | No |
| `exclude_keywords` | None should match in title/brand | No |
| `min_seller_rating` | Minimum seller rating (0-5) | No |
| `webhook` | Override webhook for this search | No |
| `cooldown_minutes` | Override cooldown for this search | No |
| `enabled` | Enable/disable this search | No (default: true) |

### Example Configuration

```yaml
slack_webhook_url: "https://hooks.slack.com/services/..."
discord_webhook_url: "https://discord.com/api/webhooks/..."
default_cooldown_minutes: 60
batch_notifications: true

searches:
  - name: "Designer Sneakers"
    keywords: ["Nike", "Jordan", "Yeezy"]
    price_max: 300
    locales: ["fr", "de", "en"]
    exclude_keywords: ["fake", "replica"]
    min_seller_rating: 4.0
    cooldown_minutes: 30

  - name: "Vintage Lego"
    keywords: ["Lego", "vintage"]
    price_min: 20
    price_max: 500
    locales: ["de"]
    include_keywords: ["Star Wars", "Castle", "Space"]
```

### Environment Variables

- `SLACK_WEBHOOK_URL`: Override Slack webhook
- `DISCORD_WEBHOOK_URL`: Override Discord webhook
- `STATE_FILE`: Override state file path

## GitHub Actions

The included workflow (`.github/workflows/vinted-bot.yml`) runs the bot every 30 minutes and persists state between runs using artifacts.

### Setup

1. Fork this repository
2. Add your webhook URLs as repository secrets:
   - `SLACK_WEBHOOK_URL`
   - `DISCORD_WEBHOOK_URL`
3. Customize `config/searches.yaml` (or keep the example for testing)
4. Enable GitHub Actions in your fork

The workflow will:
- Run every 30 minutes (configurable via cron)
- Download previous state from artifacts
- Execute the bot
- Upload updated state for the next run

## Supported Locales

| Locale | Domain |
|--------|--------|
| `fr` | vinted.fr |
| `de` | vinted.de |
| `en` / `us` | vinted.com |
| `es` | vinted.es |
| `it` | vinted.it |
| `nl` | vinted.nl |
| `be` | vinted.be |
| `at` | vinted.at |
| `pl` | vinted.pl |
| `cz` | vinted.cz |
| `lt` | vinted.lt |
| `pt` | vinted.pt |
| `sk` | vinted.sk |
| `uk` | vinted.co.uk |

## Project Structure

```
vinted-bot/
├── src/
│   ├── cli.py          # Main entry point
│   ├── config.py       # Configuration loading
│   ├── filters.py      # Listing filters
│   ├── metrics.py      # Run metrics tracking
│   ├── state.py        # State persistence
│   ├── fetcher/
│   │   └── vinted.py   # Vinted API client
│   └── notifiers/
│       ├── base.py     # Notifier protocol
│       ├── slack.py    # Slack webhook
│       └── discord.py  # Discord webhook
├── config/
│   └── searches.example.yaml
├── data/               # State files (gitignored)
└── .github/workflows/
    └── vinted-bot.yml  # GitHub Actions workflow
```

## License

MIT
