import numpy as np
import pandas as pd

# 1. Load data historis
df = pd.read_csv("historical_sales.csv")

# Pastikan kolom date berformat datetime
df["date"] = pd.to_datetime(df["date"])

# 2. Agregasi per tanggal dan produk
df_aggregated = df.groupby("date")["quantity"].sum().reset_index()

# 3. Ekstraksi Calendar Features & Fitur Peak Season (Penanganan Musiman/Hari Raya)
df_aggregated["year"] = df_aggregated["date"].dt.year
df_aggregated["month"] = df_aggregated["date"].dt.month
df_aggregated["day"] = df_aggregated["date"].dt.day
df_aggregated["dayofweek"] = df_aggregated["date"].dt.dayofweek
df_aggregated["is_weekend"] = df_aggregated["dayofweek"].apply(
    lambda x: 1 if x >= 5 else 0
)

# Menambahkan fitur penanda peak season (misalnya hari ke-90 s.d. 120 dan hari ke-330 s.d. 365)
df_aggregated["day_of_year"] = df_aggregated["date"].dt.dayofyear
df_aggregated["is_peak_season"] = df_aggregated["day_of_year"].apply(
    lambda x: 1 if (90 <= x <= 120) or (330 <= x <= 365) else 0
)

# 4. Membuat Lag Features & Rolling Mean
df_aggregated["lag_7"] = df_aggregated["quantity"].shift(7)
df_aggregated["rolling_mean_7"] = (
    df_aggregated["quantity"].shift(1).rolling(window=7).mean()
)

# Bersihkan missing value akibat shifting
df_aggregated = df_aggregated.dropna()

print("Contoh hasil Feature Engineering yang Diperkaya:")
print(df_aggregated.head())

# Simpan hasil feature engineering ke versi dataset baru
df_aggregated.to_csv("processed_dataset.csv", index=False)
print(
    "\n-> Berhasil menyimpan dataset baru dengan fitur tambahan ke"
    " 'processed_dataset.csv'"
)