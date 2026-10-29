import sqlite3
import pandas as pd
import os

print("File database akan dibuat di folder:", os.getcwd())

# Lanjutkan dengan kode koneksi database Anda
db_name = "smart_inventory.db"
conn = sqlite3.connect(db_name)
# ... sisa kode Anda ...
# ==========================================
# 1. INISIALISASI DATABASE & PEMBUATAN TABEL
# ==========================================
db_name = "smart_inventory.db"
conn = sqlite3.connect(db_name)
cursor = conn.cursor()

# Tabel Master Material (Bahan baku pendukung fulfillment)
cursor.execute("""
CREATE TABLE IF NOT EXISTS materials (
    material_id INTEGER PRIMARY KEY AUTOINCREMENT,
    material_name TEXT NOT NULL,
    unit TEXT NOT NULL,
    current_stock INTEGER NOT NULL,
    lead_time_days INTEGER NOT NULL
)
""")

# Tabel Master Produk (Produk jadi)
cursor.execute("""
CREATE TABLE IF NOT EXISTS products (
    product_id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_name TEXT NOT NULL,
    price REAL NOT NULL
)
""")

# Tabel Bill of Materials (BOM / Resep kebutuhan per 1 unit produk)
cursor.execute("""
CREATE TABLE IF NOT EXISTS bill_of_materials (
    boms_id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER,
    material_id INTEGER,
    quantity_required REAL NOT NULL,
    FOREIGN KEY (product_id) REFERENCES products (product_id),
    FOREIGN KEY (material_id) REFERENCES materials (material_id)
)
""")

# Tabel Log Transaksi (Stock-in, Stock-out, Stock Opname)
cursor.execute("""
CREATE TABLE IF NOT EXISTS transactions (
    transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    transaction_type TEXT NOT NULL,
    reference_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL
)
""")

conn.commit()
print("-> Tabel database berhasil diinisialisasi!\n")

# ==========================================
# 2. MENGISI DATA DUMMY (CONTOH AWAL)
# ==========================================

# Data Dummy: Materials (Kardus, Pita, Packaging)
materials_dummy = [
    ("Kardus Box Ukuran M", "pcs", 45, 3),
    ("Kardus Box Ukuran L", "pcs", 20, 3),
    ("Pita Emas Satin", "meter", 150, 2),
    ("Plastik Wrapping", "pcs", 80, 1),
    ("Greeting Card Eksklusif", "pcs", 12, 2)
]

cursor.executemany("""
INSERT INTO materials (material_name, unit, current_stock, lead_time_days)
VALUES (?, ?, ?, ?)
""", materials_dummy)

# Data Dummy: Products (Hampers Handuk & Sajadah)
products_dummy = [
    ("Hampers Sajadah Premium", 150000),
    ("Hampers Handuk Seserahan", 120000)
]

cursor.executemany("""
INSERT INTO products (product_name, price)
VALUES (?, ?)
""", products_dummy)

# Data Dummy: Bill of Materials (BOM)
# Asumsi:
# Product 1 (Hampers Sajadah Premium) butuh:
# - 1 Kardus Box Ukuran M (material_id=1)
# - 2 Meter Pita Emas Satin (material_id=3)
# - 1 Greeting Card Eksklusif (material_id=5)
# Product 2 (Hampers Handuk Seserahan) butuh:
# - 1 Kardus Box Ukuran L (material_id=2)
# - 1.5 Meter Pita Emas Satin (material_id=3)
# - 1 Plastik Wrapping (material_id=4)
boms_dummy = [
    (1, 1, 1.0),  # Hampers Sajadah -> Kardus M (1 pcs)
    (1, 3, 2.0),  # Hampers Sajadah -> Pita Emas (2 meter)
    (1, 5, 1.0),  # Hampers Sajadah -> Greeting Card (1 pcs)
    (2, 2, 1.0),  # Hampers Handuk -> Kardus L (1 pcs)
    (2, 3, 1.5),  # Hampers Handuk -> Pita Emas (1.5 meter)
    (2, 4, 1.0)   # Hampers Handuk -> Plastik Wrapping (1 pcs)
]

cursor.executemany("""
INSERT INTO bill_of_materials (product_id, material_id, quantity_required)
VALUES (?, ?, ?)
""", boms_dummy)

conn.commit()
print("-> Data dummy berhasil dimasukkan ke dalam database!\n")

# ==========================================
# 3. CONTOH QUERY & SIMULASI KALKULASI STOK
# ==========================================
print("=== MENAMPILKAN MASTER MATERIAL ===")
df_materials = pd.read_sql_query("SELECT * FROM materials", conn)
print(df_materials, "\n")

print("=== MENAMPILKAN RESEP BOM (BILL OF MATERIALS) ===")
query_bom = """
SELECT 
    p.product_name, 
    m.material_name, 
    b.quantity_required, 
    m.unit 
FROM bill_of_materials b
JOIN products p ON b.product_id = p.product_id
JOIN materials m ON b.material_id = m.material_id
"""
df_bom = pd.read_sql_query(query_bom, conn)
print(df_bom, "\n")

# Tutup koneksi database setelah selesai
conn.close()