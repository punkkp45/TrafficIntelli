#include <ESP8266WiFi.h>
#include <ESP8266WebServer.h>
#include <ESP8266HTTPClient.h>

// =====================================================
// WIFI & BACKEND CONFIGURATION
// =====================================================

const char* ssid     = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";

// PC running FastAPI server.
// Must be the PC's CURRENT IPv4 on the SAME network as the ESP (check with ipconfig).
const char* apiHost = "YOUR_PC_IP"; // e.g., "192.168.1.50"
const int   apiPort = 8001;
const String apiURL = String("http://") + apiHost + ":" + apiPort + "/traffic/cycle";

ESP8266WebServer server(80);

// =====================================================
// SYSTEM STATE & TELEMETRY
// =====================================================

String displayData     = "";
String lastCycleData   = "";
String lastApiResponse = "None";
String lastResult      = "NONE";   // INSERTED / DUPLICATE / REJECTED / SERVER_ERROR / HTTP_ERROR / WIFI_DOWN
int    lastHttpCode    = 0;
unsigned long cyclesSent     = 0;  // any 2xx (kept for compatibility)
unsigned long lastWifiCheck  = 0;

// Per-stage diagnostic counters (exposed on /status)
unsigned long serialLines      = 0;  // complete lines received from Mega
unsigned long livePackets      = 0;
unsigned long cyclePackets     = 0;  // lines starting with CYCLE|
unsigned long cycleBadFields   = 0;  // CYCLE lines without 30 fields (still forwarded for server-side detail)
int           lastCycleFields  = 0;
unsigned long rxOverflows      = 0;  // oversize lines + UART overruns
unsigned long httpAttempts     = 0;
unsigned long cyclesInserted   = 0;
unsigned long cyclesDuplicate  = 0;
unsigned long cyclesRejected   = 0;  // HTTP 4xx (validation)
unsigned long serverErrors     = 0;  // HTTP 5xx (e.g. database error)
unsigned long transportErrors  = 0;  // negative codes: connection refused/timeout, WiFi down
unsigned long retriesDropped   = 0;

// One pending packet is retried after transport/5xx failures
String pendingCycle = "";
int    pendingAttempts = 0;
unsigned long lastRetry = 0;
#define RETRY_INTERVAL_MS 10000
#define MAX_ATTEMPTS      5

// Raw UART diagnostics: distinguishes "no bytes arrive at the ESP's RX pin"
// from "bytes arrive but never form a complete line" (baud/framing problem).
unsigned long bytesReceived = 0;
String lastRaw = "";   // tail of the raw characters actually read from UART0

// Serial reception buffer
String rxBuffer = "";

// UART0 RX (GPIO3) is shared with the USB-serial bridge on a NodeMCU. Enabling
// this moves UART0 to GPIO13(RX)/GPIO15(TX) via Serial.swap(), so the Mega gets
// a dedicated RX pin and the USB monitor stops contending with it.
// Leave at 0 unless you rewire the Mega's TX1 to GPIO13 (D7).
#define USE_SWAPPED_UART 0

void noteRaw(char c) {
  bytesReceived++;
  // Keep a short printable tail for inspection via /status
  if (c >= 32 && c <= 126) lastRaw += c;
  else if (c == '\n')      lastRaw += "<LF>";
  else if (c == '\r')      lastRaw += "<CR>";
  else                     lastRaw += '.';   // non-printable: usually a baud mismatch
  if (lastRaw.length() > 120) lastRaw.remove(0, lastRaw.length() - 120);
}

void handleRoot() {
  server.sendHeader("Access-Control-Allow-Origin", "*");
  server.send(200, "text/plain", "TrafficIntelli ESP8266 IoT Node Online");
}

void handleData() {
  server.sendHeader("Access-Control-Allow-Origin", "*");
  server.send(200, "text/plain", displayData);
}

void handleStatus() {
  server.sendHeader("Access-Control-Allow-Origin", "*");
  String json = "{";
  json += "\"wifi\":\"" + String(WiFi.status() == WL_CONNECTED ? "CONNECTED" : "DISCONNECTED") + "\",";
  json += "\"esp_ip\":\"" + WiFi.localIP().toString() + "\",";
  json += "\"pc_ip\":\"" + String(apiHost) + "\",";
  json += "\"api_url\":\"" + apiURL + "\",";
  json += "\"rssi\":" + String(WiFi.RSSI()) + ",";
  json += "\"uart_swapped\":" + String(USE_SWAPPED_UART ? "true" : "false") + ",";
  json += "\"bytes_received\":" + String(bytesReceived) + ",";

  String safeRaw = lastRaw;
  safeRaw.replace("\\", "/");
  safeRaw.replace("\"", "'");
  json += "\"last_raw\":\"" + safeRaw + "\",";
  json += "\"serial_lines\":" + String(serialLines) + ",";
  json += "\"live_packets\":" + String(livePackets) + ",";
  json += "\"cycle_packets\":" + String(cyclePackets) + ",";
  json += "\"cycle_bad_fields\":" + String(cycleBadFields) + ",";
  json += "\"last_cycle_fields\":" + String(lastCycleFields) + ",";
  json += "\"rx_overflows\":" + String(rxOverflows) + ",";
  json += "\"http_attempts\":" + String(httpAttempts) + ",";
  json += "\"cycles_inserted\":" + String(cyclesInserted) + ",";
  json += "\"cycles_duplicate\":" + String(cyclesDuplicate) + ",";
  json += "\"cycles_rejected\":" + String(cyclesRejected) + ",";
  json += "\"server_errors\":" + String(serverErrors) + ",";
  json += "\"transport_errors\":" + String(transportErrors) + ",";
  json += "\"retry_pending\":" + String(pendingCycle.length() > 0 ? "true" : "false") + ",";
  json += "\"retries_dropped\":" + String(retriesDropped) + ",";
  json += "\"last_result\":\"" + lastResult + "\",";
  json += "\"last_cycle\":\"" + lastCycleData + "\",";
  json += "\"http_code\":" + String(lastHttpCode) + ",";
  json += "\"cycles_sent\":" + String(cyclesSent) + ",";

  String safeResponse = lastApiResponse;
  safeResponse.replace("\"", "'");
  safeResponse.replace("\n", " ");
  safeResponse.replace("\r", " ");
  json += "\"api_response\":\"" + safeResponse + "\"";
  json += "}";

  server.send(200, "application/json", json);
}

void handleCmd() {
  String cmd = server.arg("c");
  cmd.trim();

  if (cmd.length() > 0) {
    // Forward command to Arduino Mega via hardware serial
    Serial.println(cmd);
  }

  server.send(200, "text/plain", "OK");
}

// =====================================================
// API DISPATCH (POST TO FASTAPI)
// =====================================================

// Returns true if the packet should be retried (transport error or HTTP 5xx).
bool sendCycleToAPI(const String& cycleData) {
  if (cycleData.length() == 0) return false;

  lastCycleData = cycleData;

  if (WiFi.status() != WL_CONNECTED) {
    lastHttpCode = -1;
    lastApiResponse = "WiFi disconnected";
    lastResult = "WIFI_DOWN";
    transportErrors++;
    return true;
  }

  WiFiClient client;
  HTTPClient http;
  http.setTimeout(5000);

  if (!http.begin(client, apiURL)) {
    lastHttpCode = -2;
    lastApiResponse = "HTTP begin failed";
    lastResult = "HTTP_ERROR";
    transportErrors++;
    return true;
  }

  http.addHeader("Content-Type", "text/plain");
  httpAttempts++;
  int httpCode = http.POST(cycleData);
  lastHttpCode = httpCode;
  bool retry = false;

  if (httpCode > 0) {
    lastApiResponse = http.getString();
    if (httpCode >= 200 && httpCode < 300) {
      cyclesSent++;

      // Backend: 201 + "inserted" = new row, 200 + "duplicate" = nothing written
      if (lastApiResponse.indexOf("\"status\":\"inserted\"") >= 0) {
        cyclesInserted++;
        lastResult = "INSERTED";
      } else if (lastApiResponse.indexOf("\"status\":\"duplicate\"") >= 0) {
        cyclesDuplicate++;
        lastResult = "DUPLICATE";
      } else {
        lastResult = "OK_UNKNOWN";
      }

      // Pulse LED twice rapidly to acknowledge success
      digitalWrite(LED_BUILTIN, HIGH);
      delay(70);
      digitalWrite(LED_BUILTIN, LOW);
      delay(70);
      digitalWrite(LED_BUILTIN, HIGH);
      delay(70);
      digitalWrite(LED_BUILTIN, LOW);
    } else if (httpCode >= 500) {
      serverErrors++;
      lastResult = "SERVER_ERROR";
      retry = true;
    } else {
      // 4xx: packet is invalid, retrying the same bytes cannot succeed
      cyclesRejected++;
      lastResult = "REJECTED";
    }
  } else {
    lastApiResponse = http.errorToString(httpCode);
    lastResult = "HTTP_ERROR";
    transportErrors++;
    retry = true;
  }

  http.end();
  return retry;
}

void submitCycle(const String& cycleData) {
  if (pendingCycle.length() > 0) retriesDropped++;  // superseded by a newer cycle

  if (sendCycleToAPI(cycleData)) {
    pendingCycle = cycleData;
    pendingAttempts = 1;
    lastRetry = millis();
  } else {
    pendingCycle = "";
    pendingAttempts = 0;
  }
}

void retryPendingCycle() {
  if (pendingCycle.length() == 0 || millis() - lastRetry < RETRY_INTERVAL_MS) return;

  lastRetry = millis();
  pendingAttempts++;

  if (!sendCycleToAPI(pendingCycle)) {
    pendingCycle = "";
    pendingAttempts = 0;
  } else if (pendingAttempts >= MAX_ATTEMPTS) {
    retriesDropped++;
    pendingCycle = "";
    pendingAttempts = 0;
  }
}

// =====================================================
// SETUP
// =====================================================

void setup() {
  // ESP Serial connects to Arduino Mega Serial1 at 9600 baud.
  // Larger RX buffer: the Mega keeps streaming LIVE lines while an HTTP POST
  // blocks for up to ~5 s; the default 256-byte buffer can overrun.
  Serial.setRxBufferSize(1024);
  Serial.begin(9600);

#if USE_SWAPPED_UART
  // Move UART0 to GPIO13(RX)/GPIO15(TX); the USB bridge no longer shares RX.
  Serial.swap();
#endif

  // Active-LOW onboard LED configuration
  pinMode(LED_BUILTIN, OUTPUT);
  digitalWrite(LED_BUILTIN, HIGH); // Off initially

  // Configure Wi-Fi station mode
  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(true);
  WiFi.persistent(true);
  WiFi.begin(ssid, password);

  // Wait up to 15s for connection
  unsigned long startWait = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - startWait < 15000) {
    delay(100);
  }

 if (WiFi.status() == WL_CONNECTED) {
  digitalWrite(LED_BUILTIN, LOW);

  Serial.println();
  Serial.println("================================");
  Serial.println(" TrafficIntelli ESP8266 Online");
  Serial.println("================================");

  Serial.print("WiFi SSID: ");
  Serial.println(WiFi.SSID());

  Serial.print("ESP8266 IP Address: ");
  Serial.println(WiFi.localIP());

  Serial.print("Backend URL: ");
  Serial.println(apiURL);

  Serial.println("================================");
} else {
  Serial.println("ERROR: WiFi connection failed!");
}

  // Web server routing
  server.on("/", HTTP_GET, handleRoot);
  server.on("/data", HTTP_GET, handleData);
  server.on("/status", HTTP_GET, handleStatus);
  server.on("/cmd", handleCmd);

  server.begin();
}

// =====================================================
// MAIN LOOP
// =====================================================

void loop() {
  // Periodic Wi-Fi connection health check every 5 seconds
  if (millis() - lastWifiCheck > 5000) {
    lastWifiCheck = millis();
    if (WiFi.status() != WL_CONNECTED) {
      digitalWrite(LED_BUILTIN, HIGH); // Turn LED off
      WiFi.reconnect();
    } else {
      digitalWrite(LED_BUILTIN, LOW); // Turn LED on (active LOW)
    }
  }

  // Handle incoming HTTP client requests
  server.handleClient();

  // Retry a cycle that previously failed (transport error / 5xx)
  retryPendingCycle();

  if (Serial.hasOverrun()) rxOverflows++;

  // Non-blocking serial read from Arduino Mega
  while (Serial.available() > 0) {
    char c = (char)Serial.read();
    noteRaw(c);              // count every raw byte before any filtering
    if (c == '\r') continue; // Ignore carriage return

    if (c == '\n') {
      rxBuffer.trim();
      if (rxBuffer.length() > 0) {
        serialLines++;

        // 1. Completed cycle telemetry packet: forward to FastAPI
        if (rxBuffer.startsWith("CYCLE|")) {
          cyclePackets++;

          int fields = 1;
          for (unsigned int i = 0; i < rxBuffer.length(); i++) {
            if (rxBuffer.charAt(i) == '|') fields++;
          }
          lastCycleFields = fields;
          if (fields != 30) cycleBadFields++;

          digitalWrite(LED_BUILTIN, HIGH);
          delay(40);
          digitalWrite(LED_BUILTIN, LOW);

          submitCycle(rxBuffer);
        }
        // 2. Real-time telemetry prefixed with LIVE|
        else if (rxBuffer.startsWith("LIVE|")) {
          livePackets++;
          displayData = rxBuffer.substring(5);
        }
        // 3. Fallback raw CSV packet: 11 fields = 10 commas
        else {
          int commas = 0;
          for (unsigned int i = 0; i < rxBuffer.length(); i++) {
            if (rxBuffer.charAt(i) == ',') {
              commas++;
            }
          }
          if (commas == 10) {
            displayData = rxBuffer;
          }
        }
      }
      rxBuffer = ""; // Reset buffer for next packet
    } else {
      // Buffer incoming character with safety cap against overflow
      if (rxBuffer.length() < 300) {
        rxBuffer += c;
      } else {
        rxBuffer = ""; // Flush on oversized/corrupted line
        rxOverflows++;
      }
    }
  }
}