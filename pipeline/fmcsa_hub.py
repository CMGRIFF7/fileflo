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
    """Pull Socrata inspections (30 days for OOS, 12 months for violation history).
    Return merged DOT list sorted by recency."""
    now = datetime.now(timezone.utc)
    cutoff_30  = (now - timedelta(days=30)).strftime("%Y%m%d")
    cutoff_365 = (now - timedelta(days=365)).strftime("%Y%m%d")

    # ── Recent inspections (last 30 days) for OOS signal ──
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
            if ts > dots[dot]["latest_inspection_ts"]:
                dots[dot]["latest_inspection_ts"] = ts
                dots[dot]["latest_inspection_date"] = readable

        if oos > 0:
            dots[dot]["oos_count"] += oos
            if "oos" not in dots[dot]["signals"]:
                dots[dot]["signals"].append("oos")
                # violation_date and location from the most recent OOS inspection (rows sorted DESC)
                if not dots[dot]["violation_date"]:
                    dots[dot]["violation_date"] = readable
                    dots[dot]["violation_location"] = row.get("insp_carrier_state", "")
                    dots[dot]["violation_type"] = "out-of-service"

    print(f"Phase 1a: {len(insp_rows)} inspection rows -> {len(dots)} unique DOTs")

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

    sorted_dots = sorted(dots.values(), key=lambda x: x["latest_inspection_ts"], reverse=True)
    result = sorted_dots[:batch_size]
    print(f"Phase 1 complete: {len(dots)} total unique DOTs, returning top {len(result)} by recency")
    return result


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
