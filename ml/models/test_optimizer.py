import sys

sys.path.append(r"D:\TrafficIntelli IOE Lab\backend")

from signal_optimizer import optimize_signal


predicted_traffic = {
    "L1": 12.51,
    "L2": 14.86,
    "L3": 9.25,
    "L4": 13.47
}

result = optimize_signal(
    predicted_traffic,
    emergency_detected=True,
    emergency_lane=3
)


print("\nAdaptive Signal Optimization")
print("----------------------------")

print("\nPredicted Traffic:")

for lane, count in result["predicted_traffic"].items():
    print(f"{lane}: {count}")


print("\nRecommended Green Times:")

for lane, green in result["recommended_green"].items():
    print(f"{lane}: {green} seconds")


print(f"\nRecommended Cycle Duration: {result['cycle_duration']} seconds")

print(f"Emergency Priority: {result['emergency_priority']}")