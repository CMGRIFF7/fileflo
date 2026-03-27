$f = 'C:\Users\ChadGriffith\.claude\projects\C--Users-ChadGriffith-Downloads-fileflo-f11afbf5-main--2-\25f4119b-38a1-45f8-905d-b6d5752789d6\tool-results\toolu_0151Yw3EdmnvauE5WCtdz5p8.json'
$raw = Get-Content $f -Raw
$outer = $raw | ConvertFrom-Json
$inner = $outer[0].text | ConvertFrom-Json
$people = $inner.people

Write-Host "Total people returned: $($people.Count)"

$results = @()
foreach ($p in $people) {
    $score = 0
    $title = if ($p.title) { $p.title.ToLower() } else { '' }
    $lastRefreshed = $p.last_refreshed_at
    $hasEmail = $p.has_email
    $hasPhone = $p.has_direct_phone
    $hasRevenue = if ($p.organization) { $p.organization.has_revenue } else { $false }

    # Seniority scoring
    if ($title -match 'owner|president|founder|principal|ceo|coo|cfo|managing') { $score += 25 }
    elseif ($title -match '\bvp\b|vice president|svp|director') { $score += 20 }
    elseif ($title -match 'senior|manager|producer|supervisor') { $score += 15 }
    elseif ($title -match 'agent|broker|account') { $score += 10 }

    # Commercial/OSHA title bonus
    if ($title -match 'commercial|workers comp|workers compensation|osha|safety|risk|liability') { $score += 10 }

    # Has email
    if ($hasEmail) { $score += 20 }

    # Phone
    if ($hasPhone -eq 'Yes') { $score += 10 }
    elseif ($hasPhone -eq 'Maybe') { $score += 3 }

    # Revenue
    if ($hasRevenue) { $score += 10 }

    # Recency
    if ($lastRefreshed) {
        $refreshDate = [datetime]::Parse($lastRefreshed)
        $daysAgo = ([datetime]::UtcNow - $refreshDate).Days
        if ($daysAgo -le 14) { $score += 5 }
        elseif ($daysAgo -le 30) { $score += 3 }
        elseif ($daysAgo -le 60) { $score += 1 }
    }

    $orgName = if ($p.organization) { $p.organization.name } else { 'N/A' }

    $results += [PSCustomObject]@{
        Id        = $p.id
        FirstName = $p.first_name
        LastObf   = $p.last_name_obfuscated
        Title     = $p.title
        OrgName   = $orgName
        HasEmail  = $hasEmail
        HasPhone  = $hasPhone
        HasRevenue = $hasRevenue
        Score     = $score
    }
}

$sorted = $results | Sort-Object Score -Descending
$top20 = $sorted | Select-Object -First 20

Write-Host "`nTOP 20 LEADS:"
$i = 1
foreach ($r in $top20) {
    Write-Host "$i. [$($r.Score)pts] $($r.FirstName) $($r.LastObf) | $($r.Title) | $($r.OrgName) | ID: $($r.Id)"
    $i++
}

Write-Host "`nTop 20 IDs for bulk_match:"
$ids = $top20 | ForEach-Object { $_.Id }
Write-Host ($ids -join '", "')
