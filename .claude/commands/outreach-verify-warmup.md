# /outreach-verify-warmup

Check sender account health, warmup status, and deliverability metrics.

## Instructions

You are verifying the health of FileFlo's email sending infrastructure.

### Step 1: List All Accounts

Call `list_accounts` to get all sender email accounts.

For each account, note:
- Email address
- Status (1=Active, 2=Paused, -1/-2/-3=Errors)
- Provider (1=IMAP, 2=Google, 3=Microsoft, 4=AWS)

### Step 2: Check Warmup Analytics

Call `get_warmup_analytics` with all account emails for the last 7 days.

For each account, evaluate:
- **Inbox placement rate**: Target 90%+, flag below 85%
- **Spam rate**: Target below 2%, flag above 3%
- **Warmup emails sent/received**: Should be consistent daily
- **Reply rate**: Should be healthy (20%+ in warmup)

### Step 3: Check Account Details

For any flagged accounts, call `get_account` with the email to get:
- Connection status (IMAP/SMTP working?)
- Daily sending limit configuration
- Warmup configuration (enabled? limit?)
- Tracking domain settings

### Step 4: Test Connectivity (if issues found)

For accounts with errors, call `manage_account_state` with `action: "test_vitals"` to test IMAP/SMTP connectivity.

### Step 5: Generate Health Report

```
=== SENDER ACCOUNT HEALTH CHECK ===
Date: [date]

SUMMARY:
  Total accounts: [N]
  Healthy: [N]
  Warning: [N]
  Critical: [N]

ACCOUNT DETAILS:
[For each account:]
  [email@domain.com]
  Status: [Active/Paused/Error]
  Provider: [Google/Microsoft/IMAP/AWS]
  Warmup: [Enabled/Disabled]
  Inbox Placement: [X]% [OK/WARNING/CRITICAL]
  Spam Rate: [X]% [OK/WARNING/CRITICAL]
  Daily Limit: [N] emails/day
  Assessment: [HEALTHY / WARNING / CRITICAL]

RECOMMENDED ACTIONS:
[For each non-healthy account:]
  - [account]: [specific action - pause, reduce limit, re-warm, check SMTP, etc.]
```

### Step 6: Recommend Actions

**Healthy (inbox placement 90%+, spam rate <2%):**
- Ready for campaign sending at 30/day

**Warning (inbox placement 85-90%, spam rate 2-3%):**
- Reduce daily sending limit to 20/day
- Enable/increase warmup volume
- Monitor for 3 days before campaign use

**Critical (inbox placement <85%, spam rate >3%, or errors):**
- Pause all campaign sending immediately
- Enable warmup-only mode
- Call `manage_account_state` with `action: "disable_warmup"` then `action: "enable_warmup"` to reset
- Do NOT use for campaigns until metrics recover (minimum 7 days)

### Important Notes
- Run this check BEFORE launching any new campaigns
- Run weekly as part of the Monday `/outreach-weekly-report` routine
- The previous campaign had 100% spam block rate -- deliverability is the #1 priority
- If multiple accounts are unhealthy, the issue may be domain-level (check DNS, SPF, DKIM, DMARC)
- Never send campaigns from accounts with inbox placement below 85%
