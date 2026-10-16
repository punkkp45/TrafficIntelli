def optimize_signal(
    predicted_counts,
    emergency_detected=False,
    emergency_lane=0
):
    """
    Adaptive signal optimizer for TrafficIntelli.

    Normal operation:
        - 30 sec minimum green per lane
        - Remaining cycle time allocated proportionally
        - Maximum cycle = 150 sec

    Emergency operation:
        - Keeps the normal 150-sec adaptive cycle
        - Emergency lane receives priority
        - Actual RFID emergency override remains a separate
          20-second hardware action
    """

    lanes = ["L1", "L2", "L3", "L4"]

    BASE_GREEN = 30
    MAX_CYCLE = 150

    # ---------------------------------------------------------
    # 1. Read predicted traffic
    # ---------------------------------------------------------

    counts = {
        lane: max(0, float(predicted_counts.get(lane, 0)))
        for lane in lanes
    }

    total_traffic = sum(counts.values())

    # ---------------------------------------------------------
    # 2. Normal adaptive allocation
    # ---------------------------------------------------------

    if total_traffic == 0:

        green_times = {
            lane: BASE_GREEN
            for lane in lanes
        }

    else:

        # 150 seconds total
        # 30 seconds minimum per lane
        # 30 seconds × 4 = 120 seconds
        # Therefore 30 seconds remain for adaptive allocation.

        adaptive_time = MAX_CYCLE - (BASE_GREEN * len(lanes))

        green_times = {}

        for lane in lanes:

            extra = (
                counts[lane] / total_traffic
            ) * adaptive_time

            green_times[lane] = BASE_GREEN + extra

    # ---------------------------------------------------------
    # 3. Emergency priority
    # ---------------------------------------------------------

    emergency_priority = None

    if emergency_detected and emergency_lane in [1, 2, 3, 4]:

        emergency_priority = f"L{emergency_lane}"

        # Give the emergency lane the available adaptive
        # priority budget while preserving the 30-second
        # minimum for every other lane.

        other_lanes = [
            lane for lane in lanes
            if lane != emergency_priority
        ]

        # Total time available after minimum green
        adaptive_time = MAX_CYCLE - (BASE_GREEN * len(lanes))

        # Give emergency lane the full adaptive budget
        green_times[emergency_priority] = (
            BASE_GREEN + adaptive_time
        )

        # Other lanes remain at minimum green
        for lane in other_lanes:
            green_times[lane] = BASE_GREEN

    # ---------------------------------------------------------
    # 4. Round values
    # ---------------------------------------------------------

    green_times = {
        lane: round(time, 2)
        for lane, time in green_times.items()
    }

    # ---------------------------------------------------------
    # 5. Calculate cycle duration
    # ---------------------------------------------------------

    cycle_duration = round(
        sum(green_times.values()),
        2
    )

    return {
        "predicted_traffic": counts,

        "recommended_green": green_times,

        "cycle_duration": cycle_duration,

        "emergency_priority": emergency_priority,

        "emergency_override_seconds": (
            20
            if emergency_priority
            else 0
        )
    }