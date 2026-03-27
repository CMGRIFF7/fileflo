$nl = [System.Environment]::NewLine
$rows = 'firstName,lastName,email,companyName,title'
$count = 0

# p57c inline
$rows += $nl + 'John,Jordan,jjordan@totallogisticservices.com,Total Logistic Services,President & CEO'
$rows += $nl + 'Rodrigo,Alves,rodrigo.alves@mondego-group.com,Mondego Group,Co Owner CEO'
$rows += $nl + 'Deepak,Gupta,deepak@bgfcindia.com,Bombay Goods Freight Carriers,CEO'
# p58g3 inline
$rows += $nl + 'Frank,Malson,frank-malson@alliancelogist.com,Alliance Logistics Inc,Vice President / Owner'
$rows += $nl + 'Maiquel,Mello,mmello@suntransportationservice.com,Sun Global Transportation,CEO'
$count = 5

[System.IO.File]::WriteAllText('C:\Users\ChadGriffith\Downloads\fileflo-f11afbf5-main (2)\compliance_proof_leads_batch25.csv', $rows)
Write-Host ('Done. Leads: ' + $count)
