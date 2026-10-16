import joblib
import pandas as pd
from pathlib import Path


# Get the ML model directory
MODEL_DIR = Path(r"D:\TrafficIntelli IOE Lab\ml\models")

# Load saved model and preprocessor
model = joblib.load(MODEL_DIR / "traffic_prediction_model.joblib")
preprocessor = joblib.load(MODEL_DIR / "traffic_preprocessor.joblib")


FEATURES = [
    "l1_count", "l2_count", "l3_count", "l4_count",
    "l1_density", "l2_density", "l3_density", "l4_density",
    "l1_green", "l2_green", "l3_green", "l4_green",
    "l1_cleared", "l2_cleared", "l3_cleared", "l4_cleared",
    "l1_remaining", "l2_remaining", "l3_remaining", "l4_remaining",
    "total_count",
    "emergency_detected", "emergency_lane",
    "hour", "day_type", "part_of_day"
]


def predict_traffic(data):
    """
    Predict next-cycle traffic for all four lanes.
    """

    df = pd.DataFrame([data])

    # Ensure feature order is exactly the same as training
    df = df[FEATURES]

    # Apply the same preprocessing used during training
    X_processed = preprocessor.transform(df)

    # Predict next-cycle traffic
    prediction = model.predict(X_processed)[0]

    return {
        "next_l1_count": round(float(prediction[0]), 2),
        "next_l2_count": round(float(prediction[1]), 2),
        "next_l3_count": round(float(prediction[2]), 2),
        "next_l4_count": round(float(prediction[3]), 2)
    }