import joblib
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.model_selection import train_test_split
from xgboost import XGBRegressor

# Load dataset baru
df = pd.read_csv("processed_dataset.csv")

# Pilih fitur yang diperbarui
features = [
    "year",
    "month",
    "day",
    "dayofweek",
    "is_weekend",
    "is_peak_season",
    "lag_7",
    "rolling_mean_7",
]
target = "quantity"

X = df[features]
y = df[target]

# Split kronologis
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, shuffle=False
)

# Inisialisasi XGBoost dengan parameter yang disetel untuk akurasi lebih baik
model = XGBRegressor(
    n_estimators=200,
    learning_rate=0.05,
    max_depth=5,
    subsample=0.8,
    colsample_bytree=0.8,
    random_state=42,
)
model.fit(X_train, y_train)

# Evaluasi
predictions = model.predict(X_test)
mse = mean_squared_error(y_test, predictions)
rmse = mse**0.5
mae = mean_absolute_error(y_test, predictions)

print("=== EVALUASI MODEL ===")
print(f"RMSE: {rmse:.4f}")
print(f"MAE: {mae:.4f}")

# Simpan model baru
joblib.dump(model, "demand_forecast_model.pkl")
print("\n-> Model berhasil disimpan sebagai 'demand_forecast_model.pkl'")