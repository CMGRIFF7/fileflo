# /outreach-manage-replies

Review, classify, and respond to incoming email replies from outreach campaigns.

## Instructions

You are managing replies to FileFlo's cold outreach campaigns targeting insurance brokers.

### Step 1: Check Inbox

Call `count_unread_emails` to get the unread count.

Then call `list_emails` with:
- `is_unread`: true
- `email_type`: "received"
- `mode`: "emode_all"
- `limit`: 50

### Step 2: Review Each Reply

For each unread email, call `get_email` with the email ID to get full content.

Display to the user:
- Sender name and email
- Campaign name (which sequence triggered this)
- Subject line
- Full reply body
- Lead details (company, title)

### Step 3: Classify Each Reply

Ask the user to classify each reply (or classify automatically based on content):

| Classification | Description | Interest Status | Action |
|---------------|-------------|-----------------|--------|
| **Positive** | Interested, wants demo/call | 2 (interested) | Draft response, book meeting |
| **Question** | Asking for more info | 1 (maybe interested) | Draft informative response |
| **Not Now** | Timing is off, maybe later | 0 (neutral) | Add to 90-day recycle list |
| **Not Interested** | Clear rejection | -1 (not interested) | Remove from sequences |
| **Unsubscribe** | Wants to stop emails | -2 (do not contact) | Remove immediately |
| **Out of Office** | Auto-reply, OOO | 0 (neutral) | Leave in sequence (auto-paused) |
| **Wrong Person** | Not the right contact | -1 | Remove, note for future filtering |

### Step 4: Update Lead Status

For each classified reply, call `update_lead` with:
- `lead_id`: the lead's UUID
- `lt_interest_status`: based on classification above

### Step 5: Draft Responses for Positive Replies

For **Positive** and **Question** replies, draft a response for user approval.

**Template for Positive (wants demo):**
```
Hi {{firstName}},

Great to hear from you. I would love to show you how FileFlo works for your clients.

How does [suggest 2-3 specific times this week] work for a quick 15-minute walkthrough? I can tailor it to your book -- whether that is trucking/DOT compliance or workplace safety.

Looking forward to it,
{{senderFirstName}}
```

**Template for Question (wants more info):**
```
Hi {{firstName}},

Great question. [Address their specific question here.]

The quick version: FileFlo auto-classifies compliance documents (CDLs, med cards, OSHA logs, training certs) and flags gaps before auditors do. Your clients upload docs, we handle the rest.

If you want to see it in action, I can do a quick 10-minute screen share. Otherwise, happy to answer more questions here.

{{senderFirstName}}
```

Present each draft to the user for approval/editing before sending.

### Step 6: Send Approved Responses

After user approves a response, call `reply_to_email` with:
- `reply_to_uuid`: the original email UUID
- `eaccount`: the sender account email from the original campaign
- `subject`: the reply subject line
- `body`: { "html": "[approved response]" }

**IMPORTANT:** Always get explicit user confirmation before sending any reply.

### Step 7: Summary Report

After processing all replies:

```
=== REPLY MANAGEMENT SUMMARY ===
Date: [date]

Total unread: [N]
Processed: [N]

Positive (demo interest): [N] -- [list names]
Questions: [N] -- [list names]
Not Now: [N]
Not Interested: [N]
Unsubscribe: [N]
Out of Office: [N]

Responses sent: [N]
Responses pending user approval: [N]

Pipeline update:
  New meetings to book: [N]
  Leads removed from sequences: [N]
  Leads added to recycle list: [N]
```

### Important Notes
- NEVER send a reply without explicit user approval
- Positive replies are the highest priority — respond within 2 hours during business hours
- If a broker asks about the partner program, provide the revenue share details (15% recurring, $44.85/mo per client at $299/mo)
- If a broker asks about pricing, direct them to getfileflo.com/pricing or mention the 14-day free trial
- Mark threads as read after processing using `mark_thread_as_read`
