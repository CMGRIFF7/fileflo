$nl = [System.Environment]::NewLine
$rows = 'firstName,lastName,email,companyName,title'

# Group p78g2 inline
$rows += $nl + 'Renee,Osaer,rosaer@moonstarexpress.com,MOON STAR EXPRESS LLC,Director Human Resources Safety'
$rows += $nl + 'Tadej,Brce,tadej@prevozi-brce.si,Brce d.o.o.,CEO'
$rows += $nl + 'Alice,Xu,alice@yunquna.com,YQN Logistics,Co-founder'
$rows += $nl + 'Fabio,Garcia,fgarcia@fgmglobal.com,FGM Supply Chain,CEO'
$rows += $nl + 'Alexander,Olafsson,alexander@isafolddc.com,Isafold Distribution Center,CEO'

# Group p78g3 inline
$rows += $nl + 'Jack,Williams,jwilliams@penntanklines.com,Penn Tank Lines,COO'
$rows += $nl + 'Julio,Guimaraes,julio@loogistico.com,Loogistico.com,Founder/CEO'
$rows += $nl + 'Ross,Schager,ross@hightidelogistics.com,High Tide Logistics,Owner'
$rows += $nl + 'Kasey,Bistritz,kasey@unitedroutes.com,United Routes LLC,CEO & Founder'
$rows += $nl + 'Paul,Randhawa,paul@nflfreight.com,National Freight Logistics Inc,CEO'

# Group p78g6 inline
$rows += $nl + 'Bryan,Wainwright,bryan@lantraxlogistics.com,Lantrax Logistics Ltd,President'
$rows += $nl + 'Renata,Riaz,renata.riaz@allportcs.com,Allport Cargo Services USA,SVP Operations'
$rows += $nl + 'Nayana,Suphavong,nayana@shipjade.com,Jade Logistics,President & CEO'
$rows += $nl + 'Tom,Sanderfoot,tom@northshorelogistics.com,North Shore Logistics,President'
$rows += $nl + 'Evan,Lamensdorf,evan@tanklogisticsllc.com,Tank Logistics LLC,VP Operations'

# Group p78g7 inline
$rows += $nl + 'Brian,Stoller,bstoller@stollertrucking.com,Stoller Trucking LLC,Owner'
$rows += $nl + 'Amy,Neal,amy@mtnstatelogistics.com,Mountain State Logistics,Business Owner'
$rows += $nl + 'Scholastica,McIlscm,mcilscm@aseplogistics.com,ASEP Logistics,Managing Director/CEO'
$rows += $nl + 'Shaun,Kark,shaun@prologik.co.za,Prologik (Pty) Ltd,CEO'
$rows += $nl + 'Stephen,Jones,sjones@blackwoodgroup.net,Blackwood Industries,President COO'

# Group p78g8 inline
$rows += $nl + 'Stacey,Lieberman,stacey@normansairfreight.com,Norman''s Air Freight,President'
$rows += $nl + 'Susan,Duckworth,s_duckworth@nefreighttransfer.com,Northeast Freight Transfer,President'
$rows += $nl + 'Ekaterina,Noymann,ekaterina.noymann@noytech.com,NOYTECH Supply Chain Solutions,Group CEO'
$rows += $nl + 'Shawn,Shumate,shawn@eaglerockfreight.com,Eagle Rock Freight,Owner'

# Group p78g10 inline
$rows += $nl + 'Can,Eryigit,can.eryigit@yekas.com,Yekas Fides Global Logistics,COO Seafreight'
$rows += $nl + 'Ronnie,Herrin,ronnie.herrin@bightransport.com,Big H Transport LLC,CEO'
$rows += $nl + 'Herbert,Karl,herbert.karl@logistica-ils.com,ILS Servicios Logisticos,CEO'
$rows += $nl + 'Patricia,Coelho,patricia.coelho@grupojpcargo.com.br,JP Logistica e Transportes,CEO'
$rows += $nl + 'Aman,Singh,aman@transcanamlogistics.ca,TRANS-CANAM LOGISTICS INC,President'

# Group p78g1 recovery
$rows += $nl + 'Jesus,Lozano Gil,jlozano@lotransportes.com,Lotrans Portes SL,CEO'
$rows += $nl + 'Joshua,Ruple,jruple@usdg.com,USD Group LLC,EVP & COO'
$rows += $nl + 'Kristin,Persu,kpersu@goscr.com,SCR Medical Transportation Inc.,Vice President Operations'
$rows += $nl + 'Gene,Maher,gene.maher@vplogistics.com,VP Logistics,President'
$rows += $nl + 'Stuart,Reid,sreid@islesofscilly-travel.co.uk,Isles of Scilly Steamship Group,Chief Executive Officer'

# Group p78g4 recovery
$rows += $nl + 'Jason,Campbell,jason@dedicatedfh.com,Dedicated Freight Handlers,President of Operations'
$rows += $nl + 'Lakhotia,Rajeev,lakhotia.rajeev@rbtlogistics.in,RBT Logistics,Company Owner'
$rows += $nl + 'Betty,Brown,bbrown@citylogistics.com,CITY LOGISTICS SERVICES INC,Owner/President'
$rows += $nl + 'Bobby,Andhika,bobby.andhika@abl.co.id,PT Asian Bulk Logistics,Chief Operating Officer'

# Group p78g5 recovery
$rows += $nl + 'Giancarlo,Staffieri,gstaffieri@proactivegroup.ca,Proactive Supply Chain Group,President'
$rows += $nl + 'Manas,Fcilt,manas@oceanicllp.com,Oceanic Express LLP,CEO & Partner'
$rows += $nl + 'Rolf,Maliepaard,rm@vanderwees.nl,Koninklijke Van der Wees Transporten,CEO'
$rows += $nl + 'Jo,McCormick,jmccormick@jlrothrock.com,J.L. Rothrock Inc,Vice President/Owner'
$rows += $nl + 'Garrett,Sweigert,gsweigert@blkout.com,Blk Out Logistics,President'
$rows += $nl + 'Marat,Martirosyan,marat@nslbrokers.com,NorthStar Logistics LLC,President'

# Group p78g9 recovery
$rows += $nl + 'Andrzej,Krupowicz,a.krupowicz@multi-spedytor.pl,Multi Spedytor,Chief Operating Officer'
$rows += $nl + 'Eddy,Batty,eddy.batty@clearship.com,Clearship Group,COO'

$count = 46
[System.IO.File]::WriteAllText('C:\Users\ChadGriffith\Downloads\fileflo-f11afbf5-main (2)\compliance_proof_leads_batch33.csv', $rows)
Write-Host ('Done. Leads: ' + $count)
