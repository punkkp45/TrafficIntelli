#include <SPI.h>
#include <MFRC522.h>

#define SS_PIN 53
#define RST_PIN 5
MFRC522 mfrc522(SS_PIN, RST_PIN);

byte emergencyUID[4] = {0x26, 0x59, 0x7C, 0x12};

// IR
int ir[4][2] = {{23,22},{27,26},{31,30},{35,34}};

// LED
int red[4]   = {24,28,32,36};
int green[4] = {25,29,33,37};

// ================= TRAFFIC DATA =================

int count[4] = {0, 0, 0, 0};
int prev[4][2];

// Vehicles cleared during CURRENT cycle
int cleared[4] = {0, 0, 0, 0};

// Vehicle count captured at START of cycle
int cycleStartCount[4] = {0, 0, 0, 0};

// 0 = Low, 1 = Medium, 2 = High
int density[4] = {0, 0, 0, 0};

// Extra green time
int extraTime[4] = {0, 0, 0, 0};

// Final green time
int laneTime[4] = {30, 30, 30, 30};

int currentLane = 0;

unsigned long signalStart = 0;

// ================= CYCLE =================

int cycleNumber = 1;

unsigned long cycleStartMillis = 0;
unsigned long cycleEndMillis = 0;

int cycleDuration = 120;

bool densityMode = false;
bool prevDensityMode = false;

// ================= MODE =================

bool autoMode = true;

// ================= EMERGENCY =================

bool emergencyActive = false;

unsigned long emergencyStart = 0;

int emergencyLane = -1;

int previousLane = 0;
int previousRemaining = 30;

// Emergency information for current cycle
bool cycleEmergencyDetected = false;
int cycleEmergencyLane = -1;
unsigned long cycleEmergencyOffset = 0;

// Change this according to where your RFID reader is physically installed.
// 0 = Lane 1
// 1 = Lane 2
// 2 = Lane 3
// 3 = Lane 4
const int RFID_LANE = 0;

// SERIAL
unsigned long serialTimer = 0;
#define SERIAL_DELAY 1000

void setup() {
  Serial.begin(9600);
  Serial1.begin(9600);
  Serial1.setTimeout(50);

  SPI.begin();
  mfrc522.PCD_Init();

  for(int i=0;i<4;i++){
    for(int j=0;j<2;j++){
      pinMode(ir[i][j], INPUT);
      prev[i][j] = HIGH;
    }
    pinMode(red[i], OUTPUT);
    pinMode(green[i], OUTPUT);
  }

  setLane(0);
  signalStart = millis();
  startNewCycle();
}

void loop() {

  readSensors();
  checkRFID();
  readESP();

  if(emergencyActive) handleEmergency();
  else controlTraffic();

  sendData();
}

// SENSOR
void readSensors(){

  for(int i = 0; i < 4; i++){

    int far = digitalRead(ir[i][0]);
    int near = digitalRead(ir[i][1]);

    // Vehicle enters lane
    if(far == LOW && prev[i][0] == HIGH){
      count[i]++;
    }

    // Vehicle exits lane
    if(near == LOW && prev[i][1] == HIGH){

      if(count[i] > 0){
        count[i]--;
        cleared[i]++;
      }
    }

    prev[i][0] = far;
    prev[i][1] = near;
  }
}

// 🔥 RECEIVE COMMAND FROM ESP
void readESP(){

  if(Serial1.available()){

    String cmd = Serial1.readStringUntil('\n');

    cmd.trim();

    Serial.print("CMD RECEIVED → ");
    Serial.println(cmd);

    // ================= MANUAL CONTROL =================

    if(cmd == "L1"){
      autoMode = false;
      currentLane = 0;
      setLane(currentLane);
      signalStart = millis();
    }

    else if(cmd == "L2"){
      autoMode = false;
      currentLane = 1;
      setLane(currentLane);
      signalStart = millis();
    }

    else if(cmd == "L3"){
      autoMode = false;
      currentLane = 2;
      setLane(currentLane);
      signalStart = millis();
    }

    else if(cmd == "L4"){
      autoMode = false;
      currentLane = 3;
      setLane(currentLane);
      signalStart = millis();
    }

    // ================= AUTO =================

    else if(cmd == "AUTO"){

    autoMode = true;

    currentLane = 0;

    setLane(currentLane);

    signalStart = millis();

    startNewCycle();

    Serial.println("AUTO MODE ENABLED");
}
    // ================= EMERGENCY =================

    else if(cmd == "EMG"){

      // Manual emergency without lane information.
      // Current lane is used for now.
      startEmergency(currentLane);
    }

    // Optional manual emergency lane commands
    else if(cmd == "EMG1"){
      startEmergency(0);
    }

    else if(cmd == "EMG2"){
      startEmergency(1);
    }

    else if(cmd == "EMG3"){
      startEmergency(2);
    }

    else if(cmd == "EMG4"){
      startEmergency(3);
    }
  }
}

// MODE
void calculateTimes(){

  // ==========================================
  // PROPORTIONAL TRAFFIC CONTROL
  // ==========================================

  int total = 0;

  cycleDuration = 0;
  densityMode = false;

  // ------------------------------------------
  // 1. Capture traffic at beginning of cycle
  // ------------------------------------------

  for(int i = 0; i < 4; i++){

    cycleStartCount[i] = count[i];

    total += count[i];
  }

  // ------------------------------------------
  // 2. Reset timing values
  // ------------------------------------------

  for(int i = 0; i < 4; i++){

    laneTime[i] = 30;
    extraTime[i] = 0;
    density[i] = 0;
  }

  // ------------------------------------------
  // 3. Calculate proportional allocation
  // ------------------------------------------

  if(total > 0){

    for(int i = 0; i < 4; i++){

      /*
        Maximum additional time = 30 seconds.

        Proportion of traffic:
        
        lane count / total count

        Additional time:

        proportion × 30
      */

      int proportionalExtra =
        (count[i] * 30) / total;

      // Limit additional time to 30 seconds
      if(proportionalExtra > 30)
        proportionalExtra = 30;

      extraTime[i] = proportionalExtra;

      laneTime[i] = 30 + extraTime[i];

      // --------------------------------------
      // Density classification
      // --------------------------------------

      if(count[i] <= 10){

        density[i] = 0;       // LOW
      }

      else if(count[i] <= 20){

        density[i] = 1;       // MEDIUM
      }

      else{

        density[i] = 2;       // HIGH
      }
    }
  }

  // ------------------------------------------
  // 4. Determine whether adaptive mode active
  // ------------------------------------------

  for(int i = 0; i < 4; i++){

    if(count[i] > 10){

      densityMode = true;
      break;
    }
  }

  // ------------------------------------------
  // 5. Calculate complete cycle duration
  // ------------------------------------------

  for(int i = 0; i < 4; i++){

    cycleDuration += laneTime[i];
  }

  // ------------------------------------------
  // 6. Serial monitoring
  // ------------------------------------------

  Serial.println();
  Serial.println("========== TRAFFIC ANALYSIS ==========");

  Serial.print("Cycle: ");
  Serial.println(cycleNumber);

  Serial.print("Total Vehicles: ");
  Serial.println(total);

  for(int i = 0; i < 4; i++){

    Serial.print("L");
    Serial.print(i + 1);

    Serial.print(" | Vehicles: ");
    Serial.print(count[i]);

    Serial.print(" | Density: ");

    if(density[i] == 0)
      Serial.print("LOW");

    else if(density[i] == 1)
      Serial.print("MEDIUM");

    else
      Serial.print("HIGH");

    Serial.print(" | Extra: +");
    Serial.print(extraTime[i]);

    Serial.print("s | Green: ");
    Serial.print(laneTime[i]);
    Serial.println("s");
  }

  Serial.print("TOTAL CYCLE TIME: ");
  Serial.print(cycleDuration);
  Serial.println(" seconds");

  Serial.println("=======================================");

  if(densityMode != prevDensityMode){

    Serial.println(
      densityMode
      ? "⚡ ADAPTIVE TRAFFIC MODE"
      : "✅ NORMAL TRAFFIC MODE"
    );

    prevDensityMode = densityMode;
  }
}

void startNewCycle(){

  cycleStartMillis = millis();

  // Reset cycle-specific values
  for(int i = 0; i < 4; i++){
    cleared[i] = 0;
  }

  cycleEmergencyDetected = false;
  cycleEmergencyLane = -1;
  cycleEmergencyOffset = 0;

  // Calculate traffic conditions for this cycle
  calculateTimes();

  Serial.print("===== CYCLE ");
  Serial.print(cycleNumber);
  Serial.println(" START =====");
}
// RFID
void checkRFID(){

  if(!mfrc522.PICC_IsNewCardPresent())
    return;

  if(!mfrc522.PICC_ReadCardSerial())
    return;

  bool match = true;

  for(byte i = 0; i < 4; i++){

    if(mfrc522.uid.uidByte[i] != emergencyUID[i]){

      match = false;
      break;
    }
  }

  if(match){

    Serial.println("🚑 EMERGENCY RFID");

    startEmergency(RFID_LANE);
  }

  mfrc522.PICC_HaltA();
  mfrc522.PCD_StopCrypto1();
}

void startEmergency(int lane){

  if(emergencyActive)
    return;

  // Save current traffic state
  previousLane = currentLane;

  int elapsed =
    (millis() - signalStart) / 1000;

  previousRemaining =
    laneTime[currentLane] - elapsed;

  if(previousRemaining < 0)
    previousRemaining = 0;

  // Emergency information
  emergencyLane = lane;

  emergencyActive = true;

  emergencyStart = millis();

  // Record emergency in current cycle
  cycleEmergencyDetected = true;
  cycleEmergencyLane = lane;

  cycleEmergencyOffset =
    (millis() - cycleStartMillis) / 1000;

  Serial.print("🚑 Emergency Lane: ");
  Serial.println(lane + 1);

  Serial.print("Returning to Lane: ");
  Serial.println(previousLane + 1);

  Serial.print("Remaining Time: ");
  Serial.println(previousRemaining);
}
// TRAFFIC
void controlTraffic(){
  if(!autoMode)
    return;
  unsigned long elapsed =
    (millis() - signalStart) / 1000;

  if(elapsed >= laneTime[currentLane]){
    // If Lane 4 has finished,
    // the COMPLETE cycle has finished.
    if(currentLane == 3){
      finishCycle();
      cycleNumber++;
      currentLane = 0;
      setLane(currentLane);
      signalStart = millis();
      startNewCycle();
    }

    else{
      currentLane++;
      setLane(currentLane);
      signalStart = millis();
    }
  }
}

void finishCycle(){

  cycleEndMillis = millis();

  Serial.println();
  Serial.println("========== CYCLE COMPLETE ==========");

  Serial.print("Cycle Number: ");
  Serial.println(cycleNumber);

  Serial.print("Cycle Duration: ");
  Serial.print(cycleDuration);
  Serial.println(" sec");

  Serial.println("Vehicle Count at Start:");

  for(int i = 0; i < 4; i++){

    Serial.print("L");
    Serial.print(i + 1);
    Serial.print(": ");
    Serial.println(cycleStartCount[i]);
  }

  Serial.println("Vehicles Cleared:");

  for(int i = 0; i < 4; i++){

    Serial.print("L");
    Serial.print(i + 1);
    Serial.print(": ");
    Serial.println(cleared[i]);
  }

  Serial.println("Vehicles Remaining:");

  for(int i = 0; i < 4; i++){

    Serial.print("L");
    Serial.print(i + 1);
    Serial.print(": ");
    Serial.println(count[i]);
  }

  Serial.println("====================================");

  // Send cycle record to USB Serial.
  // ESP8266 integration will be added in Phase 2.
  sendCycleData();
}
// ================= SEND CYCLE DATA =================

void sendCycleData(){

  String data = "CYCLE|";

  // Cycle number
  data += String(cycleNumber);
  data += "|";

  // Planned cycle duration
  data += String(cycleDuration);
  data += "|";

  // ================= VEHICLE COUNT =================

  for(int i = 0; i < 4; i++){
    data += String(cycleStartCount[i]);
    data += "|";
  }

  // ================= DENSITY =================

  for(int i = 0; i < 4; i++){

    if(density[i] == 0)
      data += "LOW";

    else if(density[i] == 1)
      data += "MEDIUM";

    else
      data += "HIGH";

    data += "|";
  }

  // ================= GREEN TIME =================

  for(int i = 0; i < 4; i++){
    data += String(laneTime[i]);
    data += "|";
  }

  // ================= EXTRA TIME =================

  for(int i = 0; i < 4; i++){
    data += String(extraTime[i]);
    data += "|";
  }

  // ================= VEHICLES CLEARED =================

  for(int i = 0; i < 4; i++){
    data += String(cleared[i]);
    data += "|";
  }

  // ================= VEHICLES REMAINING =================

  for(int i = 0; i < 4; i++){
    data += String(count[i]);
    data += "|";
  }

  // ================= EMERGENCY =================

  data += String(cycleEmergencyDetected ? 1 : 0);
  data += "|";

  data += String(cycleEmergencyLane + 1);
  data += "|";

  data += String(cycleEmergencyOffset);

  // ================= SEND =================

  Serial.println("===== CYCLE DATA =====");
  Serial.println(data);
  Serial.println("======================");
}
// EMERGENCY
void handleEmergency(){

  // Give green to emergency lane
  setLane(emergencyLane);

  // Emergency green = 20 seconds
  if((millis() - emergencyStart) >= 20000){

    emergencyActive = false;

    // Return to previous lane
    currentLane = previousLane;

    setLane(currentLane);

    // Resume previous lane from where it stopped
    signalStart =
      millis() -
      (laneTime[currentLane] - previousRemaining) * 1000UL;

    Serial.println("🚑 Emergency Complete");
    Serial.print("Resuming Lane: ");
    Serial.println(currentLane + 1);
  }
}

// SIGNAL
void setLane(int lane){
  currentLane = lane;

  for(int i=0;i<4;i++){
    digitalWrite(red[i], HIGH);
    digitalWrite(green[i], LOW);
  }

  digitalWrite(green[lane], HIGH);
  digitalWrite(red[lane], LOW);
}

// SEND DATA
void sendData(){

  if(millis() - serialTimer > SERIAL_DELAY){

    serialTimer = millis();

    int remaining = laneTime[currentLane] - (millis()-signalStart)/1000;
    if(remaining < 0) remaining = 0;

    int t[4];
    t[currentLane] = remaining;

    int sum = remaining;

    for(int i=1;i<4;i++){
      int idx = (currentLane + i) % 4;
      t[idx] = sum + laneTime[idx];
      sum = t[idx];
    }

    String mode = densityMode ? "DENSITY" : "NORMAL";

    String data =
      String(count[0])+","+String(count[1])+","+String(count[2])+","+String(count[3])+","+
      mode+","+String(emergencyActive)+","+String(currentLane+1)+","+
      String(t[0])+","+String(t[1])+","+String(t[2])+","+String(t[3]);

    Serial1.println(data);
  }
}