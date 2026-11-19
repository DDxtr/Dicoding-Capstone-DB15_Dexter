import sqlite3
import pandas as pd
import os

"""
Modul Inisialisasi Database SQLite UMKM Firaza (Smart Inventory)
Membuat skema tabel master material, produk, BOM, dan log transaksi.
"""

DB_NAME = os.path.join(os.path.dirname(__file__), "smart_inventory.db")
print(f"Menginisialisasi database pada: {DB_NAME}")

conn = sqlite3.connect(DB_NAME)
cursor = conn.cursor()

# ==========================================
# 1. PEMBUATAN TABEL SKEMA
# ==========================================

# Tabel Master Material (Bahan baku pendukung fulfillment)
cursor.execute("""
CREATE TABLE IF NOT EXISTS materials (
    material_id INTEGER PRIMARY KEY AUTOINCREMENT,
    material_name TEXT NOT NULL,
    unit TEXT NOT NULL,
    current_stock INTEGER NOT NULL,
    lead_time_days INTEGER NOT NULL,
    min_stock_threshold INTEGER DEFAULT 30
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

# Tabel Bill of Materials (BOM / Resep kebutuhan per unit produk)
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
    quantity INTEGER NOT NULL,
    note TEXT DEFAULT ''
)
""")

conn.commit()
print("-> Tabel database berhasil diverifikasi & diinisialisasi!\n")

# ==========================================
# 2. SEED DATA AWAL (JIKA KOSONG)
# ==========================================

# Cek tabel materials
cursor.execute("SELECT COUNT(*) FROM materials")
if cursor.fetchone()[0] == 0:
    materials_dummy = [
        ("Kardus Box Ukuran M", "pcs", 45, 3, 30),
        ("Kardus Box Ukuran L", "pcs", 20, 3, 25),
        ("Pita Emas Satin", "meter", 150, 2, 50),
        ("Plastik Wrapping", "pcs", 80, 1, 30),
        ("Greeting Card Eksklusif", "pcs", 12, 2, 20)
    ]
    cursor.executemany("""
    INSERT INTO materials (material_name, unit, current_stock, lead_time_days, min_stock_threshold)
    VALUES (?, ?, ?, ?, ?)
    """, materials_dummy)
    print("-> Data awal Material berhasil dimasukkan.")

# Cek tabel products
cursor.execute("SELECT COUNT(*) FROM products")
if cursor.fetchone()[0] == 0:
    products_dummy = [
        ("Hampers Sajadah Premium", 150000.0),
        ("Hampers Handuk Seserahan", 120000.0)
    ]
    cursor.executemany("""
    INSERT INTO products (product_name, price)
    VALUES (?, ?)
    """, products_dummy)
    print("-> Data awal Produk berhasil dimasukkan.")

# Cek tabel bill_of_materials
cursor.execute("SELECT COUNT(*) FROM bill_of_materials")
if cursor.fetchone()[0] == 0:
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
    print("-> Data awal Bill of Materials (BOM) berhasil dimasukkan.")

conn.commit()

# ==========================================
# 3. VERIFIKASI DATA
# ==========================================
print("\n=== RINGKASAN DATA DATABASE ===")
df_materials = pd.read_sql_query("SELECT * FROM materials", conn)
print("Master Materials:\n", df_materials)

df_products = pd.read_sql_query("SELECT * FROM products", conn)
print("\nMaster Products:\n", df_products)

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
print("\nBill of Materials (BOM):\n", df_bom)

conn.close()
print("\n-> Inisialisasi Database Selesai!")
