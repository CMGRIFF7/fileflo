#!/usr/bin/env python3
"""
Michigan CRA Signal Hub — Pipeline Script
Phases 1-4: Signal Collection, Dedup, Enrichment, Lead Upload

Data source: Michigan Cannabis Regulatory Agency (CRA) Disciplinary Action Reports
  - Index page: https://www.michigan.gov/cra/disciplinary-actions
  - Current month HTML: /cra/disciplinary-actions/dar-report/[month-year]-dar
  - Older months: PDF files — requires pdfplumber (deferred to v2)

Table columns on HTML pages:
  ENF Record ID | Entity Name (DBA) | License Number(s) | City |
  Date Mailed | Disciplinary Action Imposed | Basis for Action

Outputs: pipeline/michigan_hub_output.json for Claude MCP contact-finding
"""
import argparse
import json
import os
import re
import time
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser

# ── Constants ────────────────────────────────────────────────────────────────
MEMORY_DIR = r"C:\Users\ChadGriffith\.claude\projects\C--Users-ChadGriffith-Downloads-fileflo-f11afbf5-main--2-\memory"
DEDUP_FILE = os.path.join(MEMORY_DIR, "michigan-processed-licenses.json")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = os.path.join(SCRIPT_DIR, "michigan_hub_output.json")

BATCH_CAP = 150        # smaller market than FMCSA
DEDUP_WINDOW_DAYS = 90

INSTANTLY_API_KEY = os.environ.get("INSTANTLY_API_KEY", "")
INSTANTLY_BASE_URL = "https://api.instantly.ai/api/v2"

MICHIGAN_CAMPAIGNS = {
    "violation":        "VIOLATION_CAMPAIGN_ID",       # placeholder — replace with real ID
    "expiring_license": "EXPIRING_CAMPAIGN_ID",        # placeholder — replace with real ID
    "new_licensee":     "NEW_LICENSEE_CAMPAIGN_ID",    # placeholder — replace with real ID
}

# Most-specific signal wins
PRIORITY_ORDER = ["violation", "expiring_license", "new_licensee"]

# Violation lookback window
VIOLATION_LOOKBACK_DAYS = 60

# CRA index page — lists all DAR report links
CRA_INDEX_URL = "https://www.michigan.gov/cra/disciplinary-actions"
CRA_BASE_URL  = "https://www.michigan.gov"


# ── DAR Table Parser ──────────────────────────────────────────────────────────
class DARTableParser(HTMLParser):
    """
    Parses the Michigan CRA DAR HTML page.
    The page has a single <table> with columns:
      ENF Record ID | Entity Name (DBA) | License Number(s) | City |
      Date Mailed | Disciplinary Action Imposed | Basis for Action
    """

    def __init__(self):
        super().__init__()
        self.rows = []           # list of lists (each inner list = one row's cells)
        self._in_table = False
        self._in_row = False
        self._in_cell = False
        self._current_row = []
        self._current_cell = []

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            self._in_table = True
        elif tag == "tr":
            if self._in_table:
                self._in_row = True
                self._current_row = []
        elif tag in ("td", "th"):
            if self._in_row:
                self._in_cell = True
                self._current_cell = []

    def handle_endtag(self, tag):
        if tag == "table":
            self._in_table = False
        elif tag == "tr":
            if self._in_row and self._current_row:
                self.rows.append(list(self._current_row))
            self._in_row = False
            self._current_row = []
        elif tag in ("td", "th"):
            if self._in_cell:
                cell_text = " ".join(self._current_cell).strip()
                # Collapse internal whitespace
                cell_text = re.sub(r"\s+", " ", cell_text).strip()
                self._current_row.append(cell_text)
            self._in_cell = False
            self._current_cell = []

    def handle_data(self, data):
        if self._in_cell:
            self._current_cell.append(data.strip())


# ── Helpers ───────────────────────────────────────────────────────────────────
def _http_get(url, timeout=30):
    """Fetch URL, return HTML string or None on failure."""
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                              "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
            }
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="ignore")
    except urllib.error.HTTPError as e:
        print(f"  HTTP {e.code}: {url}")
        return None
    except Exception as e:
        print(f"  Fetch failed ({type(e).__name__}): {url}")
        return None


def _discover_dar_html_links(index_html):
    """
    Parse the CRA index page to find HTML DAR report links.
    Returns list of full URLs (HTML pages only; PDFs are handled separately).

    Current month is published as an HTML page at:
      /cra/disciplinary-actions/dar-report/[month-year]-dar
    Previous months are PDFs (deferred to v2 when pdfplumber is available).
    """
    if not index_html:
        return []
    # Match links like /cra/disciplinary-actions/dar-report/march-2026-dar
    pattern = r'href=["\'](?:https://www\.michigan\.gov)?(/cra/disciplinary-actions/dar-report/[^"\'&\s]+)["\']'
    found = re.findall(pattern, index_html, re.IGNORECASE)
    html_links = []
    for path in found:
        if ".pdf" not in path.lower():
            full = CRA_BASE_URL + path if not path.startswith("http") else path
            if full not in html_links:
                html_links.append(full)
    return html_links


def _parse_dar_table(html, source_url):
    """
    Parse the DAR HTML page table into violation dicts.
    Expected columns (0-indexed):
      0: ENF Record ID
      1: Entity Name (DBA)
      2: License Number(s)
      3: City
      4: Date Mailed
      5: Disciplinary Action Imposed
      6: Basis for Action

    Returns list of violation dicts.
    """
    violations = []
    if not html:
        return violations

    parser = DARTableParser()
    try:
        parser.feed(html)
    except Exception as e:
        print(f"  DARTableParser error: {e}")
        return violations

    # Known header cell values — exact skip (case-insensitive)
    HEADER_CELLS = {
        "enf record id", "entity name (dba)", "license number(s)", "city",
        "date mailed", "disciplinary action imposed", "basis for action",
        "dar report",
    }
    data_rows = 0

    for row in parser.rows:
        if len(row) < 3:
            continue
        # Skip header/title rows: first cell exactly matches a known header value
        first_norm = row[0].lower().strip()
        if first_norm in HEADER_CELLS:
            continue
        # Also skip rows where ALL cells are short header-like values
        if all(c.lower().strip() in HEADER_CELLS for c in row if c.strip()):
            continue

        enf_id       = row[0].strip() if len(row) > 0 else ""
        entity_raw   = row[1].strip() if len(row) > 1 else ""
        license_nums = row[2].strip() if len(row) > 2 else ""
        city         = row[3].strip() if len(row) > 3 else ""
        date_mailed  = row[4].strip() if len(row) > 4 else ""
        action       = row[5].strip() if len(row) > 5 else ""
        basis        = row[6].strip() if len(row) > 6 else ""

        # Parse entity name + DBA: "Legal Name (DBA Name)"
        licensee_name = entity_raw
        dba_name = ""
        dba_match = re.match(r"^(.*?)\s*\(([^)]+)\)\s*$", entity_raw)
        if dba_match:
            licensee_name = dba_match.group(1).strip()
            dba_name = dba_match.group(2).strip()

        # Parse date: "03/03/2026" -> "March 03, 2026"
        violation_date = date_mailed
        try:
            dt = datetime.strptime(date_mailed, "%m/%d/%Y")
            violation_date = dt.strftime("%B %d, %Y")
        except Exception:
            pass

        # Each row may have multiple license numbers (comma-separated)
        # We emit one violation per license number
        license_list = [l.strip() for l in re.split(r"[,;]", license_nums) if l.strip()]
        if not license_list:
            license_list = [""]   # emit at least one record

        for lic in license_list:
            violation_type = f"{action} — {basis}" if basis else action
            violations.append({
                "enf_id":        enf_id,
                "license_number": lic,
                "licensee_name": dba_name or licensee_name,
                "legal_name":    licensee_name,
                "dba_name":      dba_name,
                "violation_type": violation_type[:300],
                "penalty":       "",    # not in table; enriched from detail if needed
                "violation_date": violation_date,
                "city":          city,
                "state":         "MI",
                "source_url":    source_url,
            })
            data_rows += 1

    print(f"  Parsed {data_rows} violation records from {len(parser.rows)} table rows")
    return violations


# ── Phase 1: Signal Collection ────────────────────────────────────────────────

def collect_dar_signals():
    """
    Fetch the CRA index page, discover current HTML DAR pages, parse them.
    Returns list of violation dicts within VIOLATION_LOOKBACK_DAYS.

    Also constructs fallback URLs for the current and previous month in case
    they aren't linked yet from the index (e.g., new month just published).
    """
    print(f"Fetching CRA index: {CRA_INDEX_URL}")
    index_html = _http_get(CRA_INDEX_URL)

    # Discover HTML DAR pages from index
    html_links = _discover_dar_html_links(index_html)
    print(f"  Found {len(html_links)} HTML DAR page(s) on index: {html_links}")

    # Fallback: construct current + previous month URLs in case they aren't linked yet
    now = datetime.now(timezone.utc)
    fallback_urls = []
    for delta_months in range(0, 3):
        target = now - timedelta(days=30 * delta_months)
        slug = target.strftime("%B-%Y").lower()  # e.g. "april-2026"
        url = f"{CRA_BASE_URL}/cra/disciplinary-actions/dar-report/{slug}-dar"
        if url not in html_links:
            fallback_urls.append(url)

    all_urls = html_links + fallback_urls
    print(f"  Checking {len(all_urls)} DAR URL(s) total (index + fallback)")

    # Cutoff date for VIOLATION_LOOKBACK_DAYS filter
    cutoff_dt = datetime.now(timezone.utc) - timedelta(days=VIOLATION_LOOKBACK_DAYS)

    all_violations = {}   # license_number (or enf_id) -> violation dict

    for url in all_urls:
        print(f"  Fetching DAR: {url}")
        html = _http_get(url)
        if not html:
            continue
        violations = _parse_dar_table(html, url)

        for v in violations:
            # Date filter: only keep violations within lookback window
            date_str = v.get("violation_date", "")
            try:
                vd = datetime.strptime(date_str, "%B %d, %Y").replace(tzinfo=timezone.utc)
                if vd < cutoff_dt:
                    continue
            except Exception:
                pass   # Can't parse date — include anyway

            # Dedup key: prefer license number, fall back to enf_id
            key = v.get("license_number") or v.get("enf_id") or ""
            if key and key not in all_violations:
                all_violations[key] = v
            elif not key:
                # Use licensee+city as fallback key
                fb_key = f"{v.get('licensee_name','').lower()}|{v.get('city','').lower()}"
                if fb_key and fb_key not in all_violations:
                    all_violations[fb_key] = v

        time.sleep(1.0)   # polite crawl rate

    results = list(all_violations.values())
    print(f"Phase 1a (DAR violations): {len(results)} unique licenses within {VIOLATION_LOOKBACK_DAYS} days")
    return results


def collect_signals():
    """
    Collect all three signals and return unified list of licensee dicts.

    v1 implementation:
    - Signal 1 (violation): scrapes HTML DAR pages — ACTIVE
    - Signal 2 (expiring_license): requires Accela portal bulk export — DEFERRED v2
    - Signal 3 (new_licensee): requires Accela portal bulk export — DEFERRED v2
    """
    all_licensees = {}  # key -> licensee dict

    # ── Signal 1: Recent violations from DAR ──────────────────────────────────
    violations = collect_dar_signals()
    for v in violations:
        key = v.get("license_number") or v.get("enf_id") or f"{v.get('licensee_name','').lower()}|{v.get('city','').lower()}"
        if not key:
            continue
        if key not in all_licensees:
            all_licensees[key] = {
                "license_number":  v.get("license_number", ""),
                "enf_id":          v.get("enf_id", ""),
                "licensee_name":   v.get("licensee_name", ""),
                "legal_name":      v.get("legal_name", ""),
                "dba_name":        v.get("dba_name", ""),
                "city":            v.get("city", ""),
                "state":           "MI",
                "signals":         [],
                "violation_type":  v.get("violation_type", ""),
                "violation_date":  v.get("violation_date", ""),
                "penalty":         v.get("penalty", ""),
                "license_expiry":  "",
                "license_issued":  "",
                "email":           "",
                "phone":           "",
                "first_name":      "",
                "last_name":       "",
                "title":           "",
                "website":         "",
                "source_url":      v.get("source_url", ""),
            }
        lic_rec = all_licensees[key]
        if "violation" not in lic_rec["signals"]:
            lic_rec["signals"].append("violation")
        if v.get("violation_type"):
            lic_rec["violation_type"] = v["violation_type"]
        if v.get("violation_date"):
            lic_rec["violation_date"] = v["violation_date"]

    # ── Signal 2 & 3: License expiry / new licensee — deferred to v2 ─────────
    # The Accela portal (aca-prod.accela.com/MICHIGAN) is JavaScript-heavy and
    # requires authentication for bulk data. v2 options:
    #   a) Use Michigan's open data portal if CRA publishes a dataset
    #   b) Headless browser (Playwright) to paginate Accela search results
    #   c) Michigan CRA direct data partnership / FOIA request
    print("Phase 1b (expiring_license): SKIPPED — Accela portal requires auth; deferred to v2")
    print("Phase 1c (new_licensee): SKIPPED — Accela portal requires auth; deferred to v2")

    results = list(all_licensees.values())
    print(f"Phase 1 complete: {len(results)} unique licensees with signals")
    return results


# ── Phase 2: Cross-Run Deduplication ─────────────────────────────────────────
def filter_seen_licenses(licensees):
    """Skip licenses processed in last DEDUP_WINDOW_DAYS days."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=DEDUP_WINDOW_DAYS)

    processed = {}
    if os.path.exists(DEDUP_FILE):
        with open(DEDUP_FILE) as f:
            try:
                processed = json.load(f)
            except json.JSONDecodeError:
                processed = {}

    fresh, skipped = [], 0
    for lic in licensees:
        key = lic.get("license_number") or lic.get("enf_id") or lic.get("licensee_name", "").lower()
        if key in processed:
            try:
                pd_str = processed[key].get("processed_date", "1970-01-01")
                pd = datetime.fromisoformat(pd_str)
                if pd.tzinfo is None:
                    pd = pd.replace(tzinfo=timezone.utc)
                if pd > cutoff:
                    skipped += 1
                    continue
            except Exception:
                pass
        fresh.append(lic)

    print(f"Phase 2: {skipped} licenses skipped (seen <={DEDUP_WINDOW_DAYS} days), {len(fresh)} fresh")
    return fresh


# ── Phase 3: Contact Enrichment (prep) ───────────────────────────────────────
def enrich_contacts(licensees):
    """
    Prepare licensees for contact enrichment.

    Contact enrichment chain (mirrors fmcsa_hub.py Phase 3):
    1. CRA license data for contact info  — minimal in DAR; not available v1
    2. Web search for owner/COO name + email  — SKILL.md handles via WebSearch MCP
    3. Apollo people search  — SKILL.md handles via apollo MCP
    4. Email pattern fallback (firstname@domain)  — SKILL.md applies after above

    This function marks each record so SKILL.md knows what to do next.
    """
    enriched = []
    for lic in licensees:
        contact_found = bool(lic.get("email") or lic.get("phone"))
        lic["contact_found"] = contact_found
        lic["needs_enrichment"] = not contact_found
        enriched.append(lic)

    needs = sum(1 for l in enriched if l.get("needs_enrichment"))
    print(f"Phase 3: {len(enriched)} licensees prepared, {needs} need contact enrichment by SKILL.md")
    return enriched


# ── Phase 4: Lead Scoring ─────────────────────────────────────────────────────
def score_licensees(licensees):
    """Apply scoring rubric. Sort highest score first."""
    for lic in licensees:
        score = 0
        sigs = lic.get("signals", [])

        if "violation" in sigs:
            score += 5
            # Fine in violation type = more pain
            vtype = lic.get("violation_type", "").lower()
            if "fine" in vtype:
                score += 2
            if "revocation" in vtype or "suspension" in vtype:
                score += 3

        if "expiring_license" in sigs:
            score += 4
            expiry = lic.get("license_expiry", "")
            if expiry:
                try:
                    exp_date = datetime.strptime(expiry, "%Y-%m-%d")
                    days_until = (exp_date - datetime.now()).days
                    if days_until <= 30:
                        score += 2
                    elif days_until <= 45:
                        score += 1
                except Exception:
                    pass

        if "new_licensee" in sigs:
            score += 3

        if lic.get("contact_found"):
            score += 1

        lic["lead_score"] = score

    licensees.sort(key=lambda x: x["lead_score"], reverse=True)
    top = licensees[0]["lead_score"] if licensees else 0
    print(f"Phase 4 complete: {len(licensees)} licensees scored. Top score: {top}")
    return licensees


# ── Campaign Assignment ───────────────────────────────────────────────────────
def assign_campaign(licensee):
    """Return (campaign_id, signal_name) based on highest-priority signal."""
    for signal in PRIORITY_ORDER:
        if signal in licensee.get("signals", []):
            return MICHIGAN_CAMPAIGNS[signal], signal
    return None, None


# ── Instantly Upload ──────────────────────────────────────────────────────────
def _instantly_request(method, path, payload=None):
    """
    Make an Instantly API v2 request.
    Mirrors the HTTP pattern used by the FMCSA hub SKILL.md.
    """
    if not INSTANTLY_API_KEY:
        raise ValueError("INSTANTLY_API_KEY environment variable not set")

    url = f"{INSTANTLY_BASE_URL}{path}"
    data = json.dumps(payload or {}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Content-Type": "application/json",
            "Authorization": INSTANTLY_API_KEY,
        }
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def build_instantly_payload(licensee):
    """
    Build Instantly lead payload from licensee dict.
    IMPORTANT: open_tracking and click_tracking are ALWAYS False.
    Mirrors fmcsa_hub.py payload structure.
    """
    custom_vars = {
        "license_number":  licensee.get("license_number", ""),
        "licensee_name":   licensee.get("licensee_name", ""),
        "dba_name":        licensee.get("dba_name", ""),
        "violation_type":  licensee.get("violation_type", ""),
        "violation_date":  licensee.get("violation_date", ""),
        "penalty":         licensee.get("penalty", ""),
        "city":            licensee.get("city", ""),
        "signal_used":     licensee.get("signal_used", ""),
        "lead_score":      str(licensee.get("lead_score", 0)),
        "enf_id":          licensee.get("enf_id", ""),
    }

    return {
        "campaign_id":       licensee.get("campaign_id", ""),
        "email":             licensee.get("email", ""),
        "first_name":        licensee.get("first_name", ""),
        "last_name":         licensee.get("last_name", ""),
        "company_name":      licensee.get("licensee_name", ""),
        "custom_variables":  custom_vars,
        # Tracking NEVER enabled — project-wide policy
        "open_tracking":  False,
        "click_tracking": False,
    }


def upload_to_instantly(licensees, dry_run=False):
    """
    Upload enriched licensees to assigned Instantly campaigns.
    Skips: no email, placeholder campaign IDs.
    Never enables tracking.
    """
    uploaded = 0
    skipped_no_email = 0
    skipped_placeholder = 0

    placeholder_ids = set(MICHIGAN_CAMPAIGNS.values())

    for lic in licensees:
        campaign_id = lic.get("campaign_id", "")
        email = lic.get("email", "").strip()

        if not email:
            skipped_no_email += 1
            continue

        if campaign_id in placeholder_ids or not campaign_id:
            skipped_placeholder += 1
            continue

        payload = build_instantly_payload(lic)

        if dry_run:
            print(f"  [DRY RUN] Would upload: {email} -> campaign {campaign_id[:8]}...")
            uploaded += 1
            continue

        try:
            _instantly_request("POST", "/leads", payload)
            uploaded += 1
            time.sleep(0.2)
        except Exception as e:
            print(f"  WARNING: Instantly upload failed for {email}: {e}")

    print(f"Instantly upload: {uploaded} uploaded, "
          f"{skipped_no_email} skipped (no email), "
          f"{skipped_placeholder} skipped (placeholder campaign ID)")
    return uploaded


# ── Processed-Licenses Update ─────────────────────────────────────────────────
def mark_licenses_processed(licensees, run_label):
    """Persist processed license numbers to dedup file with today's date."""
    processed = {}
    if os.path.exists(DEDUP_FILE):
        with open(DEDUP_FILE) as f:
            try:
                processed = json.load(f)
            except json.JSONDecodeError:
                processed = {}

    today = datetime.now().strftime("%Y-%m-%d")
    for lic in licensees:
        key = lic.get("license_number") or lic.get("enf_id") or lic.get("licensee_name", "").lower()
        if not key:
            continue
        processed[key] = {
            "processed_date": today,
            "run":            run_label,
            "lead_score":     lic.get("lead_score", 0),
            "campaign_id":    lic.get("campaign_id"),
            "signal_used":    lic.get("signal_used"),
            "contact_found":  lic.get("contact_found", False),
        }

    with open(DEDUP_FILE, "w") as f:
        json.dump(processed, f, indent=2)
    print(f"Marked {len(licensees)} licenses as processed in michigan-processed-licenses.json")


# ── Entry Point ───────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Michigan CRA Cannabis Signal Hub Pipeline")
    parser.add_argument("--dry-run", action="store_true",
                        help="Fetch and parse signals, print output, do NOT upload to Instantly")
    parser.add_argument("--run", default="AM",
                        help="Run label for logging (default: AM)")
    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"Michigan CRA Signal Hub -- {args.run} Run{'  [DRY RUN]' if args.dry_run else ''}")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Batch cap: {BATCH_CAP} | Dedup window: {DEDUP_WINDOW_DAYS} days")
    print(f"{'='*60}\n")

    # Phase 1: Collect signals
    licensees = collect_signals()

    # Phase 2: Dedup
    licensees = filter_seen_licenses(licensees)

    if not licensees:
        print("No fresh licensees to process. Exiting.")
        with open(OUTPUT_FILE, "w") as f:
            json.dump({
                "run":           args.run,
                "dry_run":       args.dry_run,
                "timestamp":     datetime.now().isoformat(),
                "total_enriched": 0,
                "licensees":     [],
            }, f)
        return

    # Apply batch cap (prioritize violations first)
    licensees.sort(key=lambda l: (0 if "violation" in l.get("signals", []) else 1))
    if len(licensees) > BATCH_CAP:
        print(f"Batch cap: {len(licensees)} licensees -> taking top {BATCH_CAP}")
        licensees = licensees[:BATCH_CAP]

    # Phase 3: Contact enrichment prep
    licensees = enrich_contacts(licensees)

    # Phase 4: Lead scoring
    licensees = score_licensees(licensees)

    # Campaign assignment
    for lic in licensees:
        campaign_id, signal_used = assign_campaign(lic)
        lic["campaign_id"] = campaign_id
        lic["signal_used"] = signal_used

    uploadable = [l for l in licensees if l.get("campaign_id")]

    # Mark processed BEFORE upload so re-runs skip them
    if not args.dry_run:
        mark_licenses_processed(licensees, args.run)

    # Upload (or dry-run print)
    uploaded = upload_to_instantly(uploadable, dry_run=args.dry_run)

    # Write output file for SKILL.md agent
    output = {
        "run":             args.run,
        "dry_run":         args.dry_run,
        "timestamp":       datetime.now().isoformat(),
        "total_collected": len(licensees),
        "total_uploadable": len(uploadable),
        "uploaded":        uploaded,
        "signal_breakdown": {
            signal: sum(1 for l in uploadable if l.get("signal_used") == signal)
            for signal in PRIORITY_ORDER
        },
        "licensees": licensees,
    }

    with open(OUTPUT_FILE, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\n{'='*60}")
    if args.dry_run:
        print(f"DRY RUN complete: {len(licensees)} licensees collected and scored")
        print(f"Signal breakdown: {output['signal_breakdown']}")
        print()
        print("NOTES:")
        print("  - Replace placeholder campaign IDs in MICHIGAN_CAMPAIGNS before live run")
        print("    VIOLATION_CAMPAIGN_ID, EXPIRING_CAMPAIGN_ID, NEW_LICENSEE_CAMPAIGN_ID")
        print("  - Contact enrichment (email/phone) handled by SKILL.md via WebSearch + Apollo MCP")
        print("  - expiring_license + new_licensee signals deferred to v2")
        print("    (needs Accela portal auth or Michigan open data dataset)")
        print("  - Historical PDFs: install pdfplumber to parse months older than current HTML page")
    else:
        print(f"Run complete: {uploaded} leads uploaded to Instantly")
        print(f"Signal breakdown: {output['signal_breakdown']}")
    print(f"Output saved to: {OUTPUT_FILE}")
    print(f"{'='*60}\n")

    # Print sample output for dry-run
    if args.dry_run and licensees:
        print("Sample output (first 5 licensees):")
        for lic in licensees[:5]:
            print(json.dumps({
                k: lic[k]
                for k in ["license_number", "enf_id", "licensee_name", "dba_name",
                          "city", "signals", "violation_type", "violation_date",
                          "lead_score", "signal_used"]
                if k in lic
            }, indent=2))
            print()


if __name__ == "__main__":
    main()
