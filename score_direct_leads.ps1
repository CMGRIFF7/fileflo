# Score Apollo trucking + construction leads, output top 20 IDs for each
$truckingFile    = 'C:\Users\ChadGriffith\.claude\projects\C--Users-ChadGriffith-Downloads-fileflo-f11afbf5-main--2-\25f4119b-38a1-45f8-905d-b6d5752789d6\tool-results\toolu_01Xn5fYc2wuShoCMXe7yJVYm.json'
$constructFile   = 'C:\Users\ChadGriffith\.claude\projects\C--Users-ChadGriffith-Downloads-fileflo-f11afbf5-main--2-\25f4119b-38a1-45f8-905d-b6d5752789d6\tool-results\toolu_01NpsDW3BpdmBZQL68WFijsf.json'
$outTrucking     = 'C:\Users\ChadGriffith\Downloads\fileflo-f11afbf5-main (2)\top_trucking_ids.txt'
$outConstruction = 'C:\Users\ChadGriffith\Downloads\fileflo-f11afbf5-main (2)\top_construction_ids.txt'

function Score-Lead($p) {
    $score = 0
    $title = if ($p.title) { $p.title.ToLower() } else { '' }
    $emp   = 0
    if ($p.organization -and $p.organization.num_employees) {
        try { $emp = [int]$p.organization.num_employees } catch {}
    }
    $emailStatus = if ($p.email_status) { $p.email_status.ToLower() } else { '' }
    $hasEmail    = if ($p.has_email) { $p.has_email } else { $false }

    if ($title -match 'owner|president|ceo|founder|principal')                     { $score += 30 }
    elseif ($title -match 'safety director|director of safety|vp safety')          { $score += 28 }
    elseif ($title -match 'dot compliance|compliance manager|fleet manager|fleet safety') { $score += 26 }
    elseif ($title -match 'operations manager|vp operations|director of operations'){ $score += 22 }
    elseif ($title -match 'general manager|gm\b|managing director')                { $score += 18 }
    elseif ($title -match 'manager')                                               { $score += 10 }
    else                                                                           { $score += 2 }

    if ($emp -ge 10 -and $emp -le 50)  { $score += 20 }
    elseif ($emp -ge 51 -and $emp -le 200)  { $score += 18 }
    elseif ($emp -ge 201 -and $emp -le 500) { $score += 12 }
    elseif ($emp -ge 1 -and $emp -lt 10)    { $score += 5 }

    if ($emailStatus -eq 'verified')              { $score += 15 }
    elseif ($emailStatus -eq 'likely to engage')  { $score += 10 }
    elseif ($emailStatus -eq 'unverified')        { $score += 3 }
    elseif ($hasEmail -eq $true)                  { $score += 5 }

    if ($p.has_direct_phone -eq 'Yes') { $score += 5 }
    return $score
}

function Load-People($file) {
    $outerJson = Get-Content $file -Raw | ConvertFrom-Json
    # Handle wrapped format: [{type:"text", text:"{ people: [...] }"}]
    if ($outerJson -is [System.Array] -and $outerJson[0].PSObject.Properties.Name -contains 'text') {
        $innerText = $outerJson[0].text
        $inner = $innerText | ConvertFrom-Json
        if ($inner.PSObject.Properties.Name -contains 'people') {
            return $inner.people
        }
    }
    # Fallback: try direct
    if ($outerJson.PSObject.Properties.Name -contains 'people') { return $outerJson.people }
    return @()
}

foreach ($dataset in @('trucking','construction')) {
    $file    = if ($dataset -eq 'trucking') { $truckingFile } else { $constructFile }
    $outFile = if ($dataset -eq 'trucking') { $outTrucking } else { $outConstruction }

    Write-Host "=== Scoring $dataset leads ==="
    $people = Load-People $file
    Write-Host "  Total people loaded: $($people.Count)"

    $scored = $people | Where-Object { $_.id -and $_.id -ne '' } | ForEach-Object {
        [PSCustomObject]@{
            id      = $_.id
            score   = Score-Lead $_
            name    = "$($_.first_name) $($_.last_name_obfuscated)".Trim()
            title   = $_.title
            company = if ($_.organization) { $_.organization.name } else { '' }
            emp     = if ($_.organization -and $_.organization.num_employees) { $_.organization.num_employees } else { 0 }
            email_status = $_.email_status
            has_email    = $_.has_email
        }
    } | Sort-Object score -Descending

    Write-Host "  Top 25 leads:"
    $scored | Select-Object -First 25 | ForEach-Object {
        Write-Host "    [$($_.score)] $($_.name) | $($_.title) | $($_.company) (emp:$($_.emp)) | email:$($_.email_status)"
    }

    $top20 = $scored | Select-Object -First 20 | Select-Object -ExpandProperty id
    $top20 | Set-Content $outFile
    Write-Host "  Top 20 IDs saved to: $outFile"
    Write-Host ""
}
