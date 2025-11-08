# Telegram Raffle Bot

A Telegram bot for running provably fair raffles with two payment methods: Telegram Stars and Russian Rubles (RUB).

## Features

- **Dual Payment System**: Accept both Telegram Stars and Russian Rubles
- **Provably Fair**: Uses Random.org Signed API for verifiable randomness
- **Automated Payouts**: Instant payouts to winners
- **Admin Panel**: Complete raffle management interface
- **Transparent**: Public verification links for each raffle
- **Scalable**: Built with async/await and Docker

## Prerequisites

- Python 3.11+
- Telegram Bot Token (from [@BotFather](https://t.me/BotFather))
- Random.org API Key (from [Random.org](https://api.random.org/))
- YooKassa Account (optional, for RUB payments)

**For Docker deployment:**
- Docker and Docker Compose

**For local development:**
- PostgreSQL 14+
- Redis 6+

## Quick Start

### ⚡ Super Quick Start (Local Development)

```bash
./scripts/setup.sh    # Setup everything
./scripts/run.sh      # Start the bot
```

See [QUICKSTART.md](QUICKSTART.md) for 5-minute setup guide!

### 📦 Docker Deployment

### 1. Clone and Setup

```bash
# Clone repository
git clone <your-repo-url>
cd raffle-telegram-bot

# Copy environment template
cp .env.example .env
```

### 2. Configure Environment

Edit `.env` file with your credentials:

```env
TELEGRAM_BOT_TOKEN=your_bot_token_here
ADMIN_USER_ID=your_telegram_user_id
RANDOM_ORG_API_KEY=your_random_org_api_key

# Optional: For RUB payments
YOOKASSA_SHOP_ID=your_shop_id
YOOKASSA_SECRET_KEY=your_secret_key
```

**How to get your Telegram User ID:**
1. Start a chat with [@userinfobot](https://t.me/userinfobot)
2. It will reply with your user ID

### 3. Run with Docker

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f bot

# Stop services
docker-compose down
```

### 4. Run Locally (Without Docker)

**Option A: Quick Setup (Recommended)**
```bash
./scripts/setup.sh           # One-time setup
./scripts/run.sh             # Run the bot
```

**Option B: Manual Setup**
```bash
# Install PostgreSQL and Redis
./scripts/install_services_macos.sh    # macOS
# or
sudo ./scripts/install_services_linux.sh   # Linux

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Initialize database
python scripts/init_db.py

# Start bot
python app/main.py
```

**Using Makefile (if available):**
```bash
make setup      # Initial setup
make run        # Run the bot
make check      # Check services
```

📖 **Detailed guide:** See [LOCAL_DEVELOPMENT.md](LOCAL_DEVELOPMENT.md) for complete local setup instructions.

## Bot Commands

**User Commands:**
- `/start` - Welcome message and main menu
- `/balance` - Show your balance
- `/help` - Help information

**Admin Commands:**
- `/admin` - Access admin panel

## Admin Panel Features

- ✅ Create new raffle
- ✅ View current raffle status
- ✅ Force start raffle
- ✅ Stop/cancel raffle
- ✅ View statistics
- ✅ Configure settings

## How It Works

### For Users

1. **Join Raffle**: Click "Участвовать в розыгрыше"
2. **Choose Payment**: Select Stars or RUB
3. **Pay Entry Fee**: Complete payment
4. **Wait for Draw**: Raffle starts when minimum participants reached
5. **Win Prize**: Winner receives automatic payout

### For Admins

1. **Create Raffle**: Set minimum participants and entry fee
2. **Monitor**: Watch participants join
3. **Auto-Execute**: Raffle runs automatically when ready
4. **Verify**: Check Random.org signature for fairness

## Architecture

```
app/
├── config.py              # Configuration management
├── database/
│   ├── models.py          # SQLAlchemy models
│   ├── crud.py            # Database operations
│   └── session.py         # Database connection
├── handlers/
│   ├── start.py           # /start and basic commands
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
```

## Database Schema

- **users**: User accounts and balances
- **raffles**: Raffle information and status
- **participants**: Raffle participation records
- **transactions**: Payment history
- **bot_settings**: Bot configuration

## Configuration

Edit `.env` to customize:

- **Entry Fees**: `STARS_ENTRY_FEE`, `RUB_ENTRY_FEE`
- **Commission**: `STARS_COMMISSION_PERCENT`, `RUB_COMMISSION_PERCENT`
- **Min Participants**: `MIN_PARTICIPANTS`
- **Reserve Settings**: `STARS_RESERVE_MIN`, `STARS_RESERVE_TARGET`

## Security Features

- ✅ Provable fairness with Random.org signatures
- ✅ Transaction idempotency (prevent double payments)
- ✅ Admin-only protected routes
- ✅ Input validation and sanitization
- ✅ Comprehensive error handling
- ✅ Audit logging

## Payment Methods

### Telegram Stars

- Built-in Telegram payment system
- Instant processing
- No additional setup required
- 21-day reserve system for liquidity

### Russian Rubles (YooKassa)

- Supports bank cards, SBP, YooMoney
- Automatic payouts
- Receipt generation for self-employed
- Requires YooKassa account

## Troubleshooting

### Bot doesn't start

```bash
# Check logs
docker-compose logs bot

# Verify environment variables
cat .env

# Check database connection
docker-compose logs postgres
```

### Database issues

```bash
# Reset database
docker-compose down -v
docker-compose up -d postgres redis
alembic upgrade head
docker-compose up -d bot
```

### Payment issues

- Verify API keys in `.env`
- Check YooKassa account status
- Review bot logs for errors

## Development

### Create Database Migration

```bash
# Auto-generate migration
alembic revision --autogenerate -m "description"

# Apply migration
alembic upgrade head

# Rollback
alembic downgrade -1
```

### Run Tests

```bash
pytest tests/ -v
```

### Code Style

```bash
# Format code
black app/

# Lint
flake8 app/
```

## Deployment

### Production Setup

1. Use production `.env` with secure credentials
2. Enable SSL for webhook mode (optional)
3. Set up monitoring (Sentry, Prometheus)
4. Configure automated backups
5. Use reverse proxy (nginx)

### Backup Database

```bash
# Manual backup
docker-compose exec postgres pg_dump -U postgres raffle_bot > backup.sql

# Restore
docker-compose exec -T postgres psql -U postgres raffle_bot < backup.sql
```

## Legal Considerations

- Position as "entertainment game" not gambling
- Avoid terms like "lottery" or "casino"
- Maintain transparent rules
- Public verification of fairness
- Comply with local regulations

## License

MIT License - see LICENSE file

## Support

For issues and questions:
- Check logs: `docker-compose logs -f bot`
- Review CLAUDE.md for implementation details
- Check plan.md for architecture

## Contributing

1. Fork the repository
2. Create feature branch
3. Make changes
4. Test thoroughly
5. Submit pull request

---

**Built with ❤️ using aiogram 3.x**
