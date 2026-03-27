"""
create_campaigns_mcp.py
Creates 3 FMCSA campaigns via Instantly MCP HTTP endpoint (curl workaround).
The MCP endpoint accepts tool calls directly after session init.
"""

import requests
import json
import sys

MCP_URL = "https://mcp.instantly.ai/mcp/ZWU5MTFiNjEtZDg3YS00ZjcwLTlkMDEtYzVkMjI4ZGEwMzViOlNXbUpJZ0JBZ3JBWA=="

EMAIL_LIST = [
    "megan@nowregulation.com", "cgriffith@meetfileflo.org", "chadgriffith@meetfileflo.org",
    "haley@nowregulation.com", "haley@lookcompliance.com", "chad@tryfileflo.com",
    "griffith@meetfileflo.org", "brandon@lookcompliance.com", "karen@nowcompliance.org",
    "chad@meetfileflo.org", "brandon@nowregulation.com", "megan@lookcompliance.com",
    "haley@nowcompliance.org", "cgriffith@tryfileflo.com", "griffith@tryfileflo.com",
    "karen@lookcompliance.com", "karen@nowregulation.com", "chadgriffith@tryfileflo.com",
    "brandon@nowcompliance.org", "chad@fileflobinder.com", "megan@nowcompliance.org"
]


def init_session():
    resp = requests.post(
        MCP_URL,
        headers={"Content-Type": "application/json", "Accept": "application/json, text/event-stream"},
        json={"jsonrpc": "2.0", "method": "initialize", "params": {
            "protocolVersion": "2024-11-05", "capabilities": {},
            "clientInfo": {"name": "claude", "version": "1.0"}
        }, "id": 1},
        stream=True, timeout=15
    )
    session_id = resp.headers.get("mcp-session-id")
    if not session_id:
        print("ERROR: Could not get session ID")
        sys.exit(1)
    print(f"Session: {session_id}")
    return session_id


def call_tool(session_id, tool_name, arguments, call_id=2):
    resp = requests.post(
        MCP_URL,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "mcp-session-id": session_id
        },
        json={"jsonrpc": "2.0", "method": "tools/call", "params": {
            "name": tool_name, "arguments": arguments
        }, "id": call_id},
        stream=True, timeout=30
    )
    # Parse SSE stream
    result_text = ""
    for line in resp.iter_lines():
        if line:
            decoded = line.decode("utf-8")
            if decoded.startswith("data:"):
                try:
                    data = json.loads(decoded[5:].strip())
                    result_text = data
                except Exception:
                    pass
    return result_text


# Campaign definitions
campaigns = [
    {
        "name": "FMCSA CSA Score Alert",
        "subject": "CSA scores",
        "body": "<p>Hi {{firstName}},</p><p>How are you keeping track of {{companyName}}'s CSA scores across the seven BASICs?</p><p>Most carriers I talk to check once a year, maybe. The problem is FMCSA doesn't wait. Once a score crosses the intervention threshold, you're on their radar whether you know it or not.</p><p>I built something that monitors your CSA scores in real time and alerts you before a category goes critical.</p><p>Worth 10 minutes to see it?</p><p>Chad</p>",
        "sequences": [{"steps": [
            {"type": "email", "delay": 0, "delay_unit": "days", "variants": [
                {"subject": "CSA scores", "body": "<p>Hi {{firstName}},</p><p>How are you keeping track of {{companyName}}'s CSA scores across the seven BASICs?</p><p>Most carriers I talk to check once a year, maybe. The problem is FMCSA doesn't wait. Once a score crosses the intervention threshold, you're on their radar whether you know it or not.</p><p>I built something that monitors your CSA scores in real time and alerts you before a category goes critical.</p><p>Worth 10 minutes to see it?</p><p>Chad</p>"},
                {"subject": "{{companyName}} -- {{csaCategory}} score", "body": "<p>Hi {{firstName}},</p><p>{{companyName}}'s CSA score in {{csaCategory}} is above the federal intervention threshold.</p><p>Carriers at this level get warning letters, compliance reviews, or targeted roadside inspections. Most don't know they're there until it happens.</p><p>I built FileFlo to track exactly this. Real-time CSA monitoring across all seven BASICs, with alerts before a score goes critical.</p><p>Want me to pull up what it looks like for your fleet?</p><p>Chad</p>"},
                {"subject": "$84,000 and a compliance review", "body": "<p>Hi {{firstName}},</p><p>A 12-truck fleet in Texas got hit with a compliance review last year after their Unsafe Driving CSA score crossed 65. They didn't know they were in the intervention zone.</p><p>The review found documentation gaps. $84,000 in fines.</p><p>I built FileFlo to catch this before it happens. It monitors all seven CSA BASICs and alerts you when a score is trending toward intervention.</p><p>Want to see what your fleet looks like inside it?</p><p>Chad</p>"}
            ]},
            {"type": "email", "delay": 3, "delay_unit": "days", "variants": [
                {"subject": "", "body": "<p>Worth adding -- when a CSA score crosses the intervention threshold, FMCSA's first step is usually a warning letter, but the second step is a targeted compliance review. By then you're already on the back foot.</p><p>FileFlo keeps you on the front foot. 10 minutes if you want to see it.</p><p>Chad</p>"}
            ]},
            {"type": "email", "delay": 3, "delay_unit": "days", "variants": [
                {"subject": "{{firstName}}, quick question", "body": "<p>{{firstName}},</p><p>If FMCSA sent you a letter tomorrow saying {{companyName}} was selected for a compliance review, how confident are you that every document they'd ask for is current and in the right place?</p><p>That's the question most carriers can't answer until they're asked for real.</p><p>FileFlo keeps everything audit-ready at all times. 14-day free trial, no credit card: getfileflo.com</p><p>Chad</p>"}
            ]},
            {"type": "email", "delay": 4, "delay_unit": "days", "variants": [
                {"subject": "", "body": "<p>Last note from me. If CSA monitoring is already handled, no problem.</p><p>If scores are something you're tracking manually or not at all, that's exactly what we fix.</p><p>Free audit at getfileflo.com if you ever want to check where you stand. No signup required.</p><p>Chad</p>"}
            ]}
        ]}],
        "custom_variables": {"csaCategory": True, "fleetSize": True, "dotNumber": True, "state": True}
    },
    {
        "name": "FMCSA Safety Rating Alert",
        "subject": "safety rating question",
        "body": "<p>Hi {{firstName}},</p><p>How is {{companyName}} working toward improving its safety rating right now?</p><p>Worth 10 minutes to talk through it?</p><p>Chad</p>",
        "sequences": [{"steps": [
            {"type": "email", "delay": 0, "delay_unit": "days", "variants": [
                {"subject": "safety rating question", "body": "<p>Hi {{firstName}},</p><p>How is {{companyName}} working toward improving its safety rating right now?</p><p>Most carriers with a Conditional rating know they need to do something but aren't sure where to start. The documentation piece is almost always part of it.</p><p>I built FileFlo to handle exactly that -- DQFs, training records, inspection logs, written programs -- everything auditors look for when they review a rating.</p><p>Worth 10 minutes to talk through it?</p><p>Chad</p>"},
                {"subject": "{{companyName}} -- {{safetyRating}} rating", "body": "<p>Hi {{firstName}},</p><p>{{companyName}} is currently rated {{safetyRating}} by FMCSA.</p><p>A Conditional rating means heightened scrutiny. Unsatisfactory gives FMCSA grounds for a cease-and-desist within 45 days.</p><p>The fastest path to improving a safety rating is getting documentation in order fast. That is exactly what FileFlo does.</p><p>Can I show you what it looks like for a {{fleetSize}}-truck fleet?</p><p>Chad</p>"},
                {"subject": "Conditional to Satisfactory in 60 days", "body": "<p>Hi {{firstName}},</p><p>A carrier in Indiana came to us with a Conditional safety rating and six months of inspection failures. Their problem was not operations. It was missing and expired documentation that made every inspection look worse than it was.</p><p>60 days after using FileFlo, they passed a compliance review and got back to Satisfactory.</p><p>15 minutes if you want to see what we did.</p><p>Chad</p>"}
            ]},
            {"type": "email", "delay": 3, "delay_unit": "days", "variants": [
                {"subject": "", "body": "<p>Worth adding -- most carriers with a Conditional rating are one compliance review away from Unsatisfactory. The difference is almost always documentation, not operations.</p><p>FileFlo gets the documentation side locked in fast. Happy to show you.</p><p>Chad</p>"}
            ]},
            {"type": "email", "delay": 3, "delay_unit": "days", "variants": [
                {"subject": "{{firstName}}, quick question", "body": "<p>{{firstName}},</p><p>If an FMCSA auditor reviewed {{companyName}}'s driver qualification files today, how many would be complete?</p><p>That is usually where the gap is. And it is fixable faster than most carriers think.</p><p>14-day free trial, no credit card: getfileflo.com</p><p>Chad</p>"}
            ]},
            {"type": "email", "delay": 4, "delay_unit": "days", "variants": [
                {"subject": "", "body": "<p>Last note from me.</p><p>If the rating situation is already being worked through another path, best of luck. If you want a faster route, we are at getfileflo.com. Free audit, no signup required.</p><p>Chad</p>"}
            ]}
        ]}],
        "custom_variables": {"safetyRating": True, "fleetSize": True, "dotNumber": True, "state": True}
    },
    {
        "name": "FMCSA Violation History Pattern",
        "subject": "violation patterns",
        "body": "<p>Hi {{firstName}},</p><p>How are you tracking repeat violations across {{companyName}}'s fleet right now?</p><p>Worth 10 minutes?</p><p>Chad</p>",
        "sequences": [{"steps": [
            {"type": "email", "delay": 0, "delay_unit": "days", "variants": [
                {"subject": "violation patterns", "body": "<p>Hi {{firstName}},</p><p>How are you tracking repeat violations across {{companyName}}'s fleet right now?</p><p>Most carriers do not see a pattern forming until FMCSA points it out in a warning letter. By then the compliance review is already scheduled.</p><p>I built FileFlo to surface exactly this. It maps your violation history across all categories and shows you where the exposure is concentrated before it becomes a problem.</p><p>Worth 10 minutes?</p><p>Chad</p>"},
                {"subject": "{{companyName}} -- {{violationCount}} violations", "body": "<p>Hi {{firstName}},</p><p>{{companyName}} has {{violationCount}} violations on record over the past {{timeframe}}.</p><p>FMCSA uses violation frequency as a trigger for compliance reviews -- even without a single severe incident. A pattern across {{fleetSize}} trucks is enough to put you on their list.</p><p>FileFlo maps your full violation history and shows you exactly what is driving the pattern and what documentation needs to be in order.</p><p>Want me to pull it up for your fleet?</p><p>Chad</p>"},
                {"subject": "7 violations, no OOS, still got audited", "body": "<p>Hi {{firstName}},</p><p>A 9-truck carrier in Florida had seven minor violations over 18 months. No out-of-service orders, no critical violations. They thought they were fine.</p><p>FMCSA flagged the frequency pattern and scheduled a compliance review. It turned into a $62,000 fine for documentation failures that had nothing to do with the violations themselves.</p><p>FileFlo tracks both. 15 minutes if you want to see it.</p><p>Chad</p>"}
            ]},
            {"type": "email", "delay": 3, "delay_unit": "days", "variants": [
                {"subject": "", "body": "<p>Worth adding -- FMCSA's compliance review triggers are not just about severity. Violation frequency over a rolling 12 months is its own signal. Most carriers do not track their own pattern closely enough to know when they have crossed it.</p><p>FileFlo tracks it for you.</p><p>Chad</p>"}
            ]},
            {"type": "email", "delay": 3, "delay_unit": "days", "variants": [
                {"subject": "{{firstName}}, quick question", "body": "<p>{{firstName}},</p><p>If you pulled {{companyName}}'s full violation history for the last 24 months right now, would you know which category is driving the most exposure?</p><p>Most carriers cannot answer that without spending a few hours in FMCSA's portal. FileFlo shows it in 30 seconds.</p><p>14-day free trial, no credit card: getfileflo.com</p><p>Chad</p>"}
            ]},
            {"type": "email", "delay": 4, "delay_unit": "days", "variants": [
                {"subject": "", "body": "<p>Last note from me. If violation tracking is already handled, no problem.</p><p>If you do not have a clear picture of where the pattern is coming from, that is exactly what we fix.</p><p>Free audit at getfileflo.com -- no signup required.</p><p>Chad</p>"}
            ]}
        ]}],
        "custom_variables": {"violationCount": True, "timeframe": True, "fleetSize": True, "dotNumber": True, "state": True}
    }
]

# Init session
session_id = init_session()

# Create each campaign
for i, c in enumerate(campaigns):
    print(f"\nCreating: {c['name']}...")
    result = call_tool(session_id, "create_campaign", {
        "params": {
            "name": c["name"],
            "subject": c["subject"],
            "body": c["body"],
            "sequence_steps": 4,
            "step_delay_days": 3,
            "email_list": EMAIL_LIST,
            "daily_limit": 50,
            "track_opens": False,
            "track_clicks": False,
            "stop_on_reply": True,
            "stop_on_auto_reply": True,
            "timing_from": "08:00",
            "timing_to": "17:00",
            "timezone": "America/Chicago"
        }
    }, call_id=i + 2)

    if result:
        content = result.get("result", {}).get("content", [{}])
        text = content[0].get("text", str(result)) if content else str(result)
        print(f"  Result: {text[:400]}")
    else:
        print("  No result returned")
