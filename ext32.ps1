$nl = [System.Environment]::NewLine
$rows = 'firstName,lastName,email,companyName,title'

# Group 1 (p76g1) inline
$rows += $nl + 'Shawnte,Mays,s.mays@rctransportations.com,RC''s Logistics & Transportation,Founder and CEO'
$rows += $nl + 'Rodrigo,Torres Gonzalez,rtorres@dpods.io,DPODS,Founder & CEO'
$rows += $nl + 'Mayra,Montezano,mayra.montezano@wpclogistics.com.br,WPC Logistics,Chief Operating Officer'
$rows += $nl + 'Daren,Wickham,dwickham@cavlog.com,Cavalier Logistics,Vice President Operations'
$rows += $nl + 'Roland,Pfister,roland.pfister@crossfreight-logistics.com,Crossfreight Logistics Ltd.,President & CEO'

# Group 2 (p76g2) inline
$rows += $nl + 'Tom,Chalermkarnchana,tom@tccs.co.th,TCC Logistics Limited,CEO'
$rows += $nl + 'Joshua,McGrory,josh@rogerstransport.com.au,Rogers Transport Pty Ltd,COO'
$rows += $nl + 'Kamil,Korab,k.korab@simcotransport.pl,Simco Transport,Co-founder CEO'
$rows += $nl + 'Michael,Smith,msmith@butlertransport.com,Butler Transport Inc.,Director of Safety & Training'
$rows += $nl + 'Raymond,Fleurant,raymond.fleurant@thegtigroup.com,THE GTI GROUP,Director of Safety and Training'

# Group 3 (p76g3) inline
$rows += $nl + 'Anabel,Panayotti,anabelp@ptpshipping.com,Port to Port International Corp.,President/CEO'
$rows += $nl + 'Matthew,Smith,matt@rngtransportation.com,RenewGas Transportation,President and Founder'
$rows += $nl + 'Aaron,Washington,aaron@scandsolutions.com,Safety Compliance Solutions,President/CEO'
$rows += $nl + 'Joseph,Benny,j.benny@swenlog.com,SWENLOG SUPPLY CHAIN SOLUTIONS PVT LTD,COO'
$rows += $nl + 'Dominic,Forbes,dominicforbes@classictransportation.com,Classic Transportation & Warehousing,Safety Director'

# Group 4 (p76g4) inline
$rows += $nl + 'Paul,Talley,laxptal@airseainc.com,Air-Sea Forwarders Inc.,President & COO'
$rows += $nl + 'Gary,Whitacre,gwhitacre@whitacrelogistics.com,Whitacre Logistics LLC,CEO'
$rows += $nl + 'Doug,Mellum,dougm@elitetransportationsys.com,Elite Transportation Systems Inc,President/Owner/Founder'
$rows += $nl + 'Kristine,Kupcane,kristine@wellman.lv,Wellman Logistics,CEO'
$rows += $nl + 'Bill,Brandt,bill@brandttruck.com,Paul Brandt Trucking Ltd.,President & Operations Manager'

# Group 5 (p76g5) inline
$rows += $nl + 'Harman,Mago,harman@gsmfreight.ca,GSM Freight,CEO'
$rows += $nl + 'Jeff,Moore,jeff.moore@alpinetubular.com,Alpine Supply Chain Management,Owner & CEO'
$rows += $nl + 'Manuel,Rojas Barbosa,mrojas@logistecsa.com,LOGISTECSA Supply Chain Solutions Provider,CEO'

# Group 6 (p77g6) inline
$rows += $nl + 'Paul,Melin,pmelin@vt.edu,Four Star Transportation,Vice President Operations'
$rows += $nl + 'Billy,Forkey,billy@fourkeyslogistics.com,Four Keys Logistics,CEO'
$rows += $nl + 'Megan,Fortenberry,mfortenberry@rwilogistics.com,RWI Logistics LLC,COO'
$rows += $nl + 'Matt,Manke,matt@manketrucking.com,Manke Trucking,Owner'
$rows += $nl + 'Joeleen,Naidoo,joeleen@kialogistics.co.za,King''s InterAfrica Logistics,COO'

# Group 7 (p77g7) inline
$rows += $nl + 'Tony,Serrano,tony@yvtllc.com,YVT - Yakima Valley Transportation LLC,CEO'
$rows += $nl + 'Cecil,Bryan,cecilb@logistics-alliance.com,Logistics Alliance Network,President & CEO'
$rows += $nl + 'Amit,Hasak,amit@transship.net,Transship Corp,Founder/CEO'
$rows += $nl + 'Tom,Boyle,tboyle@quikpickexpress.com,Quik Pick Express,CEO'
$rows += $nl + 'Chad,Porterfield,chad@ilgfreight.com,Indelible Logistics Group,President & Co-Founder'

# Group 8 (p77g8) inline
$rows += $nl + 'Walt,Kontra,waltk@ivbulk.com,INDIAN VALLEY BULK CARRIERS INC,VP/COO'
$rows += $nl + 'Mohit,Wadhwa,mohit.wadhwa@yatra.com,Yatra Freight,COO'
$rows += $nl + 'Louie,Sejdini,louie@cietransport.net,CIE TRANSPORT INC,CEO & President'
$rows += $nl + 'Gurvinder,Bhatthal,gurvinder@lightspeedcrown.com,LIGHTSPEEDCROWN GROUP,CEO & Founder'

$count = 37
[System.IO.File]::WriteAllText('C:\Users\ChadGriffith\Downloads\fileflo-f11afbf5-main (2)\compliance_proof_leads_batch32.csv', $rows)
Write-Host ('Done. Leads: ' + $count)
