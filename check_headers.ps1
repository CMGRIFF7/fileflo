$dir = 'C:\Users\ChadGriffith\Downloads\osha_extracted'
$files = Get-ChildItem $dir -Filter '*.csv' | Sort-Object Name

$inspFile = $files | Where-Object { $_.Name -match '04-17-12' } | Select-Object -First 1
$violFile = $files | Where-Object { $_.Name -match '04-27-29' } | Select-Object -First 1

Write-Host '=== INSPECTION HEADERS ==='
Get-Content $inspFile.FullName -TotalCount 1

Write-Host ''
Write-Host '=== VIOLATION HEADERS ==='
Get-Content $violFile.FullName -TotalCount 1

Write-Host ''
Write-Host '=== VIOLATION SAMPLE ROW ==='
Get-Content $violFile.FullName -TotalCount 2 | Select-Object -Last 1

$inspCount = ($files | Where-Object { $_.Name -match '04-17-12' }).Count
$violCount = ($files | Where-Object { $_.Name -match '04-27-29' }).Count
Write-Host ""
Write-Host "Inspection chunks: $inspCount"
Write-Host "Violation chunks:  $violCount"

Write-Host ""
Write-Host "=== FMCSA SAMPLE ROWS ==="
$fmcsa = 'C:\Users\ChadGriffith\Downloads\rbkj-cgst_version_108.csv'
Get-Content $fmcsa -TotalCount 4
