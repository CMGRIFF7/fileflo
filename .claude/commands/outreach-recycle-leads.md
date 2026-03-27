# /outreach-recycle-leads

Identify leads eligible for re-engagement and manage lead recycling.

## Instructions

You are managing lead recycling for FileFlo's outreach pipeline to prevent list exhaustion and re-engage cold leads.

### Step 1: Determine Recycling Type

Ask the user which recycling mode to run:

- **no-reply-90**: Leads who completed the full 4-step sequence with no reply, 90+ days ago
- **opened-no-reply-45**: Leads who opened emails but never replied, 45+ days ago
- **geographic-refresh**: Re-target the same segment in new geographic areas
- **title-expansion**: Expand ICP to adjacent titles (risk manager, agency principal, etc.)

### Step 2: Find Eligible Leads

**For no-reply-90:**
Call `list_leads` with:
- `filter`: "FILTER_VAL_COMPLETED"
- `created_before`: 90 days ago
- Iterate through campaigns to find completed-no-reply leads

**For opened-no-reply-45:**
Call `list_leads` with:
- `filter`: "FILTER_VAL_CONTACTED"
- `created_before`: 45 days ago
- Cross-reference with campaign analytics for opens without replies

### Step 3: Filter Out Exclusions

Remove any leads with:
- `lt_interest_status`: -1 (not interested) or -2 (do not contact)
- Previously bounced emails
- Previously unsubscribed
- Already in an active campaign

### Step 4: Create Re-engagement Campaign

Use DIFFERENT messaging than the original sequence. The lead already saw the first approach.

**Re-engagement Template (Trucking):**

Step 1 | Subject: `compliance update`
```html
<p>Hi {{firstName}},</p>

<p>We connected a few months back about DOT compliance for your trucking clients. Wanted to share a quick update.</p>

<p>Since then, we have helped 50+ brokers run compliance audits across their book. The average broker finds $200K+ in hidden penalty exposure on their first scan.</p>

<p>We also launched a broker partner program with 15% recurring revenue share for every client referral.</p>

<p>Worth revisiting?</p>

<p>{{senderFirstName}}</p>
```

**Re-engagement Template (OSHA):**

Step 1 | Subject: `safety compliance update`
```html
<p>Hi {{firstName}},</p>

<p>Reaching back out with some news. OSHA has been increasing inspections across construction and manufacturing this quarter.</p>

<p>Since we last connected, we have helped brokers automate OSHA compliance tracking for their clients. The brokers who use us tell us it makes renewal conversations easier because their clients can prove compliance.</p>

<p>Would a quick update call make sense?</p>

<p>{{senderFirstName}}</p>
```

Use only 2 steps for re-engagement (not 4) — these leads have already heard from you.

### Step 5: Import and Launch

Call `create_campaign` with re-engagement copy.
Call `add_leads_to_campaign_or_list_bulk` with `skip_if_in_campaign: true`.
Assign sender accounts and activate.

### Step 6: Geographic/Title Expansion

**For geographic-refresh:**
Identify states NOT yet targeted in previous batches. Suggest next batch of states:
- Tier 2 states: Michigan, Missouri, Virginia, New Jersey, Arizona, Washington, Wisconsin, Minnesota, Maryland, Louisiana

**For title-expansion:**
Suggest adjacent titles to add to Apollo searches:
- "risk manager"
- "agency principal"
- "agency owner"
- "commercial lines manager"
- "safety director"
- "loss control specialist"
- "surety bond specialist"

### Step 7: Output Report

```
=== LEAD RECYCLING REPORT ===
Date: [date]

Recycling Mode: [selected mode]

Eligible Leads Found: [N]
Excluded (do not contact): [N]
Excluded (already active): [N]
Available for Re-engagement: [N]

New Campaign Created: [campaign name/ID]
Leads Imported: [N]

Geographic Coverage:
  States exhausted: [list]
  States available: [list]
  Recommended next batch: [states]

Title Coverage:
  Titles exhausted: [list]
  Titles available: [list]
```

### Important Notes
- NEVER re-contact leads classified as "not interested" or "unsubscribe"
- Minimum 90-day gap for full-sequence-completed leads
- Minimum 45-day gap for opened-but-no-reply leads
- Re-engagement sequences should be 2 steps max (not the full 4)
- Use entirely different subject lines and opening hooks
- Track recycled leads separately — their reply rates will be lower than fresh leads (target 3-5% vs 10%+)
- Monthly cadence for recycling: run this on the first Monday of each month
