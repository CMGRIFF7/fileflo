# FMCSA Signal Hub — Design Spec
**Date:** 2026-03-26
**Goal:** 50 closed sales/week by reaching trucking owners at their highest-pain moment using multiple FMCSA compliance signals, a stacked contact-finding chain, and four segmented Instantly campaigns.

---

## 1. Overview

The current pipeline processes ~200 carriers per run (Tue/Thu), pulls only OOS inspection data, finds contacts via Apollo only (1% yield), and uploads to one campaign. That caps output at ~1-2 contacts per run.

This redesign replaces it with a unified **FMCSA Signal Hub** that:
- Pulls from four FMCSA signals simultaneously
- Enriches each carrier with CSA scores, safety rating, fleet size, and violation history
- Finds owner contacts via a stacked chain (web search → domain → Apollo → email pattern → verify)
- Routes leads to the right campaign based on signal priority
- Runs twice daily Mon–Fri at 7am and 1pm
- Tracks processed carriers to avoid re-work

Target: **~1,200 contacts/week → ~7–8 closes/week from this pipeline**. Combined with DOT consultant, direct operator, and insurance broker campaigns already running, total target is 50 closes/week across all channels.

---

## 2. Campaign Map

| Campaign | Instantly ID | Signal | Daily Limit |
|---|---|---|---|
| FMCSA Violation Targets — Direct | `b514c694-b372-4d89-8b93-6ed325571963` | OOS violations | 1,500 |
| FMCSA CSA Score Alert | `53b6c3d3-e4d6-4067-be6e-87542f1be716` | CSA score above threshold | 1,500 |
| FMCSA Safety Rating Alert | `a4f77f6e-3033-4db0-8b1e-f128b5bfbdd6` | Conditional/Unsatisfactory rating | 1,500 |
| FMCSA Violation History Pattern | `8f41f5d5-a3f8-41f2-9143-b01bfa5bdc8b` | 3+ violations in 12 months | 1,500 |

**Note:** CSA, Safety Rating, and Violation History campaigns are currently in Draft status with a 50/day limit. They must be activated and their daily limits raised to 1,500 before the pipeline goes live.

---

## 3. FMCSA Data Sources

### 3a. Socrata Inspections (OOS Signal)
- **URL:** `https://data.transportation.gov/resource/fx4q-ay7w.json`
- **Filter:** Any inspection in last 30 days, `insp_interstate = 'Y'`
- **OOS tag:** `oos_total > 0` → routes to OOS campaign
- **Non-OOS:** Still pulled for CSA/safety rating enrichment and other signals
- **Pool size:** ~23,000+ unique carriers per 30-day window

### 3b. Socrata Violations (Violation History Signal)
- **URL:** `https://data.transportation.gov/resource/876r-jsdb.json`
- **Filter:** Last 12 months, group by `dot_number`, keep carriers with 3+ violations
- **Variables captured:** `violationCount`, `timeframe` (e.g. "12 months")
- **Pool:** Overlaps with inspections but catches carriers with non-OOS violation patterns

### 3c. QCMobile Enrichment (Fleet Filter + Safety Rating Signal)
- **URL:** `https://mobile.fmcsa.dot.gov/qc/services/carriers/{dot}?webKey=ea050d55fc6f7368ffa7e575d6b021e87d60fea0`
- **Returns:** `legalName`, `totalPowerUnits`, `statusCode`, `phyState`, `phyCountry`, `safetyRating`, `phone`
- **Fleet filter:** Keep only carriers with `totalPowerUnits` 2–50, `statusCode = A`, US country
- **Safety rating tag:** Carriers with `safetyRating = Conditional or Unsatisfactory` → tagged for Safety Rating campaign
- **Phone captured:** Stored for carriers where no email is found

### 3d. FMCSA SMS Scrape (CSA Score Signal)
- **URL per carrier:** `https://ai.fmcsa.dot.gov/SMS/Carrier/{dot}/Overview.aspx`
- **Scraped fields:** CSA score per BASIC (Unsafe Driving, HOS, Driver Fitness, Controlled Substances, Vehicle Maintenance, Hazmat, Crash Indicator)
- **Tag:** Carrier flagged for CSA campaign if any BASIC score exceeds intervention threshold
- **Intervention thresholds:** Unsafe Driving/HOS/Crash: 65 | Driver Fitness/Substances/Maintenance/Hazmat: 80
- **Variables captured:** `csaCategory` (highest BASIC above threshold), `csaScore`
- **Rate limiting:** 1s delay between requests, scrape in parallel with QCMobile enrichment

---

## 4. Pipeline Phases

### Phase 1 — Signal Collection (parallel, daily 7am + 1pm)

Run both Socrata pulls simultaneously:
1. Pull last 30 days of inspections from `fx4q-ay7w` — all interstate inspections
2. Pull last 12 months of violations from `876r-jsdb` — group by DOT, count violations

Merge all DOT numbers. Tag each DOT with which raw signals triggered it (`oos`, `violation_history`). Deduplicate.

**Batch size per run:** Up to 1,000 unique DOTs after dedup, selected by most recent inspection date first (newest violations = hottest leads).

### Phase 2 — Cross-Run Deduplication

Before enrichment, check `memory/processed-dots.json`:
```json
{ "dot_number": "488105", "processed_date": "2026-03-26", "campaign_id": "b514c694" }
```
Skip any DOT processed within the last 90 days. This prevents re-processing carriers already in the email sequence and stops burning QCMobile/SMS API calls on known contacts.

Remaining DOTs proceed to enrichment.

### Phase 3 — QCMobile + SMS Enrichment

For each remaining DOT (0.5s delay between QCMobile calls, 1s delay between SMS scrapes):

1. **QCMobile call** → get fleet size, status, state, legal name, safety rating, phone
2. **Filter out:** fleet outside 2–50, inactive, non-US, no state
3. **Tag:** `safety_rating` signal if Conditional or Unsatisfactory
4. **SMS scrape** → get CSA scores by BASIC, tag `csa` signal if any BASIC above threshold, capture `csaCategory` and `csaScore`

Result: each qualified carrier has a full signal tag set e.g. `["oos", "csa", "safety_rating"]`

### Phase 4 — Lead Scoring

Score each carrier before contact-finding. Process highest scores first when the daily contact cap is hit.

| Factor | Points |
|---|---|
| Unsatisfactory safety rating | +5 |
| OOS violation in last 7 days | +4 |
| Conditional safety rating | +3 |
| 3+ violations in 12 months | +2 |
| Any CSA BASIC above threshold | +1 per BASIC (max +4) |
| Fleet size 10–50 trucks | +2 |
| Fleet size 2–9 trucks | +1 |

Carriers scoring 7+ are processed first regardless of which campaign they'll go to.

### Phase 5 — Contact Finding (stacked)

For each scored carrier, run the following chain in order. Stop at the first verified result.

**Step 1 — Web search**
Query: `"{legal_name}" "{city}" "{state}" trucking`
Use the WebSearch MCP tool. Take the first result domain that is not in the skip list: `safer.fmcsa.dot.gov`, `ai.fmcsa.dot.gov`, `data.transportation.gov`, `yellowpages.com`, `yelp.com`, `manta.com`, `dnb.com`, `bizapedia.com`, `opencorporates.com`, `linkedin.com`, news domains (`.com/news`, `.com/article`). If no clean domain found, skip to Step 3.

**Step 2 — Apollo by domain**
Call `apollo_mixed_people_api_search` with:
- `q_organization_domain: domain`
- `person_titles: ["owner", "president", "ceo", "founder", "principal", "general manager"]`
- `email_status: ["verified"]`
Take first verified result.

**Step 3 — Email pattern fallback**
Try in order: `owner@domain`, `firstname@domain`, `info@domain`, `contact@domain`
Run each through Instantly's `verify_email` tool. Take first that returns verified + non-catchall.

**Step 4 — No contact found**
Store the carrier's phone number in `memory/phone-only-carriers.json` for future SMS/manual outreach.

Target yield: 35–45% of qualified carriers.

### Phase 6 — Signal Priority & Campaign Routing

If a carrier qualifies for multiple signals, route to the **single highest-priority campaign** only. `skip_if_in_workspace: true` enforces deduplication as a backstop.

Priority order (highest to lowest):
```
1. Safety Rating (Unsatisfactory or Conditional) → a4f77f6e
2. OOS Violation                                 → b514c694
3. Violation History Pattern (3+ violations)     → 8f41f5d5
4. CSA Score Above Threshold                     → 53b6c3d3
```

Custom variables per campaign:

| Campaign | Variables |
|---|---|
| OOS | `violationDate`, `violationLocation`, `violationType`, `oosCount`, `fleetSize`, `dotNumber`, `state`, `title` |
| CSA | `csaCategory`, `csaScore`, `fleetSize`, `dotNumber`, `state`, `title` |
| Safety Rating | `safetyRating`, `fleetSize`, `dotNumber`, `state`, `title` |
| Violation History | `violationCount`, `timeframe`, `fleetSize`, `dotNumber`, `state`, `title` |

### Phase 7 — Logging

After each run, append to `memory/CURRENT-STATE-AUDIT.md`:
- Run timestamp and which run (AM/PM)
- Carriers pulled per signal source
- DOTs skipped (seen-DOTs log)
- Carriers qualified after fleet filter
- Contacts found (yield %)
- Leads uploaded per campaign
- Phone-only carriers stored
- Errors or NEEDS MANUAL REVIEW flags

---

## 5. Scheduled Task Structure

| Task | Schedule | Description |
|---|---|---|
| `fmcsa-signal-hub-am` | Mon–Fri 7am CT | Full pipeline run, 1,000 carrier batch |
| `fmcsa-signal-hub-pm` | Mon–Fri 1pm CT | Full pipeline run, next 1,000 carrier batch |

The existing `fmcsa-weekly-lead-upload` task (Tue/Thu) is **replaced** by these two tasks.

---

## 6. Volume Math

| Metric | Value |
|---|---|
| Carriers processed per run | 1,000 |
| Runs per week | 10 (2x daily, Mon–Fri) |
| Gross carriers per week | 10,000 |
| After seen-DOTs skip (~60% new) | 6,000 |
| After fleet filter (~50% pass) | 3,000 |
| Contact yield (35–45%) | ~1,200 contacts/week |
| Reply rate (5%) | 60 replies |
| Positive reply rate (50%) | 30 positive |
| Close rate (25%) | **~7–8 closes/week** |

To materially increase closes from this pipeline beyond 7–8/week, the primary lever is contact yield — moving from 35% to 55%+ would roughly double output without changing carrier volume. The remaining closes/week come from DOT consultant, direct operator, and insurance broker campaigns already running.

---

## 7. Files & Memory

| File | Purpose |
|---|---|
| `memory/processed-dots.json` | DOT numbers seen in last 90 days + campaign routed to |
| `memory/phone-only-carriers.json` | Carriers with phone but no email found |
| `memory/CURRENT-STATE-AUDIT.md` | Run log appended after every run |
| `.claude/scheduled-tasks/fmcsa-signal-hub-am/SKILL.md` | AM scheduled task skill |
| `.claude/scheduled-tasks/fmcsa-signal-hub-pm/SKILL.md` | PM scheduled task skill |

The existing `fmcsa-weekly-lead-upload` task and skill file are deprecated by this system.

---

## 8. Open Questions / Phase 2

- **SMS scraping reliability:** The FMCSA SMS page may have bot protection or rate limits. If scraping fails consistently, CSA scores can be approximated by counting violations per BASIC category from the Socrata violations dataset (proxy, not exact).
- **Phone outreach:** `memory/phone-only-carriers.json` is write-only in phase 1. A future skill can process this list for SMS or manual call campaigns once the email pipeline is proven.
- **Daily limit increases:** CSA, Safety Rating, and Violation History campaigns must be manually activated in Instantly and daily limits raised from 50 → 1,500 before the pipeline launches.
