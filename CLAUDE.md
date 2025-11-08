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
Stars are locked for 21 days after payment. The bot maintains a "hot reserve" of 5000-10000 stars to enable immediate payouts to winners. After 21 days, received stars become available and replenish the reserve.

**Stars Withdrawal System:**
- **Minimum withdrawal: 1 star** (no minimum limit - any amount can be withdrawn)
- **Admin approval required:** All withdrawal requests must be approved by administrators
- **Automatic refund:** If user has recent star payments, system tries to use `refundStarPayment` API
- **Manual gift transfer:** If automatic refund fails, admin manually sends stars as gift to user

**Test Environment for Stars:**
- Use Telegram Test Server for testing without real money
- Create separate test bot in Test Server via @BotFather
- Set `ENV=development` and `TEST_BOT_TOKEN` in `.env`
- All payments in test mode are free and simulated
- Access Test Server: iOS (tap Settings 10x), Desktop (Shift+Alt+Right-click "Add Account"), macOS (⌘+Click "Add Account")

**Provable Fairness:**
All random winner selection uses Random.org's Signed API (`generateSignedIntegers`). The signature is stored in the `raffles.random_result` field and can be publicly verified, ensuring transparency and preventing manipulation.

**Async Notifications:**
Telegram API allows 30 messages/second. The notification service (`services/notification.py`) sends messages in batches of 30 with 1-second delays between batches using asyncio.gather(). Priority order: winner → participants → observers.

you must dont create trashable md files, for fixed or anything else. You must fully realize features and make bot smoothe best UI UX practices and telegram navigations usage. All menu you must check if has Back button and similar content.
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

# Edit .env with required values:
# - TELEGRAM_BOT_TOKEN (production bot from @BotFather)
# - ADMIN_USER_IDS (your Telegram user ID)
# - RANDOM_ORG_API_KEY
# - DATABASE_URL, REDIS_URL
```

**For Production:**
```bash
ENV=production
TELEGRAM_BOT_TOKEN=your_production_bot_token
```

**For Testing (Test Server):**
1. Access Telegram Test Server:
   - **iOS**: Tap Settings icon 10 times → Accounts → Login to another account → Test
   - **Desktop**: Settings → Shift+Alt+Right-click "Add Account" → Test Server
   - **macOS**: Tap Settings icon 10 times → ⌘+Click "Add Account"

2. Create test bot in Test Server via @BotFather

3. Configure `.env`:
```bash
ENV=development
TEST_BOT_TOKEN=your_test_bot_token_from_test_server
TELEGRAM_BOT_TOKEN=your_production_token  # Still required
```

4. Bot will automatically use test token and log "🧪 TEST MODE" on startup

5. All star payments in test mode are FREE and simulated

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
