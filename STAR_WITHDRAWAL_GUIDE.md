# Telegram Stars Withdrawal System Guide

## Overview

This bot implements a **smart dual-method withdrawal system** for Telegram Stars that combines automatic refunds with manual admin transfers.

## ⚠️ Critical Understanding: How Telegram Stars Work

### What Bots CAN Do:
- ✅ **Receive stars** from users via `sendInvoice` API
- ✅ **Refund stars** to users via `refundStarPayment` API (only within 21 days of payment)

### What Bots CANNOT Do:
- ❌ **Directly send stars** to users (no "send stars" API exists)
- ❌ **Access bot's star balance** or transfer from it
- ❌ **Refund partial amounts** (must refund full payment amount)

## How Withdrawal System Works

### 🤖 Method 1: Automatic Refunds (Primary)

**When it works:**
- User has made star payments to the bot within the last 21 days
- System finds eligible transactions and refunds them
- Stars are **instantly returned** to user's Telegram Stars balance

**Process:**
1. User requests withdrawal (e.g., 50 stars)
2. System searches for user's recent payments (last 21 days)
3. System calls `bot.refundStarPayment()` for each eligible transaction
4. Stars automatically appear in user's Telegram account
5. No admin intervention needed!

**Limitations:**
- Only works for payments within 21-day window
- Cannot partially refund a transaction (must refund full amount)
- If user paid 10 stars but wants to withdraw 15, can only refund the 10-star payment

**Example:**
```
User balance: 50 stars
Withdrawal request: 40 stars

Recent payments:
- Payment 1: 10 stars (5 days ago) ✅ Eligible
- Payment 2: 10 stars (10 days ago) ✅ Eligible
- Payment 3: 10 stars (15 days ago) ✅ Eligible
- Payment 4: 10 stars (20 days ago) ✅ Eligible

Result: All 4 payments refunded = 40 stars returned automatically
```

### 👤 Method 2: Admin Manual Send (Fallback)

**When it's needed:**
- User has no recent payments (all older than 21 days)
- Automatic refunds don't cover the full withdrawal amount
- User's payment amounts don't match withdrawal amount

**Process:**
1. System attempts automatic refunds first
2. If remaining amount > 0, admin receives instructions
3. **Admin uses their PERSONAL Telegram account** (not the bot!) to send stars
4. Admin clicks confirmation button after sending
5. User receives notification about completed withdrawal

**How Admin Sends Stars Manually:**

#### Option 1: Via Personal Telegram Account (Recommended)
1. Open Telegram app with admin's personal account
2. Navigate to user's chat (click username in bot message)
3. Click attachment button (📎) → Gift → Telegram Stars
4. Enter amount and send
5. Click "✅ I sent X stars manually" button in bot

#### Option 2: Via Another Bot
1. Use a different bot that admin controls
2. Create star invoice/gift for the user
3. Click confirmation button in original bot

#### Option 3: Alternative Payment
1. Contact user directly
2. Offer alternative (e.g., RUB transfer instead)
3. Complete transaction
4. Click confirmation button

## Complete Withdrawal Flow Diagram

```
User Requests Withdrawal (50 stars)
           ↓
Admin Approves Withdrawal
           ↓
    Balance Deducted
           ↓
  Search Recent Payments
           ↓
   ┌──────┴──────┐
   │             │
Found?         Not Found?
   │             │
   ↓             ↓
Try Refunds    Admin Manual Send
   │                    ↓
   ├→ Success (40★)    Send via Personal Account
   ├→ Failed (0★)           ↓
   ↓                  Click Confirm Button
   │                         ↓
   ↓                  Status: COMPLETED
Remaining = 10★              ↓
   ↓                  User Notified
Admin Manual Send
   ↓
Send 10★ Manually
   ↓
Click Confirm Button
   ↓
Status: COMPLETED
   ↓
User Notified
```

## User Experience

### Scenario 1: Full Automatic Refund
```
User: "I want to withdraw 30 stars"
Bot: "✅ Request created!"

Admin: Approves request
System: Automatically refunds 30 stars from recent payments

User receives:
"✅ Withdrawal completed!
🤖 Automatically returned: 30 ⭐
All stars have been returned to your Telegram Stars balance."
```

### Scenario 2: Partial Automatic + Manual
```
User: "I want to withdraw 50 stars"
Bot: "✅ Request created!"

Admin: Approves request
System: Automatically refunds 30 stars, 20 stars remaining

Admin sees:
"✅ Auto-refunded: 30 ⭐
⚠️ Manually send: 20 ⭐
[Instructions how to send]
[✅ I sent 20 ⭐ manually] ← Button"

Admin: Sends 20 stars from personal account → Clicks button

User receives:
"✅ Withdrawal completed!
🤖 Automatically returned: 30 ⭐
👤 Sent by admin: 20 ⭐
Total: 50 ⭐"
```

### Scenario 3: Fully Manual
```
User: "I want to withdraw 100 stars"
(User has no payments in last 21 days)

Bot: "✅ Request created!"

Admin: Approves request
System: No refundable payments found

Admin sees:
"⚠️ No refundable payments
Manually send: 100 ⭐
[Instructions]
[✅ I sent 100 ⭐ manually] ← Button"

Admin: Sends 100 stars → Clicks button

User receives:
"✅ Withdrawal completed!
👤 Sent by admin: 100 ⭐"
```

## Database Tracking

### withdrawal_requests.payment_metadata JSON Structure

**After Automatic Refunds:**
```json
{
  "total_refunded": 30,
  "remaining": 20,
  "refund_count": 3,
  "refund_rate": 60.0,
  "refund_details": [
    {
      "transaction_id": 123,
      "payment_id": "tg_charge_abc123",
      "amount": 10,
      "created_at": "2025-01-15T10:30:00"
    },
    ...
  ]
}
```

**After Admin Confirmation:**
```json
{
  "total_refunded": 30,
  "remaining": 20,
  "manual_send_confirmed": true,
  "manual_send_amount": 20,
  "manual_send_confirmed_at": "2025-01-18T14:45:00",
  "manual_send_confirmed_by": 123456789
}
```

### Status Transitions

```
PENDING
   ↓ (Admin approves)
APPROVED
   ↓ (Full auto-refund OR admin confirms manual send)
COMPLETED
```

## Admin Panel Features

### Withdrawal Review Screen
```
💸 Withdrawal Request #123

User: @username (ID: 123456)
Amount: 50 ⭐
Status: pending

Current balance: 50 ⭐

[✅ Approve] [❌ Reject]
```

### After Approval (Partial Refund)
```
✅ Request #123 approved!

Balance deducted: 50 ⭐

✅ Auto-refunded: 30 ⭐ via 3 payments

⚠️ Remaining: 20 ⭐

📱 HOW TO SEND STARS:

Method 1 (Recommended):
1. Open chat with @username
2. Click 📎 → Gift → Telegram Stars
3. Send 20 stars

⚠️ Click button below after sending!

[✅ I sent 20 ⭐ manually]
[◀️ Back to menu]
```

### After Confirmation
```
✅ Withdrawal completed!

Request: #123
User: @username
Total: 50 ⭐

🤖 Auto: 30 ⭐
👤 Manual: 20 ⭐

User has been notified.
```

## Security & Best Practices

### For Admins:
1. ✅ Always verify user identity before manual send
2. ✅ Check that stars were actually sent before clicking confirm
3. ✅ Keep records of manual sends (Telegram gift history)
4. ❌ Never confirm without actually sending
5. ❌ Don't share admin credentials

### For System:
1. ✅ Balance is deducted BEFORE processing (prevents double withdrawal)
2. ✅ All refunds are logged with transaction IDs
3. ✅ Manual sends are tracked with timestamp and admin ID
4. ✅ Users receive detailed breakdown of auto vs manual amounts
5. ✅ Withdrawal history is maintained

## Troubleshooting

### "No refundable payments found"
**Cause:** User has no star payments within 21 days
**Solution:** Admin must manually send all stars

### "Partial refund only"
**Cause:** Some payments are too old or amounts don't match
**Solution:** System refunds what it can, admin sends remainder

### "Refund failed"
**Possible causes:**
- Payment already refunded
- Payment older than 21 days
- Telegram API error
**Solution:** Fallback to manual send

### User didn't receive stars
**Check:**
1. Was automatic refund successful? (check logs)
2. Did admin actually send manual portion?
3. Did admin click confirmation button?
4. Check user's Telegram Stars balance directly

## Technical Implementation

### Key Files:
- `app/services/stars_service.py` - Refund logic
- `app/handlers/admin.py` - Approval & confirmation handlers
- `app/handlers/withdrawal.py` - User withdrawal requests
- `app/database/models.py` - WithdrawalRequest model

### Key Functions:
- `process_withdrawal_with_multiple_refunds()` - Auto-refund engine
- `callback_admin_approve_withdrawal()` - Admin approval handler
- `callback_confirm_manual_send()` - Manual send confirmation handler

### API Calls:
```python
# Automatic refund (bot CAN do this)
await bot.refund_star_payment(
    user_id=telegram_user_id,
    telegram_payment_charge_id=charge_id
)

# Manual send (admin does this via Telegram UI, not API)
# No programmatic way - must be done manually!
```

## Future Improvements

### Potential Enhancements:
1. **Batch manual sends** - Queue multiple withdrawals for admin
2. **Alternative currencies** - Allow conversion to RUB if stars unavailable
3. **Reserve fund tracking** - Monitor how many stars are "locked" in 21-day window
4. **Predictive analytics** - Estimate refund success rate before approval
5. **Automated reminders** - Notify admin of pending manual sends

### Limitations to Accept:
- Cannot fully automate (Telegram API limitation)
- Requires admin intervention for old payments
- Manual send relies on admin trustworthiness
- No way to verify admin actually sent stars (honor system)

## Conclusion

This hybrid system provides the **best possible user experience** within Telegram's API limitations:
- ✅ Automatic when possible (fast, no admin work)
- ✅ Clear admin instructions when manual send needed
- ✅ Full tracking and transparency
- ✅ Secure (balance deducted upfront)
- ✅ User-friendly notifications

The key insight: **Bots cannot send stars directly - they can only refund previous payments or ask admins to manually send from personal accounts.**
