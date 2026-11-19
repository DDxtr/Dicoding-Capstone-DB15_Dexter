import re
from database import calculate_order_bom_impact, get_products_df

"""
Modul AI Order Parsing (On-Premise / Standalone)
Mengekstrak pesan percakapan chat WhatsApp pelanggan (unstructured text)
menjadi data pesanan terstruktur (structured JSON) secara lokal tanpa dependensi API eksternal.
"""

def extract_order_entities(text):
    """
    Ekstraksi cerdas berbasis pemrosesan bahasa alami (NLP) lokal untuk percakapan pesanan hampers.
    Mendeteksi kuantitas, produk, batas waktu, intent pemesanan, dan nama pelanggan secara deterministik.
    """
    text_lower = text.lower()

    # 1. Deteksi Kuantitas (pax, pcs, biji, buah, unit, hampers, box, atau angka berdiri sendiri)
    qty = 50  # default
    qty_patterns = [
        r'(\d+)\s*(?:pax|pcs|buah|biji|box|kotak|unit|hampers|paket|set)',
        r'(?:pesan|order|sebanyak|butuh|butuhin|buat|minta)\s*(\d+)',
        r'(\d+)\s*(?:an|an\s*pax|an\s*box)?'
    ]
    for pattern in qty_patterns:
        match = re.search(pattern, text_lower)
        if match:
            found_qty = int(match.group(1))
            if 1 <= found_qty <= 10000:
                qty = found_qty
                break

    # 2. Deteksi Produk
    if "sajadah" in text_lower:
        product_name = "Hampers Sajadah Premium"
        product_id = 1
    elif "handuk" in text_lower:
        product_name = "Hampers Handuk Seserahan"
        product_id = 2
    else:
        # Default produk utama
        product_name = "Hampers Sajadah Premium"
        product_id = 1

    # 3. Deteksi Waktu / Tenggat
    timeframe = "Segera / Belum Ditentukan"
    time_matches = [
        ("bulan depan", "Bulan Depan"),
        ("minggu depan", "Minggu Depan"),
        ("akhir bulan", "Akhir Bulan Ini"),
        ("lusa", "Lusa (Sangat Mendesak)"),
        ("lebaran", "Menjelang Idul Fitri / Lebaran"),
        ("natal", "Menjelang Akhir Tahun / Natal"),
        ("hari raya", "Musim Hari Raya"),
        ("acara kantor", "Acara Gathering / Kantor"),
        ("pernikahan", "Acara Seserahan / Wedding"),
        ("souvenir", "Souvenir Event")
    ]
    for kw, label in time_matches:
        if kw in text_lower:
            timeframe = label
            break

    # 4. Deteksi Intent & Probabilitas Pemesanan
    high_intent_kws = ["mau pesan", "mau order", "transfer", "dp", "keburu", "fix", "kirim invoice", "invoice", "deal", "ambil"]
    med_intent_kws = ["tanya", "berapa", "apakah bisa", "kira-kira", "diskon", "katalog", "price list", "ready"]

    if any(k in text_lower for k in high_intent_kws):
        intent = "High Intent (Siap Transaksi / Konfirmasi Pemesanan)"
        prob_pct = 90
        urgency = "Tinggi"
    elif any(k in text_lower for k in med_intent_kws):
        intent = "Medium Intent (Konsultasi Harga & Ketersediaan)"
        prob_pct = 70
        urgency = "Sedang"
    else:
        intent = "Exploration / Inquiry Umum"
        prob_pct = 50
        urgency = "Normal"

    # 5. Ekstraksi Nama Pelanggan
    customer_name = "Calon Klien UMKM"
    name_patterns = [
        r'(?:dari|atas nama|nama saya)\s+([A-Za-z0-9\s]{2,25})',
        r'(?:halo kak firaza,? saya)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b(?!\s+(?:mau|ingin|butuh|tanya|pesan|order|bisa))'
    ]
    for np in name_patterns:
        match = re.search(np, text, re.IGNORECASE)
        if match:
            candidate = match.group(1).strip()
            if not any(stop in candidate.lower() for stop in ["mau", "ingin", "pesan", "order", "tanya"]):
                customer_name = candidate
                break

    return {
        "customer_name": customer_name,
        "product_name": product_name,
        "product_id": product_id,
        "quantity": qty,
        "target_timeframe": timeframe,
        "intent_category": intent,
        "probability_order": f"{prob_pct}%",
        "urgency": urgency,
        "raw_text": text,
        "engine": "Local Semantic NLP Engine (On-Premise)"
    }

def process_order_inquiry(chat_text):
    """
    Fungsi utama: Memproses teks chat pelanggan, mengekstrak data order terstruktur,
    dan menghitung dampaknya secara otomatis terhadap stok gudang berbasis Bill of Materials (BOM).
    """
    if not chat_text or not chat_text.strip():
        return None

    # Ekstraksi entitas menggunakan engine NLP lokal
    parsed = extract_order_entities(chat_text)

    # Hitung dampak BOM ke database SQLite
    product_id = parsed.get("product_id", 1)
    qty = parsed.get("quantity", 50)
    bom_impact_df, has_shortage = calculate_order_bom_impact(product_id, qty)

    # Identifikasi material kritis
    shortage_materials = []
    if has_shortage:
        critical_rows = bom_impact_df[bom_impact_df["is_shortage"] == True]
        shortage_materials = critical_rows["Material"].tolist()

    return {
        "parsed_entities": parsed,
        "bom_impact_df": bom_impact_df,
        "has_shortage": has_shortage,
        "shortage_materials": shortage_materials,
        "summary": {
            "target_product": parsed.get("product_name"),
            "order_qty": qty,
            "status_fulfillment": "🚨 BOTTLENECK TERDETEKSI" if has_shortage else "✅ SIAP DIPRODUKSI"
        }
    }
