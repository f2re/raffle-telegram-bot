# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Telegram bot for running raffles/prize drawings with two payment methods: Telegram Stars and Russian Rubles (RUB). The bot ensures provably fair randomness using Random.org's Signed API and handles automated payouts.

## Technology Stack

- **Python 3.11+** with aiogram 3.x for Telegram Bot API
- **PostgreSQL** for persistent data storage (users, raffles, transactions)
- **Redis** for caching and temporary data
- **YooKassa API** for RUB payments and payouts
- **Random.org Signed API** for verifiable random number generation
- **Docker** for deployment

## Repository Structure

```
app/
├── config.py              # Configuration (tokens, API keys)
├── database/
│   ├── models.py          # SQLAlchemy models
│   ├── crud.py            # CRUD operations
│   └── session.py         # Database connection
├── handlers/
│   ├── start.py           # /start command
│   ├── payment.py         # Payment processing
│   ├── raffle.py          # Raffle logic
│   └── admin.py           # Admin panel
├── services/
│   ├── payment_service.py # YooKassa integration
│   ├── random_service.py  # Random.org integration
│   └── notification.py    # Mass notifications
├── keyboards/
│   └── inline.py          # Inline keyboards
└── main.py                # Entry point
migrations/                # Alembic migrations
```

## Core Architecture

### Database Schema

**users table:**
- id, telegram_id, username
- balance_stars, balance_rub (user balances)
- created_at

**raffles table:**
- id, min_participants
- entry_fee_type (stars/rub), entry_fee_amount
- status (pending/active/finished)
- started_at, finished_at
- winner_id, random_result (Random.org signature for verification)

**participants table:**
- id, raffle_id, user_id
- joined_at, transaction_id

**transactions table:**
- id, user_id, type, amount, currency
- status, payment_id, created_at

### Critical Design Decisions

**Telegram Stars Reserve System:**
Stars are locked for 21 days after payment. The bot maintains a "hot reserve" of 5000-10000 stars to enable immediate payouts to winners. After 21 days, received stars become available and replenish the reserve. Minimum withdrawal is 1000 stars.

**Provable Fairness:**
All random winner selection uses Random.org's Signed API (`generateSignedIntegers`). The signature is stored in the `raffles.random_result` field and can be publicly verified, ensuring transparency and preventing manipulation.

**Async Notifications:**
Telegram API allows 30 messages/second. The notification service (`services/notification.py`) sends messages in batches of 30 with 1-second delays between batches using asyncio.gather(). Priority order: winner → participants → observers.

## Key Implementation Patterns

### Payment Processing

**Telegram Stars:**
- Use `sendInvoice` with empty `provider_token=""` for built-in Stars support
- Handle `pre_checkout_query` and `successful_payment` callbacks
- Use `refundStarPayment` API for payouts (or pay from reserve fund)

**Russian Rubles:**
- YooKassa API for payment acceptance
- Configure webhook for payment notifications
- Use YooKassa Payouts API for automated transfers (bank cards, SBP, YooMoney)
- Supports automatic receipt generation for self-employed users

### Raffle Flow

1. **Start:** Admin creates raffle with entry fee and min participants
2. **Acceptance:** Users join by paying entry fee → added to participants list
3. **Execution:** When min participants reached → call Random.org API
4. **Selection:** Random number maps to participant index → winner determined
5. **Payout:** Calculate prize (entry_fee × participants - commission) → send to winner
6. **Notification:** Send results to all participants via async batch sending

### Random.org Integration

```python
# services/random_service.py pattern:
def get_signed_random(min_val, max_val, api_key):
    payload = {
        "jsonrpc": "2.0",
        "method": "generateSignedIntegers",
        "params": {
            "apiKey": api_key,
            "n": 1,
            "min": min_val,
            "max": max_val
        },
        "id": 1
    }
    response = requests.post(
        "https://api.random.org/json-rpc/4/invoke",
        json=payload
    )
    return response.json()  # Contains number + signature
```

## Development Commands

### Environment Setup

```bash
# Copy environment template
cp .env.example .env

# Edit .env with:
# - TELEGRAM_BOT_TOKEN (from @BotFather)
# - YOOKASSA_SHOP_ID, YOOKASSA_SECRET_KEY
# - RANDOM_ORG_API_KEY
# - DATABASE_URL, REDIS_URL
```

### Running Locally

```bash
# Start infrastructure
docker-compose up -d postgres redis

# Run database migrations
alembic upgrade head

# Start bot
python app/main.py
```

### Testing

```bash
# Run unit tests
pytest tests/

# Run integration tests
pytest tests/integration/

# Test specific module
pytest tests/test_raffle.py -v
```

### Database Operations

```bash
# Create new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# Backup database
docker-compose exec postgres pg_dump -U postgres raffle_bot > backup.sql
```

## Security & Validation

**Pre-payout Checks:**
- Verify sufficient balance in reserve fund
- Validate Random.org signature authenticity
- Check transaction status to prevent double payouts (idempotency)

**Anti-fraud:**
- Rate limit on daily participation
- Detect duplicate payments
- Log all financial operations with timestamps

**Error Handling:**
Always wrap payout operations in try/except blocks. On PaymentError: rollback transaction, refund user, notify admin, write to logs.

## Commission Structure

**Telegram Stars:**
- Entry fee: 10 stars (~$0.13 USD)
- Commission: 15-20% (profit + reserve coverage)
- Prize pool: 80-85% of total

**Russian Rubles:**
- Entry fee: 100-300 RUB
- Commission: 10-15% (includes YooKassa ~3% + profit)
- Prize pool: 85-90% of total

## Bot Commands

```
/start - Welcome message + main menu
/balance - Show stars/ruble balance
/join_raffle - Join current raffle
/my_raffles - Participation history
/admin - Admin panel (owner only)
```

## Admin Functions

- Create new raffle (fee, min participants, deadline)
- Stop raffle manually
- Force-start raffle
- View all participants
- Payout statistics
- Manage stars reserve fund
- Configure commission percentage

## Legal & Transparency

- Position as "entertainment game" not gambling (avoid terms like "lottery", "casino")
- Publish Random.org signature links for public verification
- Display prize pool calculation transparently
- Show commission explicitly
- Maintain complete raffle history

## Monitoring & Deployment

**Production Deployment:**
```bash
# On VPS (DigitalOcean, Timeweb, etc.)
docker-compose up -d

# View logs
docker-compose logs -f bot

# Restart bot
docker-compose restart bot
```

**Reserve Monitoring:**
- Initial reserve: 5000-10000 stars (~$65-130 USD)
- Alert threshold: < 3000 stars
- Auto-notify admin on low balance

**Logging:**
- Use structured logging (Loguru)
- Integrate Sentry for error tracking
- Optional: Prometheus + Grafana for metrics
