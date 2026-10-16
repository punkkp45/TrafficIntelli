import sys

sys.path.append(r"D:\TrafficIntelli IOE Lab\backend")

from ml_prediction import predict_traffic


sample_data = {
    "l1_count": 12,
    "l2_count": 18,
    "l3_count": 9,
    "l4_count": 15,

    "l1_density": "MEDIUM",
    "l2_density": "MEDIUM",
    "l3_density": "LOW",
    "l4_density": "MEDIUM",

    "l1_green": 36,
    "l2_green": 40,
    "l3_green": 30,
    "l4_green": 38,

    "l1_cleared": 8,
    "l2_cleared": 11,
    "l3_cleared": 7,
    "l4_cleared": 9,

    "l1_remaining": 4,
    "l2_remaining": 7,
    "l3_remaining": 2,
    "l4_remaining": 6,

    "total_count": 54,

    "emergency_detected": 0,
    "emergency_lane": 0,

    "hour": 18.0,
    "day_type": "Weekday",
    "part_of_day": "Evening"
}


result = predict_traffic(sample_data)

print("\nTraffic Prediction")
print("------------------")

for lane, value in result.items():
    print(f"{lane}: {value}")