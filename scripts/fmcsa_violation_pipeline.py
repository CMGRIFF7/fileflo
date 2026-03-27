"""
fmcsa_violation_pipeline.py
FileFlo — FMCSA Violation Lead Pipeline

Pulls recent out-of-service violations from the FMCSA Socrata API, enriches
each carrier via QCMobile, finds owner contacts via Apollo, and uploads
qualified leads to the Instantly violation campaign.

Usage:
    APOLLO_API_KEY=... INSTANTLY_API_KEY=... python fmcsa_violation_pipeline.py

Dependencies: requests (standard library otherwise)
"""

import csv
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone

import requests

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

FMCSA_WEBKEY = "ea050d55fc6f7368ffa7e575d6b021e87d60fea0"
# Inspection file — confirmed working, provides dot_number, insp_date, carrier name/state, oos_total
SOCRATA_URL = "https://data.transportation.gov/resource/fx4q-ay7w.json"
QCMOBILE_BASE = "https://mobile.fmcsa.dot.gov/qc/services/carriers"

APOLLO_API_KEY = os.environ.get("APOLLO_API_KEY", "")
INSTANTLY_API_KEY = os.environ.get("INSTANTLY_API_KEY", "")
INSTANTLY_CAMPAIGN_ID = "b514c694-b372-4d89-8b93-6ed325571963"  # FMCSA Violation Targets -- Direct
INSTANTLY_BASE = "https://api.instantly.ai/api/v2"

# Fleet size filter (inclusive)
MIN_POWER_UNITS = 2
MAX_POWER_UNITS = 50

# Max carriers to enrich per pipeline run (prevents multi-hour QCMobile calls).
# At 0.5s/carrier + Apollo, 200 carriers ~ 5 minutes. Rotate through the list
# across Tue/Thu runs — 400 carriers/week ~ 80 qualified leads/week.
MAX_CARRIERS_PER_RUN = 200

# Apollo owner titles to search for
OWNER_TITLES = ["owner", "president", "CEO", "founder", "general manager"]

# Retry settings
MAX_RETRIES = 3
RETRY_BACKOFF = 2  # seconds, doubled each retry

# QCMobile rate limit: max 2 req/sec
QCMOBILE_RATE_LIMIT_DELAY = 0.5  # seconds between requests


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def api_get(url: str, params: dict = None, headers: dict = None,
            retries: int = MAX_RETRIES, label: str = "") -> dict | list | None:
    """
    Perform a GET request with retry/backoff. Returns parsed JSON or None on
    persistent failure.
    """
    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=30)
            if resp.status_code == 429:
                wait = RETRY_BACKOFF ** attempt
                print(f"    [rate-limit] {label} — waiting {wait}s before retry {attempt}/{retries}")
                time.sleep(wait)
                continue
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.RequestException as exc:
            if attempt < retries:
                wait = RETRY_BACKOFF ** attempt
                print(f"    [warn] {label} GET failed ({exc}), retry {attempt}/{retries} in {wait}s")
                time.sleep(wait)
            else:
                print(f"    [error] {label} GET failed after {retries} retries: {exc}")
                return None


def api_post(url: str, payload: dict, headers: dict = None,
             retries: int = MAX_RETRIES, label: str = "") -> dict | None:
    """
    Perform a POST request with retry/backoff. Returns parsed JSON or None on
    persistent failure.
    """
    for attempt in range(1, retries + 1):
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=30)
            if resp.status_code == 429:
                wait = RETRY_BACKOFF ** attempt
                print(f"    [rate-limit] {label} — waiting {wait}s before retry {attempt}/{retries}")
                time.sleep(wait)
                continue
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.RequestException as exc:
            if attempt < retries:
                wait = RETRY_BACKOFF ** attempt
                print(f"    [warn] {label} POST failed ({exc}), retry {attempt}/{retries} in {wait}s")
                time.sleep(wait)
            else:
                print(f"    [error] {label} POST failed after {retries} retries: {exc}")
                return None


# ---------------------------------------------------------------------------
# Step 1: Pull violations from Socrata
# ---------------------------------------------------------------------------

def pull_violations() -> list[dict]:
    """
    Fetch out-of-service inspection records for interstate carriers from the
    last 30 days via the FMCSA Socrata inspection file (fx4q-ay7w).
    Deduplicates on DOT number, keeping the most recent inspection per carrier.

    Field names for fx4q-ay7w (inspection file):
        dot_number, insp_date, insp_carrier_name, insp_carrier_city,
        insp_carrier_state, oos_total, viol_total, insp_interstate

    Returns a list of dicts with keys:
        dot_number, inspection_date, violation_category, report_state, oos_count
    """
    # insp_date is stored as YYYYMMDD integer string — use that format for comparison
    cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y%m%d")

    # Use urllib to build the URL safely — do NOT use requests params= for Socrata
    # because requests double-encodes the $where clause.
    import urllib.parse
    where_val = f"insp_date > '{cutoff}' AND oos_total > '0' AND insp_interstate = 'Y'"
    select_val = "dot_number,insp_date,insp_carrier_name,insp_carrier_city,insp_carrier_state,oos_total,viol_total"
    query_str = (
        "$where=" + urllib.parse.quote(where_val)
        + "&$select=" + urllib.parse.quote(select_val)
        + "&$order=" + urllib.parse.quote("insp_date DESC")
        + "&$limit=50000"
    )
    url = f"{SOCRATA_URL}?{query_str}"

    print("Step 1: Pulling OOS inspection records from FMCSA Socrata API...")
    import urllib.request
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            rows = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        print(f"[error] Socrata request failed: {exc}")
        sys.exit(1)

    if not rows:
        print("[error] No data returned from Socrata. Exiting.")
        sys.exit(1)

    print(f"  Pulled {len(rows)} raw inspection records")

    # Deduplicate: keep most recent inspection per DOT number.
    seen: dict[str, dict] = {}
    oos_counts: dict[str, int] = {}

    for row in rows:
        dot = row.get("dot_number", "").strip()
        if not dot:
            continue

        try:
            oos_this = int(row.get("oos_total", 0))
        except (ValueError, TypeError):
            oos_this = 1

        oos_counts[dot] = oos_counts.get(dot, 0) + oos_this

        if dot not in seen:
            seen[dot] = row
        else:
            existing_date = seen[dot].get("insp_date", "")
            new_date = row.get("insp_date", "")
            if new_date > existing_date:
                seen[dot] = row

    # Build clean deduplicated list
    violations = []
    for dot, row in seen.items():
        # Convert YYYYMMDD -> "Month DD, YYYY" for readable email variable
        raw_date = row.get("insp_date", "")
        try:
            parsed = datetime.strptime(str(raw_date)[:8], "%Y%m%d")
            readable_date = parsed.strftime("%B %d, %Y")  # e.g. "March 24, 2026"
        except (ValueError, TypeError):
            readable_date = str(raw_date)

        violations.append({
            "dot_number": dot,
            "inspection_date": readable_date,
            "violation_category": "out-of-service violation",  # generic; inspection file has no category
            "report_state": row.get("insp_carrier_state", ""),
            "carrier_name": row.get("insp_carrier_name", ""),
            "carrier_city": row.get("insp_carrier_city", ""),
            "oos_count": oos_counts[dot],
        })

    print(f"  Deduplicated to {len(violations)} unique DOT numbers")

    # Cap per-run volume so scheduled runs complete in reasonable time
    if len(violations) > MAX_CARRIERS_PER_RUN:
        print(f"  Capping to {MAX_CARRIERS_PER_RUN} carriers for this run (most recent first)")
        violations = violations[:MAX_CARRIERS_PER_RUN]

    return violations


# ---------------------------------------------------------------------------
# Step 2: Enrich carriers via QCMobile
# ---------------------------------------------------------------------------

def enrich_carrier(dot_number: str) -> dict | None:
    """
    Call QCMobile to retrieve carrier details for a single DOT number.
    Returns a dict of relevant fields or None if the carrier should be
    filtered out or the API call fails.
    """
    url = f"{QCMOBILE_BASE}/{dot_number}"
    params = {"webKey": FMCSA_WEBKEY}

    data = api_get(url, params=params, label=f"QCMobile/{dot_number}")
    if not data:
        return None

    # QCMobile wraps results in a "content" key
    content = data.get("content", {})
    if not content:
        return None

    carrier = content.get("carrier", {})
    if not carrier:
        return None

    # Extract fields
    legal_name = (carrier.get("legalName") or "").strip()
    dba_name = (carrier.get("dbaName") or "").strip()
    mailing_street = (carrier.get("mailingStreet") or carrier.get("phyStreet") or "").strip()
    mailing_city = (carrier.get("mailingCity") or carrier.get("phyCity") or "").strip()
    mailing_state = (carrier.get("mailingState") or carrier.get("phyState") or "").strip().upper()
    mailing_country = (carrier.get("mailingCountry") or carrier.get("phyCountry") or "US").strip().upper()

    # Power units — may come back as string
    try:
        power_units = int(carrier.get("totalPowerUnits") or 0)
    except (ValueError, TypeError):
        power_units = 0

    safety_rating = (carrier.get("safetyRating") or "").strip()
    oos_date = (carrier.get("outOfServiceDate") or "").strip()

    # --- Filter rules ---

    # Must be a US carrier
    if mailing_country not in ("US", "USA", ""):
        return None

    # Must have a state
    if not mailing_state:
        return None

    # Fleet size must be 2–50 power units
    if power_units < MIN_POWER_UNITS or power_units > MAX_POWER_UNITS:
        return None

    # Must not be inactive/revoked (carrier entity status)
    # QCMobile may return statusCode: A=Active, I=Inactive, etc.
    status_code = (carrier.get("statusCode") or "").strip().upper()
    if status_code and status_code not in ("A", ""):
        return None

    # Must not currently be out-of-service at entity level
    if oos_date:
        return None

    return {
        "dot_number": dot_number,
        "legal_name": legal_name or dba_name,
        "dba_name": dba_name,
        "mailing_street": mailing_street,
        "mailing_city": mailing_city,
        "mailing_state": mailing_state,
        "power_units": power_units,
        "safety_rating": safety_rating,
    }


def enrich_carriers(violations: list[dict]) -> list[dict]:
    """
    Enrich all violation records with QCMobile data, applying fleet/status
    filters. Respects the 2 req/sec rate limit.

    Returns a merged list of dicts combining violation data + carrier data.
    """
    print(f"\nStep 2: Enriching {len(violations)} carriers via QCMobile...")

    qualified = []
    filtered_out = 0

    for i, v in enumerate(violations, 1):
        dot = v["dot_number"]
        carrier = enrich_carrier(dot)

        if carrier is None:
            filtered_out += 1
        else:
            # Merge violation metadata into carrier record
            carrier.update({
                "inspection_date": v["inspection_date"],
                "violation_category": v["violation_category"],
                "report_state": v["report_state"],
                "oos_count": v["oos_count"],
            })
            qualified.append(carrier)

        # Progress every 50
        if i % 50 == 0:
            print(f"  Enriched {i}/{len(violations)} — {len(qualified)} qualified so far")

        # Rate limit: max 2 requests per second
        time.sleep(QCMOBILE_RATE_LIMIT_DELAY)

    print(f"  Enriched {len(violations)} carriers — {len(qualified)} qualified, {filtered_out} filtered out")
    return qualified


# ---------------------------------------------------------------------------
# Step 3: Apollo people search
# ---------------------------------------------------------------------------

def search_apollo_contact(carrier: dict) -> dict | None:
    """
    Search Apollo for a verified owner/founder/CEO email at the given carrier.
    Returns the best contact dict or None if no verified match found.
    """
    if not APOLLO_API_KEY:
        print("  [warn] APOLLO_API_KEY not set — skipping Apollo enrichment")
        return None

    payload = {
        "q_organization_name": carrier["legal_name"],
        "person_locations": [carrier["mailing_state"]],
        "person_titles": OWNER_TITLES,
        "email_status": ["verified"],
        "per_page": 3,
    }
    headers = {
        "Content-Type": "application/json",
        "x-api-key": APOLLO_API_KEY,
    }

    result = api_post(
        "https://api.apollo.io/api/v1/mixed_people/search",
        payload=payload,
        headers=headers,
        label=f"Apollo/{carrier['legal_name'][:30]}",
    )

    if not result:
        return None

    people = result.get("people", [])
    for person in people:
        email_status = person.get("email_status", "")
        catchall = person.get("email_domain_catchall", True)

        # Only keep verified, non-catchall emails
        if email_status == "verified" and not catchall:
            return {
                "first_name": person.get("first_name", ""),
                "last_name": person.get("last_name", ""),
                "email": person.get("email", ""),
                "title": person.get("title", ""),
                "linkedin_url": person.get("linkedin_url", ""),
            }

    return None


def match_apollo_contacts(carriers: list[dict]) -> list[dict]:
    """
    For each qualified carrier, attempt to find a verified owner email via
    Apollo. Returns only carriers for which a contact was found.
    """
    print(f"\nStep 3: Searching Apollo for owner emails on {len(carriers)} carriers...")

    matched = []
    not_found = 0

    for i, carrier in enumerate(carriers, 1):
        contact = search_apollo_contact(carrier)

        if contact:
            carrier.update(contact)
            matched.append(carrier)
        else:
            not_found += 1

        if i % 20 == 0:
            print(f"  Apollo progress: {i}/{len(carriers)} — {len(matched)} matched")

        # Small delay to be polite to Apollo API
        time.sleep(0.3)

    print(f"  Matched {len(matched)} emails, {not_found} carriers had no verified contact")
    return matched


# ---------------------------------------------------------------------------
# Step 4: Upload to Instantly
# ---------------------------------------------------------------------------

def upload_to_instantly(leads: list[dict]) -> int:
    """
    Upload qualified leads to the Instantly violation campaign using the v2
    API. Uses skip_if_in_workspace=True to avoid double-emailing contacts who
    have already replied.

    Returns the number of leads successfully uploaded.
    """
    if not INSTANTLY_API_KEY:
        print("  [warn] INSTANTLY_API_KEY not set — skipping Instantly upload")
        return 0

    print(f"\nStep 4: Uploading {len(leads)} leads to Instantly campaign...")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {INSTANTLY_API_KEY}",
    }

    uploaded = 0

    # Instantly v2 supports bulk upload; batch in groups of 100 to stay safe
    batch_size = 100
    for batch_start in range(0, len(leads), batch_size):
        batch = leads[batch_start: batch_start + batch_size]

        instantly_leads = []
        for lead in batch:
            instantly_leads.append({
                "email": lead["email"],
                "first_name": lead.get("first_name", ""),
                "last_name": lead.get("last_name", ""),
                "company_name": lead.get("legal_name", ""),
                "personalization": "",  # filled by campaign sequence
                "website": "",
                "phone": "",
                "custom_variables": {
                    # Violation-specific variables for personalized Variant B
                    "violationDate": lead.get("inspection_date", ""),
                    "violationLocation": lead.get("report_state", ""),
                    "violationType": lead.get("violation_category", "out-of-service violation"),
                    "oosCount": str(lead.get("oos_count", "")),
                    "fleetSize": str(lead.get("power_units", "")),
                    # Core campaign declared variables
                    "dotNumber": lead.get("dot_number", ""),
                    "state": lead.get("report_state", ""),
                    "title": lead.get("title", ""),
                },
            })

        payload = {
            "campaign_id": INSTANTLY_CAMPAIGN_ID,
            "leads": instantly_leads,
            "skip_if_in_workspace": True,
        }

        result = api_post(
            f"{INSTANTLY_BASE}/leads/add",
            payload=payload,
            headers=headers,
            label=f"Instantly batch {batch_start // batch_size + 1}",
        )

        if result:
            # v2 returns {"total_new_leads": N, ...}
            batch_uploaded = result.get("total_new_leads", len(batch))
            uploaded += batch_uploaded
            print(f"  Batch {batch_start // batch_size + 1}: uploaded {batch_uploaded} leads")
        else:
            print(f"  Batch {batch_start // batch_size + 1}: upload failed")

    print(f"  Total uploaded to Instantly: {uploaded}")
    return uploaded


# ---------------------------------------------------------------------------
# CSV export
# ---------------------------------------------------------------------------

def save_csv(leads: list[dict]) -> str:
    """
    Write all uploaded leads to a dated CSV file in the current directory.
    Returns the filename.
    """
    filename = f"fmcsa_leads_{datetime.now().strftime('%Y-%m-%d')}.csv"

    fieldnames = [
        "email", "first_name", "last_name", "title",
        "legal_name", "dba_name",
        "mailing_street", "mailing_city", "mailing_state",
        "power_units", "safety_rating",
        "dot_number", "inspection_date", "violation_category",
        "report_state", "oos_count",
        "linkedin_url",
    ]

    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(leads)

    print(f"\nSaved {len(leads)} leads to {filename}")
    return filename


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("FileFlo — FMCSA Violation Lead Pipeline")
    print(f"Run date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # Validate required env vars early (warn, not hard-fail — pipeline can
    # still be useful for generating the CSV even without upload credentials)
    if not APOLLO_API_KEY:
        print("[warn] APOLLO_API_KEY environment variable not set")
    if not INSTANTLY_API_KEY:
        print("[warn] INSTANTLY_API_KEY environment variable not set")

    # --- Step 1: Pull violations ---
    violations = pull_violations()
    total_violations = len(violations)

    # --- Step 2: Enrich + filter carriers ---
    qualified_carriers = enrich_carriers(violations)
    total_qualified = len(qualified_carriers)

    # --- Step 3: Match Apollo contacts ---
    if qualified_carriers and APOLLO_API_KEY:
        matched_leads = match_apollo_contacts(qualified_carriers)
    else:
        matched_leads = []
        if not APOLLO_API_KEY:
            print("\nStep 3: Skipped (APOLLO_API_KEY not set)")

    total_emails = len(matched_leads)

    # --- Step 4: Upload to Instantly ---
    if matched_leads and INSTANTLY_API_KEY:
        total_uploaded = upload_to_instantly(matched_leads)
    else:
        total_uploaded = 0
        if not INSTANTLY_API_KEY:
            print("\nStep 4: Skipped (INSTANTLY_API_KEY not set)")

    # --- Save CSV (of all Apollo-matched leads, regardless of upload outcome) ---
    if matched_leads:
        csv_file = save_csv(matched_leads)
    else:
        csv_file = "(none — no matched leads)"

    # --- Summary ---
    print("\n" + "=" * 60)
    print("PIPELINE SUMMARY")
    print("=" * 60)
    print(f"  Violations pulled (last 30 days, OOS):  {total_violations:>6,}")
    print(f"  Carriers qualified (fleet 2-50, active): {total_qualified:>6,}")
    print(f"  Owner emails found (verified, no catch):  {total_emails:>6,}")
    print(f"  Leads uploaded to Instantly:              {total_uploaded:>6,}")
    print(f"  CSV saved to:                             {csv_file}")
    print("=" * 60)


if __name__ == "__main__":
    main()
