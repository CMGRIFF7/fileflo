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
OFFSET_STATE_FILE = os.path.join(MEMORY_DIR, "offset_state.json")

POOL_SIZE = 35000  # Reset offset when we've walked the full list

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
FRESH_DAYS   = 3    # violations within this window are always "fresh tier"
FRESH_SIZE   = 500  # how many fresh carriers to pull per run
BACKLOG_SIZE = 500  # how many backlog carriers to pull per run

def collect_signals(backlog_offset=0):
    """Pull Socrata inspections. Returns up to FRESH_SIZE + BACKLOG_SIZE carriers.

    Fresh tier  — last FRESH_DAYS days, always pulled from position 0 so new
                  violations are touched within 24 hrs regardless of backlog offset.
    Backlog tier — days FRESH_DAYS+1 through 30, sliced by backlog_offset so we
                  walk through older carriers without repeating.

    Dedup (Phase 2) handles any overlap between runs.
    """
    now = datetime.now(timezone.utc)
    cutoff_30    = (now - timedelta(days=30)).strftime("%Y%m%d")
    cutoff_fresh = (now - timedelta(days=FRESH_DAYS)).strftime("%Y%m%d")
    cutoff_365   = (now - timedelta(days=365)).strftime("%Y%m%d")

    def _fetch_oos_rows(where_clause):
        insp_select = "dot_number,insp_date,insp_carrier_name,insp_carrier_city,insp_carrier_state,oos_total"
        url = (
            "https://data.transportation.gov/resource/fx4q-ay7w.json?"
            + "$where=" + urllib.parse.quote(where_clause)
            + "&$select=" + urllib.parse.quote(insp_select)
            + "&$order=" + urllib.parse.quote("insp_date DESC")
            + "&$limit=50000"
        )
        with urllib.request.urlopen(url, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def _rows_to_dots(rows):
        dots = {}
        for row in rows:
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
                if ts > dots[dot]["latest_inspection_ts"]:
                    dots[dot]["latest_inspection_ts"] = ts
                    dots[dot]["latest_inspection_date"] = readable
            if oos > 0:
                dots[dot]["oos_count"] += oos
                if "oos" not in dots[dot]["signals"]:
                    dots[dot]["signals"].append("oos")
                    if not dots[dot]["violation_date"]:
                        dots[dot]["violation_date"] = readable
                        dots[dot]["violation_location"] = row.get("insp_carrier_state", "")
                        dots[dot]["violation_type"] = "out-of-service"
        return dots

    # ── Fresh tier: last FRESH_DAYS days ──────────────────────────────────────
    fresh_where = f"insp_date > '{cutoff_fresh}' AND oos_total > '0' AND insp_interstate = 'Y'"
    fresh_rows  = _fetch_oos_rows(fresh_where)
    fresh_dots  = _rows_to_dots(fresh_rows)
    fresh_sorted = sorted(fresh_dots.values(), key=lambda x: x["latest_inspection_ts"], reverse=True)
    fresh_slice  = fresh_sorted[:FRESH_SIZE]
    print(f"Phase 1a (fresh ≤{FRESH_DAYS}d): {len(fresh_rows)} rows -> {len(fresh_dots)} DOTs -> {len(fresh_slice)} selected")

    # ── Backlog tier: days FRESH_DAYS+1 through 30 ────────────────────────────
    backlog_where = (f"insp_date > '{cutoff_30}' AND insp_date <= '{cutoff_fresh}'"
                     f" AND oos_total > '0' AND insp_interstate = 'Y'")
    backlog_rows  = _fetch_oos_rows(backlog_where)
    backlog_dots  = _rows_to_dots(backlog_rows)
    # Remove any DOTs already in fresh tier
    for dot in fresh_dots:
        backlog_dots.pop(dot, None)
    backlog_sorted = sorted(backlog_dots.values(), key=lambda x: x["latest_inspection_ts"], reverse=True)
    backlog_slice  = backlog_sorted[backlog_offset:backlog_offset + BACKLOG_SIZE]
    print(f"Phase 1a (backlog {FRESH_DAYS+1}-30d): {len(backlog_rows)} rows -> {len(backlog_dots)} DOTs "
          f"-> {len(backlog_slice)} selected (offset {backlog_offset})")

    # ── Merge: fresh first, then backlog ─────────────────────────────────────
    seen = set()
    merged = []
    for c in fresh_slice + backlog_slice:
        if c["dot_number"] not in seen:
            seen.add(c["dot_number"])
            merged.append(c)

    dots = {c["dot_number"]: c for c in merged}
    print(f"Phase 1a total: {len(merged)} unique DOTs after merge")

    # ── 12-month inspections for violation_history signal ──
    try:
        hist_where  = f"insp_date > '{cutoff_365}' AND insp_interstate = 'Y'"
        hist_select = "dot_number,insp_date,insp_carrier_name,insp_carrier_city,insp_carrier_state,viol_total"
        hist_url = (
            "https://data.transportation.gov/resource/fx4q-ay7w.json?"
            + "$where=" + urllib.parse.quote(hist_where)
            + "&$select=" + urllib.parse.quote(hist_select)
            + "&$limit=100000"
        )
        with urllib.request.urlopen(hist_url, timeout=30) as resp:
            hist_rows = json.loads(resp.read().decode("utf-8"))

        # Count cumulative violations per DOT over 12 months
        viol_counts = {}
        for row in hist_rows:
            dot = row.get("dot_number", "").strip()
            if dot:
                v = int(row.get("viol_total") or 0)
                viol_counts[dot] = viol_counts.get(dot, 0) + v

        added = 0
        tagged = 0
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
                    tagged += 1
                dots[dot]["violation_count"] = count

        print(f"Phase 1b: {len(hist_rows)} 12-month inspection rows -> {added} new DOTs, {tagged} violation_history tagged")
    except Exception as e:
        print(f"Phase 1b WARNING: 12-month pull failed: {e}")

    print(f"Phase 1 complete: {len(merged)} carriers ({len(fresh_slice)} fresh + {len(backlog_slice)} backlog)")
    return merged


# ── Phase 2: Cross-Run Deduplication ─────────────────────────────────────────
def filter_seen_dots(carriers):
    """Skip DOTs processed in last 90 days."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=90)

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
                pd_str = processed[dot].get("processed_date", "1970-01-01")
                pd = datetime.fromisoformat(pd_str)
                if pd.tzinfo is None:
                    pd = pd.replace(tzinfo=timezone.utc)
                if pd > cutoff:
                    skipped += 1
                    continue
            except Exception:
                pass
        fresh.append(c)

    print(f"Phase 2: {skipped} DOTs skipped (seen <=90 days), {len(fresh)} fresh")
    return fresh


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
        except Exception:
            pass  # Skip on timeout/error
        time.sleep(0.5)

    print(f"Phase 3a complete: {len(qualified)}/{len(carriers)} qualified (fleet 2-50, active, US)")
    return qualified


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
            if val <= 100:  # sanity check -- percentile can't exceed 100
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


# ── Auto Offset ──────────────────────────────────────────────────────────────
def resolve_backlog_offset(run_label):
    """
    Manage a persistent backlog offset. Only the backlog tier advances —
    the fresh tier always starts from position 0.

    - AM run: if last_date != today, advance backlog_offset by 2 * BACKLOG_SIZE
      (covers yesterday's AM + PM backlog slices). Reset at POOL_SIZE.
      Returns backlog_offset (start of today's AM backlog window).
    - PM run: returns backlog_offset + BACKLOG_SIZE (PM picks up where AM left off).
      Does NOT advance state — AM owns the advance.
    """
    state = {"backlog_offset": 0, "last_date": ""}
    if os.path.exists(OFFSET_STATE_FILE):
        with open(OFFSET_STATE_FILE) as f:
            try:
                state = json.load(f)
            except json.JSONDecodeError:
                pass

    today = datetime.now().strftime("%Y-%m-%d")

    if run_label == "AM":
        if state.get("last_date") != today:
            new_offset = state["backlog_offset"] + 2 * BACKLOG_SIZE
            if new_offset >= POOL_SIZE:
                new_offset = 0
                print(f"Backlog offset: full pool walked ({POOL_SIZE} DOTs). Resetting to 0.")
            state["backlog_offset"] = new_offset
            state["last_date"] = today
            with open(OFFSET_STATE_FILE, "w") as f:
                json.dump(state, f, indent=2)
            print(f"Backlog offset: advanced to {new_offset} (AM, new day)")
        else:
            print(f"Backlog offset: {state['backlog_offset']} (AM, same-day re-run)")
        return state["backlog_offset"]
    else:  # PM
        pm_offset = state["backlog_offset"] + BACKLOG_SIZE
        print(f"Backlog offset: {pm_offset} (PM = {state['backlog_offset']} + {BACKLOG_SIZE})")
        return pm_offset


# ── Entry Point ───────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="FMCSA Signal Hub Pipeline")
    parser.add_argument("--backlog-offset", default="auto",
                        help="Backlog slice offset: integer or 'auto' (default: auto — reads offset_state.json)")
    parser.add_argument("--run", choices=["AM", "PM"], default="AM",
                        help="Run label for logging (default: AM)")
    args = parser.parse_args()

    if args.backlog_offset == "auto":
        backlog_offset = resolve_backlog_offset(args.run)
    else:
        backlog_offset = int(args.backlog_offset)

    print(f"\n{'='*60}")
    print(f"FMCSA Signal Hub -- {args.run} Run")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Fresh tier: top {FRESH_SIZE} (last {FRESH_DAYS} days) | Backlog tier: {BACKLOG_SIZE} @ offset {backlog_offset}")
    print(f"{'='*60}\n")

    carriers = collect_signals(backlog_offset)
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
