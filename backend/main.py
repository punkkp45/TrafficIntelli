from fastapi import FastAPI, Depends, HTTPException, Body   
from sqlalchemy.orm import Session
from sqlalchemy import text

from database import get_db
from models import TrafficCycle

from datetime import datetime


app = FastAPI(
    title="TrafficIntelli API",
    description="API for TrafficIntelli traffic data collection",
    version="1.0"
)


@app.get("/")
def root():
    return {
        "message": "TrafficIntelli API is running"
    }


@app.get("/health")
def health():
    return {
        "status": "OK"
    }


@app.post("/traffic/cycle")
def create_cycle(
    cycle_data: str = Body(..., media_type="text/plain"),
    db: Session = Depends(get_db)
):

    try:

        # -----------------------------------------
        # 1. Split Arduino packet
        # -----------------------------------------

        data = cycle_data.strip().split("|")

        if data[0] != "CYCLE":
            raise HTTPException(
                status_code=400,
                detail="Invalid cycle packet"
            )

        # Arduino sends 30 fields including CYCLE
        if len(data) != 30:
            raise HTTPException(
                status_code=400,
                detail=f"Expected 30 fields, received {len(data)}"
            )

        # -----------------------------------------
        # 2. Extract cycle information
        # -----------------------------------------

        cycle_number = int(data[1])
        cycle_duration = int(data[2])

        # -----------------------------------------
        # 3. Vehicle counts
        # -----------------------------------------

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

        # -----------------------------------------
        # 4. Density
        # -----------------------------------------

        l1_density = data[7]
        l2_density = data[8]
        l3_density = data[9]
        l4_density = data[10]

        # -----------------------------------------
        # 5. Green time
        # -----------------------------------------

        l1_green = int(data[11])
        l2_green = int(data[12])
        l3_green = int(data[13])
        l4_green = int(data[14])

        # -----------------------------------------
        # 6. Extra green time
        # -----------------------------------------

        l1_extra = int(data[15])
        l2_extra = int(data[16])
        l3_extra = int(data[17])
        l4_extra = int(data[18])

        # -----------------------------------------
        # 7. Vehicles cleared
        # -----------------------------------------

        l1_cleared = int(data[19])
        l2_cleared = int(data[20])
        l3_cleared = int(data[21])
        l4_cleared = int(data[22])

        # -----------------------------------------
        # 8. Vehicles remaining
        # -----------------------------------------

        l1_remaining = int(data[23])
        l2_remaining = int(data[24])
        l3_remaining = int(data[25])
        l4_remaining = int(data[26])

        # -----------------------------------------
        # 9. Emergency information
        # -----------------------------------------

        emergency_detected = bool(int(data[27]))

        emergency_lane = int(data[28])

        if emergency_lane == 0:
            emergency_lane = None

        emergency_offset = int(data[29])

        # -----------------------------------------
        # 10. Server timestamp
        # -----------------------------------------

        end_time = datetime.now()

        start_time = datetime.fromtimestamp(
            end_time.timestamp() - cycle_duration
        )

        cycle_date = end_time.date()

        day_of_week = end_time.strftime("%A")

        hour = end_time.hour

        if 5 <= hour < 12:
            part_of_day = "Morning"

        elif 12 <= hour < 17:
            part_of_day = "Afternoon"

        elif 17 <= hour < 21:
            part_of_day = "Evening"

        else:
            part_of_day = "Night"

        # -----------------------------------------
        # 11. Determine extended lanes
        # -----------------------------------------

        extended = []

        if l1_extra > 0:
            extended.append("L1")

        if l2_extra > 0:
            extended.append("L2")

        if l3_extra > 0:
            extended.append("L3")

        if l4_extra > 0:
            extended.append("L4")

        cycle_extended = len(extended) > 0

        extended_lanes = ",".join(extended) if extended else None

        if cycle_extended:
            extension_reason = "Proportional traffic allocation"
        else:
            extension_reason = "Normal Traffic"

        # -----------------------------------------
        # 12. Emergency timestamp
        # -----------------------------------------

        emergency_time = None

        if emergency_detected:

            emergency_time = (
                start_time.timestamp() + emergency_offset
            )

            emergency_time = datetime.fromtimestamp(
                emergency_time
            )

        # -----------------------------------------
        # 13. Create database record
        # -----------------------------------------

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

            created_at=end_time
        )

        db.add(cycle)

        db.commit()

        db.refresh(cycle)

        return {
            "message": "Cycle stored successfully",
            "cycle_id": cycle.cycle_id,
            "cycle_number": cycle_number,
            "total_vehicles": total_count,
            "cycle_duration": cycle_duration,
            "extended_lanes": extended_lanes,
            "emergency": emergency_detected
        }

    except HTTPException:
        raise

    except Exception as e:

        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )