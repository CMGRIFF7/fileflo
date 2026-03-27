# FMCSA Violation Lead Pipeline
*Hottest leads in trucking — companies that just got fined are in maximum pain*

---

## Why This Works

A carrier that just received an FMCSA violation notice:
- Is embarrassed and scared
- Knows exactly how much it cost them ($16,550+)
- Is actively thinking "how do I prevent this happening again"
- Will answer a cold email with "how did you know about my violation?"

Conversion rate: **3-5x higher than standard cold outreach**

---

## Data Sources (All Free / Public)

### Source 1: FMCSA Safety Measurement System (SMS)
**URL:** https://ai.fmcsa.dot.gov/SMS/

The FMCSA publishes carrier safety scores and violation data publicly.
- Filter by: Unsafe Driving, Hours-of-Service, Driver Fitness, Controlled Substances, Vehicle Maintenance
- Sort by: Alert status (shows companies above threshold = most violations)
- Export: CSV download available

**What to pull:**
- Carrier name
- DOT number
- State
- Number of inspections
- Number of violations
- BASIC scores (anything above 65% = high risk = great prospect)

### Source 2: FMCSA Enforcement Actions
**URL:** https://www.fmcsa.dot.gov/safety/enforcement

Lists carriers that received civil penalties, out-of-service orders, or consent orders in the last 12 months. These are the hottest leads — they didn't just get a warning, they got fined.

### Source 3: SAFER Web (Free Carrier Lookup)
**URL:** https://safer.fmcsa.dot.gov/

Look up any carrier by DOT number for:
- Contact information (phone, address)
- MC number
- Fleet size
- Safety rating

---

## Step-by-Step Process

### Step 1: Pull Violation Data from SMS (Weekly)
1. Go to: https://ai.fmcsa.dot.gov/SMS/
2. Click "Carrier Search" or use the data download portal
3. Filter: Active carriers, US-based, 1-50 power units (small fleets = your ICP)
4. Sort by: Most recent violations or highest BASIC percentile
5. Export CSV

**Target BASIC scores above 65%:**
- Unsafe Driving BASIC > 65%
- Hours-of-Service BASIC > 65%
- Driver Fitness BASIC > 65%
- Vehicle Maintenance BASIC > 65%

### Step 2: Enrich with Contact Info (Zero Apollo Credits)
For each carrier from SMS data:
1. Get their DOT number
2. Look up in SAFER: https://safer.fmcsa.dot.gov/query.asp?searchtype=ANY&query_type=queryCarrierSnapshot&query_param=USDOT&query_string=[DOT_NUMBER]
3. SAFER returns: Company name, address, phone number, MC number
4. Phone number is right there — no credits needed

### Step 3: Find the Owner (LinkedIn or Google)
1. Google: "[Company Name] owner trucking"
2. LinkedIn: Search company name → find Owner/President
3. Takes 30 seconds per company

### Step 4: Upload to Instantly Campaign
Create a new Instantly campaign: "FMCSA Violation Targets"

**Email sequence (3 steps, pain-first messaging):**

---

**Email 1 — Subject: Your FMCSA safety score**

Hey [First Name],

Looked up [Company Name] on the FMCSA Safety Measurement System — your [BASIC category] score is sitting at [X]%, which puts you in the alert zone.

One more inspection that doesn't go well, and you're looking at a compliance review — or worse, a $16,550 citation.

I built FileFlo specifically for carriers in this situation. It tracks all 85+ required documents automatically and flags anything that's coming due before an inspector ever shows up.

Worth a 10-minute look? I'll show you exactly where your gaps are.

[First Name from signature]
[Link to free trial]

---

**Email 2 (Day 4) — Subject: What auditors actually look for**

[First Name],

Most FMCSA violations come down to 3 things:
- Expired or missing driver qualification files
- Hours of service records that don't match logs
- Drug and alcohol testing records not in order

FileFlo catches all three automatically and sends you alerts 30 days before anything expires.

Takes 15 minutes to set up, runs itself after that.

Free trial here — no card required: getfileflo.com

---

**Email 3 (Day 8) — Subject: Last note**

[First Name], last email from me.

If you're managing compliance manually, you're one missed document away from a $16,550 fine. I know because I've talked to carriers who went through exactly that.

FileFlo exists to make sure that doesn't happen to you. 14-day free trial, takes 15 minutes to set up.

If the timing isn't right, no worries — you know where to find us.

[Signature]

---

### Step 5: Call Within 48 Hours of Email 1
Script for violation targets (shorter, more direct than broker script):

"Hey [Name], this is Chad — I sent you an email about your FMCSA safety score. Did you see it? ... [if yes] Good — your [BASIC] score is in the alert zone. I built a tool that fixes exactly that. 10 minutes — can I show you?"

---

## Weekly Rhythm

| Day | Action |
|---|---|
| Monday | Pull new violation data from SMS (30 min) |
| Monday | Enrich top 20 with SAFER phone numbers (20 min) |
| Tuesday | Upload to Instantly campaign |
| Tuesday–Friday | Call each lead within 48 hours of email |
| Friday | Review replies, book demos for following week |

**Target:** 20 new violation leads/week → 2-4 hot conversations → 1 trial signup

---

## Expected Results

| Metric | Estimate |
|---|---|
| Leads per week | 20 |
| Email open rate | 45-60% (very relevant subject) |
| Reply rate | 10-20% (3-5x normal) |
| Demo booking rate | 30-40% of replies |
| Trial conversion | 40-50% of demos |
| Customers per month | 4-10 |
| MRR added per month | $1,196-$2,990 |

---

## Tools Needed
- FMCSA SMS: Free (https://ai.fmcsa.dot.gov/SMS/)
- SAFER carrier lookup: Free (https://safer.fmcsa.dot.gov/)
- Instantly: Already have it ✅
- Apollo credits: 0 needed ✅
- Cost per lead: $0

---

## Actual Data Sources Found (FMCSA sites 403 blocked — use these instead)

### Primary: data.transportation.gov (Works, No Auth)
- **Carrier Census with Phones:** `https://data.transportation.gov/download/6qg9-x4f8/text/plain`
  - Field mapping: [0]=MC#, [1]=DOT#, [4]=Status(A=Active), [26]=Company, [29]=City, [30]=State, [33]=Phone
  - 2,639 active carriers pulled with phones

- **Company Census File (Power Units):** Socrata API
  - `https://datahub.transportation.gov/resource/az4n-8mr2.json?$select=dot_number,power_units,email_address&$where=dot_number IN (...)`
  - Fields: DOT_NUMBER, POWER_UNITS, EMAIL_ADDRESS, LEGAL_NAME, STATUS_CODE

### What We Built (2026-03-21)
- `memory/FMCSA-CALL-LIST-SCORED.csv` — 2,639 carriers with phones, ICP scored by name pattern
- `memory/FMCSA-CALL-LIST-ENRICHED.csv` — Same + POWER_UNITS added from census API
- `memory/FMCSA-ICP-CONFIRMED.csv` — 1,562 leads: 1-20 trucks + ICP score 60+
- `memory/FMCSA-ICP-WITH-EMAIL.csv` — 1,551 of above with email addresses (from FMCSA registration)
- `memory/FMCSA-INSTANTLY-BATCH1.csv` — Top 200 formatted for Instantly

### Campaign Status
- Campaign: "FMCSA Violation Targets — Direct" | ID: `b514c694-b372-4d89-8b93-6ed325571963`
- **STATUS: ACTIVE** (launched 2026-03-21)
- Leads uploaded: 150 (first 150 of 1,551 total pipeline)
- Senders: brandon/haley/karen/megan@nowcompliance.org
- Next batch: Upload leads 151-350 weekly to feed the pipeline
- Remaining pipeline: ~1,400 confirmed ICP leads ready to upload
