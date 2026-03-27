$b = 'C:\Users\ChadGriffith\.claude\projects\C--Users-ChadGriffith-Downloads-fileflo-f11afbf5-main--2-\31bdd4b3-ff41-4e86-aa81-da4c2cf3d78b\tool-results\'
$f1  = $b + 'toulu_01HNdMKynjSmGM9JV7Wt3dXM.json'
$f2  = $b + 'mcp-58c0745d-668a-4639-b569-2ea04a11af76-apollo_people_bulk_match-1773836995882.txt'
$f3  = $b + 'toulu_01KDgqiWCJfvji7cM4qHQqDN.json'
$f4  = $b + 'toulu_01XLXqNBsgVuk2Lx8u9FcXuZ.json'
$f5  = $b + 'toulu_01SdHPEc22MK1SCoWdSqpUWa.json'
$f6  = $b + 'toulu_01WPQj6upK8oRRGAvqg2yaFv.json'
$f7  = $b + 'toulu_01HipJ4fpTk6nuQcLaBk3yyK.json'
$files = $f1,$f2,$f3,$f4,$f5,$f6,$f7

$nl = [System.Environment]::NewLine
$rows = 'firstName,lastName,email,companyName,title'
$count = 0

foreach ($f in $files) {
    if (-not [System.IO.File]::Exists($f)) { Write-Host ('MISSING: ' + $f); continue }
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

# Inline results (p22c+p23b batch - returned directly)
$rows += $nl + 'John,Vlasic,jvlasic@bestdelivery.com,Best Delivery LLC,President and CEO'
$rows += $nl + 'Rosica,Gancheva,safety@merxglobal.com,Merx Global,Director of Safety Compliance and Training'
$rows += $nl + 'Mario,Arechiga,mario.arechiga@4onthego.com,4 ON THE GO TRANSPORTATION-LOGISTICS,CEO'
$rows += $nl + 'Phillis,Felice,pfelice@tsdlogistics.com,TSD Logistics,Assistant Safety Director'
$rows += $nl + 'Jerry,Qira,jerryq@jrx-logistics.com,JRX LOGISTICS,Chief Executive Officer'
$count += 5

[System.IO.File]::WriteAllText('C:\Users\ChadGriffith\Downloads\fileflo-f11afbf5-main (2)\compliance_proof_leads_batch9.csv', $rows)
Write-Host ('Done. Leads: ' + $count)
