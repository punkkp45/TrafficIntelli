import sys
from datetime import timedelta
import pandas as pd
from sqlalchemy import text

from database import engine


CSV_PATH = sys.argv[1] if len(sys.argv) > 1 else "TrafficIntelli_ML_Dataset_10000.csv"
SOURCE = "SYNTHETIC"


def density_from_count(count):
    if count <= 10:
        return "LOW"
    elif count <= 20:
        return "MEDIUM"
    return "HIGH"


def main():
    print("=" * 60)
    print("TrafficIntelli Synthetic Dataset Importer")
    print("=" * 60)

    print(f"Reading: {CSV_PATH}")
    df = pd.read_csv(CSV_PATH)

    print(f"Rows found: {len(df)}")
    print(f"Columns found: {len(df.columns)}")

    required = [
        "timestamp", "cycle_number", "day_of_week", "part_of_day",
        "l1_count", "l2_count", "l3_count", "l4_count",
        "l1_density", "l2_density", "l3_density", "l4_density",
        "l1_green", "l2_green", "l3_green", "l4_green",
        "l1_cleared", "l2_cleared", "l3_cleared", "l4_cleared",
        "l1_remaining", "l2_remaining", "l3_remaining", "l4_remaining",
        "total_count", "emergency_detected", "emergency_lane"
    ]

    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    df["timestamp"] = pd.to_datetime(df["timestamp"])

    # The Arduino's cycle duration is the sum of the four lane green times.
    df["cycle_duration"] = (
        df["l1_green"] +
        df["l2_green"] +
        df["l3_green"] +
        df["l4_green"]
    )

    df["end_time"] = df["timestamp"] + pd.to_timedelta(
        df["cycle_duration"], unit="s"
    )

    # Synthetic data is clearly marked so it can be separated from future
    # REAL hardware data.
    df["cycle_extended"] = (
        (df["l1_green"] > 30) |
        (df["l2_green"] > 30) |
        (df["l3_green"] > 30) |
        (df["l4_green"] > 30)
    )

    def extended_lanes(row):
        lanes = []
        for i in range(1, 5):
            if row[f"l{i}_green"] > 30:
                lanes.append(f"L{i}")
        return ",".join(lanes) if lanes else None

    df["extended_lanes"] = df.apply(extended_lanes, axis=1)
    df["extension_reason"] = df["cycle_extended"].map(
        lambda x: "Proportional traffic allocation" if x else None
    )

    df["emergency_detected"] = df["emergency_detected"].astype(bool)

    # Database columns to populate.
    db_columns = [
        "cycle_number", "cycle_date", "start_time", "end_time",
        "cycle_duration", "day_of_week", "part_of_day",
        "l1_count", "l2_count", "l3_count", "l4_count", "total_count",
        "l1_density", "l2_density", "l3_density", "l4_density",
        "l1_green", "l2_green", "l3_green", "l4_green",
        "l1_extra", "l2_extra", "l3_extra", "l4_extra",
        "l1_cleared", "l2_cleared", "l3_cleared", "l4_cleared",
        "l1_remaining", "l2_remaining", "l3_remaining", "l4_remaining",
        "emergency_detected", "emergency_lane", "emergency_time",
        "cycle_extended", "extended_lanes", "extension_reason",
        "created_at", "data_source"
    ]

    records = []

    for _, r in df.iterrows():
        green = [int(r[f"l{i}_green"]) for i in range(1, 5)]
        extra = [max(0, g - 30) for g in green]

        emergency = bool(r["emergency_detected"])
        emergency_lane = int(r["emergency_lane"]) if emergency else None

        records.append({
            "cycle_number": int(r["cycle_number"]),
            "cycle_date": r["timestamp"].date(),
            "start_time": r["timestamp"].to_pydatetime(),
            "end_time": r["end_time"].to_pydatetime(),
            "cycle_duration": int(r["cycle_duration"]),
            "day_of_week": str(r["day_of_week"]),
            "part_of_day": str(r["part_of_day"]),

            "l1_count": int(r["l1_count"]),
            "l2_count": int(r["l2_count"]),
            "l3_count": int(r["l3_count"]),
            "l4_count": int(r["l4_count"]),
            "total_count": int(r["total_count"]),

            "l1_density": str(r["l1_density"]),
            "l2_density": str(r["l2_density"]),
            "l3_density": str(r["l3_density"]),
            "l4_density": str(r["l4_density"]),

            "l1_green": green[0],
            "l2_green": green[1],
            "l3_green": green[2],
            "l4_green": green[3],

            "l1_extra": extra[0],
            "l2_extra": extra[1],
            "l3_extra": extra[2],
            "l4_extra": extra[3],

            "l1_cleared": int(r["l1_cleared"]),
            "l2_cleared": int(r["l2_cleared"]),
            "l3_cleared": int(r["l3_cleared"]),
            "l4_cleared": int(r["l4_cleared"]),

            "l1_remaining": int(r["l1_remaining"]),
            "l2_remaining": int(r["l2_remaining"]),
            "l3_remaining": int(r["l3_remaining"]),
            "l4_remaining": int(r["l4_remaining"]),

            "emergency_detected": emergency,
            "emergency_lane": emergency_lane,
            "emergency_time": r["timestamp"].to_pydatetime() if emergency else None,

            "cycle_extended": bool(r["cycle_extended"]),
            "extended_lanes": r["extended_lanes"],
            "extension_reason": r["extension_reason"],

            "created_at": r["timestamp"].to_pydatetime(),
            "data_source": SOURCE
        })

    insert_sql = text("""
        INSERT INTO traffic_cycles (
            cycle_number, cycle_date, start_time, end_time,
            cycle_duration, day_of_week, part_of_day,
            l1_count, l2_count, l3_count, l4_count, total_count,
            l1_density, l2_density, l3_density, l4_density,
            l1_green, l2_green, l3_green, l4_green,
            l1_extra, l2_extra, l3_extra, l4_extra,
            l1_cleared, l2_cleared, l3_cleared, l4_cleared,
            l1_remaining, l2_remaining, l3_remaining, l4_remaining,
            emergency_detected, emergency_lane, emergency_time,
            cycle_extended, extended_lanes, extension_reason,
            created_at, data_source
        )
        VALUES (
            :cycle_number, :cycle_date, :start_time, :end_time,
            :cycle_duration, :day_of_week, :part_of_day,
            :l1_count, :l2_count, :l3_count, :l4_count, :total_count,
            :l1_density, :l2_density, :l3_density, :l4_density,
            :l1_green, :l2_green, :l3_green, :l4_green,
            :l1_extra, :l2_extra, :l3_extra, :l4_extra,
            :l1_cleared, :l2_cleared, :l3_cleared, :l4_cleared,
            :l1_remaining, :l2_remaining, :l3_remaining, :l4_remaining,
            :emergency_detected, :emergency_lane, :emergency_time,
            :cycle_extended, :extended_lanes, :extension_reason,
            :created_at, :data_source
        )
    """)

    print("Connecting to PostgreSQL...")
    with engine.begin() as conn:
        conn.execute(insert_sql, records)

        # Keep the cycle_id auto-increment sequence synchronized.
        conn.execute(text("""
            SELECT setval(
                pg_get_serial_sequence('traffic_cycles', 'cycle_id'),
                COALESCE((SELECT MAX(cycle_id) FROM traffic_cycles), 1),
                true
            )
        """))

    print()
    print("IMPORT COMPLETE")
    print(f"Inserted rows: {len(records)}")
    print(f"Data source: {SOURCE}")
    print("=" * 60)


if __name__ == "__main__":
    main()
