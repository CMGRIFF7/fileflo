$f1 = 'C:\Users\ChadGriffith\.claude\projects\C--Users-ChadGriffith-Downloads-fileflo-f11afbf5-main--2-\31bdd4b3-ff41-4e86-aa81-da4c2cf3d78b\tool-results\mcp-58c0745d-668a-4639-b569-2ea04a11af76-apollo_people_bulk_match-1773785061497.txt'
$f2 = 'C:\Users\ChadGriffith\.claude\projects\C--Users-ChadGriffith-Downloads-fileflo-f11afbf5-main--2-\31bdd4b3-ff41-4e86-aa81-da4c2cf3d78b\tool-results\toolu_01WN7sqReCSVLXCTSd9zHSrn.json'

$csv = "firstName,lastName,email,companyName,title`n"

# Manual leads already confirmed from small batch
$csv += "Erick,Mendoza,emendoza@unilinktransportation.com,Unilink Transportation,CEO`n"
$csv += "Carlos,Navarro,cnavarro@diligentusa.com,Diligent Delivery Systems,CEO`n"
$csv += "Harsimran,Singh,harsimran@gillsontrucking.net,Gillson Trucking Inc,CEO`n"
$csv += "Shawn,Crowley,shawn@highcountrytrans.com,High Country Transportation Inc,CEO`n"
$csv += "Trajce,Ristovski,tristovski@driveforz.com,Z Transportation Inc.,CEO`n"

# Batch 1
$raw1 = [System.IO.File]::ReadAllText($f1)
$arr1 = $raw1 | ConvertFrom-Json
$inner1 = $arr1[0].text | ConvertFrom-Json
for ($i = 0; $i -lt $inner1.matches.Count; $i++) {
    $m = $inner1.matches[$i]
    $fn = $m.first_name
    $ln = $m.last_name
    $em = $m.email
    $es = $m.email_status
    $co = $m.organization.name
    $ti = $m.title
    if ($em -and $es -eq 'verified') {
        $csv += "$fn,$ln,$em,$co,$ti`n"
    }
}

# Batch 2
$raw2 = [System.IO.File]::ReadAllText($f2)
$arr2 = $raw2 | ConvertFrom-Json
$inner2 = $arr2[0].text | ConvertFrom-Json
for ($i = 0; $i -lt $inner2.matches.Count; $i++) {
    $m = $inner2.matches[$i]
    $fn = $m.first_name
    $ln = $m.last_name
    $em = $m.email
    $es = $m.email_status
    $co = $m.organization.name
    $ti = $m.title
    if ($em -and $es -eq 'verified') {
        $csv += "$fn,$ln,$em,$co,$ti`n"
    }
}

$csv | Out-File -FilePath 'C:\Users\ChadGriffith\Downloads\fileflo-f11afbf5-main (2)\compliance_proof_leads_batch1.csv' -Encoding UTF8 -NoNewline
Write-Host "Done. CSV written."
Write-Host $csv
