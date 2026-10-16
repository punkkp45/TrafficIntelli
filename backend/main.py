import logging

from fastapi import FastAPI, Depends, HTTPException, Body, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime, timedelta

from database import engine, get_db, Base
from models import TrafficCycle
from pydantic import BaseModel
from prediction_service import predict_and_optimize


logger = logging.getLogger("trafficintelli.ingest")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

# A packet is treated as a duplicate only when an identical packet (same source,
# cycle number and lane data) was stored within this window. Cycle numbers restart
# at 1 whenever the Arduino resets, so cycle_number alone is not unique.
DUPLICATE_WINDOW_SECONDS = 600

ALLOWED_SOURCES = {"REAL", "SIMULATED"}
ALLOWED_DENSITIES = {"LOW", "MEDIUM", "HIGH"}

# =========================================================
# CREATE DATABASE TABLES
# =========================================================

Base.metadata.create_all(bind=engine)


from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="TrafficIntelli API",
    description="API for TrafficIntelli Smart Traffic Management System",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================
# ROOT
# =========================================================

@app.get("/")
def root():

    return {
        "message": "TrafficIntelli API is running",
        "version": "1.0.0",
        "status": "online"
    }


# =========================================================
# HEALTH
# =========================================================

@app.get("/health")
def health():

    return {
        "status": "OK",
        "service": "TrafficIntelli API"
    }


# =========================================================
# CREATE TRAFFIC CYCLE
# =========================================================

@app.post("/traffic/cycle")
def create_cycle(
    cycle_data: str = Body(
        ...,
        media_type="text/plain"
    ),
    source: str = Query(
        "REAL",
        description="REAL for hardware packets (default), SIMULATED for test harnesses"
    ),
    db: Session = Depends(get_db)
):

    source = source.upper()

    try:

        # -------------------------------------------------
        # 1. Validate packet
        # -------------------------------------------------

        if source not in ALLOWED_SOURCES:

            raise HTTPException(
                status_code=400,
                detail=f"Invalid source '{source}'. Allowed: {sorted(ALLOWED_SOURCES)}"
            )

        cycle_data = cycle_data.strip()

        data = cycle_data.split("|")


        if len(data) != 30:

            raise HTTPException(
                status_code=400,
                detail=f"Expected 30 fields, received {len(data)}"
            )


        if data[0] != "CYCLE":

            raise HTTPException(
                status_code=400,
                detail="Invalid packet. Packet must start with CYCLE"
            )


        empty_fields = [i + 1 for i, v in enumerate(data) if v.strip() == ""]

        if empty_fields:

            raise HTTPException(
                status_code=400,
                detail=f"Empty value in field(s) {empty_fields}"
            )


        for i in range(7, 11):

            if data[i] not in ALLOWED_DENSITIES:

                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid density '{data[i]}' in field {i + 1}"
                )


        # -------------------------------------------------
        # 2. Cycle information
        # -------------------------------------------------

        cycle_number = int(data[1])

        cycle_duration = int(data[2])


        # -------------------------------------------------
        # 3. Vehicle counts
        # -------------------------------------------------

        l1_count = int(data[3])
        l2_count = int(data[4])
        l3_count = int(data[5])
        l4_count = int(data[6])


        total_count = (
            l1_count +
            l2_count +
            l3_count +
            l4_count
        )


        # -------------------------------------------------
        # 4. Density
        # -------------------------------------------------

        l1_density = data[7]
        l2_density = data[8]
        l3_density = data[9]
        l4_density = data[10]


        # -------------------------------------------------
        # 5. Green time
        # -------------------------------------------------

        l1_green = int(data[11])
        l2_green = int(data[12])
        l3_green = int(data[13])
        l4_green = int(data[14])


        # -------------------------------------------------
        # 6. Extra green
        # -------------------------------------------------

        l1_extra = int(data[15])
        l2_extra = int(data[16])
        l3_extra = int(data[17])
        l4_extra = int(data[18])


        # -------------------------------------------------
        # 7. Vehicles cleared
        # -------------------------------------------------

        l1_cleared = int(data[19])
        l2_cleared = int(data[20])
        l3_cleared = int(data[21])
        l4_cleared = int(data[22])


        # -------------------------------------------------
        # 8. Vehicles remaining
        # -------------------------------------------------

        l1_remaining = int(data[23])
        l2_remaining = int(data[24])
        l3_remaining = int(data[25])
        l4_remaining = int(data[26])


        # -------------------------------------------------
        # 9. Emergency
        # -------------------------------------------------

        emergency_detected = bool(
            int(data[27])
        )


        emergency_lane = int(data[28])

        if emergency_lane == 0:

            emergency_lane = None


        emergency_offset = int(data[29])


        # -------------------------------------------------
        # 9b. Duplicate retransmission check
        # -------------------------------------------------

        end_time = datetime.now()

        existing_cycle = (
            db.query(TrafficCycle)
            .filter(
                TrafficCycle.data_source == source,
                TrafficCycle.cycle_number == cycle_number,
                TrafficCycle.cycle_duration == cycle_duration,
                TrafficCycle.created_at >= end_time - timedelta(seconds=DUPLICATE_WINDOW_SECONDS),
                TrafficCycle.l1_count == l1_count,
                TrafficCycle.l2_count == l2_count,
                TrafficCycle.l3_count == l3_count,
                TrafficCycle.l4_count == l4_count,
                TrafficCycle.l1_cleared == l1_cleared,
                TrafficCycle.l2_cleared == l2_cleared,
                TrafficCycle.l3_cleared == l3_cleared,
                TrafficCycle.l4_cleared == l4_cleared,
                TrafficCycle.l1_remaining == l1_remaining,
                TrafficCycle.l2_remaining == l2_remaining,
                TrafficCycle.l3_remaining == l3_remaining,
                TrafficCycle.l4_remaining == l4_remaining,
                TrafficCycle.emergency_detected == emergency_detected
            )
            .order_by(TrafficCycle.cycle_id.desc())
            .first()
        )

        if existing_cycle:

            logger.info(
                "DUPLICATE cycle_number=%s source=%s matches cycle_id=%s",
                cycle_number, source, existing_cycle.cycle_id
            )

            return {
                "status": "duplicate",
                "inserted": False,
                "message": f"Identical cycle {cycle_number} already recorded within {DUPLICATE_WINDOW_SECONDS}s",
                "cycle_id": existing_cycle.cycle_id,
                "cycle_number": cycle_number,
                "data_source": source
            }


        # -------------------------------------------------
        # 10. Server timestamps
        # -------------------------------------------------

        start_time = (
            end_time -
            timedelta(seconds=cycle_duration)
        )

        cycle_date = end_time.date()

        day_of_week = end_time.strftime("%A")


        # -------------------------------------------------
        # 11. Part of day
        # -------------------------------------------------

        hour = end_time.hour


        if 5 <= hour < 12:

            part_of_day = "Morning"

        elif 12 <= hour < 17:

            part_of_day = "Afternoon"

        elif 17 <= hour < 21:

            part_of_day = "Evening"

        else:

            part_of_day = "Night"


        # -------------------------------------------------
        # 12. Extended lanes
        # -------------------------------------------------

        extended = []


        if l1_extra > 0:
            extended.append("L1")

        if l2_extra > 0:
            extended.append("L2")

        if l3_extra > 0:
            extended.append("L3")

        if l4_extra > 0:
            extended.append("L4")


        cycle_extended = (
            len(extended) > 0
        )


        extended_lanes = (
            ",".join(extended)
            if extended
            else None
        )


        if cycle_extended:

            extension_reason = (
                "Proportional traffic allocation"
            )

        else:

            extension_reason = (
                "Normal Traffic"
            )


        # -------------------------------------------------
        # 13. Emergency timestamp
        # -------------------------------------------------

        emergency_time = None


        if emergency_detected:

            emergency_time = (
                start_time +
                timedelta(
                    seconds=emergency_offset
                )
            )


        # -------------------------------------------------
        # 14. Create database object
        # -------------------------------------------------

        cycle = TrafficCycle(

            cycle_number=cycle_number,

            cycle_date=cycle_date,

            start_time=start_time,

            end_time=end_time,

            cycle_duration=cycle_duration,

            day_of_week=day_of_week,

            part_of_day=part_of_day,


            l1_count=l1_count,
            l2_count=l2_count,
            l3_count=l3_count,
            l4_count=l4_count,

            total_count=total_count,


            l1_density=l1_density,
            l2_density=l2_density,
            l3_density=l3_density,
            l4_density=l4_density,


            l1_green=l1_green,
            l2_green=l2_green,
            l3_green=l3_green,
            l4_green=l4_green,


            l1_extra=l1_extra,
            l2_extra=l2_extra,
            l3_extra=l3_extra,
            l4_extra=l4_extra,


            l1_cleared=l1_cleared,
            l2_cleared=l2_cleared,
            l3_cleared=l3_cleared,
            l4_cleared=l4_cleared,


            l1_remaining=l1_remaining,
            l2_remaining=l2_remaining,
            l3_remaining=l3_remaining,
            l4_remaining=l4_remaining,


            emergency_detected=emergency_detected,

            emergency_lane=emergency_lane,

            emergency_time=emergency_time,


            cycle_extended=cycle_extended,

            extended_lanes=extended_lanes,

            extension_reason=extension_reason,

            created_at=end_time,
            data_source=source
        )


        # -------------------------------------------------
        # 15. Save
        # -------------------------------------------------

        db.add(cycle)

        db.commit()

        db.refresh(cycle)

        logger.info(
            "INSERTED cycle_id=%s cycle_number=%s source=%s total=%s",
            cycle.cycle_id, cycle_number, source, total_count
        )


        # -------------------------------------------------
        # 16. Response
        # -------------------------------------------------

        return JSONResponse(status_code=201, content={

            "status":
                "inserted",

            "inserted":
                True,

            "message":
                "Cycle stored successfully",

            "cycle_id":
                cycle.cycle_id,

            "cycle_number":
                cycle_number,

            "data_source":
                source,

            "total_vehicles":
                total_count,

            "cycle_duration":
                cycle_duration,

            "extended_lanes":
                extended_lanes,

            "emergency":
                emergency_detected

        })


    except HTTPException as e:

        logger.warning("REJECTED (validation) %s | packet=%r", e.detail, cycle_data[:200])

        raise


    except ValueError as e:

        db.rollback()

        logger.warning("REJECTED (numeric) %s | packet=%r", e, cycle_data[:200])

        raise HTTPException(
            status_code=400,
            detail=f"Invalid numeric value: {str(e)}"
        )


    except SQLAlchemyError as e:

        db.rollback()

        logger.error("DB_ERROR %s: %s", type(e).__name__, getattr(e, "orig", e))

        raise HTTPException(
            status_code=500,
            detail=f"Database error: {type(e).__name__}"
        )


    except Exception as e:

        db.rollback()

        logger.exception("SERVER_ERROR while ingesting cycle")

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# =========================================================
# ANALYTICS — SUMMARY
# =========================================================

@app.get("/traffic/analytics/summary")
def analytics_summary(
    db: Session = Depends(get_db)
):

    total_cycles = db.query(
        func.count(
            TrafficCycle.cycle_id
        )
    ).scalar() or 0


    total_vehicles = db.query(
        func.sum(
            TrafficCycle.total_count
        )
    ).scalar() or 0


    average_vehicles = db.query(
        func.avg(
            TrafficCycle.total_count
        )
    ).scalar() or 0


    average_cycle_duration = db.query(
        func.avg(
            TrafficCycle.cycle_duration
        )
    ).scalar() or 0


    emergency_events = db.query(
        func.count(
            TrafficCycle.cycle_id
        )
    ).filter(
        TrafficCycle.emergency_detected.is_(True)
    ).scalar() or 0


    # Clearance

    cycles = db.query(
        TrafficCycle
    ).all()


    clearance_rates = []


    for cycle in cycles:

        total_cleared = (
            cycle.l1_cleared +
            cycle.l2_cleared +
            cycle.l3_cleared +
            cycle.l4_cleared
        )


        total_remaining = (
            cycle.l1_remaining +
            cycle.l2_remaining +
            cycle.l3_remaining +
            cycle.l4_remaining
        )


        total_initial = (
            total_cleared +
            total_remaining
        )


        if total_initial > 0:

            clearance_rates.append(
                (
                    total_cleared /
                    total_initial
                ) * 100
            )


    if clearance_rates:

        average_clearance_rate = (
            sum(clearance_rates) /
            len(clearance_rates)
        )

    else:

        average_clearance_rate = 0


    return {

        "total_cycles":
            total_cycles,

        "total_vehicles":
            total_vehicles,

        "average_vehicles_per_cycle":
            round(
                float(average_vehicles),
                2
            ),

        "average_cycle_duration":
            round(
                float(average_cycle_duration),
                2
            ),

        "average_clearance_rate":
            round(
                average_clearance_rate,
                2
            ),

        "emergency_events":
            emergency_events

    }


# =========================================================
# ANALYTICS — LANES
# =========================================================

@app.get("/traffic/analytics/lanes")
def analytics_lanes(
    db: Session = Depends(get_db)
):

    cycles = db.query(
        TrafficCycle
    ).all()


    if not cycles:

        return {
            "message":
                "No traffic data available"
        }


    result = {}


    for lane in range(1, 5):

        counts = [
            getattr(
                c,
                f"l{lane}_count"
            )
            for c in cycles
        ]


        greens = [
            getattr(
                c,
                f"l{lane}_green"
            )
            for c in cycles
        ]


        extras = [
            getattr(
                c,
                f"l{lane}_extra"
            )
            for c in cycles
        ]


        cleared = [
            getattr(
                c,
                f"l{lane}_cleared"
            )
            for c in cycles
        ]


        remaining = [
            getattr(
                c,
                f"l{lane}_remaining"
            )
            for c in cycles
        ]


        total_count = sum(counts)

        average_count = (
            total_count /
            len(counts)
        )


        average_green = (
            sum(greens) /
            len(greens)
        )


        average_extra = (
            sum(extras) /
            len(extras)
        )


        total_cleared = sum(cleared)

        total_remaining = sum(remaining)


        total_initial = (
            total_cleared +
            total_remaining
        )


        if total_initial > 0:

            clearance_rate = (
                total_cleared /
                total_initial
            ) * 100

        else:

            clearance_rate = 0


        result[f"L{lane}"] = {

            "total_vehicles":
                total_count,

            "average_vehicles":
                round(
                    average_count,
                    2
                ),

            "average_green_time":
                round(
                    average_green,
                    2
                ),

            "average_extra_time":
                round(
                    average_extra,
                    2
                ),

            "vehicles_cleared":
                total_cleared,

            "vehicles_remaining":
                total_remaining,

            "clearance_rate":
                round(
                    clearance_rate,
                    2
                )

        }


    return result


# =========================================================
# ANALYTICS — CYCLES
# =========================================================

@app.get("/traffic/analytics/cycles")
def analytics_cycles(
    db: Session = Depends(get_db)
):

    cycles = (
        db.query(TrafficCycle)
        .order_by(
            TrafficCycle.cycle_number
        )
        .all()
    )


    result = []


    for cycle in cycles:

        total_cleared = (
            cycle.l1_cleared +
            cycle.l2_cleared +
            cycle.l3_cleared +
            cycle.l4_cleared
        )


        total_remaining = (
            cycle.l1_remaining +
            cycle.l2_remaining +
            cycle.l3_remaining +
            cycle.l4_remaining
        )


        total_initial = (
            total_cleared +
            total_remaining
        )


        if total_initial > 0:

            clearance_rate = (
                total_cleared /
                total_initial
            ) * 100

        else:

            clearance_rate = 0


        result.append({

            "cycle_number":
                cycle.cycle_number,

            "cycle_duration":
                cycle.cycle_duration,

            "total_vehicles":
                cycle.total_count,

            "l1_count":
                cycle.l1_count,

            "l2_count":
                cycle.l2_count,

            "l3_count":
                cycle.l3_count,

            "l4_count":
                cycle.l4_count,

            "l1_green":
                cycle.l1_green,

            "l2_green":
                cycle.l2_green,

            "l3_green":
                cycle.l3_green,

            "l4_green":
                cycle.l4_green,

            "l1_extra":
                cycle.l1_extra,

            "l2_extra":
                cycle.l2_extra,

            "l3_extra":
                cycle.l3_extra,

            "l4_extra":
                cycle.l4_extra,

            "vehicles_cleared":
                total_cleared,

            "vehicles_remaining":
                total_remaining,

            "clearance_rate":
                round(
                    clearance_rate,
                    2
                ),

            "emergency":
                cycle.emergency_detected,

            "emergency_lane":
                cycle.emergency_lane

        })


    return {

        "total_cycles":
            len(result),

        "cycles":
            result

    }


# =========================================================
# ANALYTICS — DENSITY
# =========================================================

@app.get("/traffic/analytics/density")
def analytics_density(
    db: Session = Depends(get_db)
):

    cycles = db.query(
        TrafficCycle
    ).all()


    result = {}


    for lane in range(1, 5):

        low = 0
        medium = 0
        high = 0


        for cycle in cycles:

            density = getattr(
                cycle,
                f"l{lane}_density"
            )


            if not density:
                continue


            density = density.upper()


            if density == "LOW":
                low += 1

            elif density == "MEDIUM":
                medium += 1

            elif density == "HIGH":
                high += 1


        result[f"L{lane}"] = {

            "LOW": low,

            "MEDIUM": medium,

            "HIGH": high

        }


    return result


# =========================================================
# ANALYTICS — TIME
# =========================================================

@app.get("/traffic/analytics/time")
def analytics_time(
    db: Session = Depends(get_db)
):

    cycles = db.query(
        TrafficCycle
    ).all()


    periods = {

        "Morning": [],

        "Afternoon": [],

        "Evening": [],

        "Night": []

    }


    for cycle in cycles:

        period = cycle.part_of_day


        if period in periods:

            periods[period].append(
                cycle.total_count
            )


    result = {}


    for period, values in periods.items():

        if values:

            result[period] = {

                "cycles":
                    len(values),

                "total_vehicles":
                    sum(values),

                "average_vehicles":
                    round(
                        sum(values) /
                        len(values),
                        2
                    )

            }

        else:

            result[period] = {

                "cycles": 0,

                "total_vehicles": 0,

                "average_vehicles": 0

            }


    return result


# =========================================================
# ANALYTICS — EMERGENCY
# =========================================================

@app.get("/traffic/analytics/emergency")
def analytics_emergency(
    db: Session = Depends(get_db)
):

    cycles = db.query(
        TrafficCycle
    ).filter(
        TrafficCycle.emergency_detected.is_(True)
    ).all()


    lane_counts = {

        "L1": 0,
        "L2": 0,
        "L3": 0,
        "L4": 0

    }


    total_emergency_vehicles = 0

    total_emergency_cleared = 0


    for cycle in cycles:

        lane = cycle.emergency_lane


        if lane is not None:

            lane_key = f"L{lane}"

            if lane_key in lane_counts:

                lane_counts[lane_key] += 1


            # Emergency lane statistics
            # are derived from existing fields.

            if lane == 1:

                total_emergency_vehicles += (
                    cycle.l1_count
                )

                total_emergency_cleared += (
                    cycle.l1_cleared
                )

            elif lane == 2:

                total_emergency_vehicles += (
                    cycle.l2_count
                )

                total_emergency_cleared += (
                    cycle.l2_cleared
                )

            elif lane == 3:

                total_emergency_vehicles += (
                    cycle.l3_count
                )

                total_emergency_cleared += (
                    cycle.l3_cleared
                )

            elif lane == 4:

                total_emergency_vehicles += (
                    cycle.l4_count
                )

                total_emergency_cleared += (
                    cycle.l4_cleared
                )


    if total_emergency_vehicles > 0:

        cleared_percentage = (
            total_emergency_cleared /
            total_emergency_vehicles
        ) * 100

    else:

        cleared_percentage = 0


    return {

        "total_events":
            len(cycles),

        "by_lane":
            lane_counts,

        "emergency_lane_vehicles":
            total_emergency_vehicles,

        "emergency_lane_cleared":
            total_emergency_cleared,

        "cleared_percentage":
            round(
                cleared_percentage,
                2
            )

    }


# =========================================================
# ANALYTICS — VEHICLES
# =========================================================

@app.get("/traffic/analytics/vehicles")
def analytics_vehicles(
    db: Session = Depends(get_db)
):

    cycles = db.query(
        TrafficCycle
    ).all()


    if not cycles:

        return {
            "message":
                "No data available"
        }


    result = {}


    for lane in range(1, 5):

        total = 0

        cleared = 0


        for cycle in cycles:

            total += getattr(
                cycle,
                f"l{lane}_count"
            )

            cleared += getattr(
                cycle,
                f"l{lane}_cleared"
            )


        if total > 0:

            cleared_percentage = (
                cleared /
                total
            ) * 100

        else:

            cleared_percentage = 0


        result[f"L{lane}"] = {

            "total_vehicles":
                total,

            "vehicles_cleared":
                cleared,

            "cleared_percentage":
                round(
                    cleared_percentage,
                    2
                )

        }


    return result

# =========================================================
# ML — TRAFFIC PREDICTION
# =========================================================

class TrafficPredictionRequest(BaseModel):
    l1_count: int
    l2_count: int
    l3_count: int
    l4_count: int

    l1_density: str
    l2_density: str
    l3_density: str
    l4_density: str

    l1_green: int
    l2_green: int
    l3_green: int
    l4_green: int

    l1_cleared: int
    l2_cleared: int
    l3_cleared: int
    l4_cleared: int

    l1_remaining: int
    l2_remaining: int
    l3_remaining: int
    l4_remaining: int

    total_count: int

    emergency_detected: int
    emergency_lane: int

    hour: float
    day_type: str
    part_of_day: str


@app.post("/traffic/predict")
def predict_next_cycle(data: TrafficPredictionRequest):

    result = predict_and_optimize(
        data.model_dump()
    )

    return result


# =========================================================
# LATEST CYCLE & LIVE SYSTEM STATUS
# =========================================================

@app.get("/traffic/cycle/latest")
def get_latest_cycle(db: Session = Depends(get_db)):
    """
    Returns the most recent traffic cycle (preferring REAL hardware cycles if available)
    along with on-the-fly ML predictions and signal optimization recommendations.
    """
    # Check for real hardware cycles first, fallback to any latest cycle
    cycle = (
        db.query(TrafficCycle)
        .filter(TrafficCycle.data_source == "REAL")
        .order_by(TrafficCycle.cycle_id.desc())
        .first()
    )

    if not cycle:
        cycle = (
            db.query(TrafficCycle)
            .order_by(TrafficCycle.cycle_id.desc())
            .first()
        )

    if not cycle:
        return {
            "status": "empty",
            "message": "No traffic cycles found"
        }

    # Run ML prediction & signal optimization on the cycle
    cycle_hour = float(cycle.start_time.hour) if cycle.start_time else 12.0
    day_type = "Weekend" if cycle.day_of_week in ["Saturday", "Sunday"] else "Weekday"

    feature_payload = {
        "l1_count": cycle.l1_count,
        "l2_count": cycle.l2_count,
        "l3_count": cycle.l3_count,
        "l4_count": cycle.l4_count,
        "l1_density": cycle.l1_density or "LOW",
        "l2_density": cycle.l2_density or "LOW",
        "l3_density": cycle.l3_density or "LOW",
        "l4_density": cycle.l4_density or "LOW",
        "l1_green": cycle.l1_green,
        "l2_green": cycle.l2_green,
        "l3_green": cycle.l3_green,
        "l4_green": cycle.l4_green,
        "l1_cleared": cycle.l1_cleared,
        "l2_cleared": cycle.l2_cleared,
        "l3_cleared": cycle.l3_cleared,
        "l4_cleared": cycle.l4_cleared,
        "l1_remaining": cycle.l1_remaining,
        "l2_remaining": cycle.l2_remaining,
        "l3_remaining": cycle.l3_remaining,
        "l4_remaining": cycle.l4_remaining,
        "total_count": cycle.total_count,
        "emergency_detected": 1 if cycle.emergency_detected else 0,
        "emergency_lane": cycle.emergency_lane or 0,
        "hour": cycle_hour,
        "day_type": day_type,
        "part_of_day": cycle.part_of_day or "Afternoon"
    }

    ai_result = predict_and_optimize(feature_payload)

    return {
        "cycle_id": cycle.cycle_id,
        "cycle_number": cycle.cycle_number,
        "data_source": cycle.data_source,
        "cycle_date": str(cycle.cycle_date),
        "cycle_duration": cycle.cycle_duration,
        "day_of_week": cycle.day_of_week,
        "part_of_day": cycle.part_of_day,
        "total_count": cycle.total_count,
        "lanes": {
            "L1": {
                "count": cycle.l1_count,
                "density": cycle.l1_density,
                "green": cycle.l1_green,
                "extra": cycle.l1_extra,
                "cleared": cycle.l1_cleared,
                "remaining": cycle.l1_remaining
            },
            "L2": {
                "count": cycle.l2_count,
                "density": cycle.l2_density,
                "green": cycle.l2_green,
                "extra": cycle.l2_extra,
                "cleared": cycle.l2_cleared,
                "remaining": cycle.l2_remaining
            },
            "L3": {
                "count": cycle.l3_count,
                "density": cycle.l3_density,
                "green": cycle.l3_green,
                "extra": cycle.l3_extra,
                "cleared": cycle.l3_cleared,
                "remaining": cycle.l3_remaining
            },
            "L4": {
                "count": cycle.l4_count,
                "density": cycle.l4_density,
                "green": cycle.l4_green,
                "extra": cycle.l4_extra,
                "cleared": cycle.l4_cleared,
                "remaining": cycle.l4_remaining
            }
        },
        "emergency": {
            "detected": cycle.emergency_detected,
            "lane": cycle.emergency_lane,
            "time": str(cycle.emergency_time) if cycle.emergency_time else None
        },
        "cycle_extended": cycle.cycle_extended,
        "extended_lanes": cycle.extended_lanes,
        "extension_reason": cycle.extension_reason,
        "created_at": str(cycle.created_at) if cycle.created_at else None,
        "ml_prediction": ai_result["prediction"],
        "signal_optimization": ai_result["signal_optimization"]
    }