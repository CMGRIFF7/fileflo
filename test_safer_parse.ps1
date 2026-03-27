# Test SAFER API HTML structure for a known DOT number
$dot = '818175'
$url = "https://safer.fmcsa.dot.gov/query.asp?searchtype=ANY&query_type=queryCarrierSnapshot&query_param=USDOT&query_string=$dot"

$response = Invoke-WebRequest -Uri $url -TimeoutSec 15 -UseBasicParsing
$html = $response.Content

# Save to file so we can inspect it
$html | Out-File 'C:\Users\ChadGriffith\Downloads\fileflo-f11afbf5-main (2)\safer_sample.html'
Write-Host "HTML saved. Length: $($html.Length)"

# Find "Legal Name" context
$lnIdx = $html.IndexOf('Legal Name')
Write-Host "Legal Name found at index: $lnIdx"
if ($lnIdx -gt 0) {
    Write-Host "Context around Legal Name (200 chars):"
    Write-Host $html.Substring($lnIdx, [Math]::Min(400, $html.Length - $lnIdx))
}

# Find all TD values in the page
Write-Host ""
Write-Host "=== ALL TD VALUES (non-empty, under 100 chars) ==="
$tdPat = [System.Text.RegularExpressions.Regex]::new('<td[^>]*>([^<]{2,100})</td>')
$tdMatches = $tdPat.Matches($html)
$count = 0
foreach ($m in $tdMatches) {
    $val = $m.Groups[1].Value.Trim()
    if ($val -ne '' -and $val -ne '&#160;' -and $count -lt 30) {
        Write-Host "  TD[$count]: '$val'"
        $count++
    }
}
