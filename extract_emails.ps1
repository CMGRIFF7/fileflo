$f1 = 'C:\Users\ChadGriffith\.claude\projects\C--Users-ChadGriffith-Downloads-fileflo-f11afbf5-main--2-\25f4119b-38a1-45f8-905d-b6d5752789d6\tool-results\toolu_01TQN9obkgv8CAoFsDPmr2uN.json'
$f2 = 'C:\Users\ChadGriffith\.claude\projects\C--Users-ChadGriffith-Downloads-fileflo-f11afbf5-main--2-\25f4119b-38a1-45f8-905d-b6d5752789d6\tool-results\toolu_01KUqE3B9uprAco7pSpAN482.json'

Write-Host "=== BATCH 1 ==="
$raw1 = Get-Content $f1 -Raw
$outer1 = $raw1 | ConvertFrom-Json
$inner1 = $outer1[0].text | ConvertFrom-Json
foreach ($m in $inner1.matches) {
    $orgName = if ($m.organization) { $m.organization.name } else { 'N/A' }
    Write-Host "$($m.name) | $($m.email) | $($m.email_status) | $orgName"
}

Write-Host ""
Write-Host "=== BATCH 2 ==="
$raw2 = Get-Content $f2 -Raw
$outer2 = $raw2 | ConvertFrom-Json
$inner2 = $outer2[0].text | ConvertFrom-Json
foreach ($m in $inner2.matches) {
    $orgName = if ($m.organization) { $m.organization.name } else { 'N/A' }
    Write-Host "$($m.name) | $($m.email) | $($m.email_status) | $orgName"
}
