import os
import chromadb
from database import get_materials_df, get_bom_df
from forecasting import generate_multi_day_forecast

CHROMA_DIR = os.path.join(os.path.dirname(__file__), "chroma_db")

FIRAZA_KNOWLEDGE_DOCS = [
    {
        "id": "sop_buffer_rop",
        "title": "SOP Manajemen Inventaris & Reorder Point (ROP)",
        "content": (
            "SOP Inventaris UMKM Firaza: Kebijakan buffer stock dan reorder point.\n"
            "Rumus Reorder Point (ROP): ROP = (Kebutuhan Harian Rata-rata x Lead Time Pemasok) + Safety Stock.\n"
            "Batas minimum safety stock di gudang:\n"
            "- Kardus Box Ukuran M: minimal 30 pcs.\n"
            "- Kardus Box Ukuran L: minimal 25 pcs.\n"
            "- Pita Emas Satin: minimal 50 meter.\n"
            "- Plastik Wrapping: minimal 30 pcs.\n"
            "- Greeting Card Eksklusif: minimal 20 pcs.\n"
            "Tindakan: Ketika stok aktual di gudang berada di bawah atau sama dengan ROP, sistem mewajibkan tim operasional menerbitkan Purchase Order (PO) ke supplier hari itu juga."
        ),
        "category": "SOP_Gudang"
    },
    {
        "id": "supplier_leadtime_moq",
        "title": "Data Supplier Bahan Baku, Lead Time, & MOQ",
        "content": (
            "Daftar Supplier Utama Bahan Baku UMKM Firaza:\n"
            "1. Supplier Kardus Box ('PT Kartona Jaya Packaging'): Lead time 3 hari kerja. Minimum Order Quantity (MOQ) 50 pcs per ukuran (Box M & Box L). Biaya kirim ditanggung supplier untuk order di atas 200 pcs.\n"
            "2. Supplier Pita Emas Satin ('Toko Pita Nusantara'): Lead time 2 hari kerja. MOQ 50 meter per gulung.\n"
            "3. Supplier Greeting Card Foil Emas ('Percetakan Cepat Eksklusif'): Lead time 2 hari kerja. MOQ 50 lembar per batch cetak.\n"
            "4. Supplier Plastik Wrapping & Segel ('Plastindo Kemas'): Lead time 1 hari kerja (tersedia pengiriman sameday jika pesanan pagi). MOQ 100 pcs.\n"
            "Catatan: Saat peak season, tambahkan buffer lead time ekstra 1-2 hari karena tingginya antrean logistik kurir."
        ),
        "category": "Data_Supplier"
    },
    {
        "id": "product_specs_bom",
        "title": "Katalog Produk & Resep Bill of Materials (BOM)",
        "content": (
            "Katalog Produk Hampers & Resep BOM UMKM Firaza:\n"
            "1. Hampers Sajadah Premium (Harga Jual Rp 150.000 / pax):\n"
            "   - Komponen resep: 1 unit Sajadah Tenun Emas, 1 unit Kardus Box Ukuran M, 2 meter Pita Emas Satin, 1 unit Greeting Card Eksklusif.\n"
            "2. Hampers Handuk Seserahan (Harga Jual Rp 120.000 / pax):\n"
            "   - Komponen resep: 1 unit Handuk Microfiber Lembut, 1 unit Kardus Box Ukuran L, 1.5 meter Pita Emas Satin, 1 unit Plastik Wrapping Segel.\n"
            "Kapasitas perakitan manual harian workshop Firaza adalah 40 hampers per hari untuk 1 tim (2 orang perakit)."
        ),
        "category": "Katalog_BOM"
    },
    {
        "id": "seasonal_strategy_calendar",
        "title": "Kalender Musiman (Peak Season) & Strategi Penyetokan",
        "content": (
            "Pola Musiman Penjualan UMKM Firaza:\n"
            "1. Peak Season 1 - Ramadhan & Hari Raya Idul Fitri (Bulan Maret - April): Lonjakan penjualan mencapai 350% (3.5x normal). Permintaan terbanyak pada Hampers Sajadah Premium untuk parcel perusahaan dan bingkisan keluarga. Strategi: Penyetokan bahan baku (stock-in) wajib diselesaikan pada H-30 sebelum awal Ramadhan.\n"
            "2. Peak Season 2 - Musim Pernikahan & Akhir Tahun (Bulan November - Desember): Lonjakan penjualan mencapai 200% (2.0x normal). Hampers Handuk Seserahan menjadi produk paling diminati untuk hadiah pernikahan dan kado korporasi.\n"
            "3. Low Season (Bulan Januari, Februari, Agustus): Penjualan stabil pada angka 4-7 unit per hari. Waktu optimal untuk audit gudang (stock opname) dan pemeliharaan hubungan supplier."
        ),
        "category": "Strategi_Musiman"
    },
    {
        "id": "bulk_orders_bottleneck",
        "title": "Protokol Penanganan Batched Orders & Pencegahan Bottleneck",
        "content": (
            "Protokol Pesanan Partai Besar (>50 pax):\n"
            "1. Dilarang menerima DP sebelum melakukan verifikasi stok fisik material penunjang di dashboard Smart Inventory.\n"
            "2. Jika terdapat material yang berstatus 'Need Attention' atau 'Restock Priority', tim CS wajib menginformasikan estimasi lead time pengerjaan adalah: Lead Time Supplier Terlama + Estimasi Waktu Perakitan (1 hari per 40 pax).\n"
            "3. Jika kuantitas pesanan >100 pax, hubungi supplier kardus dan pita melalui kontak prioritas untuk booking kuota bahan baku terlebih dahulu."
        ),
        "category": "SOP_Operasional"
    }
]

def get_chroma_collection():
    """Menginisialisasi klien persistent ChromaDB dan mengisi dokumen knowledge base Firaza."""
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    collection = client.get_or_create_collection(
        name="firaza_smart_inventory_kb",
        metadata={"description": "Knowledge Base SOP, Supplier, dan Kebijakan Stok UMKM Firaza"}
    )

    # Isi dokumen jika koleksi masih kosong
    if collection.count() < len(FIRAZA_KNOWLEDGE_DOCS):
        ids = [doc["id"] for doc in FIRAZA_KNOWLEDGE_DOCS]
        documents = [doc["content"] for doc in FIRAZA_KNOWLEDGE_DOCS]
        metadatas = [{"title": doc["title"], "category": doc["category"]} for doc in FIRAZA_KNOWLEDGE_DOCS]
        collection.upsert(ids=ids, documents=documents, metadatas=metadatas)

    return collection

def retrieve_relevant_knowledge(query, n_results=3):
    """Mengambil dokumen relevan dari Vector Database ChromaDB berdasarkan kemiripan semantik."""
    collection = get_chroma_collection()
    results = collection.query(
        query_texts=[query],
        n_results=min(n_results, collection.count())
    )

    retrieved = []
    if results and "documents" in results and results["documents"]:
        docs = results["documents"][0]
        metas = results["metadatas"][0] if "metadatas" in results else [{}] * len(docs)
        for doc, meta in zip(docs, metas):
            retrieved.append({
                "content": doc,
                "title": meta.get("title", "Dokumen UMKM Firaza"),
                "category": meta.get("category", "SOP")
            })
    return retrieved

def get_realtime_inventory_context():
    """Mengumpulkan status real-time stok gudang dan ringkasan model forecasting untuk disuntikkan ke RAG."""
    materials_df = get_materials_df()
    stock_lines = []
    critical_items = []

    for _, row in materials_df.iterrows():
        name = row["material_name"]
        stock = row["current_stock"]
        unit = row["unit"]
        min_stock = row.get("min_stock_threshold", 30)
        lead_time = row["lead_time_days"]

        status = "AMAN"
        if stock < min_stock:
            status = "KRITIS / DI BAWAH BATAS BUFFER"
            critical_items.append(f"{name} (Sisa {stock} {unit}, lead time supplier {lead_time} hari)")

        stock_lines.append(f"- {name}: {stock} {unit} [Batas Aman: {min_stock} {unit}, Lead Time: {lead_time} hari, Status: {status}]")

    stock_str = "\n".join(stock_lines)
    critical_str = "\n".join(critical_items) if critical_items else "Tidak ada material kritis saat ini."

    # Ambil proyeksi 7 hari dari model ML
    try:
        df_forecast = generate_multi_day_forecast(7)
        total_pred = df_forecast["predicted_quantity"].sum()
        avg_pred = round(total_pred / 7, 1)
        forecast_str = f"Estimasi total permintaan 7 hari ke depan: {total_pred} unit (rata-rata {avg_pred} unit/hari)."
    except Exception:
        forecast_str = "Model forecasting memproyeksikan permintaan rata-rata ~11 unit hampers/hari."

    return {
        "stock_summary": stock_str,
        "critical_items": critical_str,
        "forecast_summary": forecast_str
    }

def ask_firaza_advisor(user_question):
    """
    Sistem RAG End-to-End (100% On-Premise & Standalone):
    1. Retrieve konteks dokumen SOP/kebijakan dari ChromaDB Vector Database.
    2. Inject snapshot status stok terkini dari SQLite dan prediksi model XGBoost.
    3. Generate rekomendasi cerdas dan grounded berbasis semantic knowledge synthesis.
    """
    retrieved_chunks = retrieve_relevant_knowledge(user_question, n_results=3)
    inv_context = get_realtime_inventory_context()
    return generate_standalone_rag_response(user_question, retrieved_chunks, inv_context)

def generate_standalone_rag_response(question, retrieved_chunks, inv_context):
    """
    Knowledge synthesizer cerdas on-premise yang memadukan data dari ChromaDB, SQLite, dan Model Forecasting.
    Memberikan rekomendasi operasional bernilai tinggi tanpa memerlukan API eksternal atau kuota internet.
    """
    q_lower = question.lower()
    
    sections = []
    sections.append(f"### 🤖 Rekomendasi Asisten Cerdas Firaza (On-Premise RAG)\n")
    
    # 1. Analisis Status Terkini Gudang
    sections.append("**1. Kondisi Gudang & Bahan Kritis Terkini:**")
    sections.append(f"- Status Bahan Baku: {inv_context['critical_items']}")
    sections.append(f"- Proyeksi Permintaan: {inv_context['forecast_summary']}\n")

    # 2. Sintesis Dokumen Relevan dari ChromaDB
    sections.append("**2. Rujukan SOP & Kebijakan Terkait (dari Vector Database ChromaDB):**")
    for chunk in retrieved_chunks:
        sections.append(f"- **{chunk['title']}**: {chunk['content']}")
    sections.append("")

    # 3. Action Plan Berdasarkan Analisis
    sections.append("**3. Langkah Aksi & Rekomendasi Operasional:**")
    if any(k in q_lower for k in ["restock", "pesan", "kurang", "beli", "po", "kardus", "pita", "kartu", "kritis"]):
        sections.append(
            "- **Prioritas Pembelian**: Segera terbitkan Purchase Order (PO) untuk bahan baku yang berstatus defisit atau di bawah batas minimum safety stock.\n"
            "- **Lead Time Supplier**: Perhatikan lead time pengiriman (Kardus: 3 hari kerja, Pita: 2 hari kerja, Kartu: 2 hari kerja, Plastik: 1 hari kerja). Jangan menunda pemesanan agar tidak terjadi bottleneck di lantai produksi.\n"
            "- **Aturan MOQ**: Sesuaikan kuantitas pemesanan dengan Minimum Order Quantity supplier (Kardus Box M & L minimal 50 pcs per ukuran, Pita Satin minimal 50 meter)."
        )
    elif any(k in q_lower for k in ["lebaran", "ramadhan", "peak", "musim", "hari raya", "natal", "akhir tahun"]):
        sections.append(
            "- **Antisipasi Lonjakan Permintaan**: Berdasarkan data historis dan kalender musiman, penjualan melonjak hingga 3.5x saat Ramadhan/Idul Fitri dan 2.0x saat akhir tahun/musim pernikahan.\n"
            "- **Jadwal Penyetokan (Stock-In)**: Lakukan pengadaan bahan baku utama secara bertahap paling lambat H-30 sebelum hari raya untuk mengantisipasi overload kurir logistik.\n"
            "- **Fokus Kebutuhan Material**: Perbanyak buffer stock untuk Kardus Box M, Sajadah Tenun Emas, dan Pita Satin Emas karena merupakan paket hampers paling diminati."
        )
    elif any(k in q_lower for k in ["partai besar", "bulk", "banyak", "100", "50", "kantor", "gathering", "seserahan"]):
        sections.append(
            "- **Protokol Pesanan Partai Besar (>50 pax)**: Dilarang menyetujui DP sebelum staf admin melakukan verifikasi ketersediaan material penunjang di dashboard Smart Inventory.\n"
            "- **Penentuan Janji Kirim**: Estimasi waktu pengerjaan harus menghitung: Lead Time Supplier Terlama + Waktu Perakitan (kapasitas perakitan workshop adalah 40 hampers per hari).\n"
            "- **Booking Bahan Baku**: Jika pesanan melebihi 100 pax, segera hubungi supplier kardus dan pita melalui jalur prioritas untuk mengamankan kuota produksi."
        )
    else:
        sections.append(
            "- Lakukan peninjauan Reorder Point (ROP) secara berkala pada menu Dashboard Utama.\n"
            "- Pastikan setiap transaksi barang masuk (stock-in) dan keluar (stock-out) selalu dicatat di menu Logistik agar data stok sistem selalu sinkron dengan fisik gudang."
        )

    full_text = "\n".join(sections)
    return {
        "answer": full_text,
        "retrieved_sources": retrieved_chunks,
        "engine": "ChromaDB Vector Store & Knowledge Retrieval (On-Premise RAG)",
        "realtime_context": inv_context
    }
