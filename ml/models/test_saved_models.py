import joblib

model = joblib.load("traffic_prediction_model.joblib")
preprocessor = joblib.load("traffic_preprocessor.joblib")

print("Model loaded successfully!")
print("Model:", type(model).__name__)
print("Preprocessor:", type(preprocessor).__name__)