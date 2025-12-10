# Vinted Alert Bot: Product Plan

## Target Users
- Sneaker and streetwear resellers seeking early alerts
- Collectors hunting specific items or sizes
- Deal-seekers who want price drops or new listings under a ceiling
- Personal shoppers and power users needing multi-market coverage

## Core Value
Reliable, near-real-time alerts for new Vinted listings that match saved searches, delivered to Slack or Discord with rich context.

## Primary Use Cases
- Notify when a specific size appears under a target price
- Alert Discord channels for items that meet quality or rating thresholds
- Track multiple locales while applying price or condition-aware rules

## Feature Set
### MVP
- Saved searches with keywords, price ceiling, size/gender/category, locale
- New-listing detection with duplicate suppression
- Slack and Discord webhook delivery with rich messages (title, price, size, condition, seller rating, link, thumbnail)
- Cooldown windows to avoid spam
- Simple YAML/JSON configuration with secrets provided via environment variables
- GitHub Actions scheduler (cron) for hosted-on-GitHub runs
- Basic logging and metrics (found/notified/skipped)

### Enhanced
- Include and exclude keyword lists per search
- Seller reputation threshold and minimum sales volume
- Optional geo filters or "ships to" constraints
- Price-drop alerts for already-seen items
- Batching alerts when multiple matches appear simultaneously
- Multi-locale search routing in one run with per-locale rate limits
- Pause/resume rules and per-rule cooldown overrides
- Web dashboard for managing searches (later)

### Pro/Paid
- Higher-frequency polling and faster alert latency
- Premium filters (seller rating, condition grading, historical price guidance)
- Team or webhook quotas with per-seat or per-channel billing
- Usage analytics: alerts sent per rule, per month; success metrics
- Multiple notification channels per rule (Slack, Discord, email fallback)
- Priority support and uptime/SLA-backed monitoring
- Optional affiliate or redirect tracking (subject to Vinted terms)

## User Experience and Onboarding
- Quickstart wizard (CLI or simple UI) to define the first search and webhook
- Template gallery for common searches (sneakers, tech, collectibles)
- Clear safety notes about respecting rate limits and choosing polite polling intervals
- Troubleshooting guides for webhook setup and GitHub Actions secrets

## Operational and Compliance Considerations
- Respect Vinted rate limits and robots directives; use polite headers and backoff
- Keep secrets only in GitHub Actions secrets; avoid logging sensitive data
- Maintain a transparent changelog and status page for the hosted tier

## Monetization Paths
- Free tier: limited searches, slower polling, single webhook
- Pro tier: higher frequency, multiple rules or locales, advanced filters, priority alerts
- Team tier: multi-channel delivery, quotas per workspace, reporting
- Add-on: premium "instant" alerts with higher polling budget
- Stripe checkout with free trials; usage-based overage after notification limits
- Partner or affiliate links where permitted, otherwise focus on value-add alerts

## Next Steps
- Expand into a feature backlog with priorities and acceptance criteria
- Map features to implementation milestones and CI/CD requirements
