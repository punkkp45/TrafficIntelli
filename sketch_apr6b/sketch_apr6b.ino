#include <ESP8266WiFi.h>
#include <ESP8266WebServer.h>
#include <ESP8266HTTPClient.h>

const char* ssid = "PUNK GT 6";
const char* password = "punkgt.exe";
const char* apiURL = "http://10.163.100.90:8000/traffic/cycle";

ESP8266WebServer server(80);
String displayData = "";

void handleRoot(){ server.send(200,"text/html",webpage()); }
void handleData(){ server.send(200,"text/plain",displayData); }

// 🔥 FIXED COMMAND SENDING
void handleCmd(){
  String cmd = server.arg("c");
  cmd.trim();

  Serial.println(cmd);   // 🔥 send to Arduino

  server.send(200,"text/plain","OK");
}
// ===== WEBPAGE =====
String webpage(){
return R"rawliteral(
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1">

<style>
body {
  margin:0;
  font-family:'Segoe UI';
  background: linear-gradient(135deg,#0f0024,#1a0033,#240046);
  color:white;
  text-align:center;
}

h1 { color:#c77dff; }

/* CARD */
.card {
  width:90%;
  margin:20px auto;
  padding:20px;
  border-radius:15px;
  background:rgba(255,255,255,0.05);
  box-shadow:0 0 25px rgba(168,85,247,0.3);
}

/* TABLE */
table { width:100%; border-collapse:collapse; }
th { color:#c77dff; padding:10px; }
td { padding:10px; }

.active {
  background:rgba(168,85,247,0.3);
  box-shadow:0 0 10px #a855f7;
}

.red { color:#ff4d6d; }
.green { color:#00f5d4; }
.timer { color:#ffd60a; font-weight:bold; }

/* BUTTONS */
button {
  padding:10px 15px;
  margin:5px;
  border:none;
  border-radius:8px;
  background:#9d4edd;
  color:white;
}

/* ===== JUNCTION ===== */
.junction {
  position:relative;
  width:300px;
  height:300px;
  margin:30px auto;
}

.center {
  position:absolute;
  width:80px;
  height:80px;
  background:#222;
  top:110px;
  left:110px;
  border-radius:10px;
}

.lane {
  position:absolute;
  background:rgba(255,255,255,0.05);
  border-radius:8px;
  display:flex;
  align-items:flex-end;
  justify-content:center;
}

.vertical { width:60px; height:120px; }
.horizontal { width:120px; height:60px; }

#laneV1 { top:0; left:120px; }
#laneV2 { bottom:0; left:120px; }
#laneH3 { left:0; top:120px; }
#laneH4 { right:0; top:120px; }

.bar {
  width:80%;
  height:0%;
  background:linear-gradient(#ff0054,#ff5400);
  border-radius:5px;
  transition:0.5s;
}

.activeLane {
  box-shadow:0 0 15px #00f5d4;
}

</style>
</head>

<body>

<h1>Smart Traffic Dashboard</h1>

<div class="card">
<table>
<tr><th>Lane</th><th>Vehicles</th><th>Status</th><th>Time</th></tr>
<tr id="lane1"><td>1</td><td id="l1">0</td><td id="s1">-</td><td class="timer" id="t1">0</td></tr>
<tr id="lane2"><td>2</td><td id="l2">0</td><td id="s2">-</td><td class="timer" id="t2">0</td></tr>
<tr id="lane3"><td>3</td><td id="l3">0</td><td id="s3">-</td><td class="timer" id="t3">0</td></tr>
<tr id="lane4"><td>4</td><td id="l4">0</td><td id="s4">-</td><td class="timer" id="t4">0</td></tr>
</table>
</div>



<h3 id="mode"></h3>
<h3 id="emg"></h3>

<button onclick="send('L1')">L1</button>
<button onclick="send('L2')">L2</button>
<button onclick="send('L3')">L3</button>
<button onclick="send('L4')">L4</button>

<br>
<button onclick="send('EMG')">Emergency</button>
<button onclick="send('AUTO')">Auto</button>

<script>

function send(c){ fetch('/cmd?c='+c); }

async function update(){

 let res = await fetch('/data');
 let txt = await res.text();
 let p = txt.split(",");

 // 🔥 now expecting FULL DATA (11 values)
 if(p.length < 11) return;

 let active = parseInt(p[6]);

 let l1 = parseInt(p[0]);
 let l2 = parseInt(p[1]);
 let l3 = parseInt(p[2]);
 let l4 = parseInt(p[3]);

 // ✅ NEW: individual timers
 let timers = [
   parseInt(p[7]),
   parseInt(p[8]),
   parseInt(p[9]),
   parseInt(p[10])
 ];

 // ===== TABLE UPDATE =====
 document.getElementById("l1").innerHTML=l1;
 document.getElementById("l2").innerHTML=l2;
 document.getElementById("l3").innerHTML=l3;
 document.getElementById("l4").innerHTML=l4;

 document.getElementById("mode").innerHTML="Mode: "+p[4];
 document.getElementById("emg").innerHTML="Emergency: "+p[5];

 for(let i=1;i<=4;i++){

   document.getElementById("lane"+i).classList.remove("active");

   // 🔥 FIX: different timer per lane
   document.getElementById("t"+i).innerHTML = timers[i-1] + "s";

   if(i == active){
     document.getElementById("s"+i).innerHTML="GREEN";
     document.getElementById("s"+i).className="green";
   } else {
     document.getElementById("s"+i).innerHTML="RED";
     document.getElementById("s"+i).className="red";
   }
 }

 document.getElementById("lane"+active).classList.add("active");

 // ===== DENSITY BARS =====
 document.getElementById("bar1").style.height = (l1*8)+"%";
 document.getElementById("bar2").style.height = (l2*8)+"%";
 document.getElementById("bar3").style.width  = (l3*8)+"%";
 document.getElementById("bar4").style.width  = (l4*8)+"%";

 // ===== ACTIVE LANE HIGHLIGHT =====
 ["laneV1","laneV2","laneH3","laneH4"].forEach(id=>{
   document.getElementById(id).classList.remove("activeLane");
 });

 if(active==1) document.getElementById("laneV1").classList.add("activeLane");
 if(active==2) document.getElementById("laneV2").classList.add("activeLane");
 if(active==3) document.getElementById("laneH3").classList.add("activeLane");
 if(active==4) document.getElementById("laneH4").classList.add("activeLane");
}

// 🔥 smoother + real-time feel
setInterval(update,1000);

</script>

</body>
</html>
)rawliteral";
}
void sendCycleToAPI(String cycleData){

  if(WiFi.status() != WL_CONNECTED){
    Serial.println("API ERROR: WiFi disconnected");
    return;
  }

  WiFiClient client;
  HTTPClient http;

  http.begin(client, apiURL);

  http.addHeader("Content-Type", "text/plain");

  Serial.println("Sending cycle data to API...");

  int httpCode = http.POST(cycleData);

  if(httpCode > 0){

    Serial.print("API Response Code: ");
    Serial.println(httpCode);

    String response = http.getString();

    Serial.print("API Response: ");
    Serial.println(response);

  }
  else{

    Serial.print("API Connection Failed: ");
    Serial.println(http.errorToString(httpCode));
  }

  http.end();
}

// ===== SETUP =====
void setup(){

  Serial.begin(9600);
  delay(1000);

  Serial.println();
  Serial.println("================================");
  Serial.println("   TRAFFICINTELLI ESP8266");
  Serial.println("================================");

  Serial.print("Connecting to WiFi: ");
  Serial.println(ssid);

  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);

  int attempts = 0;

  while(WiFi.status() != WL_CONNECTED && attempts < 30){

    delay(500);

    Serial.print(".");

    attempts++;
  }

  Serial.println();

  if(WiFi.status() == WL_CONNECTED){

    Serial.println("WiFi Connected!");
    Serial.print("IP Address: ");
    Serial.println(WiFi.localIP());

    Serial.print("Signal Strength: ");
    Serial.print(WiFi.RSSI());
    Serial.println(" dBm");

  }
  else{

    Serial.println("ERROR: WiFi connection failed!");
    Serial.println("Check SSID and password.");
  }

  // Start web server regardless
  server.on("/", handleRoot);
  server.on("/data", handleData);
  server.on("/cmd", handleCmd);

  server.begin();

  Serial.println("Web server started.");
  Serial.println("================================");
}

void loop(){

  server.handleClient();

  if(Serial.available()){

    String incomingData = Serial.readStringUntil('\n');
    incomingData.trim();

    if(incomingData.startsWith("CYCLE|")){

      sendCycleToAPI(incomingData);

    }
    else{

      displayData = incomingData;
    }
  }
}