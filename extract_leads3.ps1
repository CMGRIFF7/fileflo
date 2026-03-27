$baseDir = 'C:\Users\ChadGriffith\.claude\projects\C--Users-ChadGriffith-Downloads-fileflo-f11afbf5-main--2-\31bdd4b3-ff41-4e86-aa81-da4c2cf3d78b\tool-results\'

$files = @(
    $baseDir + 'toolu_01EYWMQkHFzXMQoGwLqi8Jw6.json',
    $baseDir + 'mcp-58c0745d-668a-4639-b569-2ea04a11af76-apollo_people_bulk_match-1773785739267.txt',
    $baseDir + 'mcp-58c0745d-668a-4639-b569-2ea04a11af76-apollo_people_bulk_match-1773785743312.txt',
    $baseDir + 'mcp-58c0745d-668a-4639-b569-2ea04a11af76-apollo_people_bulk_match-1773785746473.txt',
    $baseDir + 'mcp-58c0745d-668a-4639-b569-2ea04a11af76-apollo_people_bulk_match-1773785751193.txt',
    $baseDir + 'toolu_018DNzn1NxbWJ1n6KYH7Ynjg.json',
    $baseDir + 'mcp-58c0745d-668a-4639-b569-2ea04a11af76-apollo_people_bulk_match-1773785760316.txt',
    $baseDir + 'toolu_011BJEDQYYr2uRKv2aVaFSF1.json',
    $baseDir + 'toolu_018xtqFPL9nW9bcz8mSPKYVK.json'
)

$csv = "firstName,lastName,email,companyName,title`n"
$count = 0

foreach ($f in $files) {
    if (-not (Test-Path $f)) {
        Write-Host "MISSING: $f"
        continue
    }
    $raw = [System.IO.File]::ReadAllText($f)
    $arr = $raw | ConvertFrom-Json
    $inner = $arr[0].text | ConvertFrom-Json
    for ($i = 0; $i -lt $inner.matches.Count; $i++) {
        $m = $inner.matches[$i]
        $fn = $m.first_name
        $ln = $m.last_name
        $em = $m.email
        $es = $m.email_status
        $co = $m.organization.name
        $ti = $m.title
        if ($em -and ($es -eq 'verified' -or $es -eq 'likely to engage')) {
            $csv += "$fn,$ln,$em,$co,$ti`n"
            $count++
        }
    }
}

$csv | Out-File -FilePath 'C:\Users\ChadGriffith\Downloads\fileflo-f11afbf5-main (2)\compliance_proof_leads_batch3.csv' -Encoding UTF8 -NoNewline
Write-Host "Done. $count leads written."
Write-Host $csv
