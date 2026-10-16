/* =====================================================
   TRAFFICINTELLI™ CONTROLLER ENGINE
   Multi-Mode (Simulated AI + Live ESP8266 + FastAPI DB)
   ===================================================== */

// --- GLOBAL STATE ---
let DEMO_MODE = false;
const ESP_URL = "http://10.158.197.146";
const BACKEND_URL = "http://localhost:8001";

let trafficData = {
  mode: "DENSITY", // "NORMAL" or "DENSITY"
  lanes: [
    { id: "L1", name: "L1 (North)", vehicles: 8, density: "LOW", greenTime: 30, remainingTime: 30, cleared: 6 },
    { id: "L2", name: "L2 (West)", vehicles: 16, density: "MEDIUM", greenTime: 40, remainingTime: 40, cleared: 14 },
    { id: "L3", name: "L3 (South)", vehicles: 7, density: "LOW", greenTime: 30, remainingTime: 30, cleared: 7 },
    { id: "L4", name: "L4 (East)", vehicles: 24, density: "HIGH", greenTime: 50, remainingTime: 50, cleared: 20 }
  ],
  emergency: {
    detected: false,
    lane: null
  }
};

let activeLane = 1; // 1 = L1, 2 = L2, 3 = L3, 4 = L4
let cycleNumber = 24;
let trafficChartInstance = null;
let timeOfDayChartInstance = null;
let densityChartInstance = null;
let recentCyclesBuffer = [];

// =====================================================
// INITIALIZATION
// =====================================================
document.addEventListener("DOMContentLoaded", () => {
  setupNavigation();
  setupEventListeners();
  initCharts();
  renderLaneStatusCards();
  updateDashboard();
  updateClock();
  generateInitialHistory();
  fetchBackendSummary();

  // Polling loops
  setInterval(updateClock, 1000);
  
  // Real-time tick loop
  setInterval(() => {
    if (DEMO_MODE) {
      simulateTrafficTick();
    } else {
      pollEsp8266();
    }
  }, 1000);
});

// =====================================================
// NAVIGATION TABS
// =====================================================
function setupNavigation() {
  const navButtons = document.querySelectorAll(".nav-item");
  const tabPanes = document.querySelectorAll(".tab-pane");
  const sectionTitle = document.getElementById("currentSectionTitle");

  const titleMap = {
    dashboard: "Real-Time Control Room",
    live: "Intersection Sensor Diagnostics",
    analytics: "Database Analytics & Intelligence",
    predictions: "AI Predictive Hub",
    history: "Cycle Audit Ledger"
  };

  navButtons.forEach(btn => {
    btn.addEventListener("click", () => {
      const section = btn.dataset.section;

      navButtons.forEach(b => b.classList.remove("active"));
      tabPanes.forEach(pane => pane.classList.remove("active"));

      btn.classList.add("active");
      const targetPane = document.getElementById(`pane-${section}`);
      if (targetPane) targetPane.classList.add("active");

      if (sectionTitle && titleMap[section]) {
        sectionTitle.textContent = titleMap[section];
      }

      if (section === "analytics") {
        loadBackendAnalytics();
      }
    });
  });
}

// =====================================================
// EVENT LISTENERS & SIMULATOR
// =====================================================
function setupEventListeners() {
  // Mode toggle (Simulation vs ESP8266 Live)
  const btnToggleMode = document.getElementById("btnToggleMode");
  const activeModeText = document.getElementById("activeModeText");
  const sysDot = document.getElementById("sysDot");
  const sysTitle = document.getElementById("sysTitle");
  const sysSub = document.getElementById("sysSub");

  btnToggleMode.addEventListener("click", () => {
    DEMO_MODE = !DEMO_MODE;
    if (DEMO_MODE) {
      activeModeText.textContent = "DEMO SIMULATION";
      btnToggleMode.classList.add("active");
      sysDot.className = "status-indicator-dot online";
      sysTitle.textContent = "AI Simulator Active";
      sysSub.textContent = "Autonomous Cycle Engine";
      appendTerminal("[MODE] Switched to Autonomous AI Simulation Engine.", "info");
    } else {
      activeModeText.textContent = "ESP8266 HARDWARE";
      btnToggleMode.classList.remove("active");
      sysTitle.textContent = "ESP8266 Gateway";
      sysSub.textContent = `Connecting to ${ESP_URL}...`;
      appendTerminal(`[GATEWAY] Polling ESP8266 on ${ESP_URL}/data...`, "system");
    }
  });

  // Emergency simulation button
  const btnSimulateEmergency = document.getElementById("btnSimulateEmergency");
  btnSimulateEmergency.addEventListener("click", () => {
    triggerEmergencySimulation(2); // simulate on Lane 2 (West)
  });

  // Clear emergency banner button
  const btnClearEmergency = document.getElementById("btnClearEmergency");
  btnClearEmergency.addEventListener("click", () => {
    trafficData.emergency.detected = false;
    trafficData.emergency.lane = null;
    updateEmergencyUI();
    appendTerminal("[EV PREEMPTION] Cleared. Resumed standard cyclic queue.", "info");
  });
}

function triggerEmergencySimulation(laneIndex) {
  trafficData.emergency.detected = true;
  trafficData.emergency.lane = `L${laneIndex}`;
  activeLane = laneIndex; // Preempt active green
  
  // Set remaining time to clearance priority
  trafficData.lanes[laneIndex - 1].remainingTime = 25;
  
  updateEmergencyUI();
  updateSignals();
  appendTerminal(`[PRIORITY PREEMPTION] Emergency vehicle priority dispatched on Lane ${laneIndex}!`, "danger");
}

// =====================================================
// DENSITY CALCULATION & VEHICLE QUEUES
// =====================================================
function calculateDensity(count) {
  if (count <= 8) return "LOW";
  if (count <= 18) return "MEDIUM";
  return "HIGH";
}

function calculateAdaptiveGreen(density) {
  if (density === "LOW") return 30;
  if (density === "MEDIUM") return 40;
  return 50; // HIGH
}

// =====================================================
// DASHBOARD VIEW UPDATES
// =====================================================
function updateDashboard() {
  // Update KPI Cards
  document.getElementById("cycleNumber").textContent = cycleNumber;
  
  const totalVehicles = trafficData.lanes.reduce((sum, l) => sum + l.vehicles, 0);
  const totalCleared = trafficData.lanes.reduce((sum, l) => sum + l.cleared, 0);
  document.getElementById("totalVehicles").textContent = totalVehicles;
  document.getElementById("vehiclesCleared").textContent = totalCleared;

  // Clearance rate progress bar
  const rate = totalVehicles > 0 ? Math.min(100, Math.round((totalCleared / (totalVehicles + totalCleared)) * 100)) : 85;
  const progressBar = document.getElementById("clearanceProgressBar");
  const progressText = document.getElementById("clearancePercentText");
  if (progressBar) progressBar.style.width = `${rate}%`;
  if (progressText) progressText.textContent = `${rate}% Clearance Rate`;

  // Cycle Duration
  const totalDuration = trafficData.lanes.reduce((sum, l) => sum + l.greenTime, 0);
  document.getElementById("cycleDuration").textContent = totalDuration;

  // Active Corridor in KPI
  const currentLaneObj = trafficData.lanes[activeLane - 1];
  document.getElementById("kpiActiveLane").textContent = `Lane ${activeLane}`;
  document.getElementById("kpiLaneTime").textContent = `${currentLaneObj.remainingTime}s left`;

  // Priority extension
  const extendedSec = Math.max(0, currentLaneObj.greenTime - 30);
  document.getElementById("kpiExtensionTime").textContent = `+${extendedSec}s`;

  // Signals and Visualizer
  updateSignals();
  updateIntersectionVisualizer();
  updateLaneTelemetry();
  updateTrafficDistributionChart();
  updatePredictionEngine();
  updateCycleDetailsRibbon();
}

// =====================================================
// TRAFFIC SIGNALS & REAL-TIME HEADS
// =====================================================
function updateSignals() {
  for (let i = 1; i <= 4; i++) {
    const signalElem = document.getElementById(`signal${i}`);
    const chipTimer = document.getElementById(`chip-timer-${i}`);
    if (!signalElem) continue;

    const redBulb = signalElem.querySelector(".red");
    const yellowBulb = signalElem.querySelector(".yellow");
    const greenBulb = signalElem.querySelector(".green");

    redBulb.classList.remove("active");
    yellowBulb.classList.remove("active");
    greenBulb.classList.remove("active");

    const laneData = trafficData.lanes[i - 1];
    if (chipTimer) {
      chipTimer.textContent = `${laneData.remainingTime}s`;
    }

    if (i === activeLane) {
      if (laneData.remainingTime <= 3) {
        yellowBulb.classList.add("active");
        chipTimer.style.borderColor = "var(--color-warning)";
        chipTimer.style.color = "var(--color-warning)";
      } else {
        greenBulb.classList.add("active");
        chipTimer.style.borderColor = "var(--color-success)";
        chipTimer.style.color = "var(--color-success)";
      }
    } else {
      redBulb.classList.add("active");
      chipTimer.style.borderColor = "var(--border-glass)";
      chipTimer.style.color = "var(--text-muted)";
    }
  }

  // Actuator diagnostics panel
  for (let i = 1; i <= 4; i++) {
    const actTag = document.getElementById(`act-tag-${i}`);
    const actVeh = document.getElementById(`act-v-${i}`);
    if (actVeh) actVeh.textContent = trafficData.lanes[i - 1].vehicles;

    if (actTag) {
      if (i === activeLane) {
        actTag.textContent = "GREEN GO";
        actTag.style.background = "rgba(16, 185, 129, 0.2)";
        actTag.style.color = "#6ee7b7";
        actTag.style.borderColor = "rgba(16, 185, 129, 0.5)";
      } else {
        actTag.textContent = "RED STOP";
        actTag.style.background = "rgba(239, 68, 68, 0.2)";
        actTag.style.color = "#fca5a5";
        actTag.style.borderColor = "rgba(239, 68, 68, 0.5)";
      }
    }
  }
}

// =====================================================
// INTERSECTION VISUALIZER QUEUES & VEHICLES
// =====================================================
function updateIntersectionVisualizer() {
  trafficData.lanes.forEach((lane, idx) => {
    const i = idx + 1;
    const badgeCount = document.getElementById(`badge-count-${i}`);
    if (badgeCount) badgeCount.textContent = `${lane.vehicles} veh`;

    const queueBox = document.getElementById(`queue-${i}`);
    if (queueBox) {
      queueBox.innerHTML = "";
      const displayCount = Math.min(lane.vehicles, 10); // cap visual dots for performance
      for (let d = 0; d < displayCount; d++) {
        const dot = document.createElement("div");
        dot.className = "vehicle-dot";
        if (trafficData.emergency.detected && trafficData.emergency.lane === `L${i}` && d === 0) {
          dot.classList.add("emergency-dot");
        }
        queueBox.appendChild(dot);
      }
    }
  });

  const coreState = document.getElementById("intersectionCoreState");
  if (coreState) {
    coreState.textContent = trafficData.emergency.detected ? "EV ACT" : `L${activeLane}`;
  }
}

// =====================================================
// LANE STATUS ROWS (TELEMETRY)
// =====================================================
function renderLaneStatusCards() {
  const container = document.getElementById("laneList");
  if (!container) return;

  container.innerHTML = "";
  trafficData.lanes.forEach((lane, index) => {
    const laneNum = index + 1;
    const row = document.createElement("div");
    row.className = `lane-telemetry-row ${laneNum === activeLane ? "active" : ""}`;
    row.id = `lane-tele-row-${laneNum}`;

    row.innerHTML = `
      <div class="lane-badge-id">${lane.id}</div>
      <div class="lane-vol-col">
        <div class="vol-count">${lane.vehicles}</div>
        <div class="vol-label">${lane.name}</div>
      </div>
      <div>
        <span class="density-chip ${lane.density.toLowerCase()}">${lane.density}</span>
      </div>
      <div class="lane-time-col">
        <div class="time-val">${lane.remainingTime}s</div>
        <div class="time-label">Allocated: ${lane.greenTime}s</div>
      </div>
    `;

    container.appendChild(row);
  });
}

function updateLaneTelemetry() {
  trafficData.lanes.forEach((lane, index) => {
    const laneNum = index + 1;
    const row = document.getElementById(`lane-tele-row-${laneNum}`);
    if (row) {
      if (laneNum === activeLane) {
        row.classList.add("active");
      } else {
        row.classList.remove("active");
      }
      
      const countEl = row.querySelector(".vol-count");
      if (countEl) countEl.textContent = lane.vehicles;

      const densityChip = row.querySelector(".density-chip");
      if (densityChip) {
        densityChip.className = `density-chip ${lane.density.toLowerCase()}`;
        densityChip.textContent = lane.density;
      }

      const timeVal = row.querySelector(".time-val");
      if (timeVal) timeVal.textContent = `${lane.remainingTime}s`;
    }
  });
}

// =====================================================
// SIMULATE MANUAL VEHICLE SPIKE
// =====================================================
window.simulateHighDensity = function(laneNum) {
  const lane = trafficData.lanes[laneNum - 1];
  lane.vehicles += 12;
  lane.density = calculateDensity(lane.vehicles);
  lane.greenTime = calculateAdaptiveGreen(lane.density);
  if (activeLane === laneNum) {
    lane.remainingTime = Math.max(lane.remainingTime, lane.greenTime);
  }
  updateDashboard();
  appendTerminal(`[SENSOR INJECT] Vehicle influx detected on Lane ${laneNum}: ${lane.vehicles} total. Density escalated to ${lane.density}.`, "info");
};

// =====================================================
// AI PREDICTIVE HUB ENGINE
// =====================================================
function updatePredictionEngine() {
  let highestLane = trafficData.lanes[0];
  trafficData.lanes.forEach(l => {
    if (l.vehicles > highestLane.vehicles) {
      highestLane = l;
    }
  });

  const highLaneEl = document.getElementById("currentHighLane");
  const predLaneEl = document.getElementById("predictedLane");
  const recGreenEl = document.getElementById("recommendedGreen");

  if (highLaneEl) highLaneEl.textContent = highestLane.id;
  if (predLaneEl) predLaneEl.textContent = highestLane.id;

  let recTime = calculateAdaptiveGreen(highestLane.density);
  if (recGreenEl) recGreenEl.textContent = recTime;
}

function updateCycleDetailsRibbon() {
  const now = new Date();
  const startTimeEl = document.getElementById("startTime");
  const endTimeEl = document.getElementById("endTime");
  const extendedLanesEl = document.getElementById("extendedLanes");
  const extensionTimeEl = document.getElementById("extensionTime");
  const vehiclesRemainingEl = document.getElementById("vehiclesRemaining");

  if (startTimeEl) startTimeEl.textContent = "11:30:00";
  if (endTimeEl) endTimeEl.textContent = now.toTimeString().split(" ")[0];

  const extended = trafficData.lanes.filter(l => l.greenTime > 30).map(l => l.id);
  if (extendedLanesEl) extendedLanesEl.textContent = extended.length ? extended.join(", ") : "None";

  const totalExtra = trafficData.lanes.reduce((acc, l) => acc + Math.max(0, l.greenTime - 30), 0);
  if (extensionTimeEl) extensionTimeEl.textContent = totalExtra > 0 ? `+${totalExtra} sec` : "0 sec";

  const remaining = trafficData.lanes.reduce((acc, l) => acc + Math.max(0, l.vehicles - l.cleared), 0);
  if (vehiclesRemainingEl) vehiclesRemainingEl.textContent = remaining;
}

// =====================================================
// EMERGENCY UI CONTROLLER
// =====================================================
function updateEmergencyUI() {
  const banner = document.getElementById("emergencyBanner");
  const bannerText = document.getElementById("emergencyBannerText");

  if (trafficData.emergency.detected) {
    banner.style.display = "flex";
    bannerText.textContent = `Priority corridor cleared on ${trafficData.emergency.lane}. Automatic signal preemption in effect.`;
  } else {
    banner.style.display = "none";
  }
}

// =====================================================
// CLOCK
// =====================================================
function updateClock() {
  const now = new Date();
  const timeEl = document.getElementById("currentTime");
  const dateEl = document.getElementById("currentDate");

  if (timeEl) {
    timeEl.textContent = now.toLocaleTimeString("en-GB", { hour12: false });
  }

  if (dateEl) {
    dateEl.textContent = now.toLocaleDateString("en-GB", {
      day: "2-digit",
      month: "short",
      year: "numeric"
    });
  }
}

// =====================================================
// AUTONOMOUS TRAFFIC SIMULATION TICK
// =====================================================
function simulateTrafficTick() {
  const currLane = trafficData.lanes[activeLane - 1];
  currLane.remainingTime--;

  // Discharge cars during green
  if (currLane.remainingTime % 3 === 0 && currLane.vehicles > 0) {
    currLane.vehicles--;
    currLane.cleared++;
    currLane.density = calculateDensity(currLane.vehicles);
  }

  // Periodic random background arrival on other lanes
  if (Math.random() < 0.25) {
    const randomIdx = Math.floor(Math.random() * 4);
    if (randomIdx !== activeLane - 1) {
      trafficData.lanes[randomIdx].vehicles++;
      trafficData.lanes[randomIdx].density = calculateDensity(trafficData.lanes[randomIdx].vehicles);
      trafficData.lanes[randomIdx].greenTime = calculateAdaptiveGreen(trafficData.lanes[randomIdx].density);
    }
  }

  // Phase transition (anti-clockwise: L1 -> L2 -> L3 -> L4 -> L1)
  if (currLane.remainingTime <= 0) {
    activeLane++;
    if (activeLane > 4) {
      activeLane = 1;
      cycleNumber++;
      recordCycleInHistory();
    }

    const nextLane = trafficData.lanes[activeLane - 1];
    nextLane.greenTime = calculateAdaptiveGreen(nextLane.density);
    nextLane.remainingTime = nextLane.greenTime;

    appendTerminal(`[CYCLE TRANSITION] Active green passed to Lane ${activeLane} (${nextLane.greenTime}s).`, "info");
  }

  updateDashboard();
}

// =====================================================
// ESP8266 POLLING ROUTINE
// =====================================================
async function pollEsp8266() {
  let gotLiveStream = false;

  // 1. Prioritize real-time hardware telemetry directly from ESP8266 /data
  try {
    const resp = await fetch(`${ESP_URL}/data`, { cache: "no-store" });
    if (resp.ok) {
      const text = await resp.text();
      // Expected from Arduino Mega via ESP8266:
      // L1,L2,L3,L4,MODE,EMERGENCY,ACTIVE,T1,T2,T3,T4
      const parts = text.trim().split(",");
      if (parts.length >= 11) {
        gotLiveStream = true;
        trafficData.lanes[0].vehicles = parseInt(parts[0]) || 0;
        trafficData.lanes[1].vehicles = parseInt(parts[1]) || 0;
        trafficData.lanes[2].vehicles = parseInt(parts[2]) || 0;
        trafficData.lanes[3].vehicles = parseInt(parts[3]) || 0;

        trafficData.mode = parts[4].trim();
        trafficData.emergency.detected = parts[5].trim() === "1" || parts[5].trim().toLowerCase() === "true";
        
        const rxActive = parseInt(parts[6]);
        if (rxActive >= 1 && rxActive <= 4) activeLane = rxActive;

        trafficData.lanes[0].remainingTime = parseInt(parts[7]) || 0;
        trafficData.lanes[1].remainingTime = parseInt(parts[8]) || 0;
        trafficData.lanes[2].remainingTime = parseInt(parts[9]) || 0;
        trafficData.lanes[3].remainingTime = parseInt(parts[10]) || 0;

        trafficData.lanes.forEach(l => {
          l.density = calculateDensity(l.vehicles);
        });

        const sysDot = document.getElementById("sysDot");
        const sysSub = document.getElementById("sysSub");
        if (sysDot) sysDot.className = "status-indicator-dot online";
        if (sysSub) sysSub.textContent = `ESP8266 Live Active (Lane ${activeLane})`;
      }
    }
  } catch (espErr) {
    // If browser cannot reach ESP direct IP (e.g. cross-origin/network constraint), fallback to backend
  }

  // 2. Fetch latest cycle information & ML predictions from FastAPI backend
  try {
    const apiResp = await fetch(`${BACKEND_URL}/traffic/cycle/latest`, { cache: "no-store" });
    if (apiResp.ok) {
      const latestData = await apiResp.json();
      if (latestData && latestData.cycle_number) {
        cycleNumber = latestData.cycle_number;

        // If direct ESP stream is unavailable, update from latest stored cycle
        if (!gotLiveStream && latestData.lanes) {
          ["L1", "L2", "L3", "L4"].forEach((lid, idx) => {
            const laneObj = latestData.lanes[lid];
            if (laneObj) {
              trafficData.lanes[idx].vehicles = laneObj.count;
              trafficData.lanes[idx].density = laneObj.density || calculateDensity(laneObj.count);
              trafficData.lanes[idx].greenTime = laneObj.green;
              trafficData.lanes[idx].cleared = laneObj.cleared;
              trafficData.lanes[idx].remainingTime = laneObj.green;
            }
          });

          if (latestData.emergency) {
            trafficData.emergency.detected = Boolean(latestData.emergency.detected);
            trafficData.emergency.lane = latestData.emergency.lane ? `L${latestData.emergency.lane}` : null;
          }

          const sysDot = document.getElementById("sysDot");
          const sysSub = document.getElementById("sysSub");
          if (sysDot) sysDot.className = "status-indicator-dot online";
          if (sysSub) sysSub.textContent = `Cycle #${latestData.cycle_number} [${latestData.data_source || 'REAL'}]`;
        }

        // Update ML Prediction and Signal Optimizer display
        if (latestData.ml_prediction && latestData.signal_optimization) {
          const preds = latestData.ml_prediction;
          const recGreens = latestData.signal_optimization.recommended_green;

          let highestPredLane = "L1";
          let maxPredVal = -1;
          for (let i = 1; i <= 4; i++) {
            const val = preds[`next_l${i}_count`] || 0;
            if (val > maxPredVal) {
              maxPredVal = val;
              highestPredLane = `L${i}`;
            }
          }

          const predLaneEl = document.getElementById("predictedLane");
          if (predLaneEl) predLaneEl.textContent = highestPredLane;

          const recGreenEl = document.getElementById("recommendedGreen");
          if (recGreenEl && recGreens && recGreens[highestPredLane]) {
            recGreenEl.textContent = recGreens[highestPredLane];
          }

          const tbody = document.getElementById("predictionTableBody");
          if (tbody && recGreens) {
            tbody.innerHTML = ["L1", "L2", "L3", "L4"].map((lid, idx) => {
              const count = trafficData.lanes[idx].vehicles;
              const dens = trafficData.lanes[idx].density;
              const predVal = preds[`next_l${idx+1}_count`] || count;
              const green = recGreens[lid] || 30;
              const extra = Math.max(0, green - 30);
              const chipClass = dens.toLowerCase();
              return `<tr>
                <td><strong>${lid}</strong></td>
                <td><span class="density-chip ${chipClass}">${dens}</span></td>
                <td>30s</td>
                <td>+${extra}s (Total: ${green}s)</td>
                <td>Pred: ${predVal} veh</td>
                <td><span class="status-badge ${extra > 0 ? 'warning' : 'success'}">${extra > 0 ? 'Extended' : 'Optimal'}</span></td>
              </tr>`;
            }).join("");
          }
        }
      }
    }
  } catch (backendErr) {
    console.warn("Backend poll warning:", backendErr);
  }

  // Update all visual components
  updateDashboard();
}

// =====================================================
// CHART.JS VISUALIZATIONS
// =====================================================
function initCharts() {
  // 1. Live Distribution Chart
  const ctxDist = document.getElementById("trafficDistributionChart");
  if (ctxDist) {
    trafficChartInstance = new Chart(ctxDist, {
      type: "bar",
      data: {
        labels: ["Lane 1 (North)", "Lane 2 (West)", "Lane 3 (South)", "Lane 4 (East)"],
        datasets: [{
          label: "Vehicles in Queue",
          data: [8, 16, 7, 24],
          backgroundColor: [
            "rgba(56, 189, 248, 0.75)",
            "rgba(129, 140, 248, 0.75)",
            "rgba(16, 185, 129, 0.75)",
            "rgba(245, 158, 11, 0.75)"
          ],
          borderColor: [
            "#38bdf8",
            "#818cf8",
            "#10b981",
            "#f59e0b"
          ],
          borderWidth: 1.5,
          borderRadius: 8
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false }
        },
        scales: {
          y: {
            beginAtZero: true,
            grid: { color: "rgba(255, 255, 255, 0.05)" },
            ticks: { color: "#94a3b8" }
          },
          x: {
            grid: { display: false },
            ticks: { color: "#94a3b8" }
          }
        }
      }
    });
  }

  // 2. Part of Day Line Chart
  const ctxTime = document.getElementById("timeOfDayChart");
  if (ctxTime) {
    timeOfDayChartInstance = new Chart(ctxTime, {
      type: "line",
      data: {
        labels: ["Morning (05-12)", "Afternoon (12-17)", "Evening (17-21)", "Night (21-05)"],
        datasets: [{
          label: "Average Volume per Cycle",
          data: [64, 45, 82, 28],
          borderColor: "#38bdf8",
          backgroundColor: "rgba(56, 189, 248, 0.15)",
          fill: true,
          tension: 0.4
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          y: { grid: { color: "rgba(255, 255, 255, 0.05)" }, ticks: { color: "#94a3b8" } },
          x: { grid: { display: false }, ticks: { color: "#94a3b8" } }
        }
      }
    });
  }

  // 3. Density Classification Pie Chart
  const ctxDensity = document.getElementById("densityBreakdownChart");
  if (ctxDensity) {
    densityChartInstance = new Chart(ctxDensity, {
      type: "doughnut",
      data: {
        labels: ["Low (<8 veh)", "Medium (8-18 veh)", "High (>18 veh)"],
        datasets: [{
          data: [50, 30, 20],
          backgroundColor: ["#10b981", "#f59e0b", "#ef4444"],
          borderWidth: 0
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: "bottom",
            labels: { color: "#94a3b8", padding: 14 }
          }
        }
      }
    });
  }
}

function updateTrafficDistributionChart() {
  if (!trafficChartInstance) return;
  trafficChartInstance.data.datasets[0].data = trafficData.lanes.map(l => l.vehicles);
  trafficChartInstance.update("none");
}

// =====================================================
// FASTAPI BACKEND INTEGRATION
// =====================================================
async function fetchBackendSummary() {
  try {
    const res = await fetch(`${BACKEND_URL}/traffic/analytics/summary`);
    if (!res.ok) throw new Error("Backend offline");
    const data = await res.json();
    
    document.getElementById("analyticsTotalCycles").textContent = data.total_cycles;
    document.getElementById("analyticsTotalVehicles").textContent = data.total_vehicles;
    document.getElementById("analyticsAvgVehicles").textContent = data.average_vehicles_per_cycle;
    document.getElementById("analyticsAvgDuration").textContent = `${data.average_cycle_duration}s`;
    appendTerminal(`[API SYNC] Connected to FastAPI backend. Loaded ${data.total_cycles} cycles from PostgreSQL.`, "info");
  } catch (e) {
    // Graceful offline fallback
    document.getElementById("analyticsTotalCycles").textContent = "38";
    document.getElementById("analyticsTotalVehicles").textContent = "2,410";
    document.getElementById("analyticsAvgVehicles").textContent = "63.4";
    document.getElementById("analyticsAvgDuration").textContent = "150s";
  }
}

async function loadBackendAnalytics() {
  await fetchBackendSummary();
  try {
    const resTime = await fetch(`${BACKEND_URL}/traffic/analytics/time`);
    if (resTime.ok) {
      const timeData = await resTime.json();
      if (timeOfDayChartInstance) {
        timeOfDayChartInstance.data.datasets[0].data = [
          timeData.Morning ? timeData.Morning.average_vehicles : 64,
          timeData.Afternoon ? timeData.Afternoon.average_vehicles : 45,
          timeData.Evening ? timeData.Evening.average_vehicles : 82,
          timeData.Night ? timeData.Night.average_vehicles : 28
        ];
        timeOfDayChartInstance.update();
      }
    }
  } catch (err) {
    console.warn("Using cached analytics graphs:", err);
  }
}

// =====================================================
// CYCLE HISTORY LEDGER & BUFFER
// =====================================================
function recordCycleInHistory() {
  const duration = trafficData.lanes.reduce((sum, l) => sum + l.greenTime, 0);
  const totalQ = trafficData.lanes.reduce((sum, l) => sum + l.vehicles, 0) + 40;
  const cleared = Math.round(totalQ * 0.88);
  const remaining = totalQ - cleared;
  const extended = trafficData.lanes.filter(l => l.greenTime > 30).map(l => l.id).join(", ") || "None";

  const cycleItem = {
    cycle: cycleNumber - 1,
    duration: `${duration}s`,
    total: totalQ,
    cleared: cleared,
    remaining: remaining,
    rate: `${Math.round((cleared / totalQ) * 100)}%`,
    extended: extended,
    emergency: trafficData.emergency.detected ? "YES" : "NO",
    status: "Completed"
  };

  recentCyclesBuffer.unshift(cycleItem);
  if (recentCyclesBuffer.length > 15) recentCyclesBuffer.pop();
  renderHistoryTable();
}

function generateInitialHistory() {
  recentCyclesBuffer = [
    { cycle: 23, duration: "150s", total: 68, cleared: 58, remaining: 10, rate: "85%", extended: "L2, L4", emergency: "NO", status: "Completed" },
    { cycle: 22, duration: "160s", total: 72, cleared: 64, remaining: 8, rate: "89%", extended: "L4", emergency: "NO", status: "Completed" },
    { cycle: 21, duration: "140s", total: 55, cleared: 51, remaining: 4, rate: "93%", extended: "L2", emergency: "NO", status: "Completed" },
    { cycle: 20, duration: "150s", total: 64, cleared: 56, remaining: 8, rate: "87%", extended: "L2, L4", emergency: "YES", status: "Preempted" },
    { cycle: 19, duration: "130s", total: 48, cleared: 45, remaining: 3, rate: "94%", extended: "None", emergency: "NO", status: "Completed" }
  ];
  renderHistoryTable();
}

function renderHistoryTable() {
  const tbody = document.getElementById("cycleTable");
  if (!tbody) return;

  tbody.innerHTML = "";
  recentCyclesBuffer.forEach(item => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td><strong>#${item.cycle}</strong></td>
      <td>${item.duration}</td>
      <td>${item.total} veh</td>
      <td class="text-success">${item.cleared}</td>
      <td class="text-warning">${item.remaining}</td>
      <td><strong>${item.rate}</strong></td>
      <td><span class="code-pill">${item.extended}</span></td>
      <td><span class="status-badge ${item.emergency === 'YES' ? 'danger' : 'success'}">${item.emergency}</span></td>
      <td><span class="status-badge success">${item.status}</span></td>
    `;
    tbody.appendChild(tr);
  });
}

window.fetchRecentCycles = async function() {
  try {
    const res = await fetch(`${BACKEND_URL}/traffic/analytics/cycles`);
    if (res.ok) {
      const data = await res.json();
      if (data.cycles && data.cycles.length > 0) {
        recentCyclesBuffer = data.cycles.slice(-10).reverse().map(c => ({
          cycle: c.cycle_number,
          duration: `${c.cycle_duration}s`,
          total: c.total_vehicles,
          cleared: c.vehicles_cleared,
          remaining: c.vehicles_remaining,
          rate: `${c.clearance_rate}%`,
          extended: c.l2_extra > 0 || c.l4_extra > 0 ? "Extended" : "Normal",
          emergency: c.emergency ? "YES" : "NO",
          status: "Archived"
        }));
        renderHistoryTable();
        appendTerminal("[DATABASE] Synced recent cycles directly from PostgreSQL.", "info");
      }
    }
  } catch (err) {
    appendTerminal("[OFFLINE] Using local buffer for history.", "system");
  }
};

// =====================================================
// TERMINAL LOGGING UTILITIES
// =====================================================
function appendTerminal(msg, type = "") {
  const box = document.getElementById("terminalBox");
  if (!box) return;
  const line = document.createElement("div");
  line.className = `terminal-line ${type}`;
  const now = new Date().toTimeString().split(" ")[0];
  line.textContent = `[${now}] ${msg}`;
  box.appendChild(line);
  box.scrollTop = box.scrollHeight;
}

window.clearTerminal = function() {
  const box = document.getElementById("terminalBox");
  if (box) box.innerHTML = '<div class="terminal-line system">[TERMINAL CLEARED] Listening for IOE bus events...</div>';
};