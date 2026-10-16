from ml_prediction import predict_traffic
from signal_optimizer import optimize_signal


def predict_and_optimize(data):
    """
    Complete TrafficIntelli ML pipeline:

    Current traffic data
        ↓
    XGBoost prediction
        ↓
    Adaptive signal optimization
    """

    # Step 1: Predict next-cycle traffic
    prediction = predict_traffic(data)

    # Convert prediction format for optimizer
    predicted_counts = {
        "L1": prediction["next_l1_count"],
        "L2": prediction["next_l2_count"],
        "L3": prediction["next_l3_count"],
        "L4": prediction["next_l4_count"]
    }

    # Step 2: Optimize signal timings
    optimization = optimize_signal(
        predicted_counts=predicted_counts,
        emergency_detected=bool(data.get("emergency_detected", False)),
        emergency_lane=int(data.get("emergency_lane", 0))
    )

    # Step 3: Return combined result
    return {
        "prediction": prediction,
        "signal_optimization": optimization
    }