# FMCSA Signal Hub — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the Tue/Thu OOS-only pipeline with a daily Signal Hub that pulls four FMCSA signals, enriches with CSA scores + safety ratings, finds owner contacts via a stacked chain, and routes leads to four segmented Instantly campaigns.

**Architecture:** A Python script (`pipeline/fmcsa_hub.py`) handles Phases 1–4 (Socrata pulls, cross-run dedup, QCMobile enrichment, SMS scraping, lead scoring) and outputs a JSON file. Two Claude scheduled task SKILL.md files (AM + PM) read that JSON, run the contact-finding chain via MCP tools (WebSearch, Apollo, Instantly verify), upload to the right campaign, and write audit logs.

**Tech Stack:** Python 3 stdlib only (urllib, json, re, html.parser, argparse, datetime), FMCSA Socrata API, QCMobile API, FMCSA SMS page scrape, Apollo MCP, Instantly MCP, WebSearch MCP.

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `pipeline/fmcsa_hub.py` | Create | Phases 1–4: signal collection, dedup, enrichment, scoring, output |
| `pipeline/hub_output.json` | Auto-generated | Scored carriers ready for MCP contact-finding (not committed) |
| `memory/processed-dots.json` | Create | Cross-run dedup state: DOTs seen in last 90 days |
| `memory/phone-only-carriers.json` | Create | Carriers with phone but no email found |
| `memory/CURRENT-STATE-AUDIT.md` | Append | Run log after every pipeline execution |
| `C:\Users\ChadGriffith\.claude\scheduled-tasks\fmcsa-signal-hub-am\SKILL.md` | Create | AM scheduled task: runs Python script + MCP contact-finding + upload |
| `C:\Users\ChadGriffith\.claude\scheduled-tasks\fmcsa-signal-hub-pm\SKILL.md` | Create | PM scheduled task: same as AM, picks up next batch |
| `C:\Users\ChadGriffith\.claude\scheduled-tasks\fmcsa-weekly-lead-upload\SKILL.md` | Deprecate | Add deprecation notice, stop scheduling |

**Project root:** `C:\Users\ChadGriffith\Downloads\fileflo-f11afbf5-main (2)`
**Memory root:** `C:\Users\ChadGriffith\.claude\projects\C--Users-ChadGriffith-Downloads-fileflo-f11afbf5-main--2-\memory\`

---

## Task 1: Initialize Memory Files

**Files:**
- Create: `memory/processed-dots.json`
- Create: `memory/phone-only-carriers.json`

- [ ] **Step 1: Create processed-dots.json**

Create `C:\Users\ChadGriffith\.claude\projects\C--Users-ChadGriffith-Downloads-fileflo-f11afbf5-main--2-\memory\processed-dots.json` with content:
```json
{}
```

- [ ] **Step 2: Create phone-only-carriers.json**

Create `C:\Users\ChadGriffith\.claude\projects\C--Users-ChadGriffith-Downloads-fileflo-f11afbf5-main--2-\memory\phone-only-carriers.json` with content:
```json
[]
```

- [ ] **Step 3: Verify files exist**

```bash
python3 -c "
import json
with open(r'C:\Users\ChadGriffith\.claude\projects\C--Users-ChadGriffith-Downloads-fileflo-f11afbf5-main--2-\memory\processed-dots.json') as f:
    d = json.load(f)
print('processed-dots.json OK, entries:', len(d))

with open(r'C:\Users\ChadGriffith\.claude\projects\C--Users-ChadGriffith-Downloads-fileflo-f11afbf5-main--2-\memory\phone-only-carriers.json') as f:
    p = json.load(f)
print('phone-only-carriers.json OK, entries:', len(p))
"
```
Expected output:
```
processed-dots.json OK, entries: 0
phone-only-carriers.json OK, entries: 0
```

---

## Task 2: Create pipeline/fmcsa_hub.py — Phases 1 & 2

**Files:**
- Create: `pipeline/fmcsa_hub.py`

- [ ] **Step 1: Create pipeline directory and fmcsa_hub.py with Phase 1 (signal collection)**

Create `C:\Users\ChadGriffith\Downloads\fileflo-f11afbf5-main (2)\pipeline\fmcsa_hub.py`:

```python
#!/usr/bin/env python3
"""
FMCSA Signal Hub — Pipeline Script
Phases 1-4: Signal Collection, Dedup, Enrichment, Scoring
Outputs pipeline/hub_output.json for Claude MCP contact-finding
"""
import argparse
import json
import os
import re
import time
import urllib.request
import urllib.parse
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser

# ── Constants ────────────────────────────────────────────────────────────────
WEBKEY = "ea050d55fc6f7368ffa7e575d6b021e87d60fea0"

MEMORY_DIR = r"C:\Users\ChadGriffith\.claude\projects\C--Users-ChadGriffith-Downloads-fileflo-f11afbf5-main--2-\memory"
PROCESSED_DOTS_FILE = os.path.join(MEMORY_DIR, "processed-dots.json")
PHONE_ONLY_FILE = os.path.join(MEMORY_DIR, "phone-only-carriers.json")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = os.path.join(SCRIPT_DIR, "hub_output.json")

CAMPAIGN_IDS = {
    "safety_rating": "a4f77f6e-3033-4db0-8b1e-f128b5bfbdd6",
    "oos":           "b514c694-b372-4d89-8b93-6ed325571963",
    "violation_history": "8f41f5d5-a3f8-41f2-9143-b01bfa5bdc8b",
    "csa":           "53b6c3d3-e4d6-4067-be6e-87542f1be716",
}

PRIORITY_ORDER = ["safety_rating", "oos", "violation_history", "csa"]

CSA_THRESHOLDS = {
    "Unsafe Driving": 65,
    "HOS Compliance": 65,
    "Crash Indicator": 65,
    "Driver Fitness": 80,
    "Controlled Substances/Alcohol": 80,
    "Vehicle Maintenance": 80,
    "Hazardous Materials Compliance": 80,
}

# ── Phase 1: Signal Collection ────────────────────────────────────────────────
def collect_signals(batch_size=1000):
    """Pull Socrata inspections + violations. Return merged DOT list sorted by recency."""
    now = datetime.now(timezone.utc)
    cutoff_30  = (now - timedelta(days=30)).strftime("%Y%m%d")
    cutoff_365 = (now - timedelta(days=365)).strftime("%Y%m%d")

    # ── Inspections (last 30 days, all interstate) ──
    insp_where  = f"insp_date > '{cutoff_30}' AND insp_interstate = 'Y'"
    insp_select = "dot_number,insp_date,insp_carrier_name,insp_carrier_city,insp_carrier_state,oos_total"
    insp_url = (
        "https://data.transportation.gov/resource/fx4q-ay7w.json?"
        + "$where=" + urllib.parse.quote(insp_where)
        + "&$select=" + urllib.parse.quote(insp_select)
        + "&$order=" + urllib.parse.quote("insp_date DESC")
        + "&$limit=50000"
    )
    with urllib.request.urlopen(insp_url, timeout=30) as resp:
        insp_rows = json.loads(resp.read().decode("utf-8"))

    dots = {}
    for row in insp_rows:
        dot = row.get("dot_number", "").strip()
        if not dot:
            continue
        raw = str(row.get("insp_date", ""))[:8]
        try:
            readable = datetime.strptime(raw, "%Y%m%d").strftime("%B %d, %Y")
            ts       = datetime.strptime(raw, "%Y%m%d").isoformat()
        except Exception:
            readable = raw
            ts = "1970-01-01"

        oos = int(row.get("oos_total") or 0)

        if dot not in dots:
            dots[dot] = {
                "dot_number": dot,
                "carrier_name": row.get("insp_carrier_name", ""),
                "city": row.get("insp_carrier_city", ""),
                "state": row.get("insp_carrier_state", ""),
                "latest_inspection_date": readable,
                "latest_inspection_ts": ts,
                "signals": [],
                "oos_count": 0,
                "violation_count": 0,
                "violation_date": "",
                "violation_location": "",
                "violation_type": "",
            }
        else:
            # keep most recent
            if ts > dots[dot]["latest_inspection_ts"]:
                dots[dot]["latest_inspection_ts"] = ts
                dots[dot]["latest_inspection_date"] = readable

        if oos > 0 and "oos" not in dots[dot]["signals"]:
            dots[dot]["signals"].append("oos")
            dots[dot]["oos_count"] = oos
            dots[dot]["violation_date"] = readable
            dots[dot]["violation_location"] = row.get("insp_carrier_state", "")
            dots[dot]["violation_type"] = "out-of-service"

    print(f"Phase 1a: {len(insp_rows)} inspection rows → {len(dots)} unique DOTs")

    # ── Violations (last 12 months, 3+ per carrier) ──
    try:
        viol_where  = f"inspdate > '{cutoff_365}'"
        viol_select = "dotnum,inspdate"
        viol_url = (
            "https://data.transportation.gov/resource/876r-jsdb.json?"
            + "$where=" + urllib.parse.quote(viol_where)
            + "&$select=" + urllib.parse.quote(viol_select)
            + "&$limit=100000"
        )
        with urllib.request.urlopen(viol_url, timeout=30) as resp:
            viol_rows = json.loads(resp.read().decode("utf-8"))

        viol_counts = {}
        for row in viol_rows:
            dot = str(row.get("dotnum", "")).strip()
            if dot:
                viol_counts[dot] = viol_counts.get(dot, 0) + 1

        added = 0
        for dot, count in viol_counts.items():
            if count >= 3:
                if dot not in dots:
                    dots[dot] = {
                        "dot_number": dot,
                        "carrier_name": "",
                        "city": "",
                        "state": "",
                        "latest_inspection_date": "",
                        "latest_inspection_ts": "1970-01-01",
                        "signals": [],
                        "oos_count": 0,
                        "violation_count": count,
                        "violation_date": "",
                        "violation_location": "",
                        "violation_type": "",
                    }
                    added += 1
                if "violation_history" not in dots[dot]["signals"]:
                    dots[dot]["signals"].append("violation_history")
                dots[dot]["violation_count"] = count

        print(f"Phase 1b: {len(viol_rows)} violation rows → {added} new DOTs added, violation_history tagged")
    except Exception as e:
        print(f"Phase 1b WARNING: violations pull failed: {e}")

    # Sort by recency, take top batch_size
    sorted_dots = sorted(dots.values(), key=lambda x: x["latest_inspection_ts"], reverse=True)
    result = sorted_dots[:batch_size]
    print(f"Phase 1 complete: {len(dots)} total unique DOTs, returning top {len(result)} by recency")
    return result
```

- [ ] **Step 2: Add Phase 2 (cross-run dedup) to fmcsa_hub.py**

Append to `pipeline/fmcsa_hub.py`:

```python
# ── Phase 2: Cross-Run Deduplication ─────────────────────────────────────────
def filter_seen_dots(carriers):
    """Skip DOTs processed in last 90 days."""
    cutoff = datetime.now() - timedelta(days=90)

    processed = {}
    if os.path.exists(PROCESSED_DOTS_FILE):
        with open(PROCESSED_DOTS_FILE) as f:
            try:
                processed = json.load(f)
            except json.JSONDecodeError:
                processed = {}

    fresh, skipped = [], 0
    for c in carriers:
        dot = c["dot_number"]
        if dot in processed:
            try:
                pd = datetime.fromisoformat(processed[dot].get("processed_date", "1970-01-01"))
                if pd > cutoff:
                    skipped += 1
                    continue
            except Exception:
                pass
        fresh.append(c)

    print(f"Phase 2: {skipped} DOTs skipped (seen ≤90 days), {len(fresh)} fresh")
    return fresh
```

- [ ] **Step 3: Verify Phase 1 + 2 work together**

```bash
cd "C:\Users\ChadGriffith\Downloads\fileflo-f11afbf5-main (2)" && python3 -c "
from pipeline.fmcsa_hub import collect_signals, filter_seen_dots
carriers = collect_signals(batch_size=10)
print('Collected:', len(carriers))
fresh = filter_seen_dots(carriers)
print('After dedup:', len(fresh))
for c in fresh[:2]:
    print(' -', c['dot_number'], c['carrier_name'], c['signals'])
"
```
Expected: prints 10 carriers collected, all 10 fresh (empty processed-dots.json), shows signals list.

- [ ] **Step 4: Commit**

```bash
cd "C:\Users\ChadGriffith\Downloads\fileflo-f11afbf5-main (2)"
git add pipeline/fmcsa_hub.py
git commit -m "feat: fmcsa signal hub - phase 1+2 signal collection and dedup"
```

---

## Task 3: Add Phase 3a — QCMobile Enrichment

**Files:**
- Modify: `pipeline/fmcsa_hub.py`

- [ ] **Step 1: Append Phase 3a to fmcsa_hub.py**

Append to `pipeline/fmcsa_hub.py`:

```python
# ── Phase 3a: QCMobile Enrichment ────────────────────────────────────────────
def enrich_qcmobile(carriers):
    """
    Call QCMobile per DOT. Filter fleet 2-50, active, US.
    Tag safety_rating signal if Conditional or Unsatisfactory.
    Capture phone number for fallback.
    """
    qualified = []
    for i, c in enumerate(carriers):
        dot = c["dot_number"]
        url = f"https://mobile.fmcsa.dot.gov/qc/services/carriers/{dot}?webKey={WEBKEY}"
        try:
            with urllib.request.urlopen(url, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            cd = data.get("content", {}).get("carrier", {})
            if not cd:
                time.sleep(0.5)
                continue

            # Fleet size filter
            try:
                units = int(cd.get("totalPowerUnits") or 0)
            except (ValueError, TypeError):
                units = 0
            if units < 2 or units > 50:
                time.sleep(0.5)
                continue

            # Country filter
            country = (cd.get("phyCountry") or cd.get("mailingCountry") or "").strip().upper()
            if country and country not in ("US", "USA", "UNITED STATES", "U.S.", "U.S.A."):
                time.sleep(0.5)
                continue

            # State filter
            state = (cd.get("phyState") or cd.get("mailingState") or c.get("state", "")).strip()
            if not state:
                time.sleep(0.5)
                continue

            safety_rating = (cd.get("safetyRating") or "").strip()
            phone = (cd.get("telephone") or cd.get("phone") or "").strip()
            legal_name = (cd.get("legalName") or c.get("carrier_name", "")).strip()
            city = (cd.get("phyCity") or c.get("city", "")).strip()

            c.update({
                "legal_name": legal_name,
                "state": state,
                "city": city,
                "power_units": units,
                "safety_rating": safety_rating,
                "phone": phone,
            })

            if safety_rating in ("Conditional", "Unsatisfactory"):
                if "safety_rating" not in c["signals"]:
                    c["signals"].append("safety_rating")

            qualified.append(c)
            if (i + 1) % 50 == 0:
                print(f"  QCMobile: {i+1}/{len(carriers)} checked, {len(qualified)} qualified so far")
        except Exception as e:
            pass  # Skip on timeout/error
        time.sleep(0.5)

    print(f"Phase 3a complete: {len(qualified)}/{len(carriers)} qualified (fleet 2-50, active, US)")
    return qualified
```

- [ ] **Step 2: Verify QCMobile enrichment runs on 5 carriers**

```bash
cd "C:\Users\ChadGriffith\Downloads\fileflo-f11afbf5-main (2)" && python3 -c "
from pipeline.fmcsa_hub import collect_signals, filter_seen_dots, enrich_qcmobile
carriers = collect_signals(batch_size=20)
fresh = filter_seen_dots(carriers)
qualified = enrich_qcmobile(fresh[:5])
print('Qualified:', len(qualified))
for c in qualified:
    print(' -', c['legal_name'], c['state'], c['power_units'], 'trucks | rating:', c['safety_rating'] or 'N/A', '| signals:', c['signals'])
"
```
Expected: 1–4 of 5 carriers qualify, each has `legal_name`, `power_units`, `state` populated.

- [ ] **Step 3: Commit**

```bash
cd "C:\Users\ChadGriffith\Downloads\fileflo-f11afbf5-main (2)"
git add pipeline/fmcsa_hub.py
git commit -m "feat: fmcsa signal hub - phase 3a QCMobile enrichment and safety rating tagging"
```

---

## Task 4: Add Phase 3b — SMS CSA Scraping

**Files:**
- Modify: `pipeline/fmcsa_hub.py`

- [ ] **Step 1: Append Phase 3b to fmcsa_hub.py**

Append to `pipeline/fmcsa_hub.py`:

```python
# ── Phase 3b: FMCSA SMS CSA Score Scraping ───────────────────────────────────
def scrape_csa_scores(dot):
    """
    Scrape CSA percentile scores from FMCSA SMS Overview page.
    Returns dict of {basic_name: score_float} for basics above threshold.
    Returns {} if page unavailable or bot-protected.
    """
    url = f"https://ai.fmcsa.dot.gov/SMS/Carrier/{dot}/Overview.aspx"
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            }
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
    except Exception:
        return {}

    # Regex patterns for each BASIC percentile score in the SMS HTML
    # The page renders scores as numbers adjacent to BASIC names
    patterns = {
        "Unsafe Driving":                  r"Unsafe\s+Driving[^0-9]{0,80}?(\d{1,3}(?:\.\d+)?)\s*%?",
        "HOS Compliance":                  r"Hours.of.Service[^0-9]{0,80}?(\d{1,3}(?:\.\d+)?)\s*%?",
        "Driver Fitness":                  r"Driver\s+Fitness[^0-9]{0,80}?(\d{1,3}(?:\.\d+)?)\s*%?",
        "Controlled Substances/Alcohol":   r"Controlled\s+Substances[^0-9]{0,80}?(\d{1,3}(?:\.\d+)?)\s*%?",
        "Vehicle Maintenance":             r"Vehicle\s+Maintenance[^0-9]{0,80}?(\d{1,3}(?:\.\d+)?)\s*%?",
        "Hazardous Materials Compliance":  r"Hazardous\s+Materials[^0-9]{0,80}?(\d{1,3}(?:\.\d+)?)\s*%?",
        "Crash Indicator":                 r"Crash\s+Indicator[^0-9]{0,80}?(\d{1,3}(?:\.\d+)?)\s*%?",
    }

    scores = {}
    for basic, pattern in patterns.items():
        match = re.search(pattern, html, re.IGNORECASE | re.DOTALL)
        if match:
            val = float(match.group(1))
            if val <= 100:  # sanity check — percentile can't exceed 100
                scores[basic] = val
    return scores


def enrich_csa(carriers):
    """
    Scrape CSA scores per carrier. Tag csa signal if any BASIC above threshold.
    Capture csaCategory (highest-scoring BASIC above threshold) and csaScore.
    Falls back gracefully if SMS page is unavailable.
    """
    for c in carriers:
        c.setdefault("csa_category", "")
        c.setdefault("csa_score", "")
        c.setdefault("csa_basics_above", 0)

        scores = scrape_csa_scores(c["dot_number"])
        above = {
            basic: score
            for basic, score in scores.items()
            if score >= CSA_THRESHOLDS.get(basic, 100)
        }

        if above:
            top_basic = max(above, key=above.get)
            c["csa_category"] = top_basic
            c["csa_score"] = str(int(above[top_basic]))
            c["csa_basics_above"] = len(above)
            if "csa" not in c["signals"]:
                c["signals"].append("csa")

        time.sleep(1.0)

    csa_count = sum(1 for c in carriers if "csa" in c["signals"])
    print(f"Phase 3b complete: {csa_count}/{len(carriers)} carriers with CSA above threshold")
    return carriers
```

- [ ] **Step 2: Test SMS scraping on a known carrier**

```bash
cd "C:\Users\ChadGriffith\Downloads\fileflo-f11afbf5-main (2)" && python3 -c "
from pipeline.fmcsa_hub import scrape_csa_scores
# DOT 488105 = Grove Transportation Services (known carrier)
scores = scrape_csa_scores('488105')
print('Scores returned:', len(scores))
for k, v in scores.items():
    print(f'  {k}: {v}')
if not scores:
    print('No scores found (SMS page may require login or has bot protection — fallback will apply)')
"
```
Expected: Either prints CSA scores per BASIC, or prints "No scores found" — both are acceptable outcomes (fallback handles empty response).

- [ ] **Step 3: Commit**

```bash
cd "C:\Users\ChadGriffith\Downloads\fileflo-f11afbf5-main (2)"
git add pipeline/fmcsa_hub.py
git commit -m "feat: fmcsa signal hub - phase 3b SMS CSA scraping with graceful fallback"
```

---

## Task 5: Add Phase 4 + Entry Point — Scoring, Output, Processed-DOTs Update

**Files:**
- Modify: `pipeline/fmcsa_hub.py`

- [ ] **Step 1: Append Phase 4 + entry point to fmcsa_hub.py**

Append to `pipeline/fmcsa_hub.py`:

```python
# ── Phase 4: Lead Scoring ─────────────────────────────────────────────────────
def _days_since_date(date_str):
    """Return days since a 'Month DD, YYYY' date string. Returns 999 on parse failure."""
    try:
        d = datetime.strptime(date_str, "%B %d, %Y")
        return (datetime.now() - d).days
    except Exception:
        return 999


def score_carriers(carriers):
    """Apply scoring rubric. Sort highest score first."""
    for c in carriers:
        score = 0
        if c.get("safety_rating") == "Unsatisfactory":
            score += 5
        if "oos" in c["signals"] and _days_since_date(c.get("violation_date", "")) <= 7:
            score += 4
        if c.get("safety_rating") == "Conditional":
            score += 3
        if "violation_history" in c["signals"]:
            score += 2
        if "csa" in c["signals"]:
            score += min(c.get("csa_basics_above", 0), 4)
        units = c.get("power_units", 0)
        if units >= 10:
            score += 2
        elif units >= 2:
            score += 1
        c["lead_score"] = score

    carriers.sort(key=lambda x: x["lead_score"], reverse=True)
    top = carriers[0]["lead_score"] if carriers else 0
    print(f"Phase 4 complete: {len(carriers)} carriers scored. Top score: {top}")
    return carriers


# ── Campaign Assignment ───────────────────────────────────────────────────────
def assign_campaign(carrier):
    """Return (campaign_id, signal_name) based on highest-priority signal present."""
    for signal in PRIORITY_ORDER:
        if signal in carrier.get("signals", []):
            return CAMPAIGN_IDS[signal], signal
    return None, None


# ── Processed-DOTs Update ────────────────────────────────────────────────────
def mark_dots_processed(carriers, run_label):
    """Write all enriched DOTs to processed-dots.json with today's date."""
    processed = {}
    if os.path.exists(PROCESSED_DOTS_FILE):
        with open(PROCESSED_DOTS_FILE) as f:
            try:
                processed = json.load(f)
            except json.JSONDecodeError:
                processed = {}

    today = datetime.now().strftime("%Y-%m-%d")
    for c in carriers:
        processed[c["dot_number"]] = {
            "processed_date": today,
            "run": run_label,
            "lead_score": c.get("lead_score", 0),
            "campaign_id": c.get("campaign_id"),
            "signal_used": c.get("signal_used"),
            "contact_found": False,  # SKILL.md updates this to True after upload
        }

    with open(PROCESSED_DOTS_FILE, "w") as f:
        json.dump(processed, f, indent=2)
    print(f"Marked {len(carriers)} DOTs as processed in processed-dots.json")


# ── Entry Point ───────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="FMCSA Signal Hub Pipeline")
    parser.add_argument("--batch-size", type=int, default=1000,
                        help="Max carriers to process per run (default: 1000)")
    parser.add_argument("--run", choices=["AM", "PM"], default="AM",
                        help="Run label for logging (default: AM)")
    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"FMCSA Signal Hub — {args.run} Run")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Batch size: {args.batch_size}")
    print(f"{'='*60}\n")

    carriers = collect_signals(args.batch_size)
    carriers = filter_seen_dots(carriers)

    if not carriers:
        print("No fresh carriers to process. Exiting.")
        # Write empty output so SKILL.md doesn't error
        with open(OUTPUT_FILE, "w") as f:
            json.dump({"run": args.run, "timestamp": datetime.now().isoformat(),
                       "total_enriched": 0, "carriers": []}, f)
        return

    carriers = enrich_qcmobile(carriers)
    carriers = enrich_csa(carriers)
    carriers = score_carriers(carriers)

    # Assign campaign to each carrier
    for c in carriers:
        campaign_id, signal_used = assign_campaign(c)
        c["campaign_id"] = campaign_id
        c["signal_used"] = signal_used

    uploadable = [c for c in carriers if c["campaign_id"]]

    # Mark all processed DOTs NOW so PM run skips them
    mark_dots_processed(carriers, args.run)

    # Write output for SKILL.md to read
    output = {
        "run": args.run,
        "timestamp": datetime.now().isoformat(),
        "total_enriched": len(carriers),
        "carriers": uploadable,
        "signal_breakdown": {
            signal: sum(1 for c in uploadable if c.get("signal_used") == signal)
            for signal in PRIORITY_ORDER
        },
    }
    with open(OUTPUT_FILE, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\n{'='*60}")
    print(f"Output: {len(uploadable)} carriers ready for contact-finding")
    print(f"Signal breakdown: {output['signal_breakdown']}")
    print(f"Saved to: {OUTPUT_FILE}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run full pipeline end-to-end with small batch**

```bash
cd "C:\Users\ChadGriffith\Downloads\fileflo-f11afbf5-main (2)" && python pipeline/fmcsa_hub.py --batch-size 10 --run AM
```
Expected output (approximate):
```
============================================================
FMCSA Signal Hub — AM Run
Started: 2026-03-26 HH:MM:SS
Batch size: 10
============================================================

Phase 1a: NNNN inspection rows → NN unique DOTs
Phase 1b: NNNN violation rows → N new DOTs added...
Phase 1 complete: NN total unique DOTs, returning top 10 by recency
Phase 2: 0 DOTs skipped (seen ≤90 days), 10 fresh
Phase 3a: N/10 qualified (fleet 2-50, active, US)
Phase 3b complete: N/N carriers with CSA above threshold
Phase 4 complete: N carriers scored. Top score: N
Marked N DOTs as processed in processed-dots.json

============================================================
Output: N carriers ready for contact-finding
Signal breakdown: {'safety_rating': N, 'oos': N, 'violation_history': N, 'csa': N}
Saved to: ...pipeline/hub_output.json
============================================================
```

- [ ] **Step 3: Verify hub_output.json is valid**

```bash
cd "C:\Users\ChadGriffith\Downloads\fileflo-f11afbf5-main (2)" && python3 -c "
import json
with open('pipeline/hub_output.json') as f:
    out = json.load(f)
print('Run:', out['run'])
print('Total enriched:', out['total_enriched'])
print('Carriers:', len(out['carriers']))
print('Signal breakdown:', out['signal_breakdown'])
if out['carriers']:
    c = out['carriers'][0]
    print('Top carrier:', c['legal_name'], '| score:', c['lead_score'], '| signal:', c['signal_used'])
    print('Required fields present:', all(k in c for k in ['dot_number','legal_name','state','city','power_units','campaign_id','signal_used']))
"
```
Expected: All required fields present, carriers array populated.

- [ ] **Step 4: Commit**

```bash
cd "C:\Users\ChadGriffith\Downloads\fileflo-f11afbf5-main (2)"
git add pipeline/fmcsa_hub.py pipeline/hub_output.json
git commit -m "feat: fmcsa signal hub - phase 4 scoring, campaign assignment, entry point"
```

---

## Task 6: Activate the Three Draft Instantly Campaigns

**Context:** CSA Score Alert (`53b6c3d3`), Safety Rating Alert (`a4f77f6e`), and Violation History Pattern (`8f41f5d5`) are in Draft status with 50/day limits. They need to be activated and limits raised to 1,500.

- [ ] **Step 1: Activate FMCSA CSA Score Alert and raise daily limit**

Use the Instantly MCP `update_campaign` tool:
```
campaign_id: 53b6c3d3-e4d6-4067-be6e-87542f1be716
status: 1  (1 = Active)
daily_limit: 1500
```

- [ ] **Step 2: Activate FMCSA Safety Rating Alert and raise daily limit**

Use the Instantly MCP `update_campaign` tool:
```
campaign_id: a4f77f6e-3033-4db0-8b1e-f128b5bfbdd6
status: 1
daily_limit: 1500
```

- [ ] **Step 3: Activate FMCSA Violation History Pattern and raise daily limit**

Use the Instantly MCP `update_campaign` tool:
```
campaign_id: 8f41f5d5-a3f8-41f2-9143-b01bfa5bdc8b
status: 1
daily_limit: 1500
```

- [ ] **Step 4: Verify all four campaigns are active with correct limits**

Use Instantly MCP `list_campaigns` with `search: "FMCSA"`. Confirm:
- `b514c694` — status: 1, daily_limit: 1500 ✓ (already correct)
- `53b6c3d3` — status: 1, daily_limit: 1500
- `a4f77f6e` — status: 1, daily_limit: 1500
- `8f41f5d5` — status: 1, daily_limit: 1500

---

## Task 7: Build the AM Scheduled Task SKILL.md

**Files:**
- Create: `C:\Users\ChadGriffith\.claude\scheduled-tasks\fmcsa-signal-hub-am\SKILL.md`

- [ ] **Step 1: Create the directory and SKILL.md**

Create `C:\Users\ChadGriffith\.claude\scheduled-tasks\fmcsa-signal-hub-am\SKILL.md`:

````markdown
---
name: fmcsa-signal-hub-am
description: Mon-Fri 7am CT: FMCSA Signal Hub AM run — pull OOS/violation/CSA/safety signals, enrich, find contacts via web+Apollo+pattern, upload to 4 Instantly campaigns
---

Run the FMCSA Signal Hub AM pipeline. Execute all steps in order. This is a scheduled task — make autonomous decisions, do not ask questions. If a step errors, log it and continue to the next carrier.

## STEP 1 — Run the Python pipeline script

Run via Bash:
```bash
cd "C:\Users\ChadGriffith\Downloads\fileflo-f11afbf5-main (2)" && python pipeline/fmcsa_hub.py --batch-size 1000 --run AM
```

This runs Phases 1–4 and writes `pipeline/hub_output.json`. If the script exits with an error, append "NEEDS MANUAL REVIEW — Python script failed" to `memory/CURRENT-STATE-AUDIT.md` and stop.

## STEP 2 — Read hub_output.json

Read `C:\Users\ChadGriffith\Downloads\fileflo-f11afbf5-main (2)\pipeline\hub_output.json`.

Save:
- `run_timestamp` = `timestamp` field
- `total_enriched` = `total_enriched` field
- `signal_breakdown` = `signal_breakdown` field
- `carriers` = the `carriers` array

If the carriers array is empty, skip to STEP 6 and log a zero-result run.

## STEP 3 — Contact finding per carrier

Initialize counters:
- `contacts_found` = 0
- `phone_only_stored` = 0
- `uploaded_by_campaign` = {"oos": 0, "csa": 0, "safety_rating": 0, "violation_history": 0}
- `new_phone_only_entries` = []
- `uploaded_dots` = []

For each carrier in `carriers` (process ALL of them):

**3a. Web search for company website domain**

Call the WebSearch MCP tool with query:
`"[carrier.legal_name]" "[carrier.city]" "[carrier.state]" trucking`

From the results, take the first URL whose domain is NOT in this skip list:
- safer.fmcsa.dot.gov
- ai.fmcsa.dot.gov
- data.transportation.gov
- yellowpages.com, yelp.com, manta.com, dnb.com, bizapedia.com, opencorporates.com
- linkedin.com, facebook.com, twitter.com
- Any URL whose path contains: /news, /article, /press, /blog

Extract the domain from the URL (e.g., `grovetransportation.com` from `https://www.grovetransportation.com/about`).

If a clean domain found → proceed to 3b.
If no clean domain found → skip to 3c (no domain available, try 3c with no domain).

**3b. Apollo search by domain**

Call `mcp__58c0745d-668a-4639-b569-2ea04a11af76__apollo_mixed_people_api_search` with:
```json
{
  "q_organization_domain": "[domain from 3a]",
  "person_titles": ["owner", "president", "ceo", "founder", "principal", "general manager", "director of operations"],
  "email_status": ["verified"],
  "per_page": 3
}
```

If any result has a verified email → use the first result: set `found_email`, `found_first_name`, `found_last_name`, `found_title`. Skip to STEP 4.

If no verified result → proceed to 3c.

**3c. Email pattern fallback (only if domain was found in 3a)**

If a domain was found in 3a, try these email patterns in order. For each, call `mcp__instantly__verify_email` with the email address. Stop at the first that returns `status: "valid"` AND `is_catch_all: false`.

Patterns to try:
1. `owner@[domain]`
2. `[first word of legal_name, lowercased, letters only]@[domain]` — e.g., if legal_name = "GROVE TRANSPORTATION INC", try `grove@grovetransportation.com`
3. `info@[domain]`
4. `contact@[domain]`

If a valid non-catchall email found → set `found_email`, `found_first_name = "there"`, `found_last_name = ""`, `found_title = "Owner"`. Skip to STEP 4.

**3d. No contact found**

If no email found through 3a–3c: store the carrier's phone for future outreach:
```json
{"dot_number": "[carrier.dot_number]", "legal_name": "[carrier.legal_name]", "state": "[carrier.state]", "phone": "[carrier.phone]", "date": "[today YYYY-MM-DD]"}
```
Add to `new_phone_only_entries`. Increment `phone_only_stored`. Continue to next carrier.

## STEP 4 — Upload to Instantly campaign

Build the lead object based on `carrier.signal_used`. Upload via `mcp__instantly__add_leads_to_campaign_or_list_bulk`:

```json
{
  "campaign_id": "[carrier.campaign_id]",
  "skip_if_in_workspace": true,
  "leads": [{ ... }]
}
```

**If signal_used = "oos"**, the lead object is:
```json
{
  "email": "[found_email]",
  "first_name": "[found_first_name]",
  "last_name": "[found_last_name]",
  "company_name": "[carrier.legal_name]",
  "custom_variables": {
    "violationDate": "[carrier.violation_date]",
    "violationLocation": "[carrier.violation_location]",
    "violationType": "out-of-service violation",
    "oosCount": "[carrier.oos_count]",
    "fleetSize": "[carrier.power_units]",
    "dotNumber": "[carrier.dot_number]",
    "state": "[carrier.state]",
    "title": "[found_title]"
  }
}
```

**If signal_used = "safety_rating"**, the lead object is:
```json
{
  "email": "[found_email]",
  "first_name": "[found_first_name]",
  "last_name": "[found_last_name]",
  "company_name": "[carrier.legal_name]",
  "custom_variables": {
    "safetyRating": "[carrier.safety_rating]",
    "fleetSize": "[carrier.power_units]",
    "dotNumber": "[carrier.dot_number]",
    "state": "[carrier.state]",
    "title": "[found_title]"
  }
}
```

**If signal_used = "violation_history"**, the lead object is:
```json
{
  "email": "[found_email]",
  "first_name": "[found_first_name]",
  "last_name": "[found_last_name]",
  "company_name": "[carrier.legal_name]",
  "custom_variables": {
    "violationCount": "[carrier.violation_count]",
    "timeframe": "12 months",
    "fleetSize": "[carrier.power_units]",
    "dotNumber": "[carrier.dot_number]",
    "state": "[carrier.state]",
    "title": "[found_title]"
  }
}
```

**If signal_used = "csa"**, the lead object is:
```json
{
  "email": "[found_email]",
  "first_name": "[found_first_name]",
  "last_name": "[found_last_name]",
  "company_name": "[carrier.legal_name]",
  "custom_variables": {
    "csaCategory": "[carrier.csa_category]",
    "csaScore": "[carrier.csa_score]",
    "fleetSize": "[carrier.power_units]",
    "dotNumber": "[carrier.dot_number]",
    "state": "[carrier.state]",
    "title": "[found_title]"
  }
}
```

If upload succeeds: increment `contacts_found` and `uploaded_by_campaign[carrier.signal_used]`. Add carrier's dot_number to `uploaded_dots`.

## STEP 5 — Update memory files

**5a. Update processed-dots.json**

Read `memory/processed-dots.json`. For each carrier in `uploaded_dots`, find the entry and update:
```json
{
  "contact_found": true
}
```
Write the updated file back.

**5b. Update phone-only-carriers.json**

If `new_phone_only_entries` is not empty:
Read `memory/phone-only-carriers.json`, append all entries in `new_phone_only_entries`, write back.

## STEP 6 — Append to CURRENT-STATE-AUDIT.md

Append to `memory/CURRENT-STATE-AUDIT.md`:

```markdown
## [TODAY DATE] — AM Run ([run_timestamp])

| Metric | Value |
|---|---|
| Carriers pulled from Socrata | [total_enriched] |
| Signal breakdown (pre-contact) | OOS: [signal_breakdown.oos] \| Safety Rating: [signal_breakdown.safety_rating] \| Violation History: [signal_breakdown.violation_history] \| CSA: [signal_breakdown.csa] |
| Contacts found (yield %) | [contacts_found] ([contacts_found / total_enriched * 100 rounded to 1 decimal]%) |
| Phone-only carriers stored | [phone_only_stored] |
| Uploaded — OOS campaign | [uploaded_by_campaign.oos] |
| Uploaded — CSA campaign | [uploaded_by_campaign.csa] |
| Uploaded — Safety Rating campaign | [uploaded_by_campaign.safety_rating] |
| Uploaded — Violation History campaign | [uploaded_by_campaign.violation_history] |
| **Total uploaded** | **[contacts_found]** |
| Errors | [none, or list errors] |
```

If any campaign upload returned an error (not a skip/duplicate), add: **⚠️ NEEDS MANUAL REVIEW**
````

- [ ] **Step 2: Verify the SKILL.md file was created**

```bash
python3 -c "
import os
path = r'C:\Users\ChadGriffith\.claude\scheduled-tasks\fmcsa-signal-hub-am\SKILL.md'
print('Exists:', os.path.exists(path))
with open(path) as f:
    lines = f.readlines()
print('Lines:', len(lines))
print('First line:', lines[0].strip())
"
```
Expected: File exists, 100+ lines, first line is `---`.

---

## Task 8: Build the PM Scheduled Task SKILL.md

**Files:**
- Create: `C:\Users\ChadGriffith\.claude\scheduled-tasks\fmcsa-signal-hub-pm\SKILL.md`

- [ ] **Step 1: Create PM SKILL.md**

Create `C:\Users\ChadGriffith\.claude\scheduled-tasks\fmcsa-signal-hub-pm\SKILL.md`:

The PM SKILL.md is identical to the AM SKILL.md with two changes:
1. The frontmatter `name` field is `fmcsa-signal-hub-pm`
2. The frontmatter `description` says `Mon-Fri 1pm CT: FMCSA Signal Hub PM run`
3. The Bash command uses `--run PM` instead of `--run AM`
4. The audit log label says `PM Run` instead of `AM Run`

Copy the full AM SKILL.md content and make those four substitutions. The rest is identical — the Python script automatically skips AM carriers because they are now in `processed-dots.json`, so the PM batch is a fresh set of carriers.

---

## Task 9: Register Scheduled Tasks + Deprecate Old Task

- [ ] **Step 1: Register AM task**

Use the `mcp__scheduled-tasks__create_scheduled_task` tool (or CronCreate) to register `fmcsa-signal-hub-am`:
- Schedule: `0 7 * * 1-5` (7:00am Mon–Fri, CT)
- Skill file: `C:\Users\ChadGriffith\.claude\scheduled-tasks\fmcsa-signal-hub-am\SKILL.md`

- [ ] **Step 2: Register PM task**

Use the `mcp__scheduled-tasks__create_scheduled_task` tool to register `fmcsa-signal-hub-pm`:
- Schedule: `0 13 * * 1-5` (1:00pm Mon–Fri, CT)
- Skill file: `C:\Users\ChadGriffith\.claude\scheduled-tasks\fmcsa-signal-hub-pm\SKILL.md`

- [ ] **Step 3: Deprecate old task**

Add a deprecation notice to the top of `C:\Users\ChadGriffith\.claude\scheduled-tasks\fmcsa-weekly-lead-upload\SKILL.md`:

```markdown
> ⛔ DEPRECATED 2026-03-26 — Replaced by fmcsa-signal-hub-am and fmcsa-signal-hub-pm.
> Do not run this task. See docs/superpowers/specs/2026-03-26-fmcsa-signal-hub-design.md.

```

Remove the `fmcsa-weekly-lead-upload` task from the scheduled task runner (cancel/delete via the scheduled-tasks MCP or CronDelete).

- [ ] **Step 4: Verify both new tasks are registered**

Use `mcp__scheduled-tasks__list_scheduled_tasks` to confirm both tasks appear with correct schedules.

- [ ] **Step 5: Update MEMORY.md to reflect the new pipeline**

Update the "Scheduled Tasks" table in `memory/MEMORY.md` (or the main MEMORY.md at `memory/MEMORY.md`):

Replace the `fmcsa-weekly-lead-upload` row with:
```
| fmcsa-signal-hub-am | Mon-Fri 7am CT | Pull signals, enrich, contact-find, upload AM batch |
| fmcsa-signal-hub-pm | Mon-Fri 1pm CT | Same as AM, next batch of fresh carriers |
```

And remove the old `fmcsa-weekly-lead-upload` row.

---

## Task 10: Manual Test Run + Validation

- [ ] **Step 1: Run the AM pipeline manually**

```bash
cd "C:\Users\ChadGriffith\Downloads\fileflo-f11afbf5-main (2)" && python pipeline/fmcsa_hub.py --batch-size 50 --run AM
```

Verify output:
- `hub_output.json` contains carriers with all required fields
- `memory/processed-dots.json` has 50 new entries

- [ ] **Step 2: Manually trigger the AM SKILL.md for a small batch**

Edit `hub_output.json` temporarily to keep only the top 3 carriers (by `lead_score`), then invoke the AM skill manually. Verify:
- Contact-finding chain runs for each carrier
- At least 1 carrier gets an email found and uploaded to the correct campaign
- `memory/CURRENT-STATE-AUDIT.md` has a new entry
- `memory/processed-dots.json` has `contact_found: true` for uploaded carriers

- [ ] **Step 3: Verify correct campaign routing**

Check the audit log. Confirm each uploaded carrier's campaign matches its `signal_used`:
- `oos` → campaign `b514c694`
- `safety_rating` → campaign `a4f77f6e`
- `violation_history` → campaign `8f41f5d5`
- `csa` → campaign `53b6c3d3`

- [ ] **Step 4: Restore hub_output.json**

Re-run `python pipeline/fmcsa_hub.py --batch-size 1000 --run AM` to regenerate the full output file for the scheduled runs.

- [ ] **Step 5: Final commit**

```bash
cd "C:\Users\ChadGriffith\Downloads\fileflo-f11afbf5-main (2)"
git add pipeline/ docs/
git commit -m "feat: FMCSA Signal Hub complete — 4 signals, stacked contact-finding, AM/PM scheduled tasks"
```

---

## Self-Review Notes

**Spec coverage check:**
- ✅ Phase 1 (signal collection): Tasks 2, 5
- ✅ Phase 2 (cross-run dedup): Task 2
- ✅ Phase 3a (QCMobile enrichment + safety rating): Task 3
- ✅ Phase 3b (SMS CSA scraping + fallback): Task 4
- ✅ Phase 4 (lead scoring): Task 5
- ✅ Phase 5 (contact finding chain): AM SKILL.md Steps 3a–3d (Task 7)
- ✅ Phase 6 (campaign routing + upload): AM SKILL.md Step 4 (Task 7)
- ✅ Phase 7 (logging): AM SKILL.md Step 6 (Task 7)
- ✅ Campaign activation: Task 6
- ✅ Scheduled task registration: Task 9
- ✅ processed-dots.json: Phase 2 + mark_dots_processed() + SKILL.md Step 5a
- ✅ phone-only-carriers.json: SKILL.md Steps 3d + 5b
- ✅ Deprecate old task: Task 9 Step 3

**Type consistency check:**
- `carrier.dot_number` → string throughout
- `carrier.signals` → list of strings: `["oos", "safety_rating", "violation_history", "csa"]`
- `carrier.signal_used` → single string from PRIORITY_ORDER
- `carrier.campaign_id` → UUID string from CAMPAIGN_IDS
- `carrier.lead_score` → int
- `carrier.power_units` → int
- All consistent across Python script and SKILL.md references ✅
