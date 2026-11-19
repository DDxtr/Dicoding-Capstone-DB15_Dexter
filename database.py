import sqlite3
import pandas as pd
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "smart_inventory.db")

def get_connection():
    """Membuka koneksi ke database SQLite."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Inisialisasi tabel dan memastikan kolom-kolom penting tersedia."""
    conn = get_connection()
    cursor = conn.cursor()

    # 1. Tabel Materials
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

    # Periksa apakah kolom min_stock_threshold sudah ada pada tabel lama
    cursor.execute("PRAGMA table_info(materials)")
    columns = [col[1] for col in cursor.fetchall()]
    if "min_stock_threshold" not in columns:
        try:
            cursor.execute("ALTER TABLE materials ADD COLUMN min_stock_threshold INTEGER DEFAULT 30")
        except Exception:
            pass

    # 2. Tabel Products
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS products (
        product_id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_name TEXT NOT NULL,
        price REAL NOT NULL
    )
    """)

    # 3. Tabel Bill of Materials (BOM)
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

    # 4. Tabel Transactions
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

    cursor.execute("PRAGMA table_info(transactions)")
    trx_cols = [col[1] for col in cursor.fetchall()]
    if "note" not in trxCols if 'trxCols' in locals() else trx_cols:
        if "note" not in trx_cols:
            try:
                cursor.execute("ALTER TABLE transactions ADD COLUMN note TEXT DEFAULT ''")
            except Exception:
                pass

    # Seed data default jika materials kosong
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

    # Seed data default jika products kosong
    cursor.execute("SELECT COUNT(*) FROM products")
    if cursor.fetchone()[0] == 0:
        products_dummy = [
            ("Hampers Sajadah Premium", 150000.0),
            ("Hampers Handuk Seserahan", 120000.0)
        ]
        cursor.executemany("INSERT INTO products (product_name, price) VALUES (?, ?)", products_dummy)

    # Seed data default jika BOM kosong
    cursor.execute("SELECT COUNT(*) FROM bill_of_materials")
    if cursor.fetchone()[0] == 0:
        boms_dummy = [
            (1, 1, 1.0),  # Sajadah -> Kardus M
            (1, 3, 2.0),  # Sajadah -> Pita Satin (2m)
            (1, 5, 1.0),  # Sajadah -> Greeting Card
            (2, 2, 1.0),  # Handuk -> Kardus L
            (2, 3, 1.5),  # Handuk -> Pita Satin (1.5m)
            (2, 4, 1.0)   # Handuk -> Plastik Wrapping
        ]
        cursor.executemany("""
        INSERT INTO bill_of_materials (product_id, material_id, quantity_required)
        VALUES (?, ?, ?)
        """, boms_dummy)

    conn.commit()
    conn.close()

def get_materials_df():
    """Mengambil master data material dalam bentuk DataFrame."""
    init_db()
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM materials", conn)
    conn.close()
    return df

def get_products_df():
    """Mengambil master data produk dalam bentuk DataFrame."""
    init_db()
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM products", conn)
    conn.close()
    return df

def get_bom_df():
    """Mengambil relasi Bill of Materials (BOM) lengkap dengan nama produk dan material."""
    init_db()
    conn = get_connection()
    query = """
    SELECT 
        b.boms_id,
        p.product_id,
        p.product_name,
        m.material_id,
        m.material_name,
        b.quantity_required,
        m.unit
    FROM bill_of_materials b
    JOIN products p ON b.product_id = p.product_id
    JOIN materials m ON b.material_id = m.material_id
    ORDER BY p.product_name, m.material_name
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def get_recent_transactions_df(limit=30):
    """Mengambil riwayat transaksi terbaru."""
    init_db()
    conn = get_connection()
    query = f"""
    SELECT 
        t.transaction_id,
        t.date,
        t.transaction_type,
        CASE 
            WHEN m.material_name IS NOT NULL THEN m.material_name
            WHEN p.product_name IS NOT NULL THEN p.product_name
            ELSE 'Ref #' || t.reference_id
        END as item_name,
        t.quantity,
        t.note
    FROM transactions t
    LEFT JOIN materials m ON t.reference_id = m.material_id AND t.transaction_type LIKE '%stock%'
    LEFT JOIN products p ON t.reference_id = p.product_id AND t.transaction_type NOT LIKE '%stock%'
    ORDER BY t.transaction_id DESC
    LIMIT {limit}
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def record_transaction(trans_type, material_id, quantity, note=""):
    """
    Mencatat transaksi logistik (Stock-In, Stock-Out, Stock Opname) 
    dan memperbarui current_stock di tabel materials secara atomik.
    """
    init_db()
    conn = get_connection()
    cursor = conn.cursor()
    today_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Ambil stok saat ini
    cursor.execute("SELECT current_stock, material_name FROM materials WHERE material_id = ?", (material_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise ValueError(f"Material ID {material_id} tidak ditemukan.")

    current_stock = row["current_stock"]
    material_name = row["material_name"]

    if "in" in trans_type.lower():
        new_stock = current_stock + quantity
        db_trans_type = "stock_in"
    elif "out" in trans_type.lower():
        new_stock = max(0, current_stock - quantity)
        db_trans_type = "stock_out"
    elif "opname" in trans_type.lower():
        new_stock = quantity
        db_trans_type = "stock_opname"
    else:
        new_stock = current_stock + quantity
        db_trans_type = trans_type

    # Update stok
    cursor.execute("UPDATE materials SET current_stock = ? WHERE material_id = ?", (new_stock, material_id))

    # Catat ke transaksi
    cursor.execute("""
    INSERT INTO transactions (date, transaction_type, reference_id, quantity, note)
    VALUES (?, ?, ?, ?, ?)
    """, (today_str, db_trans_type, material_id, quantity, note))

    conn.commit()
    conn.close()
    return {
        "material_name": material_name,
        "old_stock": current_stock,
        "new_stock": new_stock,
        "trans_type": db_trans_type
    }

def calculate_order_bom_impact(product_name_or_id, order_qty):
    """
    Menghitung kebutuhan material berdasarkan BOM untuk pesanan tertentu,
    membandingkan dengan stok aktual saat ini di gudang.
    """
    bom_df = get_bom_df()
    materials_df = get_materials_df()

    if isinstance(product_name_or_id, int):
        filtered_bom = bom_df[bom_df["product_id"] == product_name_or_id]
    else:
        filtered_bom = bom_df[bom_df["product_name"].str.contains(str(product_name_or_id), case=False, na=False)]

    if filtered_bom.empty:
        # Fallback jika nama produk parsial (misal 'sajadah' atau 'handuk')
        if "sajadah" in str(product_name_or_id).lower():
            filtered_bom = bom_df[bom_df["product_id"] == 1]
        elif "handuk" in str(product_name_or_id).lower():
            filtered_bom = bom_df[bom_df["product_id"] == 2]

    impact_list = []
    has_shortage = False

    for _, row in filtered_bom.iterrows():
        mat_id = row["material_id"]
        mat_name = row["material_name"]
        unit = row["unit"]
        req_per_unit = row["quantity_required"]
        total_required = req_per_unit * order_qty

        # Ambil stok terkini
        mat_info = materials_df[materials_df["material_id"] == mat_id]
        current_stock = mat_info["current_stock"].values[0] if not mat_info.empty else 0
        lead_time = mat_info["lead_time_days"].values[0] if not mat_info.empty else 2
        min_thresh = mat_info["min_stock_threshold"].values[0] if "min_stock_threshold" in mat_info.columns else 20

        remaining = current_stock - total_required

        if remaining < 0:
            status = "🔴 Kritis (Defisit Stok)"
            has_shortage = True
            action = f"Pesan defisit {abs(remaining)} {unit} segera (Lead time: {lead_time} hari)"
        elif remaining < min_thresh:
            status = "🟡 Waspada (Di Bawah Buffer)"
            action = f"Sisa {remaining} {unit} mendekati batas aman ({min_thresh} {unit})"
        else:
            status = "🟢 Aman (Stok Cukup)"
            action = f"Stok surplus {remaining} {unit}"

        impact_list.append({
            "Material": mat_name,
            "Kebutuhan Resep": f"{req_per_unit} {unit}/pax",
            "Total Dibutuhkan": f"{total_required} {unit}",
            "Stok Gudang": f"{current_stock} {unit}",
            "Sisa Pasca Order": f"{remaining} {unit}",
            "Status": status,
            "Rekomendasi Tindakan": action,
            "is_shortage": remaining < 0
        })

    return pd.DataFrame(impact_list), has_shortage
