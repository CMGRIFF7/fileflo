$b = 'C:\Users\ChadGriffith\.claude\projects\C--Users-ChadGriffith-Downloads-fileflo-f11afbf5-main--2-\31bdd4b3-ff41-4e86-aa81-da4c2cf3d78b\tool-results\'
$f1  = $b + 'toulu_01EseWTtp69gpLJkHEBJaQuH.json'
$f2  = $b + 'toulu_019nK2wuFUdx8HyVQRQRuAoR.json'
$f3  = $b + 'toulu_013djMLNAgM8PVtSQnM14YPt.json'
$f4  = $b + 'toulu_01MVofH5rSWosz6BVj5TCLMQ.json'
$files = $f1,$f2,$f3,$f4

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

[System.IO.File]::WriteAllText('C:\Users\ChadGriffith\Downloads\fileflo-f11afbf5-main (2)\compliance_proof_leads_batch23.csv', $rows)
Write-Host ('Done. Leads: ' + $count)
