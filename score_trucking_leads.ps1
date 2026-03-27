# Score Apollo trucking/logistics leads from previous search
# Input: toolu_01Xn5fYc2wuShoCMXe7yJVYm.json (73,857 trucking leads)
# Output: top 20 IDs for bulk_match enrichment

$inputFile = 'C:\Users\ChadGriffith\AppData\Local\Temp\toolu_01Xn5fYc2wuShoCMXe7yJVYm.json'

# Check common paths
$paths = @(
    'C:\Users\ChadGriffith\AppData\Local\Temp\toolu_01Xn5fYc2wuShoCMXe7yJVYm.json',
    'C:\Users\ChadGriffith\Downloads\fileflo-f11afbf5-main (2)\toolu_01Xn5fYc2wuShoCMXe7yJVYm.json'
)
$found = $null
foreach ($p in $paths) { if (Test-Path $p) { $found = $p; break } }

if (-not $found) {
    Write-Host "Trucking JSON not found. Listing recent JSON files..."
    Get-ChildItem 'C:\Users\ChadGriffith\AppData\Local\Temp' -Filter 'toolu_*.json' |
        Sort-Object LastWriteTime -Descending | Select-Object -First 10 | ForEach-Object {
        Write-Host "  $($_.FullName) ($([math]::Round($_.Length/1KB,0)) KB)"
    }
} else {
    Write-Host "Found: $found"
    $raw = Get-Content $found -Raw | ConvertFrom-Json
    Write-Host "Total entries: $($raw.Count)"
    # Show structure of first entry
    Write-Host "First entry keys: $($raw[0].PSObject.Properties.Name -join ', ')"
    if ($raw[0].PSObject.Properties.Name -contains 'people') {
        Write-Host "People count in first entry: $($raw[0].people.Count)"
        Write-Host "Sample person keys: $($raw[0].people[0].PSObject.Properties.Name -join ', ')"
    }
}
