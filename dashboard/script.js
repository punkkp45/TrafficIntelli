/* =====================================================
   TRAFFICINTELLI DASHBOARD
===================================================== */


/* =====================================================
   MOCK DATA
===================================================== */

let trafficData = {

    cycleNumber: 24,

    cycleDuration: 150,

    lanes: [

        {
            id: "L1",
            vehicles: 12,
            density: "LOW",
            greenTime: 30,
            remainingTime: 18,
            cleared: 10
        },

        {
            id: "L2",
            vehicles: 26,
            density: "HIGH",
            greenTime: 50,
            remainingTime: 42,
            cleared: 19
        },

        {
            id: "L3",
            vehicles: 8,
            density: "LOW",
            greenTime: 30,
            remainingTime: 72,
            cleared: 7
        },

        {
            id: "L4",
            vehicles: 22,
            density: "MEDIUM",
            greenTime: 40,
            remainingTime: 112,
            cleared: 18
        }

    ],

    emergency: {

        detected: false,

        lane: null

    }

};


/* =====================================================
   CURRENT ACTIVE LANE
===================================================== */

let activeLane = 1;


/* =====================================================
   TOTAL VEHICLES
===================================================== */

function calculateTotalVehicles() {

    return trafficData.lanes.reduce(

        (total, lane) =>
            total + lane.vehicles,

        0

    );

}


/* =====================================================
   SUMMARY
===================================================== */

function updateSummary() {

    document.getElementById(
        "cycleNumber"
    ).textContent =
        trafficData.cycleNumber;


    document.getElementById(
        "cycleDuration"
    ).textContent =
        trafficData.cycleDuration;


    document.getElementById(
        "totalVehicles"
    ).textContent =
        calculateTotalVehicles();

}


/* =====================================================
   LANE STATUS
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

            <div class="density
                ${lane.density.toLowerCase()}">

                ${lane.density}

            </div>

            <div class="time">

                ${lane.remainingTime}s

            </div>

        `;


            container.appendChild(row);

        });

}


/* =====================================================
   SIGNAL CONTROL
   IMPORTANT:
   ONLY ONE LIGHT CAN BE ACTIVE
===================================================== */

function updateSignals() {


    for (
        let laneNumber = 1;
        laneNumber <= 4;
        laneNumber++
    ) {


        const signal =
            document.getElementById(
                `signal${laneNumber}`
            );


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


        /* FIRST TURN EVERYTHING OFF */

        red.classList.remove(
            "active"
        );

        yellow.classList.remove(
            "active"
        );

        green.classList.remove(
            "active"
        );


        /* THEN ACTIVATE ONLY ONE */

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


    chart.innerHTML = "";


    const maxVehicles =
        Math.max(
            ...trafficData.lanes.map(
                lane => lane.vehicles
            )
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

        });

}


/* =====================================================
   PREDICTION
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
        MOCK PREDICTION

        Later this will come
        from the ML model.
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


    document.getElementById(
        "confidence"
    ).textContent =
        87;

}


/* =====================================================
   CYCLE DETAILS
===================================================== */

function updateCycleDetails() {


    const total =
        calculateTotalVehicles();


    const cleared =
        trafficData.lanes.reduce(

            (sum, lane) =>
                sum + lane.cleared,

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


    const extension =
        trafficData.lanes.reduce(

            (sum, lane) =>

                sum +
                Math.max(
                    0,
                    lane.greenTime - 30
                ),

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
   EMERGENCY
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
   RECENT CYCLES
===================================================== */

function updateRecentCycles() {


    const table =
        document.getElementById(
            "cycleTable"
        );


    const cycles = [

        {
            cycle: 24,
            duration: 150,
            vehicles: 68,
            lanes: "L2, L4",
            emergency: "No"
        },

        {
            cycle: 23,
            duration: 130,
            vehicles: 51,
            lanes: "L2",
            emergency: "No"
        },

        {
            cycle: 22,
            duration: 120,
            vehicles: 32,
            lanes: "None",
            emergency: "No"
        },

        {
            cycle: 21,
            duration: 150,
            vehicles: 68,
            lanes: "L1, L4",
            emergency: "Yes"
        },

        {
            cycle: 20,
            duration: 140,
            vehicles: 56,
            lanes: "L3",
            emergency: "No"
        }

    ];


    table.innerHTML = "";


    cycles.forEach(
        cycle => {


            const row =
                document.createElement(
                    "tr"
                );


            row.innerHTML = `

            <td>
                #${cycle.cycle}
            </td>

            <td>
                ${cycle.duration}s
            </td>

            <td>
                ${cycle.vehicles}
            </td>

            <td>
                ${cycle.lanes}
            </td>

            <td>
                ${cycle.emergency}
            </td>

            <td class="table-status">
                COMPLETED
            </td>

        `;


            table.appendChild(
                row
            );

        });

}


/* =====================================================
   CLOCK
===================================================== */

function updateClock() {


    const now =
        new Date();


    document.getElementById(
        "currentTime"
    ).textContent =

        now.toLocaleTimeString(
            "en-IN",
            {
                hour: "2-digit",
                minute: "2-digit",
                second: "2-digit"
            }
        );


    document.getElementById(
        "currentDate"
    ).textContent =

        now.toLocaleDateString(
            "en-IN",
            {
                day: "2-digit",
                month: "short",
                year: "numeric"
            }
        );

}


/* =====================================================
   SIMULATE SIGNAL CYCLE
===================================================== */

function simulateTraffic() {


    /*
        Find current active lane
    */

    const current =
        trafficData.lanes[
        activeLane - 1
        ];


    current.remainingTime--;


    /*
        When current lane finishes,
        move anti-clockwise:

        L1 → L2 → L3 → L4 → L1
    */

    if (
        current.remainingTime <= 0
    ) {

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

    }


    updateLaneStatus();

    updateSignals();

}


/* =====================================================
   INITIALIZE
===================================================== */

function initializeDashboard() {


    updateSummary();

    updateLaneStatus();

    updateSignals();

    updateTrafficChart();

    updatePrediction();

    updateCycleDetails();

    updateEmergency();

    updateRecentCycles();

    updateClock();

}


initializeDashboard();


/* =====================================================
   UPDATE CLOCK
===================================================== */

setInterval(
    updateClock,
    1000
);


/* =====================================================
   SIMULATE SIGNALS
===================================================== */

setInterval(
    simulateTraffic,
    1000
);

/* =====================================================
   SIDEBAR NAVIGATION
===================================================== */

const sidebarItems =
    document.querySelectorAll(".nav-item");


sidebarItems.forEach(item => {

    item.addEventListener("click", function (event) {

        event.preventDefault();


        // Remove active state
        sidebarItems.forEach(navItem => {

            navItem.classList.remove("active");

        });


        // Activate clicked item
        this.classList.add("active");


        const section =
            this.dataset.section;


        console.log(
            "Selected section:",
            section
        );


        handleSection(section);

    });

});


/* =====================================================
   SECTION HANDLER
===================================================== */

function handleSection(section) {

    switch (section) {


        case "dashboard":

            showDashboard();

            break;


        case "live":

            showLiveTraffic();

            break;


        case "analytics":

            showAnalytics();

            break;


        case "predictions":

            showPredictions();

            break;


        case "history":

            showHistory();

            break;

    }

}


/* =====================================================
   SECTION FUNCTIONS
===================================================== */

function showDashboard() {

    console.log(
        "Dashboard selected"
    );

}


function showLiveTraffic() {

    alert(
        "Live Traffic module will be connected to the ESP8266 data stream."
    );

}


function showAnalytics() {

    alert(
        "Analytics module will use TrafficIntelli PostgreSQL data."
    );

}


function showPredictions() {

    alert(
        "Predictive Analysis module will be connected to the ML model."
    );

}


function showHistory() {

    alert(
        "Cycle History will display previous traffic cycles from PostgreSQL."
    );

}