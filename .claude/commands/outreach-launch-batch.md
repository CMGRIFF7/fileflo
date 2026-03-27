# /outreach-launch-batch

Upload a batch of enriched, pre-routed leads to the correct Instantly campaign.

## Active Campaign Registry

These are the three live campaigns. Always upload to the correct one based on lead industry. Never mix.

| Campaign | ID | ICP | Status |
|---|---|---|---|
| **Direct Operators** | `ba7dd34b-e415-472c-9c3e-fac2d88f6d3d` | Trucking carriers (SIC 4212/4213) | Active |
| **OSHA Contractors** | `2b9057f9-26dc-40dc-b801-7e607452bc52` | GCs, excavators, pavers (SIC 15xx) | Active |
| **Freight Brokers & 3PLs** | `d87311e5-15f1-4804-b3d9-0dcee8e1dae7` | Freight brokers, logistics (SIC 4731/7389) | Active |
| **Insurance Brokers — Trucking** | `1e5d0838-7632-47cf-a29a-11c3259b5a9a` | Retail trucking/commercial auto insurance brokers, 1-50 employees | Active |

---

## Instructions

### Step 1: Confirm Routing from Enrichment

Leads must have been processed by `/outreach-enrich-leads` first and have a `campaign_route` value:
- `CARRIER` → Direct Operators
- `CONTRACTOR` → OSHA Contractors
- `BROKER_3PL` → Freight Brokers & 3PLs
- `SKIP` / `UNCLEAR` → Do not upload — flag for review

If any lead is missing a `campaign_route`, run `/outreach-enrich-leads` on them first.

### Step 2: Pre-Upload Filter (Final Gate)

Before uploading, re-apply these hard blocks one final time:

| Check | Rule |
|---|---|
| Catchall domain | Block — `email_domain_catchall: true` |
| Domain mismatch | Block — email domain ≠ org primary_domain |
| Unverified email | Block — `email_status ≠ "verified"` |
| Duplicate company | Block — if another contact from same company already in that campaign (`stop_for_company` is ON) |
| SIC 4731 in wrong campaign | Block — 4731 leads must go to Broker/3PL, never to Direct Operators |
| Construction SIC in Direct Operators | Block — SIC 15xx leads must go to OSHA Contractors |

Log every blocked lead with reason before proceeding.

### Step 3: Verify Sender Accounts

Call `list_accounts` to verify:
- At least 3 accounts are active (status: 1)
- No error statuses
- Accounts have been warmed 2+ weeks

### Step 4: Upload Leads by Campaign Group

For each campaign group, call `add_leads_to_campaign_or_list_bulk`:
- `campaign_id`: the correct campaign ID from the registry above
- `skip_if_in_campaign`: true (prevent duplicates)
- `verify_leads_on_import`: true
- Leads array: `email`, `first_name`, `last_name`, `company_name`, `website`, `title`

Upload each group separately — one call per campaign. Never combine groups.

### Step 5: Confirm Upload

Report per campaign:
- Campaign name + ID
- Leads uploaded
- Leads blocked (with reasons)
- Running total leads in that campaign
- Next send window

---

## Campaign Settings Reference

All three campaigns are already configured with these settings. Do NOT change them:

| Setting | Value | Reason |
|---|---|---|
| `text_only` | `true` | Maximum deliverability |
| `track_opens` | `false` | CRITICAL — enables spam filters |
| `track_clicks` | `false` | CRITICAL — enables spam filters |
| `stop_on_reply` | `true` | Stop sequence on any reply |
| `stop_on_auto_reply` | `true` | Stop on OOO/bounce replies |
| `stop_for_company` | `true` | One contact per company at a time |
| `insert_unsubscribe_header` | `true` | Deliverability compliance |
| `daily_limit` | 30/account | Sender reputation protection |
| `email_gap` | 10 min | Avoid burst sending |
| `timing` | 8:30–13:00 CT | Peak engagement window |
| `days` | Mon–Fri | Full week coverage |

If a new campaign ever needs to be created, use `update_campaign` after creation to apply ALL of the above settings.

---

## Email Sequence Templates

### TRUCKING SEGMENT - VARIANT A

**Step 1** | Subject: `dot audit season`
```html
<p>Hi {{firstName}},</p>

<p>FMCSA just ramped up compliance reviews for Q2. A couple of your trucking clients might be sitting on missing driver qualification files right now.</p>

<p>One missing DOT medical card = $16,550 per driver. For a 20-truck fleet, that is $331,000 in exposure before the auditor even looks at HOS logs.</p>

<p>We built FileFlo to catch exactly this. It auto-classifies CDLs, med cards, MVRs, and clearinghouse docs, then flags gaps before the audit letter shows up.</p>

<p>Would it make sense to see a 3-minute demo this week?</p>

<p>Best,<br>{{senderFirstName}}</p>
```

**Step 2** | Subject: (same thread)
```html
<p>{{firstName}}, wanted to share something useful regardless.</p>

<p>FMCSA fined carriers $2.1B in the last 18 months. The top 3 violations were all paperwork: missing medical certificates, expired MVRs, and incomplete drug testing docs.</p>

<p>We built a free compliance exposure calculator that shows brokers exactly where their clients are at risk. Takes 2 minutes.</p>

<p>Want me to send the link?</p>

<p>{{senderFirstName}}</p>
```

**Step 3** | Subject: (same thread)
```html
<p>{{firstName}}, one more thing.</p>

<p>We are building a broker partner program. Brokers who recommend FileFlo to clients get a revenue share on every account.</p>

<p>Think about it: your clients stay compliant, they see you as the one who saved them from six-figure fines, and you earn recurring income.</p>

<p>If that sounds interesting, let me walk you through it.</p>

<p>{{senderFirstName}}</p>
```

**Step 4** | Subject: (same thread)
```html
<p>{{firstName}}, I will not keep filling your inbox.</p>

<p>If DOT compliance is not a priority for your clients right now, no worries.</p>

<p>But if a client ever gets hit with a compliance review and you want a fast answer, FileFlo is at getfileflo.com. We do a 14-day free trial.</p>

<p>All the best,<br>{{senderFirstName}}</p>
```

### TRUCKING SEGMENT - VARIANT B

**Step 1** | Subject: `quick question`
```html
<p>Hi {{firstName}},</p>

<p>Quick question -- do any of your trucking clients still track DOT driver files in filing cabinets or spreadsheets?</p>

<p>We help brokers identify $100K+ in hidden penalty exposure across their book, then fix it before FMCSA knocks.</p>

<p>Worth a 3-minute look?</p>

<p>{{senderFirstName}}</p>
```

**Step 2** | Subject: (same thread)
```html
<p>Following up, {{firstName}}.</p>

<p>One of our broker partners discovered 47 missing driver docs across 6 clients last month. That was $776K in penalty exposure nobody knew about.</p>

<p>The fix took her clients 2 weeks with FileFlo auto-tracking everything.</p>

<p>If you have 10 minutes Thursday, I can show you what that looks like for your book.</p>

<p>{{senderFirstName}}</p>
```

**Steps 3-4**: Same as Variant A Steps 3-4.

### OSHA SEGMENT - VARIANT A

**Step 1** | Subject: `osha inspection season`
```html
<p>Hi {{firstName}},</p>

<p>OSHA announced 3 new National Emphasis Programs for 2026. Your construction and manufacturing clients are going to see more surprise inspections this year.</p>

<p>One serious violation = $16,550. One willful violation = $165,514. A single jobsite visit can stack 10+ citations.</p>

<p>We built FileFlo to track OSHA 300 logs, training certs, forklift licenses, and safety docs automatically. It flags gaps before the inspector does.</p>

<p>Would a 3-minute demo be useful?</p>

<p>{{senderFirstName}}</p>
```

**Step 2** | Subject: (same thread)
```html
<p>{{firstName}}, thought this would be relevant.</p>

<p>OSHA cited 35,000+ workplaces last year. The most common violations: missing training documentation, incomplete OSHA 300 logs, and expired safety certifications.</p>

<p>Our tool auto-classifies 85+ document types and maps them against 50+ regulations. Brokers use it to run compliance health checks on clients in minutes instead of days.</p>

<p>If you are curious, I can show you what it looks like for a typical 50-person contractor.</p>

<p>{{senderFirstName}}</p>
```

**Step 3** | Subject: (same thread)
```html
<p>{{firstName}}, last thought on this.</p>

<p>The brokers using FileFlo tell us the same thing: their renewal conversations got easier because clients can actually prove compliance now.</p>

<p>We also offer a partner program for brokers -- recurring revenue for every client you bring on.</p>

<p>Worth 10 minutes to explore?</p>

<p>{{senderFirstName}}</p>
```

**Step 4** | Subject: (same thread)
```html
<p>Hi {{firstName}}, closing the loop.</p>

<p>If timing is off, I completely understand. Just wanted to make sure you knew this exists for when a client calls about an OSHA inspection.</p>

<p>getfileflo.com -- 14-day free trial, no commitment.</p>

<p>Take care,<br>{{senderFirstName}}</p>
```

### OSHA SEGMENT - VARIANT B

**Step 1** | Subject: `construction season risk`
```html
<p>Hi {{firstName}},</p>

<p>Quick one -- are any of your workers comp clients still managing safety training records in binders or shared drives?</p>

<p>We help brokers surface hidden OSHA exposure across their book. Average client has $50K-$200K in gaps they do not know about.</p>

<p>Worth seeing?</p>

<p>{{senderFirstName}}</p>
```

**Step 2** | Subject: (same thread)
```html
<p>Hi {{firstName}}, following up.</p>

<p>A workers comp broker we work with ran our compliance scan on 4 clients. Found 23 expired OSHA training certs and 8 missing 300 logs.</p>

<p>She fixed everything in one afternoon and used the report to justify premium reductions at renewal.</p>

<p>I would love to show you the same workflow. 10 minutes this week?</p>

<p>{{senderFirstName}}</p>
```

**Steps 3-4**: Same as OSHA Variant A Steps 3-4.

---

## Important Notes
- NEVER enable open or click tracking — this was a key factor in the previous 100% spam block rate
- Always use `skip_if_in_campaign: true` to prevent duplicate sends
- Maximum 100 leads per campaign for best reply rates
- Verify sender accounts are healthy before assigning
- Campaigns should be named with segment, batch number, and date for tracking
