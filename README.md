# Telegram Raffle Bot

A Telegram bot for running provably fair raffles with two payment methods: Telegram Stars and Russian Rubles (RUB).

## Features

- **Dual Payment System**: Accept both Telegram Stars and Russian Rubles
- **TON Connect Integration**: One-click payments with connected TON wallets
- **Provably Fair**: Uses Random.org Signed API for verifiable randomness
- **Automated Payouts**: Instant payouts to winners
- **Admin Panel**: Complete raffle management interface
- **Transparent**: Public verification links for each raffle
- **Scalable**: Built with async/await and Docker

## Prerequisites

- Python 3.11+
- Telegram Bot Token (from [@BotFather](https://t.me/BotFather))
- TON Wallet and API credentials
- Random.org API Key (from [Random.org](https://api.random.org/))
- YooKassa Account (optional, deprecated - use TON instead)

**For Docker deployment:**
- Docker and Docker Compose

**For local development:**
- PostgreSQL 14+
- Redis 6+

## 🔑 Required API Tokens & Configuration

Before starting the bot, you need to obtain several API tokens and configure your environment. Here's a complete guide:

### 1. 🤖 Telegram Bot Token (Required)

**Where to get:** [@BotFather](https://t.me/BotFather)

**Steps:**
1. Open Telegram and search for `@BotFather`
2. Send `/newbot` command
3. Follow the instructions to create your bot
4. Copy the token (looks like: `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`)
5. Add to `.env`: `TELEGRAM_BOT_TOKEN=your_token_here`

**Important:** Enable payments in your bot:
- Send `/mybots` to @BotFather
- Select your bot → Payments
- Select a payment provider (use Telegram Payments for Stars)

---

### 2. 👤 Admin User IDs (Required)

**Where to get:** [@userinfobot](https://t.me/userinfobot)

**Steps:**
1. Open Telegram and search for `@userinfobot`
2. Send any message to the bot
3. It will reply with your user ID (e.g., `123456789`)
4. Add to `.env`: `ADMIN_USER_IDS=123456789` (comma-separated for multiple admins)

---

### 3. 💎 TON Blockchain Configuration (Required for TON payments)

#### 3.1 TON Center API Key

**Where to get:** [https://toncenter.com](https://toncenter.com)

**Steps:**
1. Visit https://toncenter.com
2. Click "Get API Key" or "Sign In"
3. Create account and get your API key
4. Add to `.env`: `TON_CENTER_API_KEY=your_api_key_here`

**Alternative:** Use TON API from [https://tonapi.io](https://tonapi.io) (also provides free API keys)

#### 3.2 TON Wallet Address & Mnemonic

**Where to create:** Any TON wallet app

**Recommended wallets:**
- [Tonkeeper](https://tonkeeper.com) (Most popular)
- [TON Wallet](https://wallet.ton.org)
- [MyTonWallet](https://mytonwallet.io)

**Steps:**
1. Download Tonkeeper (or any TON wallet)
2. Create new wallet
3. **IMPORTANT:** Save your 24-word mnemonic phrase securely!
4. Copy your wallet address (starts with `UQ` or `EQ`)
5. Add to `.env`:
   ```env
   TON_WALLET_ADDRESS=UQxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   TON_WALLET_MNEMONIC=word1 word2 word3 ... word24
   ```

**⚠️ Security Warning:**
- Never share your mnemonic with anyone
- Store it in a secure password manager
- This wallet will hold raffle funds - use a dedicated wallet for the bot
- Keep at least 10-20 TON in the wallet for payouts

**Network Selection:**
- For production: `TON_NETWORK=mainnet`
- For testing: `TON_NETWORK=testnet` (get free test TON from [TON Testnet Faucet](https://t.me/testgiver_ton_bot))

#### 3.3 TON Connect Manifest URL

**Where to host:** GitHub Pages (free) or your own domain

**Quick Setup with GitHub Pages:**
1. The project includes `tonconnect-manifest.json` file
2. Enable GitHub Pages in your repository settings
3. Your manifest URL will be: `https://your-username.github.io/raffle-telegram-bot/tonconnect-manifest.json`
4. Add to `.env`: `TON_CONNECT_MANIFEST_URL=https://your-username.github.io/raffle-telegram-bot/tonconnect-manifest.json`

**Alternative:** Host on your own domain at `https://yourdomain.com/tonconnect-manifest.json`

**See detailed guide:** [GITHUB_PAGES_SETUP.md](GITHUB_PAGES_SETUP.md)

---

### 4. 🎲 Random.org API Key (Required)

**Where to get:** [https://api.random.org/api-keys](https://api.random.org/api-keys)

**Steps:**
1. Visit https://api.random.org/api-keys
2. Sign up for a free account
3. Navigate to "API Keys" section
4. Click "Create New Key"
5. Copy your API key (format: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`)
6. Add to `.env`: `RANDOM_ORG_API_KEY=your_api_key_here`

**Free tier limits:** 1,000 requests per day (sufficient for most raffles)

---

### 5. 💳 YooKassa Credentials (Optional - Deprecated)

**⚠️ Note:** YooKassa (RUB payments) is deprecated. Use TON payments instead.

**If you still need it:**

**Where to get:** [https://yookassa.ru](https://yookassa.ru)

**Steps:**
1. Register at https://yookassa.ru
2. Complete business verification
3. Get Shop ID and Secret Key from dashboard
4. Add to `.env`:
   ```env
   YOOKASSA_SHOP_ID=your_shop_id
   YOOKASSA_SECRET_KEY=your_secret_key
   ```

---

### 📋 Complete .env Template

Copy `.env.example` to `.env` and fill in all values:

```env
# === REQUIRED SETTINGS ===

# 1. Telegram Bot
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
ADMIN_USER_IDS=123456789,987654321

# 2. TON Blockchain
TON_CENTER_API_KEY=your_toncenter_api_key
TON_WALLET_ADDRESS=UQxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TON_WALLET_MNEMONIC=word1 word2 word3 word4 word5 word6 word7 word8 word9 word10 word11 word12 word13 word14 word15 word16 word17 word18 word19 word20 word21 word22 word23 word24
TON_NETWORK=mainnet
TON_CONNECT_MANIFEST_URL=https://your-username.github.io/raffle-telegram-bot/tonconnect-manifest.json

# 3. Random.org
RANDOM_ORG_API_KEY=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx

# 4. Database (auto-configured for Docker)
DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/raffle_bot
REDIS_URL=redis://redis:6379/0

# === OPTIONAL SETTINGS ===

# YooKassa (deprecated - use TON instead)
YOOKASSA_SHOP_ID=your_shop_id
YOOKASSA_SECRET_KEY=your_secret_key

# Bot Configuration
MIN_PARTICIPANTS=10
TON_ENTRY_FEE=0.5
TON_COMMISSION_PERCENT=12
TON_RESERVE_MIN=10.0
TON_ONLY=true
```

---

### ✅ Configuration Checklist

Before starting the bot, verify you have:

- [ ] Telegram Bot Token from @BotFather
- [ ] Your Telegram User ID from @userinfobot
- [ ] TON Center API Key from toncenter.com
- [ ] TON Wallet address and 24-word mnemonic
- [ ] At least 10 TON in your wallet for payouts
- [ ] TON Connect manifest published (GitHub Pages or custom domain)
- [ ] Random.org API Key
- [ ] All values added to `.env` file
- [ ] `.env` file configured with correct network (mainnet/testnet)

---

### 🔗 Quick Links Summary

| Service | URL | Purpose |
|---------|-----|---------|
| BotFather | https://t.me/BotFather | Create Telegram bot |
| UserInfoBot | https://t.me/userinfobot | Get your Telegram User ID |
| TON Center | https://toncenter.com | TON blockchain API |
| Tonkeeper | https://tonkeeper.com | TON wallet (recommended) |
| TON Wallet | https://wallet.ton.org | Official TON wallet |
| Random.org | https://api.random.org/api-keys | Random number generation API |
| YooKassa | https://yookassa.ru | RUB payments (deprecated) |
| TON Testnet Faucet | https://t.me/testgiver_ton_bot | Free test TON |

---

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

### TON Connect (Recommended)

- **One-click payments**: Connect wallet once, pay instantly
- **Better UX**: No copying addresses or comments
- **Auto-initiated transactions**: Bot sends transaction, user just confirms
- **Supported wallets**: Tonkeeper, MyTonWallet, OpenMask
- **Persistent connection**: Stays connected across sessions

**Setup**: See [GITHUB_PAGES_SETUP.md](GITHUB_PAGES_SETUP.md) to publish TON Connect manifest

**Live manifest**: https://f2re.github.io/raffle-telegram-bot/tonconnect-manifest.json

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
