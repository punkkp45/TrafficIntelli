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

int count[4] = {0,0,0,0};
int prev[4][2];

int laneTime[4] = {30,30,30,30};

int currentLane = 0;
unsigned long signalStart = 0;

bool densityMode = false;
bool prevDensityMode = false;

// EMERGENCY
bool emergencyActive = false;
unsigned long emergencyStart = 0;

int previousLane;
int previousRemaining;

// SERIAL
unsigned long serialTimer = 0;
#define SERIAL_DELAY 1000

void setup() {
  Serial.begin(9600);
  Serial1.begin(9600);

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
}

void loop() {

  readSensors();
  checkRFID();
  readESP();   // 🔥 IMPORTANT

  if(emergencyActive) handleEmergency();
  else controlTraffic();

  sendData();
}

// SENSOR
void readSensors(){
  for(int i=0;i<4;i++){
    int far = digitalRead(ir[i][0]);
    int near = digitalRead(ir[i][1]);

    if(far==LOW && prev[i][0]==HIGH) count[i]++;
    if(near==LOW && prev[i][1]==HIGH){
      count[i]--;
      if(count[i]<0) count[i]=0;
    }

    prev[i][0]=far;
    prev[i][1]=near;
  }
}

// 🔥 RECEIVE COMMAND FROM ESP
void readESP(){
  if(Serial1.available()){
    String cmd = Serial1.readStringUntil('\n');
    cmd.trim();

    Serial.print("CMD RECEIVED → ");
    Serial.println(cmd);

    if(cmd=="L1"){ setLane(0); }
    if(cmd=="L2"){ setLane(1); }
    if(cmd=="L3"){ setLane(2); }
    if(cmd=="L4"){ setLane(3); }

    if(cmd=="EMG"){
      emergencyActive = true;
      emergencyStart = millis();
    }
  }
}

// MODE
void calculateTimes(){

  densityMode = false;

  for(int i=0;i<4;i++){
    if(count[i] > 5){
      densityMode = true;
      break;
    }
  }

  if(densityMode != prevDensityMode){
    Serial.println(densityMode ? "⚡ DENSITY MODE" : "✅ NORMAL MODE");
    prevDensityMode = densityMode;
  }

  if(!densityMode){
    for(int i=0;i<4;i++) laneTime[i] = 30;
    return;
  }

  int total = count[0]+count[1]+count[2]+count[3];

  for(int i=0;i<4;i++) laneTime[i] = 30;

  if(total == 0) return;

  for(int i=0;i<4;i++){
    laneTime[i] += (count[i] * 30) / total;
  }
}

// RFID
void checkRFID(){

  if(!mfrc522.PICC_IsNewCardPresent()) return;
  if(!mfrc522.PICC_ReadCardSerial()) return;

  bool match = true;
  for(byte i=0;i<4;i++){
    if(mfrc522.uid.uidByte[i] != emergencyUID[i]){
      match = false;
      break;
    }
  }

  if(match){
    Serial.println("🚑 EMERGENCY RFID");

    previousLane = currentLane;
    previousRemaining = laneTime[currentLane] - (millis()-signalStart)/1000;

    emergencyActive = true;
    emergencyStart = millis();
  }

  mfrc522.PICC_HaltA();
}

// TRAFFIC
void controlTraffic(){

  if(currentLane == 0 && (millis()-signalStart)/1000 == 0){
    calculateTimes();
  }

  if((millis()-signalStart)/1000 >= laneTime[currentLane]){
    currentLane = (currentLane + 1) % 4;
    setLane(currentLane);
    signalStart = millis();
  }
}

// EMERGENCY
void handleEmergency(){

  setLane(0);

  if((millis() - emergencyStart) > 20000){

    emergencyActive = false;

    currentLane = previousLane;
    setLane(currentLane);

    signalStart = millis() - (laneTime[currentLane] - previousRemaining)*1000;
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