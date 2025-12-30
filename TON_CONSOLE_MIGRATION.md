# TON Console API Migration Guide

This bot now uses **TON Console API (https://tonconsole.com)** instead of direct TON blockchain node connections for better reliability and performance.

## What Changed?

### Before (Old Implementation)
- Used `pytoniq` LiteBalancer to connect directly to TON blockchain nodes (liteservers)
- Frequently experienced connection issues: "have no alive peers", "liteserver crashed", "out of sync"
- Required constant reconnection and retry logic
- Limited by blockchain node availability

### After (New Implementation)
- Uses **TON Console API** (https://tonconsole.com) via `pytonapi` SDK for read operations
- Still uses `pytoniq` for wallet operations (sending TON - this requires local signing)
- Much more reliable - no liteserver connection issues
- Better rate limits with API key
- Professional-grade infrastructure

## Architecture Overview

```
┌─────────────────────────────────────────────┐
│         Raffle Telegram Bot                 │
├─────────────────────────────────────────────┤
│                                             │
│  Read Operations (via TON Console API):    │
│  ├─ Get account balance                    │
│  ├─ Monitor incoming transactions          │
│  └─ Verify transaction details             │
│     ↓                                       │
│  [pytonapi SDK] → https://tonapi.io/v2/    │
│     ↓                                       │
│  TON Console API (tonconsole.com)          │
│                                             │
│  ─────────────────────────────────────────  │
│                                             │
│  Write Operations (wallet signing):        │
│  ├─ Send prize payouts                     │
│  ├─ Send refunds                           │
│  └─ Send any TON transaction               │
│     ↓                                       │
│  [pytoniq + WalletV4R2]                    │
│     ↓                                       │
│  Direct to TON blockchain                  │
│                                             │
└─────────────────────────────────────────────┘
```

## API Endpoints Used

### 1. Get Account Balance
**Endpoint:** `GET /v2/accounts/{account_id}`

**What it does:** Returns account information including balance, status, and metadata

**Used in:** `ton_service.get_balance()`

**Example:**
```python
account = await tonapi.accounts.get_info(account_id=wallet_address)
balance_ton = float(account.balance.to_amount())
```

### 2. Get Account Events (Transactions)
**Endpoint:** `GET /v2/accounts/{account_id}/events`

**What it does:** Returns account transaction history (events)

**Used in:** `ton_service.check_incoming_transactions()`

**Example:**
```python
events = await tonapi.accounts.get_events(
    account_id=wallet_address,
    limit=30
)

for event in events.events:
    for action in event.actions:
        if action.type == "TonTransfer":
            # Process incoming TON transfer
            amount = float(action.ton_transfer.amount) / 1_000_000_000
            sender = action.ton_transfer.sender.address
```

### 3. Verify Transaction
Uses the same events endpoint to find and verify specific transactions by event_id.

## Getting Started

### 1. Create TON Console Account

1. Visit https://tonconsole.com
2. Click "Sign Up" or "Sign In" with GitHub
3. Complete registration

### 2. Generate API Key

1. Go to your TON Console dashboard
2. Navigate to "API Keys" section
3. Click "Create New Key"
4. Give it a descriptive name (e.g., "Raffle Bot Production")
5. Copy the generated API key

**API Key Format:** `AxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxE`

### 3. Configure Environment

Add the API key to your `.env` file:

```env
# TON Configuration
TON_CENTER_API_KEY=Axxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx  # Your TON Console API key
TON_WALLET_ADDRESS=UQxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TON_WALLET_MNEMONIC=word1 word2 word3 ... word24
TON_NETWORK=mainnet
```

**Note:** The variable is called `TON_CENTER_API_KEY` for backward compatibility, but it's actually a TON Console API key.

### 4. Install Dependencies

The `pytonapi` SDK is required:

```bash
pip install -r requirements.txt
```

Or manually:
```bash
pip install pytonapi
```

### 5. Restart Bot

```bash
# Docker deployment
docker compose down
docker compose build --no-cache
docker compose up -d

# Local deployment
python -m app.main
```

## Rate Limits

### Without API Key (Free Tier)
- **Rate limit:** 1 request per 4 seconds (0.24 RPS)
- **Use case:** Testing only
- **Not recommended** for production

### With API Key (Authenticated)
- **Rate limit:** Much higher (depends on your plan)
- **Use case:** Production deployment
- **Required** for reliable bot operation

Check your current limits at: https://tonconsole.com/dashboard

## Error Handling

### Connection Errors
The new implementation handles TON Console API errors gracefully:

```python
try:
    balance = await ton_service.get_balance()
except TonPaymentError as e:
    logger.error(f"Failed to get balance: {e}")
    # Handle error appropriately
```

### Transaction Monitoring
If the API is temporarily unavailable, the bot returns an empty transaction list and retries on the next check (every 15 seconds).

## Benefits

### ✅ Reliability
- No more "liteserver crashed" errors
- No more "have no alive peers" issues
- No more "out of sync" problems
- Professional-grade infrastructure

### ✅ Performance
- Faster response times
- Better caching
- Lower latency

### ✅ Features
- Rich transaction data (sender, recipient, amount, comment)
- Event-based transaction monitoring
- Better error messages

### ✅ Developer Experience
- Official Python SDK (`pytonapi`)
- Type hints and autocomplete
- Comprehensive documentation
- Swagger API explorer

## Troubleshooting

### Error: "401 Unauthorized"
**Cause:** Invalid or missing API key

**Solution:**
1. Check your API key in `.env` file
2. Verify it's copied correctly from https://tonconsole.com
3. Ensure no extra spaces or quotes

### Error: "429 Too Many Requests"
**Cause:** Rate limit exceeded

**Solution:**
1. If using free tier, add API key
2. If already using API key, upgrade your plan at https://tonconsole.com
3. Increase `TON_TRANSACTION_CHECK_INTERVAL` in `.env` (default: 15 seconds)

### Error: "Account not found"
**Cause:** Wallet address not initialized on blockchain

**Solution:**
1. Send a small amount of TON to your wallet address to initialize it
2. Wait 1-2 minutes for confirmation
3. Check balance on https://tonscan.org

### No Transactions Detected
**Cause:** Various reasons

**Check:**
1. Wallet address in `.env` is correct
2. Transactions are confirmed on blockchain (https://tonscan.org)
3. Bot's transaction monitoring is running (check logs)
4. `last_transaction_lt` hasn't been set too high (restart bot to reset)

## Documentation Links

- **TON Console:** https://tonconsole.com
- **TON Console Docs:** https://docs.tonconsole.com
- **TON API Docs:** https://docs.tonconsole.com/tonapi
- **REST API Reference:** https://docs.tonconsole.com/tonapi/rest-api
- **Swagger UI:** https://tonapi.io (interactive API explorer)
- **Python SDK (pytonapi):** https://github.com/tonkeeper/pytonapi

## Support

If you encounter issues:

1. **Check logs:** `docker compose logs -f bot` or view console output
2. **Verify API key:** Test it at https://tonapi.io/swagger
3. **Check status:** Visit https://tonconsole.com for service status
4. **Review docs:** https://docs.tonconsole.com/tonapi
5. **GitHub Issues:** https://github.com/tonkeeper/pytonapi/issues

---

**Migration completed successfully! Your bot now uses TON Console API for reliable TON blockchain access.**
