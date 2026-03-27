$paths = @(
    'C:\Users\ChadGriffith\AppData\Local\Temp',
    'C:\Users\ChadGriffith\Downloads',
    'C:\Users\ChadGriffith\Downloads\fileflo-f11afbf5-main (2)'
)
foreach ($p in $paths) {
    $files = Get-ChildItem $p -Filter 'toolu_*.json' -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 5
    if ($files) {
        Write-Host "=== $p ==="
        foreach ($f in $files) {
            Write-Host "  $($f.Name) | $($f.Length) bytes | $($f.LastWriteTime)"
        }
    }
}

# Also check claude tool result caches
$claudeCache = 'C:\Users\ChadGriffith\.claude'
if (Test-Path $claudeCache) {
    $jsonFiles = Get-ChildItem $claudeCache -Filter 'toolu_*.json' -Recurse -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 5
    foreach ($f in $jsonFiles) { Write-Host "Claude cache: $($f.FullName)" }
}
