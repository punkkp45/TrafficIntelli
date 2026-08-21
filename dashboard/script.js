/* =====================================================
   TRAFFICINTELLI DASHBOARD
   LIVE ESP8266 + DEMO MODE
===================================================== */


/* =====================================================
   CONFIGURATION
===================================================== */

/*
   DEMO MODE
   ----------
   true  = use simulated values
   false = read values from ESP8266
*/

const DEMO_MODE = true;


/*
   When hardware is connected, change this to
   the IP address printed by the ESP8266.

   Example:

   const ESP_URL = "http://172.24.18.63";
*/

const ESP_URL = "http://192.168.4.76";


/*
   How often dashboard asks ESP for data.
   1000 = every 1 second
*/

const LIVE_UPDATE_INTERVAL = 1000;



/* =====================================================
   TRAFFIC DATA
===================================================== */

let trafficData = {

    mode: "NORMAL",

    lanes: [

        {
            id: "L1",
            vehicles: 8,
            density: "LOW",
            greenTime: 30,
            remainingTime: 30,
            cleared: 0
        },

        {
            id: "L2",
            vehicles: 16,
            density: "MEDIUM",
            greenTime: 40,
            remainingTime: 40,
            cleared: 0
        },

        {
            id: "L3",
            vehicles: 7,
            density: "LOW",
            greenTime: 30,
            remainingTime: 30,
            cleared: 0
        },

        {
            id: "L4",
            vehicles: 24,
            density: "HIGH",
            greenTime: 50,
            remainingTime: 50,
            cleared: 0
        }

    ],

    emergency: {

        detected: false,

        lane: null

    }

};


/*
   Current active lane.

   1 = L1
   2 = L2
   3 = L3
   4 = L4
*/

let activeLane = 1;



/* =====================================================
   CYCLE
===================================================== */

let cycleNumber = 1;



/* =====================================================
   TOTAL VEHICLES
===================================================== */

function calculateTotalVehicles() {

    return trafficData.lanes.reduce(

        (total, lane) => {

            return total + lane.vehicles;

        },

        0

    );

}



/* =====================================================
   DENSITY CALCULATION
===================================================== */

/*
   These thresholds currently match the logic used
   by the Arduino:

   <= 5       LOW
   6 - 15     MEDIUM
   > 15       HIGH

   If your final Arduino uses different thresholds,
   we can change these later.
*/

function calculateDensity(vehicleCount) {

    if (vehicleCount <= 5) {

        return "LOW";

    }

    if (vehicleCount <= 15) {

        return "MEDIUM";

    }

    return "HIGH";

}



/* =====================================================
   UPDATE SUMMARY CARDS
===================================================== */

function updateSummary() {

    document.getElementById(
        "cycleNumber"
    ).textContent = cycleNumber;


    document.getElementById(
        "totalVehicles"
    ).textContent =
        calculateTotalVehicles();


    /*
       Calculate actual cycle duration
       from the lane green times.
    */

    const duration =
        trafficData.lanes.reduce(

            (total, lane) => {

                return total + lane.greenTime;

            },

            0

        );


    document.getElementById(
        "cycleDuration"
    ).textContent = duration;

}



/* =====================================================
   UPDATE LANE CARDS
===================================================== */

function updateLaneStatus() {

    const container =
        document.getElementById(
            "laneList"
        );


    container.innerHTML = "";


    trafficData.lanes.forEach(

        (lane, index) => {


            const row =
                document.createElement(
                    "div"
                );


            row.className =
                "lane-row";


            /*
               Highlight active lane
            */

            if (
                index + 1 === activeLane
            ) {

                row.classList.add(
                    "active"
                );

            }


            row.innerHTML = `

                <div class="lane-name-status">
                    ${lane.id}
                </div>

                <div>

                    <div class="vehicle-count">
                        ${lane.vehicles}
                    </div>

                    <div class="vehicle-label">
                        vehicles
                    </div>

                </div>

                <div class="density ${lane.density.toLowerCase()}">
                    ${lane.density}
                </div>

                <div class="time">
                    ${lane.remainingTime}s
                </div>

            `;


            container.appendChild(row);

        }

    );

}



/* =====================================================
   UPDATE TRAFFIC SIGNALS
===================================================== */

function updateSignals() {


    /*
       IMPORTANT:

       First turn ALL lights OFF.

       Then:

       Active lane → GREEN
       Other lanes → RED

       This prevents RED + GREEN conflicts.
    */


    for (
        let laneNumber = 1;
        laneNumber <= 4;
        laneNumber++
    ) {


        const signal =
            document.getElementById(
                `signal${laneNumber}`
            );


        if (!signal) {

            continue;

        }


        const red =
            signal.querySelector(
                ".red"
            );


        const yellow =
            signal.querySelector(
                ".yellow"
            );


        const green =
            signal.querySelector(
                ".green"
            );


        /*
           Clear everything
        */

        red.classList.remove(
            "active"
        );

        yellow.classList.remove(
            "active"
        );

        green.classList.remove(
            "active"
        );


        /*
           Set signal
        */

        if (
            laneNumber === activeLane
        ) {

            green.classList.add(
                "active"
            );

        }

        else {

            red.classList.add(
                "active"
            );

        }

    }

}



/* =====================================================
   TRAFFIC CHART
===================================================== */

function updateTrafficChart() {

    const chart =
        document.getElementById(
            "trafficChart"
        );


    if (!chart) {

        return;

    }


    chart.innerHTML = "";


    const maxVehicles =
        Math.max(

            ...trafficData.lanes.map(
                lane => lane.vehicles
            ),

            1

        );


    trafficData.lanes.forEach(

        lane => {


            const container =
                document.createElement(
                    "div"
                );


            container.className =
                "bar-container";


            const height =
                Math.max(

                    20,

                    (
                        lane.vehicles /
                        maxVehicles
                    ) * 160

                );


            container.innerHTML = `

                <span class="bar-value">
                    ${lane.vehicles}
                </span>

                <div
                    class="bar"
                    style="height:${height}px">
                </div>

                <span class="bar-label">
                    ${lane.id}
                </span>

            `;


            chart.appendChild(
                container
            );

        }

    );

}



/* =====================================================
   PREDICTIVE SECTION
===================================================== */

function updatePrediction() {


    let highestLane =
        trafficData.lanes[0];


    trafficData.lanes.forEach(

        lane => {

            if (
                lane.vehicles >
                highestLane.vehicles
            ) {

                highestLane = lane;

            }

        }

    );


    document.getElementById(
        "currentHighLane"
    ).textContent =
        highestLane.id;


    /*
       Temporary prediction.

       Later this will come from
       your FastAPI ML endpoint.
    */

    document.getElementById(
        "predictedLane"
    ).textContent =
        highestLane.id;


    let recommendedTime = 30;


    if (
        highestLane.density ===
        "MEDIUM"
    ) {

        recommendedTime = 40;

    }


    if (
        highestLane.density ===
        "HIGH"
    ) {

        recommendedTime = 50;

    }


    document.getElementById(
        "recommendedGreen"
    ).textContent =
        recommendedTime;


    /*
       Temporary confidence.

       Later this will come from
       your ML model.
    */

    document.getElementById(
        "confidence"
    ).textContent = 87;

}



/* =====================================================
   CYCLE DETAILS
===================================================== */

function updateCycleDetails() {


    const total =
        calculateTotalVehicles();


    const cleared =
        trafficData.lanes.reduce(

            (sum, lane) => {

                return sum + lane.cleared;

            },

            0

        );


    const remaining =
        Math.max(

            0,

            total - cleared

        );


    document.getElementById(
        "vehiclesCleared"
    ).textContent =
        cleared;


    document.getElementById(
        "vehiclesRemaining"
    ).textContent =
        remaining;


    /*
       Find lanes with additional
       green time.
    */

    const extendedLanes =
        trafficData.lanes

            .filter(

                lane =>
                    lane.greenTime > 30

            )

            .map(

                lane =>
                    lane.id

            );


    document.getElementById(
        "extendedLanes"
    ).textContent =

        extendedLanes.length

            ? extendedLanes.join(", ")

            : "None";


    /*
       Total additional green time
    */

    const extension =
        trafficData.lanes.reduce(

            (sum, lane) => {

                return sum +
                    Math.max(
                        0,
                        lane.greenTime - 30
                    );

            },

            0

        );


    document.getElementById(
        "extensionTime"
    ).textContent =

        extension > 0

            ? `+${extension} sec`

            : "0 sec";

}



/* =====================================================
   EMERGENCY STATUS
===================================================== */

function updateEmergency() {


    const status =
        document.getElementById(
            "emergencyStatus"
        );


    const badge =
        document.getElementById(
            "emergencyBadge"
        );


    if (
        trafficData.emergency.detected
    ) {


        status.textContent =

            `Emergency vehicle detected on ${trafficData.emergency.lane}`;


        badge.textContent =
            "ACTIVE";


        badge.style.color =
            "#c52d37";


        badge.style.background =
            "#fdebed";

    }

    else {


        status.textContent =
            "No emergency vehicle detected";


        badge.textContent =
            "CLEAR";


        badge.style.color =
            "#168356";


        badge.style.background =
            "#e8f7ef";

    }

}



/* =====================================================
   UPDATE MODE
===================================================== */

function updateMode() {

    const modeElement =
        document.querySelector(
            ".adaptive"
        );


    if (!modeElement) {

        return;

    }


    if (
        trafficData.mode ===
        "DENSITY"
    ) {

        modeElement.textContent =
            "ADAPTIVE";

    }

    else {

        modeElement.textContent =
            "NORMAL";

    }

}



/* =====================================================
   UPDATE EVERYTHING
===================================================== */

function updateDashboard() {

    updateSummary();

    updateLaneStatus();

    updateSignals();

    updateTrafficChart();

    updatePrediction();

    updateCycleDetails();

    updateEmergency();

    updateMode();

}



/* =====================================================
   ESP8266 LIVE DATA
===================================================== */

async function getLiveData() {


    try {


        const response =
            await fetch(

                ESP_URL +
                "/data",

                {
                    method: "GET",

                    cache: "no-store"

                }

            );


        if (!response.ok) {

            throw new Error(
                `HTTP ${response.status}`
            );

        }


        const text =
            await response.text();


        console.log(
            "ESP DATA:",
            text
        );


        /*
           Expected:

           L1,L2,L3,L4,MODE,
           EMERGENCY,ACTIVE,
           T1,T2,T3,T4
        */


        const data =
            text
                .trim()
                .split(",");


        if (
            data.length < 11
        ) {

            console.warn(
                "Invalid ESP packet:",
                text
            );

            return;

        }


        /*
           -----------------------------------
           VEHICLE COUNTS
           -----------------------------------
        */

        trafficData.lanes[0].vehicles =
            parseInt(data[0]) || 0;


        trafficData.lanes[1].vehicles =
            parseInt(data[1]) || 0;


        trafficData.lanes[2].vehicles =
            parseInt(data[2]) || 0;


        trafficData.lanes[3].vehicles =
            parseInt(data[3]) || 0;



        /*
           -----------------------------------
           MODE
           -----------------------------------
        */

        trafficData.mode =
            data[4].trim();



        /*
           -----------------------------------
           EMERGENCY
           -----------------------------------
        */

        const emergencyValue =
            data[5]
                .trim()
                .toLowerCase();


        trafficData.emergency.detected =

            emergencyValue === "1" ||
            emergencyValue === "true";



        /*
           -----------------------------------
           ACTIVE LANE
           -----------------------------------
        */

        const receivedActiveLane =
            parseInt(data[6]);


        if (
            receivedActiveLane >= 1 &&
            receivedActiveLane <= 4
        ) {

            activeLane =
                receivedActiveLane;

        }



        /*
           -----------------------------------
           TIMERS
           -----------------------------------
        */

        trafficData.lanes[0].remainingTime =
            parseInt(data[7]) || 0;


        trafficData.lanes[1].remainingTime =
            parseInt(data[8]) || 0;


        trafficData.lanes[2].remainingTime =
            parseInt(data[9]) || 0;


        trafficData.lanes[3].remainingTime =
            parseInt(data[10]) || 0;



        /*
           -----------------------------------
           DENSITY
           -----------------------------------

           For now we calculate density
           from vehicle count.

           Later Arduino can send the
           exact density values too.
        */

        trafficData.lanes.forEach(

            lane => {

                lane.density =
                    calculateDensity(
                        lane.vehicles
                    );

            }

        );


        /*
           -----------------------------------
           UPDATE UI
           -----------------------------------
        */

        updateDashboard();


        /*
           Connection indicator
        */

        setConnectionStatus(
            true
        );


    }

    catch (error) {


        console.error(
            "ESP connection failed:",
            error
        );


        setConnectionStatus(
            false
        );

    }

}



/* =====================================================
   CONNECTION STATUS
===================================================== */

function setConnectionStatus(
    connected
) {


    const statusText =
        document.querySelector(
            ".connection-box strong"
        );


    const statusSmall =
        document.querySelector(
            ".connection-box small"
        );


    const dot =
        document.querySelector(
            ".connection-dot"
        );


    if (
        !statusText ||
        !statusSmall ||
        !dot
    ) {

        return;

    }


    if (connected) {

        statusText.textContent =
            "System Online";

        statusSmall.textContent =
            "ESP8266 Connected";

        dot.style.background =
            "#20b26b";

    }

    else {

        statusText.textContent =
            "System Offline";

        statusSmall.textContent =
            "ESP8266 Not Connected";

        dot.style.background =
            "#e23b45";

    }

}



/* =====================================================
   DEMO MODE
===================================================== */

function simulateTraffic() {


    /*
       DO NOT use this when real hardware
       is connected.
    */


    if (!DEMO_MODE) {

        return;

    }


    const current =
        trafficData.lanes[
        activeLane - 1
        ];


    current.remainingTime--;


    if (
        current.remainingTime <= 0
    ) {


        /*
           Anti-clockwise:

           L1 → L2 → L3 → L4 → L1
        */

        activeLane++;


        if (
            activeLane > 4
        ) {

            activeLane = 1;

        }


        const next =
            trafficData.lanes[
            activeLane - 1
            ];


        next.remainingTime =
            next.greenTime;


        cycleNumber++;

    }


    updateDashboard();

}



/* =====================================================
   CLOCK
===================================================== */

function updateClock() {


    const now =
        new Date();


    const timeElement =
        document.getElementById(
            "currentTime"
        );


    const dateElement =
        document.getElementById(
            "currentDate"
        );


    if (timeElement) {

        timeElement.textContent =

            now.toLocaleTimeString(
                "en-IN",
                {
                    hour: "2-digit",
                    minute: "2-digit",
                    second: "2-digit"
                }
            );

    }


    if (dateElement) {

        dateElement.textContent =

            now.toLocaleDateString(
                "en-IN",
                {
                    day: "2-digit",
                    month: "short",
                    year: "numeric"
                }
            );

    }

}



/* =====================================================
   SIDEBAR
===================================================== */

const sidebarItems =
    document.querySelectorAll(
        ".nav-item"
    );


sidebarItems.forEach(

    item => {


        item.addEventListener(

            "click",

            function (event) {

                event.preventDefault();


                sidebarItems.forEach(

                    navItem => {

                        navItem.classList.remove(
                            "active"
                        );

                    }

                );


                this.classList.add(
                    "active"
                );


                console.log(
                    "Selected:",
                    this.dataset.section
                );

            }

        );

    }

);



/* =====================================================
   INITIALIZATION
===================================================== */

function initializeDashboard() {


    /*
       Initial UI
    */

    updateDashboard();


    /*
       Clock
    */

    updateClock();


    /*
       If using REAL HARDWARE,
       start ESP polling.
    */

    if (!DEMO_MODE) {

        console.log(
            "TRAFFICINTELLI LIVE MODE"
        );

        console.log(
            "ESP URL:",
            ESP_URL
        );


        getLiveData();


        setInterval(

            getLiveData,

            LIVE_UPDATE_INTERVAL

        );

    }


    /*
       Demo mode
    */

    else {

        console.log(
            "TRAFFICINTELLI DEMO MODE"
        );


        setInterval(

            simulateTraffic,

            1000

        );

    }

}


initializeDashboard();


/*
   Clock runs regardless of mode
*/

setInterval(

    updateClock,

    1000

);