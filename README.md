# vinted-bot-101

Prototype watcher that scans Vinted for new listings matching saved searches and posts to Slack or Discord.

## Getting started
1. Create a virtual environment and install dependencies:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
2. Copy the example config and edit it:
   ```bash
   cp config/searches.example.yaml config/searches.yaml
   ```
   Fill in webhook URLs or set `SLACK_WEBHOOK_URL` / `DISCORD_WEBHOOK_URL` in your environment.
3. Run the bot locally:
   ```bash
   python -m src.cli
   ```

## Configuration
- `config/searches.yaml` holds an array of searches. Each search supports:
  - `name`: label for logs and notifications
  - `keywords`: list of search terms
  - `price_max`: optional price ceiling (not yet enforced)
  - `locales`: list of Vinted locales (e.g., `en`, `fr`, `de`)
  - `webhook`: optional override webhook per search
- Top-level keys `slack_webhook_url` and `discord_webhook_url` can be supplied via the file or environment variables.

## GitHub Actions
A scheduled workflow (`.github/workflows/vinted-bot.yml`) installs dependencies and runs the CLI. Provide `SLACK_WEBHOOK_URL` and/or `DISCORD_WEBHOOK_URL` as secrets in your repository settings. The workflow expects `config/searches.yaml` to exist in the repository (use the example file as a starting point), and it will fail fast if the file is missing.

## Roadmap
- Implement real Vinted fetching with rate limiting and duplicate suppression
- Add filtering rules (price cap, keyword include/exclude, seller rating)
- Batch notifications and add per-rule cooldowns
- Capture last-seen state between runs via artifacts
