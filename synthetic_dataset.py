import sqlite3
import numpy as np
import pandas as pd

# 1. Tentukan rentang tanggal (misal: 2 tahun terakhir hingga hari ini)
start_date = "2024-01-01"
end_date = "2025-12-31"
date_range = pd.date_range(start=start_date, end=end_date, freq="D")

# 2. Buat list untuk menampung data transaksi sintetis
sales_data = []

np.random.seed(42)  # Agar hasil acak konsisten saat dijalankan ulang

for date in date_range:
  # Tentukan dasar penjualan normal harian (Poisson distribution)
  base_sajadah = np.random.poisson(lam=3)
  base_handuk = np.random.poisson(lam=4)

  # Tambahkan simulasi Peak Season (Contoh: Bulan April / Hari Raya dan Bulan Desember / Akhir Tahun)
  month = date.month
  day_of_week = date.dayofweek

  multiplier = 1.0
  if month in [3, 4]:  # Simulasi Ramadhan / Idul Fitri (Lonjakan tinggi)
    multiplier = 3.5
  elif month in [11, 12]:  # Simulasi Akhir Tahun / Musim Pernikahan
    multiplier = 2.0
  elif day_of_week in [5, 6]:  # Sedikit naik di akhir pekan
    multiplier = 1.3

  # Hitung jumlah pesanan harian dengan pengali musim
  qty_sajadah = int(base_sajadah * multiplier)
  qty_handuk = int(base_handuk * multiplier)

  # Masukkan ke list transaksi jika ada penjualan > 0
  if qty_sajadah > 0:
    sales_data.append(
        (date.strftime("%Y-%m-%d"), "stock_out", 1, qty_sajadah)
    )  # product_id 1 = Hampers Sajadah
  if qty_handuk > 0:
    sales_data.append(
        (date.strftime("%Y-%m-%d"), "stock_out", 2, qty_handuk)
    )  # product_id 2 = Hampers Handuk

# Ubah ke DataFrame Pandas
df_history = pd.DataFrame(
    sales_data, columns=["date", "transaction_type", "reference_id", "quantity"]
)

# 3. Simpan ke file CSV dan masukkan ke database SQLite
csv_filename = "historical_sales.csv"
df_history.to_csv(csv_filename, index=False)
print(f"-> Berhasil membuat file data historis: {csv_filename}")
print(f"-> Total baris transaksi historis yang dibuat: {len(df_history)}")

# Masukkan juga ke tabel transactions di database smart_inventory.db
conn = sqlite3.connect("smart_inventory.db")
df_history.to_sql("transactions", conn, if_exists="append", index=False)
conn.close()
print("-> Data historis berhasil dimasukkan ke tabel 'transactions' di database!")