$nl = [System.Environment]::NewLine
$rows = 'firstName,lastName,email,companyName,title'

# Group 1 (p74g1) inline
$rows += $nl + 'Ben,Pinkston,ben@classicoilfieldservices.com,Classic Crane & Transport LP,Owner/CEO'
$rows += $nl + 'Laurynas,Burauskas,lb@logiquanta.lt,Logiquanta,CEO'
$rows += $nl + 'Sarka,Petrasova,sarka.petrasova@jackrichards.co.uk,Jack Richards & Son Ltd,CEO'
$rows += $nl + 'Sar,Mikhaiel,sarmikhaiel@mikhaiellogistics.com,Mikhaiel Logistics,CEO'
$rows += $nl + 'Joaquin,Nieves,jnieves@mpostal.com,Multipak Postal Service Inc.,President-CEO'

# Group 2 (p74g2) inline
$rows += $nl + 'Ken,O''Brien,kobrien@geminishippers.com,Gemini Shippers Group,CEO'
$rows += $nl + 'Will,Webber,wwebber@shipperservices.com,Shipper Services LLC,CEO'
$rows += $nl + 'Patricia,Partida,ppartida@ppgloballogistics.com,P&P Global Logistics,CEO & Founder'
$rows += $nl + 'Alex,Brooke,alexisbrooke@advancedexpress.com,ADVANCED EXPRESS INC,CEO'
$rows += $nl + 'Noman,Khan,noman@nhk-logistics.com,NHK LOGISTICS LLC,CEO'

# Group 4 (p74g4) inline
$rows += $nl + 'Mattos,Cristiano,cristiano.mattos@brachmannlogistics.com,Brachmann Worldwide Logistics,CEO'
$rows += $nl + 'Yehia,Alaily,y.alaily@mtslogistics.net,MTS Logistics,CEO'
$rows += $nl + 'Wesley,Gajda,wesley.gajda@trucktransfer.com,TRUCK TRANSFER SYSTEM,Safety & Compliance Director'
$rows += $nl + 'Edward,Haser,eph@reinsfelder.com,Reinsfelder Inc.,CEO'
$rows += $nl + 'Lisa,Kuan,lkuan@ilmcorp.net,Integrated Logisitics Management Corporation,CEO'

# Group 5 (p74g5) inline
$rows += $nl + 'Bouchard,Brian,brianb@hobouchard.com,H.O. Bouchard Inc,President/CEO'
$rows += $nl + 'Khasan,Malikov,kmalikov@wr.group,WR Logistics,CEO'
$rows += $nl + 'Amandeep,Singh,aman@safextransport.ca,SAFEX TRANSPORT,CEO'
$rows += $nl + 'Lucas,Grizz,lgrizz@raven-cargo.com,Raven Cargo,CEO'
$rows += $nl + 'Anil,Srivastava,asrivastava@pragmacharge.com,PragmaCharge,CEO'

# Group 7 (p75g2) inline
$rows += $nl + 'Zulvikar,Alvathansena,zulvikar.alvathansena@lestarijayaraya.com,LJR LOGISTICS,CEO'
$rows += $nl + 'Grancea,Razvan,g.razvan@fraexpress.com,FraExpress,CEO'
$rows += $nl + 'Thomas,Wetter,thomas@wettertransport.dk,Wetter Transport,CEO'
$rows += $nl + 'Dave,Trick,dave.trick@transport-us.com,Transport US,Director of Safety & Compliance'
$rows += $nl + 'Matt,Lawrence,mlawrence@foxlogistics.com,Fox Logistics,CEO'

# Group 8 (p75g3) inline
$rows += $nl + 'Lindemberg,Krelakian,lindemberg@dlktransportes.com.br,DLK TRANSPORTES LTDA.,CEO'
$rows += $nl + 'Tom,Boo,tboo@transunited.com,Trans-United Specialized Hauling,Director of Safety'
$rows += $nl + 'Jennifer,Raddatz,jraddatz@kandjtrucking.com,K & J Trucking Inc.,Safety Director'
$rows += $nl + 'George,Booth,george.booth@securegl.com,SecureGlobal Logistics,CEO'
$rows += $nl + 'John,Mims,jmims@cntlogistics.net,CNT Logistics LLC,CEO'

# Group 9 (p75g4) inline
$rows += $nl + 'Andrey,Rosa,andrey@unitylogistics.com.br,Unity Logistics,CEO'
$rows += $nl + 'Larry,Zogby,larry@rdsdelivery.com,RDS Same Day Delivery,CEO'
$rows += $nl + 'Donish,Dhawan,donish@goglobex.com,Globex Logistics Inc.,President & CEO'

# Group 3 (p74g3) inline
$rows += $nl + 'Robert,Comelli,rcomelli@trianglelogistics.com.au,Triangle Logistics Management,CEO'
$rows += $nl + 'Robert,Flores,rflores@classiccarriers.com,Classic Carriers Inc.,Director of Safety'
$rows += $nl + 'Viktor,Kozlovskij,viktor@lotosbaltica.lt,Lotos Baltica,CEO'
$rows += $nl + 'Drew,Taylor,drew@digitalnomadu.com,Movement Logistics,Founder & CEO'
$rows += $nl + 'Charles,Sarkis,charles.sarkis@motionisc.com,MOTION Supply Chain,Founder & CEO'
$rows += $nl + 'Mick,McMahon,mmmcmahon@intercitydirect.com,InterCity Direct LLC,CEO'

# Group 6 (p74g6) inline
$rows += $nl + 'Blake,Eldredge,beldredge@pointdedicated.com,Point Dedicated Services Inc.,CEO'
$rows += $nl + 'Rachid,Fergati,rfergati@primelogistics.ae,Prime Logistics,CEO'
$rows += $nl + 'John,Garrett,john@garrettlogistics.co,Garrett Logistics LLC.,CEO'
$rows += $nl + 'Desi,Evans,desi@dolchecorp.com,Dolche Truckload Corp.,CEO'

$count = 43
[System.IO.File]::WriteAllText('C:\Users\ChadGriffith\Downloads\fileflo-f11afbf5-main (2)\compliance_proof_leads_batch31.csv', $rows)
Write-Host ('Done. Leads: ' + $count)
