$f1 = 'C:\Users\ChadGriffith\.claude\projects\C--Users-ChadGriffith-Downloads-fileflo-f11afbf5-main--2-\31bdd4b3-ff41-4e86-aa81-da4c2cf3d78b\tool-results\mcp-58c0745d-668a-4639-b569-2ea04a11af76-apollo_people_bulk_match-1773785430954.txt'
$f2 = 'C:\Users\ChadGriffith\.claude\projects\C--Users-ChadGriffith-Downloads-fileflo-f11afbf5-main--2-\31bdd4b3-ff41-4e86-aa81-da4c2cf3d78b\tool-results\mcp-58c0745d-668a-4639-b569-2ea04a11af76-apollo_people_bulk_match-1773785437918.txt'

$csv = "firstName,lastName,email,companyName,title`n"

# Add the 5 leads from small batch already confirmed
$csv += "Brian,Serbalik,brian@otrfs.com,OTR Freight Solutions,CEO`n"
$csv += "Keith,Davis,keithd@sterlingtransportation.com,Sterling Transportation Inc.,CEO`n"
$csv += "Tom,Rzedzian,tom@go2.us,Go2 Logistics,President/CEO`n"
$csv += "Colby,Baskin,colby@cowtownexpress.com,Cowtown Logistics,CEO`n"
$csv += "Donnie,Puryear,dpuryear@puryeartanklines.com,Puryear Tank Lines,President & CEO`n"

function Extract-Emails($file) {
    $raw = [System.IO.File]::ReadAllText($file)
    $arr = $raw | ConvertFrom-Json
    $inner = $arr[0].text | ConvertFrom-Json
    $results = @()
    for ($i = 0; $i -lt $inner.matches.Count; $i++) {
        $m = $inner.matches[$i]
        $fn = $m.first_name
        $ln = $m.last_name
        $em = $m.email
        $es = $m.email_status
        $co = $m.organization.name
        $ti = $m.title
        if ($em -and ($es -eq 'verified' -or $es -eq 'likely to engage')) {
            $results += "$fn,$ln,$em,$co,$ti"
        }
    }
    return $results
}

$rows1 = Extract-Emails $f1
$rows2 = Extract-Emails $f2

foreach ($r in $rows1) { $csv += "$r`n" }
foreach ($r in $rows2) { $csv += "$r`n" }

$csv | Out-File -FilePath 'C:\Users\ChadGriffith\Downloads\fileflo-f11afbf5-main (2)\compliance_proof_leads_batch2.csv' -Encoding UTF8 -NoNewline
Write-Host "Done. CSV written."
Write-Host $csv
