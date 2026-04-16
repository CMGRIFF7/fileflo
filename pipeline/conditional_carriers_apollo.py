#!/usr/bin/env python3
"""
conditional_carriers_apollo.py — Build a high-hit-rate Apollo enrichment list.

Problem: previous Apollo runs burned credits at ~20% hit rate because the
target list wasn't pre-qualified (insurance brokers, sole proprietors, tiny
companies Apollo doesn't index). This script pre-filters FMCSA census data
to carriers Apollo actually knows, BEFORE we spend a single credit.

Pipeline:

  Phase A (free) — Census pre-filter
    Socrata az4n-8mr2 with:
      status_code = 'A'
      safety_rating IN ('C', 'U')          (only Conditional or Unsatisfactory)
      power_units BETWEEN 10 AND 50        (big enough for Apollo, small enough
                                            to need software)
      has company_officer_1                 (need a name to enrich)
      has email_address OR cell_phone      (signals real operator, not ghost)
      mcs150_date > 24 months ago rejected (filters dormant carriers)

  Phase B (paid, MCP-driven) — Apollo org-match
    For each pre-filtered carrier, call
      apollo_organizations_enrich with q.name=<legal_name> and q.domain=<email domain>
    Keep only orgs Apollo confirms (~70% hit rate expected on pre-filtered pool).

  Phase C (paid, MCP-driven) — Apollo people-match
    For each confirmed org, call
      apollo_mixed_people_api_search with:
        organization_ids: [<org_id>]
        person_titles: ["Owner","President","CEO","Operations Manager",
                        "Safety Director","Compliance Manager","Fleet Manager",
                        "Vice President","General Manager"]
        contact_email_status: ["verified"]
    Prefer people whose name matches company_officer_1.

  Phase D (free) — Local email cleaner
    Run resulting emails through email_cleaner.validate_email as a final check.

This script executes Phase A only. Phases B–D are run via MCP in the
outreach-enrich-leads skill with the output JSON from this script as input.

Usage:
    python conditional_carriers_apollo.py --limit 2000 --min-units 10 --max-units 50

Output:
    pipeline/conditional_carriers_prefilter.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

from email_cleaner import validate_email, VerdictLevel

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = os.path.join(SCRIPT_DIR, "conditional_carriers_prefilter.json")

SOCRATA_CENSUS = "https://data.transportation.gov/resource/az4n-8mr2.json"

# Titles we want Apollo to return in Phase C. Exported so the enrichment skill
# can use the same list without redefining.
DECISION_MAKER_TITLES = [
    "Owner", "President", "CEO", "Chief Executive Officer",
    "Operations Manager", "Operations Director", "Director of Operations",
    "Safety Director", "Director of Safety", "Safety Manager",
    "Compliance Manager", "Compliance Director", "Compliance Officer",
    "Fleet Manager", "Fleet Director",
    "Vice President", "General Manager", "Managing Partner",
]


def fetch_census(min_units: int, max_units: int, limit: int, months_active: int = 24) -> list[dict]:
    """
    Pull conditional/unsatisfactory carriers from FMCSA census.
    Socrata stores power_units and mcs150_date as text — numeric/date
    comparisons in the WHERE clause fail with 400. We fetch the full
    safety-rated pool then filter in Python.
    """
    where = "status_code='A' AND safety_rating IN ('C','U')"
    select = ",".join([
        "dot_number", "legal_name", "phy_city", "phy_state",
        "safety_rating", "power_units", "email_address", "cell_phone",
        "company_officer_1", "mcs150_date",
    ])
    # Fetch a larger pool than `limit` so we have room after post-filtering
    fetch_size = max(limit * 4, 5000)
    url = (
        f"{SOCRATA_CENSUS}?"
        + "$where=" + urllib.parse.quote(where)
        + "&$select=" + urllib.parse.quote(select)
        + f"&$limit={fetch_size}"
    )
    print(f"Fetching census (pool size {fetch_size}): {where}")
    with urllib.request.urlopen(url, timeout=60) as resp:
        rows = json.loads(resp.read().decode("utf-8"))

    # Post-filter in Python
    cutoff = datetime.now(timezone.utc) - timedelta(days=months_active * 30)
    kept = []
    for r in rows:
        try:
            units = int(r.get("power_units") or 0)
        except (ValueError, TypeError):
            units = 0
        if units < min_units or units > max_units:
            continue
        # Need at least one contact channel
        if not (r.get("email_address") or "").strip() and not (r.get("cell_phone") or "").strip():
            continue
        # Need an officer name for Apollo people-match
        if not (r.get("company_officer_1") or "").strip():
            continue
        # MCS-150 recency
        mcs_date = (r.get("mcs150_date") or "").strip()
        if mcs_date:
            try:
                # Socrata returns ISO like "2025-11-02T00:00:00.000"
                d = datetime.fromisoformat(mcs_date.replace("Z", "+00:00")).replace(tzinfo=timezone.utc)
                if d < cutoff:
                    continue
            except ValueError:
                pass  # keep if we can't parse
        kept.append(r)
        if len(kept) >= limit:
            break

    print(f"  After power_units [{min_units}-{max_units}], contact channel, "
          f"and {months_active}-month recency filters: {len(kept)} carriers")
    return kept


def email_domain(email: str) -> str | None:
    """Extract domain from an email. Returns None for freemail (not useful for org-match)."""
    if not email or "@" not in email:
        return None
    domain = email.split("@", 1)[1].strip().lower()
    # Freemail domains don't uniquely identify a business — skip them for org lookup
    from email_cleaner import FREEMAIL_DOMAINS
    if domain in FREEMAIL_DOMAINS:
        return None
    return domain


def transform(rows: list[dict]) -> list[dict]:
    """Shape census rows into Apollo-ready lead records."""
    out = []
    for r in rows:
        dot = (r.get("dot_number") or "").strip()
        if not dot:
            continue

        raw_email = (r.get("email_address") or "").strip()
        email_verdict = None
        clean_email = ""
        if raw_email:
            v = validate_email(raw_email)
            email_verdict = {"level": v.level.value, "reason": v.reason}
            # Keep VALID and freemail as a fallback contact, drop INVALID and role
            if v.level == VerdictLevel.VALID or (
                v.level == VerdictLevel.RISKY and v.reason == "freemail"
            ):
                clean_email = raw_email

        out.append({
            "dot_number": dot,
            "legal_name": (r.get("legal_name") or "").strip(),
            "city": (r.get("phy_city") or "").strip(),
            "state": (r.get("phy_state") or "").strip(),
            "safety_rating": "Conditional" if r.get("safety_rating") == "C" else "Unsatisfactory",
            "power_units": int(r.get("power_units") or 0),
            "officer_name": (r.get("company_officer_1") or "").strip(),
            "census_email": clean_email,
            "census_email_raw": raw_email,
            "census_email_verdict": email_verdict,
            "census_phone": (r.get("cell_phone") or "").strip(),
            "mcs150_date": (r.get("mcs150_date") or "").strip(),
            # Hints for the Apollo enrichment skill
            "apollo_org_domain_hint": email_domain(clean_email or raw_email),
            "apollo_target_titles": DECISION_MAKER_TITLES,
        })
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--min-units", type=int, default=10)
    parser.add_argument("--max-units", type=int, default=50)
    parser.add_argument("--limit", type=int, default=2000,
                        help="Max carriers to pull from census (default 2000)")
    parser.add_argument("--months-active", type=int, default=24,
                        help="Reject carriers whose MCS-150 is older than this")
    args = parser.parse_args()

    rows = fetch_census(args.min_units, args.max_units, args.limit, args.months_active)
    print(f"Census returned {len(rows)} rows")

    leads = transform(rows)
    print(f"Transformed {len(leads)} leads")

    # Summary stats
    with_clean_email = sum(1 for l in leads if l["census_email"])
    with_domain_hint = sum(1 for l in leads if l["apollo_org_domain_hint"])
    with_officer = sum(1 for l in leads if l["officer_name"])
    print(f"  with valid census email: {with_clean_email}")
    print(f"  with non-freemail domain (org-match usable): {with_domain_hint}")
    print(f"  with officer name: {with_officer}")

    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "filter": {
            "safety_rating": ["C", "U"],
            "power_units": [args.min_units, args.max_units],
            "months_active": args.months_active,
            "status_code": "A",
            "required_fields": ["company_officer_1", "email_address OR cell_phone"],
        },
        "stats": {
            "total": len(leads),
            "with_census_email": with_clean_email,
            "with_domain_hint": with_domain_hint,
            "with_officer": with_officer,
        },
        "decision_maker_titles": DECISION_MAKER_TITLES,
        "leads": leads,
    }

    with open(OUTPUT_FILE, "w") as f:
        json.dump(out, f, indent=2)
    print(f"\nWrote {OUTPUT_FILE}")
    print("\nNext: run the outreach-enrich-leads skill to Phase B (Apollo org-match) and Phase C (people-match)")


if __name__ == "__main__":
    main()
