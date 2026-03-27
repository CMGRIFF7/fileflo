$dir = 'C:\Users\ChadGriffith\Downloads\osha_extracted'
$files = Get-ChildItem $dir -Filter '*.csv' | Sort-Object Name
Write-Host "Total chunks: $($files.Count)"
$totalMB = ($files | Measure-Object Length -Sum).Sum / 1MB
Write-Host "Total size: $([math]::Round($totalMB, 1)) MB"

Write-Host "`nFirst chunk headers:"
Get-Content $files[0].FullName -TotalCount 1

Write-Host "`nFirst chunk sample row:"
Get-Content $files[0].FullName -TotalCount 2 | Select-Object -Last 1

# FMCSA file
Write-Host "`n=== FMCSA FILE ==="
$fmcsa = 'C:\Users\ChadGriffith\Downloads\rbkj-cgst_version_108.csv'
if (Test-Path $fmcsa) {
    $info = Get-Item $fmcsa
    Write-Host "Size: $([math]::Round($info.Length / 1MB, 1)) MB"
    Write-Host "Headers:"
    Get-Content $fmcsa -TotalCount 1
    Write-Host "Sample row:"
    Get-Content $fmcsa -TotalCount 2 | Select-Object -Last 1
} else {
    Write-Host "File not found"
}
