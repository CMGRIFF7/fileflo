"""
MayDay Sprint - Create all 6 Instantly campaigns via MCP HTTP session.
Run: python pipeline/create_mayday_campaigns.py
"""
import json, requests, time, sys

MCP_URL = "https://mcp.instantly.ai/mcp/ZWU5MTFiNjEtZDg3YS00ZjcwLTlkMDEtYzVkMjI4ZGEwMzViOlNXbUpJZ0JBZ3JBWA=="

# Account assignments by domain group (25 accounts total)
ACCOUNTS = {
    "fmcsa_hub": [
        "brandon@nowcompliance.org", "haley@nowcompliance.org",
        "karen@nowcompliance.org", "megan@nowcompliance.org",
        "chad@fileflobinder.com"
    ],
    "osha": [
        "brandon@lookcompliance.com", "haley@lookcompliance.com",
        "karen@lookcompliance.com", "megan@lookcompliance.com"
    ],
    "epa": [
        "brandon@nowregulation.com", "haley@nowregulation.com",
        "karen@nowregulation.com", "megan@nowregulation.com"
    ],
    "healthcare": [
        "brandon@instantoperations.com", "haley@instantoperations.com",
        "karen@instantoperations.com", "megan@instantoperations.com"
    ],
    "cannabis": [
        "chad@tryfileflo.com", "cgriffith@tryfileflo.com",
        "chadgriffith@tryfileflo.com", "griffith@tryfileflo.com"
    ],
    "faa": [
        "chad@meetfileflo.org", "cgriffith@meetfileflo.org",
        "chadgriffith@meetfileflo.org", "griffith@meetfileflo.org"
    ],
}

PS_LINE = "<div>&nbsp;</div><div>P.S. Through May 1, annual plan is $1,990 (normally $2,990). Run the free tool first, then decide.</div>"

CAMPAIGNS = [
    {
        "key": "fmcsa_hub",
        "name": "MayDay V3 - FMCSA Signal Hub",
        "tool_url": "getfileflo.com/tools/fmcsa-audit-readiness-score",
        "subjects": [
            "{{companyName}} FMCSA carrier record - free audit check",
            "Re: {{companyName}} FMCSA record",
            "Still worth running the free score, {{firstName}}",
            "Last note - FMCSA audit tool"
        ],
        "bodies": [
            f"""<div>{{{{firstName}}}},</div><div>&nbsp;</div><div>Pulled {{{{companyName}}}}'s DOT record today and ran it through the FMCSA carrier readiness tool.</div><div>&nbsp;</div><div>Free, 3 minutes, no login:<br/>getfileflo.com/tools/fmcsa-audit-readiness-score</div><div>&nbsp;</div><div>Shows exactly what a compliance auditor sees: safety rating, OOS status, insurance status, and inspection history.</div><div>&nbsp;</div><div>Even a clean public SAFER record can hide real gaps. DOT auditors go deeper - driver qualification files, maintenance logs, hours of service records, drug test results. None of that appears in the database.</div><div>&nbsp;</div><div>If anything flags, reply and I'll walk through what FileFlo covers for your operation.</div><div>&nbsp;</div><div>Chad Griffith<br/>FileFlo</div>{PS_LINE}""",
            "<div>{{firstName}},</div><div>&nbsp;</div><div>Circling back on the FMCSA readiness check for {{companyName}}. Still free, still 3 minutes:</div><div>getfileflo.com/tools/fmcsa-audit-readiness-score</div><div>&nbsp;</div><div>Shows your current public audit exposure. DOT auditors go well beyond what the public record shows - if you want a full picture, run the tool and reply with what it shows.</div><div>&nbsp;</div><div>Chad</div>",
            "<div>{{firstName}},</div><div>&nbsp;</div><div>One more. Free FMCSA audit score:</div><div>getfileflo.com/tools/fmcsa-audit-readiness-score</div><div>&nbsp;</div><div>No pitch, no signup. Just your public DOT record and what it means before an auditor shows up.</div><div>&nbsp;</div><div>Chad</div>",
            f"<div>{{{{firstName}}}},</div><div>&nbsp;</div><div>Last note. Free FMCSA carrier check:</div><div>getfileflo.com/tools/fmcsa-audit-readiness-score</div><div>&nbsp;</div><div>MayDay rate ($1,990/yr, $1,000 off) closes May 1. Run the tool first, see what it shows, then decide if FileFlo makes sense for {{{{companyName}}}}.</div><div>&nbsp;</div><div>Chad</div>"
        ]
    },
    {
        "key": "osha",
        "name": "MayDay V3 - OSHA Contractor Snapshot",
        "tool_url": "getfileflo.com/tools/osha-inspection",
        "subjects": [
            "{{companyName}} OSHA inspection record - free check",
            "Re: {{companyName}} OSHA record",
            "Still worth running the OSHA check, {{firstName}}",
            "Last note - OSHA inspection tool"
        ],
        "bodies": [
            f"""<div>{{{{firstName}}}},</div><div>&nbsp;</div><div>Ran {{{{companyName}}}} through the public OSHA inspection database. It pulls every inspection, citation type, and penalty on record.</div><div>&nbsp;</div><div>Free, 2 minutes, no account needed:<br/>getfileflo.com/tools/osha-inspection</div><div>&nbsp;</div><div>Clean record is worth confirming. Open citations or serious/willful findings are worth knowing before OSHA schedules a follow-up.</div><div>&nbsp;</div><div>Worth noting: OSHA's 2026 National Emphasis Programs are targeting your industry this year - heat illness prevention, falls, and silica exposure are active focus areas. New electronic recordkeeping requirements also hit in March. The tool shows what inspectors see in the database; it does not show your 300 log, written safety programs, or training records - which is exactly what they ask for on arrival.</div><div>&nbsp;</div><div>Chad Griffith<br/>FileFlo</div>{PS_LINE}""",
            "<div>{{firstName}},</div><div>&nbsp;</div><div>Following up on the OSHA inspection lookup for {{companyName}}. Still free:</div><div>getfileflo.com/tools/osha-inspection</div><div>&nbsp;</div><div>2026 NEPs mean inspectors are actively targeting your industry. The tool shows your public record - what they see before they walk in.</div><div>&nbsp;</div><div>Chad</div>",
            "<div>{{firstName}},</div><div>&nbsp;</div><div>One more - free OSHA inspection snapshot:</div><div>getfileflo.com/tools/osha-inspection</div><div>&nbsp;</div><div>Takes 90 seconds and tells you exactly where {{companyName}} stands in the public record.</div><div>&nbsp;</div><div>Chad</div>",
            f"<div>{{{{firstName}}}},</div><div>&nbsp;</div><div>Last note. Free OSHA inspection tool:</div><div>getfileflo.com/tools/osha-inspection</div><div>&nbsp;</div><div>MayDay rate ($1,990/yr, $1,000 off) closes May 1. Run the tool first, see what it shows, then decide if FileFlo makes sense for {{{{companyName}}}}.</div><div>&nbsp;</div><div>Chad</div>"
        ]
    },
    {
        "key": "epa",
        "name": "MayDay V3 - EPA Compliance Snapshot",
        "tool_url": "getfileflo.com/tools/epa-compliance",
        "subjects": [
            "{{companyName}} EPA compliance check - free",
            "Re: {{companyName}} EPA record",
            "Still worth the EPA check, {{firstName}}",
            "Last note - EPA compliance tool"
        ],
        "bodies": [
            f"""<div>{{{{firstName}}}},</div><div>&nbsp;</div><div>Ran {{{{companyName}}}} through the EPA ECHO enforcement database. It shows permit status, violation history, inspection dates, and any enforcement actions on record.</div><div>&nbsp;</div><div>Free, 2 minutes:<br/>getfileflo.com/tools/epa-compliance</div><div>&nbsp;</div><div>A few things to flag for 2026: EPA is expanding PFAS reporting requirements, updated Clean Water Act stormwater rules are in effect, and the agency's National Enforcement Initiatives are actively targeting chemical facilities and agricultural operations. ECHO tracks formal violations - it does not show your Tier II reports, SPCC plans, or hazardous waste manifests. Those are what an inspector reviews.</div><div>&nbsp;</div><div>Chad Griffith<br/>FileFlo</div>{PS_LINE}""",
            "<div>{{firstName}},</div><div>&nbsp;</div><div>Circling back on the EPA compliance check for {{companyName}}. Still free:</div><div>getfileflo.com/tools/epa-compliance</div><div>&nbsp;</div><div>Shows your public enforcement record. EPA's 2026 enforcement priorities are active - worth knowing where you stand.</div><div>&nbsp;</div><div>Chad</div>",
            "<div>{{firstName}},</div><div>&nbsp;</div><div>One more - free EPA compliance snapshot:</div><div>getfileflo.com/tools/epa-compliance</div><div>&nbsp;</div><div>Your public ECHO record in 2 minutes. No signup required.</div><div>&nbsp;</div><div>Chad</div>",
            f"<div>{{{{firstName}}}},</div><div>&nbsp;</div><div>Last note. Free EPA compliance tool:</div><div>getfileflo.com/tools/epa-compliance</div><div>&nbsp;</div><div>MayDay rate ($1,990/yr, $1,000 off) closes May 1. Run the tool first, then decide if FileFlo makes sense for {{{{companyName}}}}.</div><div>&nbsp;</div><div>Chad</div>"
        ]
    },
    {
        "key": "healthcare",
        "name": "MayDay V3 - Healthcare Provider License Check",
        "tool_url": "getfileflo.com/tools/provider-license",
        "subjects": [
            "{{companyName}} NPI record - free provider check",
            "Re: {{companyName}} provider license check",
            "Still worth running the provider check, {{firstName}}",
            "Last note - provider license tool"
        ],
        "bodies": [
            f"""<div>{{{{firstName}}}},</div><div>&nbsp;</div><div>Ran {{{{companyName}}}} through the NPI registry. It shows active provider records, taxonomy/specialty classifications, and deactivation status.</div><div>&nbsp;</div><div>Free, 2 minutes:<br/>getfileflo.com/tools/provider-license</div><div>&nbsp;</div><div>Worth knowing: NPI is a registration number - it does not track state license expirations, DEA schedule status, board certifications, or credentialing deadlines. A provider with an expired state license still has an active NPI. CMS credentialing reform requirements for Medicare-participating providers are also hitting in 2026, along with expanded state licensing compact coverage for nurses and physicians.</div><div>&nbsp;</div><div>If you're managing credentialing manually across multiple providers, reply and I'll show you what FileFlo tracks that the NPI registry does not.</div><div>&nbsp;</div><div>Chad Griffith<br/>FileFlo</div>{PS_LINE}""",
            "<div>{{firstName}},</div><div>&nbsp;</div><div>Following up on the NPI provider check for {{companyName}}. Still free:</div><div>getfileflo.com/tools/provider-license</div><div>&nbsp;</div><div>NPI shows registration status - not state licenses, DEA, or board certs. That gap is where credentialing problems actually happen.</div><div>&nbsp;</div><div>Chad</div>",
            "<div>{{firstName}},</div><div>&nbsp;</div><div>One more - free provider license check:</div><div>getfileflo.com/tools/provider-license</div><div>&nbsp;</div><div>Takes 90 seconds. Shows your NPI record and what it does not cover.</div><div>&nbsp;</div><div>Chad</div>",
            f"<div>{{{{firstName}}}},</div><div>&nbsp;</div><div>Last note. Free provider license tool:</div><div>getfileflo.com/tools/provider-license</div><div>&nbsp;</div><div>MayDay rate ($1,990/yr, $1,000 off) closes May 1. Run the tool first, then decide if FileFlo makes sense for {{{{companyName}}}}.</div><div>&nbsp;</div><div>Chad</div>"
        ]
    },
    {
        "key": "cannabis",
        "name": "MayDay V3 - Michigan Cannabis License Check",
        "tool_url": "getfileflo.com/tools/michigan-cannabis",
        "subjects": [
            "{{companyName}} Michigan cannabis license - free check",
            "Re: {{companyName}} CRA license status",
            "Still worth the license check, {{firstName}}",
            "Last note - Michigan cannabis license tool"
        ],
        "bodies": [
            f"""<div>{{{{firstName}}}},</div><div>&nbsp;</div><div>Ran {{{{companyName}}}} through the LARA cannabis license database. It shows license type, current status, expiration date, and days to renewal.</div><div>&nbsp;</div><div>Free, no login:<br/>getfileflo.com/tools/michigan-cannabis</div><div>&nbsp;</div><div>License status is just the starting point. CRA compliance goes far beyond it - inspectors review testing records, employee licenses, and seed-to-sale documentation on every audit. None of that appears in the LARA database. Michigan's CRA also has revised compliance rules effective 2026 and updated testing and labeling requirements that most operators have not fully documented yet.</div><div>&nbsp;</div><div>Chad Griffith<br/>FileFlo</div>{PS_LINE}""",
            "<div>{{firstName}},</div><div>&nbsp;</div><div>Following up on the Michigan cannabis license check for {{companyName}}. Still free:</div><div>getfileflo.com/tools/michigan-cannabis</div><div>&nbsp;</div><div>Shows your LARA status and what CRA auditors look for beyond it. Worth 2 minutes.</div><div>&nbsp;</div><div>Chad</div>",
            "<div>{{firstName}},</div><div>&nbsp;</div><div>One more - free Michigan cannabis license tool:</div><div>getfileflo.com/tools/michigan-cannabis</div><div>&nbsp;</div><div>Your LARA record in 60 seconds. No signup required.</div><div>&nbsp;</div><div>Chad</div>",
            f"<div>{{{{firstName}}}},</div><div>&nbsp;</div><div>Last note. Free Michigan cannabis license check:</div><div>getfileflo.com/tools/michigan-cannabis</div><div>&nbsp;</div><div>MayDay rate ($1,990/yr, $1,000 off) closes May 1. Run the tool first, then decide if FileFlo makes sense for {{{{companyName}}}}.</div><div>&nbsp;</div><div>Chad</div>"
        ]
    },
    {
        "key": "faa",
        "name": "MayDay V3 - FAA Enforcement Lookup",
        "tool_url": "getfileflo.com/tools/faa-enforcement",
        "subjects": [
            "{{companyName}} FAA enforcement history - free check",
            "Re: {{companyName}} FAA record",
            "Still worth the FAA check, {{firstName}}",
            "Last note - FAA enforcement tool"
        ],
        "bodies": [
            f"""<div>{{{{firstName}}}},</div><div>&nbsp;</div><div>Ran {{{{companyName}}}} through the FAA published enforcement reports database.</div><div>&nbsp;</div><div>Free tool:<br/>getfileflo.com/tools/faa-enforcement</div><div>&nbsp;</div><div>Important note on the data: FAA enforcement cases take 6-18 months from incident to published report. What the tool shows is historical. It does not reflect current certificate status, crew training records, or OpSpecs compliance - which is exactly what an FSDO audit checks.</div><div>&nbsp;</div><div>A few 2026 developments worth knowing: the SMS (Safety Management System) mandate for Part 135 operators takes effect this year, ADS-B enforcement is expanding to international operations, and the FAA Reauthorization Act 2024 introduced new requirements still being implemented. None of these appear in the public enforcement database.</div><div>&nbsp;</div><div>Chad Griffith<br/>FileFlo</div>{PS_LINE}""",
            "<div>{{firstName}},</div><div>&nbsp;</div><div>Following up on the FAA enforcement check for {{companyName}}. Still free:</div><div>getfileflo.com/tools/faa-enforcement</div><div>&nbsp;</div><div>Remember: published reports are 6-18 months behind actual enforcement actions. The tool shows historical cases - current FSDO compliance is a different picture.</div><div>&nbsp;</div><div>Chad</div>",
            "<div>{{firstName}},</div><div>&nbsp;</div><div>One more - free FAA enforcement lookup:</div><div>getfileflo.com/tools/faa-enforcement</div><div>&nbsp;</div><div>Historical published cases plus context on what FSDO actually audits. No signup.</div><div>&nbsp;</div><div>Chad</div>",
            f"<div>{{{{firstName}}}},</div><div>&nbsp;</div><div>Last note. Free FAA enforcement tool:</div><div>getfileflo.com/tools/faa-enforcement</div><div>&nbsp;</div><div>MayDay rate ($1,990/yr, $1,000 off) closes May 1. Run the tool first, then decide if FileFlo makes sense for {{{{companyName}}}}.</div><div>&nbsp;</div><div>Chad</div>"
        ]
    },
]


def init_session() -> str:
    resp = requests.post(
        MCP_URL,
        json={"jsonrpc": "2.0", "method": "initialize",
              "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                         "clientInfo": {"name": "mayday-launcher", "version": "1.0"}},
              "id": 0},
        headers={"Content-Type": "application/json", "Accept": "application/json, text/event-stream"},
        stream=True,
        timeout=30
    )
    session_id = resp.headers.get("mcp-session-id", "")
    if not session_id:
        raise RuntimeError(f"No session ID in response headers: {dict(resp.headers)}")
    print(f"Session: {session_id}")
    return session_id


def mcp_call(session_id: str, tool: str, args: dict, call_id: int) -> dict:
    resp = requests.post(
        MCP_URL,
        json={"jsonrpc": "2.0", "method": "tools/call",
              "params": {"name": tool, "arguments": args}, "id": call_id},
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "mcp-session-id": session_id
        },
        stream=True,
        timeout=60
    )
    raw = b""
    for chunk in resp.iter_content(chunk_size=None):
        raw += chunk
    text = raw.decode("utf-8", errors="replace")
    for line in text.split("\n"):
        if line.startswith("data:"):
            try:
                return json.loads(line[5:].strip())
            except Exception:
                pass
    return {"raw": text}


def create_campaign(session_id: str, camp: dict, call_id: int) -> str:
    args = {
        "params": {
            "name": camp["name"],
            "subject": camp["subjects"][0],
            "body": camp["bodies"][0],
            "sequence_steps": 4,
            "sequence_subjects": camp["subjects"],
            "sequence_bodies": camp["bodies"],
            "step_delay_days": 4,
            "email_list": ACCOUNTS[camp["key"]],
            "timing_from": "08:30",
            "timing_to": "13:00",
            "daily_limit": 40,
            "email_gap": 4,
            "track_opens": False,
            "track_clicks": False,
            "stop_on_reply": True,
            "stop_on_auto_reply": True,
        }
    }
    result = mcp_call(session_id, "create_campaign", args, call_id)
    text = ""
    try:
        text = result["result"]["content"][0]["text"]
        data = json.loads(text)
        campaign_id = data.get("id") or data.get("campaign_id") or str(data)
        return campaign_id
    except Exception as e:
        return f"ERROR: {e} | raw: {text[:200]}"


if __name__ == "__main__":
    print("Initializing Instantly MCP session...")
    session_id = init_session()
    time.sleep(0.5)

    results = []
    for i, camp in enumerate(CAMPAIGNS):
        print(f"\nCreating: {camp['name']} ...")
        camp_id = create_campaign(session_id, camp, i + 1)
        results.append({"name": camp["name"], "id": camp_id, "accounts": ACCOUNTS[camp["key"]]})
        print(f"  Result: {camp_id}")
        time.sleep(1)

    print("\n=== CAMPAIGN CREATION RESULTS ===")
    for r in results:
        print(f"{r['name']}: {r['id']}")
        print(f"  Accounts: {', '.join(r['accounts'])}")

    # Save results
    with open("pipeline/mayday_campaigns.json", "w") as f:
        json.dump(results, f, indent=2)
    print("\nSaved to pipeline/mayday_campaigns.json")
