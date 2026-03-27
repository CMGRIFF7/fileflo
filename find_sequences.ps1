$f = 'C:\Users\ChadGriffith\.claude\projects\C--Users-ChadGriffith-Downloads-fileflo-f11afbf5-main--2-\25f4119b-38a1-45f8-905d-b6d5752789d6.jsonl'
$lines = Get-Content $f
Write-Host "Total lines: $($lines.Count)"

# Look for lines containing campaign sequence content
foreach ($line in $lines) {
    $obj = $line | ConvertFrom-Json -ErrorAction SilentlyContinue
    if ($obj -and $obj.message) {
        $msg = $obj.message
        if ($msg.role -eq 'user') {
            $content = $msg.content
            if ($content -is [array]) {
                foreach ($c in $content) {
                    if ($c.type -eq 'text' -and $c.text -match 'Step 1.*Subject|FMCSA|sequence_bodies|Variant A|step.*delay|email.*sequence') {
                        Write-Host "=== USER MESSAGE ==="
                        Write-Host $c.text.Substring(0, [Math]::Min(5000, $c.text.Length))
                        Write-Host "..."
                        break
                    }
                }
            } elseif ($content -is [string] -and $content -match 'Step 1.*Subject|FMCSA|Variant A') {
                Write-Host "=== USER STRING MESSAGE ==="
                Write-Host $content.Substring(0, [Math]::Min(5000, $content.Length))
            }
        }
    }
}
