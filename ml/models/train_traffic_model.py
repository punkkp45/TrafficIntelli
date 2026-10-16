import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.tree import DecisionTreeRegressor
from sklearn.ensemble import RandomForestRegressor
from xgboost import XGBRegressor
import joblib

# ==========================================
# 1. LOAD DATASET
# ==========================================

DATASET_PATH = "D:/TrafficIntelli IOE Lab/ml/dataset/TrafficIntelli_ML_Dataset_10000.csv"

df = pd.read_csv(DATASET_PATH)

print("Dataset loaded successfully!")
print("Shape:", df.shape)


# ==========================================
# 2. DEFINE TARGETS
# ==========================================

TARGETS = [
    "next_l1_count",
    "next_l2_count",
    "next_l3_count",
    "next_l4_count"
]


# ==========================================
# 3. DEFINE FEATURES
# ==========================================

FEATURES = [
    "l1_count",
    "l2_count",
    "l3_count",
    "l4_count",

    "l1_density",
    "l2_density",
    "l3_density",
    "l4_density",

    "l1_green",
    "l2_green",
    "l3_green",
    "l4_green",

    "l1_cleared",
    "l2_cleared",
    "l3_cleared",
    "l4_cleared",

    "l1_remaining",
    "l2_remaining",
    "l3_remaining",
    "l4_remaining",

    "total_count",

    "emergency_detected",
    "emergency_lane",

    "hour",
    "day_type",
    "part_of_day"
]


# ==========================================
# 4. CREATE X AND Y
# ==========================================

X = df[FEATURES]
y = df[TARGETS]

print("\nFeatures:")
print(X.columns.tolist())

print("\nTargets:")
print(y.columns.tolist())

print("\nX shape:", X.shape)
print("y shape:", y.shape)

# ==========================================
# 5. CATEGORICAL AND NUMERICAL FEATURES
# ==========================================

CATEGORICAL_FEATURES = [
    "l1_density",
    "l2_density",
    "l3_density",
    "l4_density",
    "day_type",
    "part_of_day"
]

NUMERICAL_FEATURES = [
    "l1_count",
    "l2_count",
    "l3_count",
    "l4_count",

    "l1_green",
    "l2_green",
    "l3_green",
    "l4_green",

    "l1_cleared",
    "l2_cleared",
    "l3_cleared",
    "l4_cleared",

    "l1_remaining",
    "l2_remaining",
    "l3_remaining",
    "l4_remaining",

    "total_count",

    "emergency_detected",
    "emergency_lane",

    "hour"
]

# ==========================================
# 6. PREPROCESSING
# ==========================================

preprocessor = ColumnTransformer(
    transformers=[
        (
            "categorical",
            OneHotEncoder(handle_unknown="ignore"),
            CATEGORICAL_FEATURES
        ),
        (
            "numerical",
            "passthrough",
            NUMERICAL_FEATURES
        )
    ]
)

# ==========================================
# 7. TRAIN / TEST SPLIT
# ==========================================

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.20,
    random_state=42
)

print("\nTraining samples:", X_train.shape[0])
print("Testing samples:", X_test.shape[0])

# ==========================================
# 8. FIT PREPROCESSOR
# ==========================================

X_train_processed = preprocessor.fit_transform(X_train)
X_test_processed = preprocessor.transform(X_test)

print("\nOriginal training shape:", X_train.shape)
print("Processed training shape:", X_train_processed.shape)


# ==========================================
# 9. TRAIN LINEAR REGRESSION (COMMENTED OUT)
# ==========================================

# print("\nTraining Linear Regression...")
# 
# model = LinearRegression()
# 
# model.fit(X_train_processed, y_train)
# 
# print("Linear Regression training complete!")
# 
# # ==========================================
# # 10. MAKE PREDICTIONS
# # ==========================================
# 
# y_pred = model.predict(X_test_processed)
# 
# print("\nPredictions generated!")
# print("Prediction shape:", y_pred.shape)
# 
# # ==========================================
# # 11. MODEL EVALUATION
# # ==========================================
# 
# mae = mean_absolute_error(y_test, y_pred)
# 
# rmse = mean_squared_error(
#     y_test,
#     y_pred
# ) ** 0.5
# 
# r2 = r2_score(y_test, y_pred)
# 
# print("\n========== LINEAR REGRESSION RESULTS ==========")
# 
# print(f"MAE  : {mae:.4f}")
# print(f"RMSE : {rmse:.4f}")
# print(f"R²   : {r2:.4f}")
# 
# # ==========================================
# # 12. LANE-WISE EVALUATION
# # ==========================================
# 
# lane_names = [
#     "L1",
#     "L2",
#     "L3",
#     "L4"
# ]
# 
# for i, lane in enumerate(lane_names):
# 
#     lane_mae = mean_absolute_error(
#         y_test.iloc[:, i],
#         y_pred[:, i]
#     )
# 
#     lane_rmse = mean_squared_error(
#         y_test.iloc[:, i],
#         y_pred[:, i]
#     ) ** 0.5
# 
#     lane_r2 = r2_score(
#         y_test.iloc[:, i],
#         y_pred[:, i]
#     )
# 
#     print(f"\n{lane}")
#     print(f"  MAE  : {lane_mae:.4f}")
#     print(f"  RMSE : {lane_rmse:.4f}")
#     print(f"  R²   : {lane_r2:.4f}")
# 
# # ==========================================
# # 13. TRAIN DECISION TREE
# # ==========================================
# 
# print("\nTraining Decision Tree...")
# 
# tree_model = DecisionTreeRegressor(
#     max_depth=10,
#     random_state=42
# )
# 
# tree_model.fit(X_train_processed, y_train)
# 
# print("Decision Tree training complete!")
# 
# 
# # ==========================================
# # 14. DECISION TREE PREDICTIONS
# # ==========================================
# 
# tree_pred = tree_model.predict(X_test_processed)
# 
# print("Decision Tree predictions generated!")
# 
# 
# # ==========================================
# # 15. DECISION TREE EVALUATION
# # ==========================================
# 
# tree_mae = mean_absolute_error(y_test, tree_pred)
# 
# tree_rmse = mean_squared_error(
#     y_test,
#     tree_pred
# ) ** 0.5
# 
# tree_r2 = r2_score(y_test, tree_pred)
# 
# 
# print("\n========== DECISION TREE RESULTS ==========")
# 
# print(f"MAE  : {tree_mae:.4f}")
# print(f"RMSE : {tree_rmse:.4f}")
# print(f"R²   : {tree_r2:.4f}")
# 
# # ==========================================
# # 16. TRAIN RANDOM FOREST
# # ==========================================
# 
# print("\nTraining Random Forest...")
# 
# rf_model = RandomForestRegressor(
#     n_estimators=200,
#     max_depth=15,
#     random_state=42,
#     n_jobs=-1
# )
# 
# rf_model.fit(X_train_processed, y_train)
# 
# print("Random Forest training complete!")
# 
# 
# # ==========================================
# # 17. RANDOM FOREST PREDICTIONS
# # ==========================================
# 
# rf_pred = rf_model.predict(X_test_processed)
# 
# print("Random Forest predictions generated!")
# 
# 
# # ==========================================
# # 18. RANDOM FOREST EVALUATION
# # ==========================================
# 
# rf_mae = mean_absolute_error(y_test, rf_pred)
# 
# rf_rmse = mean_squared_error(
#     y_test,
#     rf_pred
# ) ** 0.5
# 
# rf_r2 = r2_score(y_test, rf_pred)
# 
# 
# print("\n========== RANDOM FOREST RESULTS ==========")
# 
# print(f"MAE  : {rf_mae:.4f}")
# print(f"RMSE : {rf_rmse:.4f}")
# print(f"R²   : {rf_r2:.4f}")
# 
# # ==========================================
# # 19. RANDOM FOREST HYPERPARAMETER TEST
# # ==========================================
# 
# print("\n==========================================")
# print("RANDOM FOREST HYPERPARAMETER COMPARISON")
# print("==========================================")
# 
# configs = [
#     {"n_estimators": 100, "max_depth": 5},
#     {"n_estimators": 100, "max_depth": 10},
#     {"n_estimators": 100, "max_depth": 15},
#     {"n_estimators": 200, "max_depth": 10},
#     {"n_estimators": 200, "max_depth": 15},
#     {"n_estimators": 200, "max_depth": 20},
# ]
# 
# results = []
# 
# for config in configs:
# 
#     print(
#         f"\nTesting: "
#         f"trees={config['n_estimators']}, "
#         f"depth={config['max_depth']}"
#     )
# 
#     model = RandomForestRegressor(
#         n_estimators=config["n_estimators"],
#         max_depth=config["max_depth"],
#         random_state=42,
#         n_jobs=-1
#     )
# 
#     model.fit(X_train_processed, y_train)
# 
#     predictions = model.predict(X_test_processed)
# 
#     mae = mean_absolute_error(
#         y_test,
#         predictions
#     )
# 
#     rmse = mean_squared_error(
#         y_test,
#         predictions
#     ) ** 0.5
# 
#     r2 = r2_score(
#         y_test,
#         predictions
#     )
# 
#     results.append({
#         "n_estimators": config["n_estimators"],
#         "max_depth": config["max_depth"],
#         "MAE": mae,
#         "RMSE": rmse,
#         "R2": r2
#     })
# 
#     print(f"MAE  : {mae:.4f}")
#     print(f"RMSE : {rmse:.4f}")
#     print(f"R²   : {r2:.4f}")
# 
# 
# # ==========================================
# # 20. DISPLAY BEST CONFIGURATION
# # ==========================================
# 
# results_df = pd.DataFrame(results)
# 
# print("\n==========================================")
# print("ALL RANDOM FOREST RESULTS")
# print("==========================================")
# 
# print(results_df)
# 
# best_model = results_df.sort_values(
#     by="MAE"
# ).iloc[0]
# 
# print("\nBEST RANDOM FOREST CONFIGURATION:")
# 
# print(
#     f"Trees     : {int(best_model['n_estimators'])}"
# )
# 
# print(
#     f"Max Depth : {int(best_model['max_depth'])}"
# )
# 
# print(
#     f"MAE       : {best_model['MAE']:.4f}"
# )
# 
# print(
#     f"RMSE      : {best_model['RMSE']:.4f}"
# )
# 
# print(
#     f"R²        : {best_model['R2']:.4f}"
# )
# ==========================================
# 21. TRAIN XGBOOST
# ==========================================

print("\nTraining XGBoost...")

xgb_model = XGBRegressor(
    n_estimators=200,
    max_depth=6,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.8,
    objective="reg:squarederror",
    random_state=42,
    n_jobs=-1
)

xgb_model.fit(
    X_train_processed,
    y_train
)

print("XGBoost training complete!")


# ==========================================
# 22. XGBOOST PREDICTIONS
# ==========================================

xgb_pred = xgb_model.predict(X_test_processed)

print("XGBoost predictions generated!")
print("Prediction shape:", xgb_pred.shape)


# ==========================================
# 23. XGBOOST EVALUATION
# ==========================================

xgb_mae = mean_absolute_error(
    y_test,
    xgb_pred
)

xgb_rmse = mean_squared_error(
    y_test,
    xgb_pred
) ** 0.5

xgb_r2 = r2_score(
    y_test,
    xgb_pred
)

print("\n========== XGBOOST RESULTS ==========")

print(f"MAE  : {xgb_mae:.4f}")
print(f"RMSE : {xgb_rmse:.4f}")
print(f"R²   : {xgb_r2:.4f}")

# ==========================================
# 24. XGBOOST HYPERPARAMETER TUNING
# ==========================================

print("\n==========================================")
print("XGBOOST HYPERPARAMETER TUNING")
print("==========================================")

xgb_configs = [
    {
        "n_estimators": 200,
        "max_depth": 3,
        "learning_rate": 0.05
    },
    {
        "n_estimators": 200,
        "max_depth": 5,
        "learning_rate": 0.05
    },
    {
        "n_estimators": 200,
        "max_depth": 6,
        "learning_rate": 0.05
    },
    {
        "n_estimators": 200,
        "max_depth": 7,
        "learning_rate": 0.05
    },
    {
        "n_estimators": 200,
        "max_depth": 6,
        "learning_rate": 0.03
    },
    {
        "n_estimators": 200,
        "max_depth": 6,
        "learning_rate": 0.10
    }
]

xgb_results = []

for config in xgb_configs:

    print(
        f"\nTesting: "
        f"trees={config['n_estimators']}, "
        f"depth={config['max_depth']}, "
        f"learning_rate={config['learning_rate']}"
    )

    model = XGBRegressor(
        n_estimators=config["n_estimators"],
        max_depth=config["max_depth"],
        learning_rate=config["learning_rate"],
        subsample=0.8,
        colsample_bytree=0.8,
        objective="reg:squarederror",
        random_state=42,
        n_jobs=-1
    )

    model.fit(
        X_train_processed,
        y_train
    )

    predictions = model.predict(
        X_test_processed
    )

    current_mae = mean_absolute_error(
        y_test,
        predictions
    )

    current_rmse = mean_squared_error(
        y_test,
        predictions
    ) ** 0.5

    current_r2 = r2_score(
        y_test,
        predictions
    )

    xgb_results.append({
        "n_estimators": config["n_estimators"],
        "max_depth": config["max_depth"],
        "learning_rate": config["learning_rate"],
        "MAE": current_mae,
        "RMSE": current_rmse,
        "R2": current_r2
    })

    print(f"MAE  : {current_mae:.4f}")
    print(f"RMSE : {current_rmse:.4f}")
    print(f"R²   : {current_r2:.4f}")


# ==========================================
# 25. DISPLAY RESULTS
# ==========================================

xgb_results_df = pd.DataFrame(xgb_results)

print("\n==========================================")
print("XGBOOST TUNING RESULTS")
print("==========================================")

print(
    xgb_results_df.to_string(index=False)
)


# ==========================================
# 26. BEST CONFIGURATION
# ==========================================

best_xgb = xgb_results_df.sort_values(
    by="MAE"
).iloc[0]

print("\n==========================================")
print("BEST XGBOOST CONFIGURATION")
print("==========================================")

print(
    f"Trees         : {int(best_xgb['n_estimators'])}"
)

print(
    f"Max Depth     : {int(best_xgb['max_depth'])}"
)

print(
    f"Learning Rate : {best_xgb['learning_rate']}"
)

print(
    f"MAE           : {best_xgb['MAE']:.4f}"
)

print(
    f"RMSE          : {best_xgb['RMSE']:.4f}"
)

print(
    f"R²            : {best_xgb['R2']:.4f}"
)
# ==========================================
# 27. TRAIN FINAL XGBOOST MODEL
# ==========================================

print("\nTraining final XGBoost model...")

final_xgb = XGBRegressor(
    n_estimators=200,
    max_depth=5,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.8,
    objective="reg:squarederror",
    random_state=42,
    n_jobs=-1
)

final_xgb.fit(
    X_train_processed,
    y_train
)

print("Final XGBoost model trained!")
# ==========================================
# 28. FEATURE IMPORTANCE
# ==========================================

feature_names = preprocessor.get_feature_names_out()

importance = final_xgb.feature_importances_

feature_importance_df = pd.DataFrame({
    "Feature": feature_names,
    "Importance": importance
})

feature_importance_df = feature_importance_df.sort_values(
    by="Importance",
    ascending=False
)

print("\n==========================================")
print("TOP 15 FEATURE IMPORTANCE")
print("==========================================")

print(
    feature_importance_df.head(15).to_string(index=False)
)

# ==========================================
# 29. FINAL SAMPLE PREDICTIONS
# ==========================================

print("\n==========================================")
print("SAMPLE PREDICTIONS")
print("==========================================")

# Generate predictions once
final_predictions = final_xgb.predict(
    X_test_processed
)

# Create comparison table
sample_predictions = pd.DataFrame({
    "Actual_L1": y_test["next_l1_count"].values,
    "Predicted_L1": final_predictions[:, 0],

    "Actual_L2": y_test["next_l2_count"].values,
    "Predicted_L2": final_predictions[:, 1],

    "Actual_L3": y_test["next_l3_count"].values,
    "Predicted_L3": final_predictions[:, 2],

    "Actual_L4": y_test["next_l4_count"].values,
    "Predicted_L4": final_predictions[:, 3]
})

# Display first 10 predictions
print(
    sample_predictions.head(10).to_string(index=False)
)

# ==========================================
# 30. SAVE FINAL MODEL
# ==========================================

print("\nSaving final model...")

joblib.dump(final_xgb, "traffic_prediction_model.joblib")
joblib.dump(preprocessor, "traffic_preprocessor.joblib")

print("Model saved successfully!")
print("Preprocessor saved successfully!")