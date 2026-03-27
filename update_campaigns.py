import subprocess, json

# Init session
init = subprocess.run([
    'curl','-si','-X','POST',
    'https://mcp.instantly.ai/mcp/ZWU5MTFiNjEtZDg3YS00ZjcwLTlkMDEtYzVkMjI4ZGEwMzViOlNXbUpJZ0JBZ3JBWA==',
    '-H','Content-Type: application/json',
    '-H','Accept: application/json, text/event-stream',
    '-d', json.dumps({
        'jsonrpc':'2.0','method':'initialize',
        'params':{'protocolVersion':'2024-11-05','capabilities':{},'clientInfo':{'name':'claude','version':'1.0'}},
        'id':1
    })
], capture_output=True, text=True)

sid = [l.split(':',1)[1].strip() for l in init.stdout.split('\n') if 'mcp-session-id' in l.lower()][0]
print('Session:', sid)

# --- UPDATED SEQUENCES ---

fmcsa_steps = [
    {
        'type':'email','delay':4,'delay_unit':'days','pre_delay_unit':'days',
        'variants':[{
            'subject':'Your FMCSA safety score',
            'body':(
                '<p></p><p>Hey {{firstName}},</p>'
                '<p>I was reviewing active FMCSA carriers in your state \u2014 most small fleets I reach out to are one bad inspection away from the alert zone without realizing it.</p>'
                '<p>One citation runs $16,550. I built FileFlo specifically for carriers like {{companyName}} \u2014 it tracks all 85+ required documents automatically and flags anything coming due before an inspector ever shows up.</p>'
                '<p>Worth a 10-minute look?</p>'
                '<p>{{senderFirstName}}<br />getfileflo.com</p><p></p>'
            )
        }]
    },
    {
        'type':'email','delay':4,'delay_unit':'days','pre_delay_unit':'days',
        'variants':[{
            'subject':'What auditors actually look for',
            'body':(
                '<p></p><p>Hey {{firstName}},</p>'
                '<p>Most FMCSA violations come down to three things:</p>'
                '<ul><li>Expired or missing driver qualification files</li><li>HOS records that don\'t match logs</li><li>Drug and alcohol testing records out of order</li></ul>'
                '<p>FileFlo catches all three automatically and alerts you 30 days before anything expires. Takes 15 minutes to set up.</p>'
                '<p>Free trial at getfileflo.com.</p>'
                '<p>{{senderFirstName}}</p><p></p>'
            )
        }]
    },
    {
        'type':'email','delay':4,'delay_unit':'days','pre_delay_unit':'days',
        'variants':[{
            'subject':'Last note',
            'body':(
                '<p></p><p>Hey {{firstName}},</p>'
                '<p>Last email from me.</p>'
                '<p>If you\'re managing compliance manually, you\'re one missed document away from a $16,550 fine. FileFlo exists to make sure that doesn\'t happen.</p>'
                '<p>14-day free trial, no card required: getfileflo.com</p>'
                '<p>{{senderFirstName}}</p><p></p>'
            )
        }]
    },
]

brokers_steps = [
    {
        'type':'email','delay':4,'delay_unit':'days','pre_delay_unit':'days',
        'variants':[{
            'subject':'your trucking book',
            'body':(
                '<p>{{firstName}},</p>'
                '<p>Quick question \u2014 if one of your fleet clients got a DOT compliance review tomorrow, would you know before they did whether they\'d pass?</p>'
                '<p>Most brokers find out after the fact. By then the carrier\'s authority is at risk, the policy\'s in chaos, and you\'re fielding calls you don\'t have good answers to.</p>'
                '<p>Worth a short conversation about how some brokers are staying ahead of that?</p>'
                '<p>{{senderFirstName}}</p>'
            )
        }]
    },
    {
        'type':'email','delay':4,'delay_unit':'days','pre_delay_unit':'days',
        'variants':[{
            'subject':'',
            'body':(
                '<p>{{firstName}},</p>'
                '<p>The brokers I hear this from most are running mid-size books \u2014 20 to 60 fleet clients. You know them all personally, but you can\'t realistically track every driver file, medical cert, and inspection record across all of them.</p>'
                '<p>A broker I talked to recently had a client lose their operating authority over expired medical certificates. She\'d been their broker for eleven years. Lost the account at renewal.</p>'
                '<p>The gap wasn\'t the coverage. It was paperwork her client thought was handled.</p>'
                '<p>The tool I built flags exactly that \u2014 before the auditor does. Would it be useful to see what it surfaces for one of your clients?</p>'
                '<p>{{senderFirstName}}</p>'
            )
        }]
    },
    {
        'type':'email','delay':4,'delay_unit':'days','pre_delay_unit':'days',
        'variants':[{
            'subject':'the math on your book, {{firstName}}',
            'body':(
                '<p>{{firstName}},</p>'
                '<p>Should\'ve mentioned this earlier \u2014 we pay brokers 15% recurring on every client they bring on.</p>'
                '<p>If 10 of your trucking clients sign up at $299/month, that\'s $450/month just sitting on top of your normal renewals. It compounds as you bring on more clients. A few brokers use it purely as a retention play \u2014 clients who track compliance with it renew more reliably because they can actually prove they\'re clean.</p>'
                '<p>Worth seeing the partner one-pager?</p>'
                '<p>{{senderFirstName}}</p>'
            )
        }]
    },
    {
        'type':'email','delay':4,'delay_unit':'days','pre_delay_unit':'days',
        'variants':[{
            'subject':'',
            'body':(
                '<p>{{firstName}},</p>'
                '<p>Last one from me \u2014 I\'m not going to keep nudging.</p>'
                '<p>If a trucking client ever calls you after a compliance notice and you want something fast to point them to, we\'re at getfileflo.com. 14-day free trial, no card required.</p>'
                '<p>Good luck with the book.</p>'
                '<p>{{senderFirstName}}</p>'
            )
        }]
    },
]

operators_steps = [
    {
        'type':'email','delay':4,'delay_unit':'days','pre_delay_unit':'days',
        'variants':[{
            'subject':'{{firstName}}, if a DOT inspector walked in today',
            'body':(
                '<p>{{firstName}} \u2014</p>'
                '<p>Quick scenario: a DOT inspector walks into {{companyName}} right now and asks for proof of compliance \u2014 driver qualification files, annual inspection records, HOS logs.</p>'
                '<p>How long does it take to pull everything they need?</p>'
                '<p>Most carriers I talk to say anywhere from 20 minutes to "we\'re not sure where everything is."</p>'
                '<p>FileFlo was built for that moment. It centralizes every compliance doc and lets you generate an audit-ready package in under 60 seconds.</p>'
                '<p>If it\'s useful, I can walk you through what it would look like for {{companyName}} \u2014 just reply.</p>'
                '<p>{{senderFirstName}}</p>'
            )
        }]
    },
    {
        'type':'email','delay':4,'delay_unit':'days','pre_delay_unit':'days',
        'variants':[{
            'subject':"what {{companyName}} probably doesn't have organized",
            'body':(
                '<p>{{firstName}} \u2014 the gaps that get carriers fined are almost always the same three things:</p>'
                '<ul><li>Driver qualification files missing or expired</li><li>Annual DOT inspection records not properly documented</li><li>Vehicle maintenance records scattered or incomplete</li></ul>'
                '<p>The thing I hear most: "We thought we were compliant \u2014 until someone actually asked for the proof."</p>'
                '<p>FileFlo organizes everything by regulation \u2014 FMCSA, OSHA, IRS, EPA \u2014 so when an inspector asks, it\'s there in seconds.</p>'
                '<p>14 days free, no card required: getfileflo.com</p>'
                '<p>{{senderFirstName}}</p>'
            )
        }]
    },
    {
        'type':'email','delay':4,'delay_unit':'days','pre_delay_unit':'days',
        'variants':[{
            'subject':'the math on one FMCSA violation',
            'body':(
                '<p>{{firstName}} \u2014 one more thought.</p>'
                '<p>FMCSA violations average over $16,000 per incident \u2014 often for one missing or expired document.</p>'
                '<p>FileFlo is $299/month. For most carriers, it pays for itself the first time it prevents a citation or helps pass a clean audit.</p>'
                '<p>14-day free trial, takes about 10 minutes to set up: getfileflo.com</p>'
                '<p>{{senderFirstName}}</p>'
            )
        }]
    },
    {
        'type':'email','delay':4,'delay_unit':'days','pre_delay_unit':'days',
        'variants':[{
            'subject':'last note, {{firstName}}',
            'body':(
                '<p>{{firstName}} \u2014 I\'ll stop reaching out after this.</p>'
                '<p>If compliance documentation isn\'t a current priority, totally understood.</p>'
                '<p>If you ever find yourself scrambling during a roadside inspection or DOT audit, FileFlo is at getfileflo.com \u2014 14 days free, no card required.</p>'
                '<p>Good luck out there.</p>'
                '<p>{{senderFirstName}}</p>'
            )
        }]
    },
]

osha_steps = [
    {
        'type':'email','delay':4,'delay_unit':'days','pre_delay_unit':'days',
        'variants':[{
            'subject':'{{firstName}}, if OSHA walked in today',
            'body':(
                '<p>{{firstName}} \u2014</p>'
                '<p>Quick scenario: an OSHA inspector walks into {{companyName}} right now and asks for your safety documentation \u2014 incident logs, training records, subcontractor insurance certs.</p>'
                '<p>How long does it take to pull everything they need?</p>'
                '<p>FileFlo centralizes every compliance document (OSHA 300 logs, safety training certs, subcontractor files, inspection records) so you can pull an audit-ready package in under 60 seconds.</p>'
                '<p>If the timing\'s right, just reply and I can show you what the audit package looks like.</p>'
                '<p>{{senderFirstName}}</p>'
            )
        }]
    },
    {
        'type':'email','delay':4,'delay_unit':'days','pre_delay_unit':'days',
        'variants':[{
            'subject':"what {{companyName}} probably doesn't have organized",
            'body':(
                '<p>{{firstName}} \u2014 the gaps that get contractors cited are almost always the same three things:</p>'
                '<ul><li>OSHA 300 injury logs missing or outdated</li><li>Subcontractor insurance certs expired or not on file</li><li>Safety training records scattered or incomplete</li></ul>'
                '<p>What I hear most: "We thought we were covered \u2014 until the inspector actually asked."</p>'
                '<p>FileFlo organizes everything by regulation \u2014 OSHA, EPA, IRS \u2014 so when you get asked for proof, it\'s there in seconds.</p>'
                '<p>14 days free, no card required: getfileflo.com</p>'
                '<p>{{senderFirstName}}</p>'
            )
        }]
    },
    {
        'type':'email','delay':4,'delay_unit':'days','pre_delay_unit':'days',
        'variants':[{
            'subject':'the math on one OSHA violation',
            'body':(
                '<p>{{firstName}} \u2014 one more thought.</p>'
                '<p>OSHA violations average over $16,000 per citation. Often for one missing or outdated safety document.</p>'
                '<p>FileFlo is $299/month. For most contractors, it pays for itself the first time it prevents a citation or helps you pass a clean safety audit.</p>'
                '<p>14-day free trial, takes about 10 minutes to set up: getfileflo.com</p>'
                '<p>{{senderFirstName}}</p>'
            )
        }]
    },
    {
        'type':'email','delay':4,'delay_unit':'days','pre_delay_unit':'days',
        'variants':[{
            'subject':'last note, {{firstName}}',
            'body':(
                '<p>{{firstName}} \u2014 I\'ll stop reaching out after this.</p>'
                '<p>If safety compliance documentation isn\'t a current priority, totally understood.</p>'
                '<p>If you ever find yourself scrambling during an OSHA inspection or safety audit, FileFlo is at getfileflo.com \u2014 14 days free, no card required.</p>'
                '<p>Good luck out there.</p>'
                '<p>{{senderFirstName}}</p>'
            )
        }]
    },
]

updates = [
    ('FMCSA Violation Targets',   'b514c694-b372-4d89-8b93-6ed325571963', fmcsa_steps),
    ('Insurance Brokers',          '1e5d0838-7632-47cf-a29a-11c3259b5a9a', brokers_steps),
    ('Direct Operators',           'ba7dd34b-e415-472c-9c3e-fac2d88f6d3d', operators_steps),
    ('OSHA Contractors',           '2b9057f9-26dc-40dc-b801-7e607452bc52', osha_steps),
]

for name, cid, steps in updates:
    payload = json.dumps({
        'jsonrpc':'2.0','method':'tools/call',
        'params':{'name':'update_campaign','arguments':{'params':{'campaign_id':cid,'sequences':[{'steps':steps}]}}},
        'id':2
    })
    r = subprocess.run([
        'curl','-s','-N','-X','POST',
        'https://mcp.instantly.ai/mcp/ZWU5MTFiNjEtZDg3YS00ZjcwLTlkMDEtYzVkMjI4ZGEwMzViOlNXbUpJZ0JBZ3JBWA==',
        '-H','Content-Type: application/json',
        '-H','Accept: application/json, text/event-stream',
        '-H',f'mcp-session-id: {sid}',
        '-d', payload
    ], capture_output=True, text=True)
    # Check result
    if 'sequences' in r.stdout and 'error' not in r.stdout.lower():
        print(f'OK  {name}')
    else:
        snippet = r.stdout[100:200] if r.stdout else r.stderr[:200]
        print(f'ERR {name}: {snippet}')
