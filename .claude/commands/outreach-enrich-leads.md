# /outreach-enrich-leads

Deep-enrich leads with verified contact data, apply SIC-based filtering, and route each lead to the correct campaign.

## Campaign Routing Table

Every enriched lead MUST be routed to one of these three campaigns based on their industry. Never mix industries into the wrong campaign.

| Campaign | Instantly ID | Target ICP |
|---|---|---|
| **Direct Operators** | `ba7dd34b-e415-472c-9c3e-fac2d88f6d3d` | Trucking carriers / motor freight companies |
| **OSHA Contractors** | `2b9057f9-26dc-40dc-b801-7e607452bc52` | GCs, excavators, pavers, specialty contractors |
| **Freight Brokers & 3PLs** | `d87311e5-15f1-4804-b3d9-0dcee8e1dae7` | Freight brokers, 3PLs, logistics intermediaries |

---

## Instructions

### Step 1: Identify Leads to Enrich

Ask the user for:
- Which leads to enrich (from `/outreach-source-leads` output, or specific names/companies)
- Enrichment depth: **basic** (Apollo only) or **full** (Apollo + web research)

### Step 2: Apollo Enrichment

For each lead, call `apollo_people_match` with:
- `first_name`, `last_name`, `organization_name` (from source data)
- `domain` (if available from source data)

Extract from the response:
- `email` + `email_status` (must be `"verified"`)
- `organization.email_domain_catchall` (if `true` → **SKIP**)
- `organization.sic_codes[]` → primary routing signal
- `organization.primary_domain` → for domain mismatch check
- Email domain (left of @) must match `primary_domain` → if mismatch → **SKIP**

### Step 3: SIC-Based Campaign Routing

**Golden rule: SIC codes are required to auto-route. Keywords alone are never sufficient to route a lead — they are hints only, shown in the UNCLEAR table to help the user decide quickly.**

Apply routing in this exact order:

---

#### 🔴 HARD SKIP — Never upload, regardless of anything else
| Trigger | Reason |
|---|---|
| `email_domain_catchall: true` | Whole domain catches all mail — undeliverable |
| Email domain ≠ org `primary_domain` | Domain mismatch — wrong person or bad data |
| `email_status` ≠ `"verified"` | Unverified email — bounce risk |

---

#### 🚫 DEAD-END SKIP — Wrong industry, no campaign for these
| SIC | Industry | Reason |
|---|---|---|
| 4225 | Warehousing/storage | Not a compliance fit for any campaign |
| 4412 | Deep sea/coastal water transport | Not FMCSA regulated |
| 4119 | Local/suburban transit, charter buses | Not carrier fleet fit |
| 6141 | Personal credit/factoring companies | Wrong industry entirely |
| 4512 | Air transportation, scheduled | FAA regulated, not FMCSA/OSHA |
| 4522 | Air transportation, nonscheduled | FAA regulated, not FMCSA/OSHA |

---

#### ✅ → Direct Operators campaign (`ba7dd34b-e415-472c-9c3e-fac2d88f6d3d`)
**Requires: SIC code present AND in the approved list below.**

| SIC | Industry |
|---|---|
| 4212 | Local/short-haul trucking, no air |
| 4213 | Trucking, except local |
| 4215 | Courier services, except by air |
| 4214 | Local trucking with storage |

If no SIC codes returned → **UNCLEAR** (do not auto-route, even if company name contains "trucking").

---

#### 🏗️ → OSHA Contractors campaign (`2b9057f9-26dc-40dc-b801-7e607452bc52`)
**Requires: SIC code present AND in the approved list below.**

| SIC | Industry |
|---|---|
| 1521 | General building contractors — residential |
| 1531 | Operative builders |
| 1541 | General building contractors — industrial |
| 1542 | General building contractors — commercial |
| 1611 | Highway and street construction |
| 1731 | Electrical work |
| 1741 | Masonry, stonework, tile setting |
| 1751 | Carpentry work |
| 1761 | Roofing, siding, sheet metal |
| 1771 | Concrete work |
| 1781 | Water well drilling |
| 1791 | Structural steel erection |
| 1794 | Excavation work |
| 1795 | Wrecking and demolition |
| 1796 | Installation of building equipment |
| 1799 | Special trade contractors, NEC |

If no SIC codes returned → **UNCLEAR** (do not auto-route, even if company name contains "construction").

---

#### 🔗 → Freight Brokers & 3PLs campaign (`d87311e5-15f1-4804-b3d9-0dcee8e1dae7`)
**Requires: SIC code present AND in the approved list below.**

| SIC | Industry |
|---|---|
| 4731 | Freight transportation arrangement |
| 4783 | Packing and crating |
| 7389 | Services to buildings/trade (3PLs often listed here) |
| 4215 | Courier (if large operation, not small fleet) |

If no SIC codes returned → **UNCLEAR** (do not auto-route, even if company name contains "logistics").

---

#### ⚠️ → UNCLEAR (manual review — do not upload)
A lead goes to UNCLEAR if ANY of these are true:
- Apollo returned no SIC codes for the company
- SIC codes returned but none match any campaign's approved list
- Industry listed in Apollo is ambiguous (e.g., "transportation" with no further detail)

**When reporting UNCLEAR leads, include a "Likely Route" column using keyword hints to help the user decide fast:**

| Keyword hint in company name | Likely Route |
|---|---|
| trucking, truck lines, motor freight, hauling | CARRIER |
| transport, transportation | CARRIER (but verify — brokers use this too) |
| construction, excavation, paving, grading, contractor | CONTRACTOR |
| logistics, freight management, 3pl, supply chain | BROKER_3PL |
| express, freight (alone) | Ambiguous — manual check required |
| No keyword match | No hint — full manual review |

The user reviews UNCLEAR leads and assigns a route or SKIP before anything is uploaded.

### Step 4: Catchall & Domain Mismatch Check

Before finalizing any KEEP decision:
1. Check `email_domain_catchall` — if `true` → **SKIP**
2. Extract domain from email address (e.g., `chad@acme.com` → `acme.com`)
3. Compare to `organization.primary_domain` — if they don't match → **SKIP**
4. Confirm `email_status === "verified"` — if not → **SKIP**

### Step 5: Web Enrichment (if "full" depth)

For Direct Operator leads, use `WebFetch` to check FMCSA SAFER data:
- URL: `https://safer.fmcsa.dot.gov/CompanySnapshot.aspx`
- Extract: inspection counts, OOS rates, violation types

For OSHA Contractor leads, use `WebSearch` to find:
- Recent OSHA citations in their state/city
- Industry-specific NEP (National Emphasis Program) activity

### Step 6: Build Personalization Variables

```json
{
  "firstName": "...",
  "lastName": "...",
  "companyName": "...",
  "email": "...",
  "website": "...",
  "title": "...",
  "campaign_route": "CARRIER | CONTRACTOR | BROKER_3PL | SKIP"
}
```

### Step 7: Output & CSV Parking Lot

**Do not stop enrichment progress waiting for UNCLEAR leads to be resolved.** Route what can be routed, park everything else to CSV, keep moving.

#### Routed leads — present in grouped tables for immediate upload:

**✅ CARRIERS → Direct Operators campaign**
Name | Email | Company | SIC | Title

**🏗️ CONTRACTORS → OSHA Contractors campaign**
Name | Email | Company | SIC | Title

**🔗 BROKERS/3PLs → Freight Brokers campaign**
Name | Email | Company | SIC | Title

#### Parked leads — write to CSV immediately, do NOT block progress:

**All SKIP and UNCLEAR leads go to `C:\Users\ChadGriffith\Downloads\leads_parking_lot.csv`**

Use this PowerShell script to append to the file (never overwrite — always append so the file accumulates across batches):

```powershell
$csvPath = 'C:\Users\ChadGriffith\Downloads\leads_parking_lot.csv'
$rows = @(
    [PSCustomObject]@{
        date        = (Get-Date -Format 'yyyy-MM-dd')
        batch       = 'B38'   # update each batch
        first_name  = 'Jane'
        last_name   = 'Smith'
        email       = 'jane@acmelogistics.com'
        company     = 'Acme Logistics'
        title       = 'Owner'
        website     = 'acmelogistics.com'
        sic         = ''
        reason      = 'UNCLEAR - no SIC, company name hints BROKER_3PL'
        likely_route = 'BROKER_3PL'
    }
    # ... add one row per parked lead
)
if (-not (Test-Path $csvPath)) {
    $rows | Export-Csv -Path $csvPath -NoTypeInformation
} else {
    $rows | Export-Csv -Path $csvPath -NoTypeInformation -Append
}
Write-Host "Parked $($rows.Count) leads to $csvPath"
```

CSV columns: `date, batch, first_name, last_name, email, company, title, website, sic, reason, likely_route`

`likely_route` values: `CARRIER`, `CONTRACTOR`, `BROKER_3PL`, `SKIP_DEAD`, `UNKNOWN`

The user reviews this file on their own schedule and either:
- Manually assigns a route → leads get added to the correct campaign in the next batch
- Marks as SKIP → leads are permanently discarded

#### After writing the CSV:

Report summary only — do not list all parked leads inline:
- ✅ X CARRIERS ready to upload
- 🏗️ X CONTRACTORS ready to upload
- 🔗 X BROKERS ready to upload
- 🅿️ X leads parked to `leads_parking_lot.csv` (SKIP: N, UNCLEAR: N)
- Credits used this session: X | Remaining: ~X

### Important Notes
- Each `apollo_people_match` call consumes 1 credit — batch carefully
- Budget: max 20-30 enrichments per session to conserve credits
- **Never upload a lead to the wrong campaign** — misrouted leads destroy reply rates
- **Never block enrichment progress waiting on UNCLEAR leads** — park and keep moving
- Verified emails are critical — previous campaign had 100% bounce from bad emails
- If a company has multiple contacts, only upload the most senior one (stop_for_company is enabled)
- The parking lot CSV accumulates forever — review it monthly with `/outreach-recycle-leads`
