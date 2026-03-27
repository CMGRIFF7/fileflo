$b = 'C:\Users\ChadGriffith\.claude\projects\C--Users-ChadGriffith-Downloads-fileflo-f11afbf5-main--2-\31bdd4b3-ff41-4e86-aa81-da4c2cf3d78b\tool-results\'
$f1  = $b + 'toulu_011SgRhqZgVExsxxHeV7ASo9.json'
$f2  = $b + 'toulu_01Mm3CH7iGXwtdMTdJeupZh6.json'
$f3  = $b + 'toulu_01Mrgo4ZrZpUw3Uy3rMhCLna.json'
$f4  = $b + 'mcp-58c0745d-668a-4639-b569-2ea04a11af76-apollo_people_bulk_match-1773836197145.txt'
$f5  = $b + 'mcp-58c0745d-668a-4639-b569-2ea04a11af76-apollo_people_bulk_match-1773836198587.txt'
$f6  = $b + 'toulu_013dGNpk42ckyYCtUsBPxGc9.json'
$f7  = $b + 'mcp-58c0745d-668a-4639-b569-2ea04a11af76-apollo_people_bulk_match-1773836203498.txt'
$files = $f1,$f2,$f3,$f4,$f5,$f6,$f7

$nl = [System.Environment]::NewLine
$rows = 'firstName,lastName,email,companyName,title'
$count = 0

foreach ($f in $files) {
    $raw = [System.IO.File]::ReadAllText($f)
    $arr = $raw | ConvertFrom-Json
    $inner = $arr[0].text | ConvertFrom-Json
    for ($i = 0; $i -lt $inner.matches.Count; $i++) {
        $m = $inner.matches[$i]
        $em = $m.email; $es = $m.email_status
        if ($em -and ($es -eq 'verified' -or $es -eq 'likely to engage')) {
            $rows += $nl + $m.first_name + ',' + $m.last_name + ',' + $em + ',' + $m.organization.name + ',' + $m.title
            $count++
        }
    }
}

# Inline results (p16-batch3 and p18-batch3 - returned directly, not saved to disk)
$rows += $nl + 'Nick,Lanham,nlanham@golighthouse.ai,Lighthouse,President & CEO'
$rows += $nl + 'Lorus,Byers,lorus@carrierintelligence.com,Carrier Intelligence,Founder / CEO'
$rows += $nl + 'Francisco,Franco,francisco@francotruckinginc.com,Franco Trucking Inc,CEO'
$rows += $nl + 'William,Pope,wmpope@popetrucking.com,Pope Trucking Inc,Chief Executive Officer'
$rows += $nl + 'Gary,Hahn,garyhahn@graytrucking.com,Gray Trucking,Director of Safety and Compliance'
$rows += $nl + 'Ryan,Andrews,randrews@thomsongroup.com,Thomson Terminals Limited,Director of Safety & Compliance'
$count += 6

[System.IO.File]::WriteAllText('C:\Users\ChadGriffith\Downloads\fileflo-f11afbf5-main (2)\compliance_proof_leads_batch6.csv', $rows)
Write-Host ('Done. Leads: ' + $count)
