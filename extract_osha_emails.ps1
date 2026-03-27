$f1 = 'C:\Users\ChadGriffith\.claude\projects\C--Users-ChadGriffith-Downloads-fileflo-f11afbf5-main--2-\25f4119b-38a1-45f8-905d-b6d5752789d6\tool-results\mcp-58c0745d-668a-4639-b569-2ea04a11af76-apollo_people_bulk_match-1773176397447.txt'
$f2 = 'C:\Users\ChadGriffith\.claude\projects\C--Users-ChadGriffith-Downloads-fileflo-f11afbf5-main--2-\25f4119b-38a1-45f8-905d-b6d5752789d6\tool-results\mcp-58c0745d-668a-4639-b569-2ea04a11af76-apollo_people_bulk_match-1773176398842.txt'

Write-Host "=== BATCH 1 ==="
$raw1 = Get-Content $f1 -Raw
$outer1 = $raw1 | ConvertFrom-Json
$inner1 = $outer1[0].text | ConvertFrom-Json
$matches1 = if ($inner1.matches) { $inner1.matches } elseif ($inner1.people) { $inner1.people } else { @() }
foreach ($m in $matches1) {
    $orgName = if ($m.organization) { $m.organization.name } else { 'N/A' }
    $email = if ($m.email) { $m.email } else { 'NO_EMAIL' }
    $status = if ($m.email_status) { $m.email_status } else { 'unknown' }
    Write-Host "$($m.first_name) $($m.last_name) | $($m.title) | $email | $status | $orgName"
}

Write-Host ""
Write-Host "=== BATCH 2 ==="
$raw2 = Get-Content $f2 -Raw
$outer2 = $raw2 | ConvertFrom-Json
$inner2 = $outer2[0].text | ConvertFrom-Json
$matches2 = if ($inner2.matches) { $inner2.matches } elseif ($inner2.people) { $inner2.people } else { @() }
foreach ($m in $matches2) {
    $orgName = if ($m.organization) { $m.organization.name } else { 'N/A' }
    $email = if ($m.email) { $m.email } else { 'NO_EMAIL' }
    $status = if ($m.email_status) { $m.email_status } else { 'unknown' }
    Write-Host "$($m.first_name) $($m.last_name) | $($m.title) | $email | $status | $orgName"
}
