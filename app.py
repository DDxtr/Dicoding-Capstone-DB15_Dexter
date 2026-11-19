import streamlit as st
import pandas as pd
import numpy as np
import os
import json
from datetime import datetime

# Import modul internal proyek
from database import (
    init_db,
    get_materials_df,
    get_products_df,
    get_bom_df,
    get_recent_transactions_df,
    record_transaction,
    calculate_order_bom_impact
)
from forecasting import (
    load_forecasting_assets,
    get_model_metrics,
    generate_multi_day_forecast,
    calculate_material_projections
)
from order_parser import process_order_inquiry
from rag_assistant import ask_firaza_advisor, get_realtime_inventory_context

# ==========================================
# KONFIGURASI HALAMAN & STYLING
# ==========================================
st.set_page_config(
    page_title="Firaza Smart Warehouse & Inventory",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling CSS (Clean, Modern, Enterprise UMKM)
st.markdown("""
<style>
    .main {
        background-color: #f8fafc;
    }
    .metric-card {
        background: #ffffff;
        padding: 1.2rem;
        border-radius: 12px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08);
        border: 1px solid #e2e8f0;
    }
    .status-badge-safe {
        background-color: #dcfce7;
        color: #166534;
        padding: 4px 8px;
        border-radius: 6px;
        font-weight: 600;
    }
    .status-badge-warning {
        background-color: #fef9c3;
        color: #854d0e;
        padding: 4px 8px;
        border-radius: 6px;
        font-weight: 600;
    }
    .status-badge-danger {
        background-color: #fee2e2;
        color: #991b1b;
        padding: 4px 8px;
        border-radius: 6px;
        font-weight: 600;
    }
    .stButton>button {
        border-radius: 8px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# Inisialisasi Database
init_db()

# ==========================================
# SIDEBAR: NAVIGASI & KONFIGURASI AI
# ==========================================
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/package.png", width=64)
    st.title("Firaza Smart Warehouse")
    st.caption("AI-Powered Inventory & Demand Forecasting System")
    
    st.markdown("---")
    menu = st.radio(
        "🧭 Navigasi Menu:",
        [
            "📊 Dashboard Utama & Forecasting",
            "💬 Simulasi Chat & Order Parsing",
            "🤖 Asisten Cerdas Restock (RAG)",
            "📦 Logistik & Transaksi Stok",
            "⚙️ Master Data & Resep BOM"
        ]
    )

    st.markdown("---")
    st.caption(
        "**Dicoding Bootcamp Capstone Project**\n"
        "ID Tim: **DB15-I028**\n"
    )

# ==========================================
# 1. HALAMAN: DASHBOARD UTAMA & DEMAND FORECASTING
# ==========================================
if menu == "📊 Dashboard Utama & Forecasting":
    st.title("📊 Dashboard Utama & Demand Forecasting")
    st.markdown("Monitor ketersediaan inventaris material secara *real-time* dan proyeksikan kebutuhan stok menggunakan model Machine Learning **XGBoost Regressor**.")

    # Ambil data terkini
    materials_df = get_materials_df()
    
    # Proyeksi 7 hari default untuk metrik dashboard
    proj_df, forecast_df, total_pred_units = calculate_material_projections(horizon_days=7)
    
    critical_count = len(proj_df[proj_df["is_critical"] == True])
    warning_count = len(proj_df[proj_df["is_warning"] == True])
    daily_avg_pred = round(total_pred_units / 7, 1)

    # Deteksi status musim saat ini
    today = datetime.now()
    day_of_year = today.timetuple().tm_yday
    is_current_peak = (90 <= day_of_year <= 120) or (330 <= day_of_year <= 365)
    season_status = "Peak Season (Lonjakan Pesanan) 🚀" if is_current_peak else "Normal / Stable Season 🍃"

    # Baris Metrik Utama (KPI Cards)
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("📦 Jenis Material Terdaftar", f"{len(materials_df)} Material", "Tersedia di Gudang")
    col2.metric("⚠️ Status Stok Kritis", f"{critical_count} Item Kritis", f"{warning_count} Perlu Perhatian", delta_color="inverse")
    col3.metric("📈 Prediksi Permintaan (7 Hari)", f"{int(total_pred_units)} Unit", f"~{daily_avg_pred} unit/hari")
    col4.metric("🗓️ Status Siklus Musim", "Peak Season" if is_current_peak else "Reguler", season_status)

    st.markdown("---")

    # Bagian 1: Status Ketersediaan Stok Material Terkini
    st.subheader("📋 Status Kesehatan Stok Material Gudang (Real-Time)")
    st.caption("Status kesehatan dihitung secara dinamis membandingkan stok aktual terhadap Reorder Point (ROP) dan kebutuhan produksi.")

    display_cols = ["Nama Material", "Stok Saat Ini", "Proyeksi Kebutuhan (7 Hari)", "Sisa Estimasi", "Reorder Point (ROP)", "Status Kesehatan", "Rekomendasi Operasional"]
    st.dataframe(proj_df[display_cols], use_container_width=True, hide_index=True)

    st.markdown("---")

    # Bagian 2: Interactive Demand Forecasting
    st.subheader("🔮 Simulasi Proyeksi Permintaan Cerdas (AI Demand Forecast)")
    st.markdown("Pilih horizon waktu proyeksi untuk melihat estimasi lonjakan pesanan dan analisis kebutuhan material pendukung.")

    col_ctrl1, col_ctrl2 = st.columns([1, 3])
    with col_ctrl1:
        horizon_choice = st.selectbox(
            "Pilih Horizon Proyeksi Masa Depan:",
            [7, 14, 30],
            index=0,
            format_func=lambda x: f"{x} Hari ke Depan"
        )
        run_sim = st.button("🔄 Perbarui Simulasi Forecast", use_container_width=True, type="primary")

    custom_proj_df, custom_forecast_df, custom_total_units = calculate_material_projections(horizon_choice)

    # Grafik Proyeksi Permintaan
    col_chart, col_details = st.columns([2, 1])
    with col_chart:
        st.markdown(f"#### 📈 Tren Permintaan Harian ({horizon_choice} Hari ke Depan)")
        chart_data = custom_forecast_df.set_index("date")[["predicted_quantity"]]
        st.line_chart(chart_data, color="#2563eb", use_container_width=True)

    with col_details:
        st.markdown("#### 💡 Ringkasan Analisis AI")
        st.info(
            f"• **Total Prediksi Permintaan:** **{int(custom_total_units)} unit** hampers.\n\n"
            f"• **Rata-rata Permintaan:** **{round(custom_total_units/horizon_choice, 1)} unit/hari**.\n\n"
            f"• **Peak Days Terdeteksi:** {len(custom_forecast_df[custom_forecast_df['is_peak_season'] != 'Normal'])} hari.\n\n"
            f"• **Fitur Kunci:** Kalender hari raya, siklus mingguan, data *lag 7*, dan *rolling mean 7*."
        )

    # Tabel Rincian Proyeksi Kebutuhan Material
    st.markdown(f"#### 📦 Proyeksi Kebutuhan Material untuk {horizon_choice} Hari")
    custom_display_cols = ["Nama Material", "Stok Saat Ini", f"Proyeksi Kebutuhan ({horizon_choice} Hari)", "Sisa Estimasi", "Reorder Point (ROP)", "Status Kesehatan", "Rekomendasi Operasional"]
    st.dataframe(custom_proj_df[custom_display_cols], use_container_width=True, hide_index=True)

    # Evaluasi Model ML Expander
    with st.expander("🔍 Informasi & Evaluasi Model Machine Learning"):
        metrics = get_model_metrics()
        col_m1, col_m2, col_m3 = st.columns(3)
        col_m1.metric("Arsitektur Model", metrics["model_name"])
        col_m2.metric("Root Mean Squared Error (RMSE)", f"{metrics['rmse']}")
        col_m3.metric("Mean Absolute Error (MAE)", f"{metrics['mae']}")
        st.markdown("**Fitur Input Model:** `year`, `month`, `day`, `dayofweek`, `is_weekend`, `is_peak_season`, `lag_7`, `rolling_mean_7`")
        st.caption("Model dilatih menggunakan validasi time-series (chronological split) tanpa data leakage untuk memastikan generalisasi optimal pada tren musiman UMKM Firaza.")

# ==========================================
# 2. HALAMAN: SIMULASI CHAT & ORDER PARSING
# ==========================================
elif menu == "💬 Simulasi Chat & Order Parsing":
    st.title("💬 Simulasi Chat & AI Order Parsing")
    st.markdown(
        "Calon pembeli UMKM Firaza sering mengirim pertanyaan pesanan via WhatsApp dengan kalimat tidak terstruktur. "
        "Sistem AI akan mengekstrak detail pesanan, menghitung kebutuhan material berdasarkan **Bill of Materials (BOM)**, dan mendeteksi potensi *bottleneck* stok di gudang."
    )

    # Preset Contoh Chat untuk Kemudahan Evaluasi & Demo
    st.markdown("##### ⚡ Pilih Contoh Percakapan Cepat (Preset):")
    preset_cols = st.columns(3)
    preset_text = None
    if preset_cols[0].button("📝 Kasus 1: Pesanan Besar 150 Sajadah", use_container_width=True):
        preset_text = "Halo Kak Firaza, saya Ibu Rina dari panitia kantor mau pesan hampers sajadah premium sebanyak 150 pax untuk acara tasyakuran bulan depan, kira-kira keburu nggak ya?"
    if preset_cols[1].button("📝 Kasus 2: Pesanan 80 Handuk Seserahan", use_container_width=True):
        preset_text = "Kak, mau tanya hampers handuk seserahan 80 unit untuk souvenir pernikahan minggu depan apakah stok kardus L dan pitanya ready?"
    if preset_cols[2].button("📝 Kasus 3: Inquiry Santai 25 Sajadah", use_container_width=True):
        preset_text = "Permisi kak firaza, tanya dong harga hampers sajadah kalau order 25 pcs buat souvenir pengajian akhir bulan berapa ya? Apakah ada diskon?"

    default_chat = preset_text or "Halo Kak Firaza, saya mau pesan hampers sajadah untuk acara kantor bulan depan sekitar 150 pax, kira-kira keburu nggak ya?"

    col_input, col_output = st.columns(2)

    with col_input:
        st.markdown("#### 📥 Input Percakapan Klien")
        chat_input = st.text_area(
            "Teks Pesan WhatsApp dari Klien:",
            value=default_chat,
            height=180
        )
        parse_btn = st.button("🚀 Analisis Percakapan dengan AI", type="primary", use_container_width=True)

    with col_output:
        st.markdown("#### 📤 Hasil Ekstraksi AI (Structured Data)")
        if parse_btn or preset_text:
            with st.spinner("AI sedang membedah entitas percakapan..."):
                analysis_result = process_order_inquiry(chat_input)

            if analysis_result:
                parsed = analysis_result["parsed_entities"]
                st.success(f"Berhasil diekstrak oleh **{parsed.get('engine', 'AI Engine')}**!")
                
                # Format kartu entitas
                c_e1, c_e2 = st.columns(2)
                c_e1.write(f"**Pelanggan:** {parsed.get('customer_name')}")
                c_e1.write(f"**Produk:** {parsed.get('product_name')}")
                c_e1.write(f"**Jumlah Unit:** `{parsed.get('quantity')} Pax`")
                c_e2.write(f"**Tenggat Waktu:** {parsed.get('target_timeframe')}")
                c_e2.write(f"**Tingkat Intent:** {parsed.get('intent_category')}")
                c_e2.write(f"**Probabilitas Order:** `{parsed.get('probability_order')}`")

                with st.expander("Lihat Format JSON Mentah"):
                    st.json(parsed)
            else:
                st.warning("Teks percakapan kosong.")
        else:
            st.info("Klik tombol 'Analisis Percakapan dengan AI' atau gunakan preset di atas untuk mengekstrak data.")

    # Analisis Dampak BOM jika sudah diproses
    if (parse_btn or preset_text) and 'analysis_result' in locals() and analysis_result:
        st.markdown("---")
        st.subheader("🔍 Analisis Dampak Kebutuhan Material (BOM Impact)")
        
        bom_impact = analysis_result["bom_impact_df"]
        has_shortage = analysis_result["has_shortage"]
        shortage_items = analysis_result["shortage_materials"]

        # Alert Banner
        if has_shortage:
            st.error(
                f"🚨 **PERINGATAN BOTTLENECK GUDANG:**\n\n"
                f"Stok saat ini **TIDAK MENCUKUPI** untuk memenuhi pesanan **{parsed.get('quantity')} unit {parsed.get('product_name')}**!\n"
                f"Bahan baku yang mengalami defisit: **{', '.join(shortage_items)}**.\n"
                f"*SOP Tindakan: Jangan terima pembayaran/DP sebelum berkoordinasi dengan supplier material terkait waktu pengiriman!*"
            )
        else:
            st.success(
                f"✅ **KAPASITAS AMAN:** Seluruh material penunjang di gudang mencukupi untuk memenuhi pesanan **{parsed.get('quantity')} unit {parsed.get('product_name')}**."
            )

        # Tabel Dampak Material
        show_impact_cols = ["Material", "Kebutuhan Resep", "Total Dibutuhkan", "Stok Gudang", "Sisa Pasca Order", "Status", "Rekomendasi Tindakan"]
        st.dataframe(bom_impact[show_impact_cols], use_container_width=True, hide_index=True)

        # Aksi Simulasi Pengurangan Stok
        col_act1, col_act2 = st.columns([1, 2])
        with col_act1:
            if st.button("📥 Simulasikan Pengurangan Stok (Commit Order)", use_container_width=True):
                # Catat transaksi pemakaian
                prod_id = parsed.get("product_id", 1)
                bom_df = get_bom_df()
                relevant_bom = bom_df[bom_df["product_id"] == prod_id]
                for _, row in relevant_bom.iterrows():
                    m_id = row["material_id"]
                    req_qty = int(row["quantity_required"] * parsed.get("quantity", 1))
                    record_transaction("Stock-Out", m_id, req_qty, f"Pesanan {parsed.get('customer_name')} ({parsed.get('quantity')} unit)")
                st.success("Stok berhasil diperbarui di database! Kunjungi menu Dashboard Utama untuk melihat stok terkini.")

# ==========================================
# 3. HALAMAN: ASISTEN CERDAS RESTOCK (RAG SYSTEM)
# ==========================================
elif menu == "🤖 Asisten Cerdas Restock (RAG)":
    st.title("🤖 Firaza Smart Restock Advisor (RAG)")
    st.markdown(
        "Asisten cerdas berbasis **Retrieval-Augmented Generation (RAG)** yang memadukan **Vector Database ChromaDB** "
        "(berisi SOP gudang, data supplier, lead time, dan strategi musiman) dengan **data stok real-time** dari database SQLite dan **proyeksi model Machine Learning**."
    )

    # Preset Pertanyaan Konsultasi Cerdas
    st.markdown("##### 💡 Contoh Topik Pertanyaan Konsultasi:")
    q_cols = st.columns(3)
    quick_q = None
    if q_cols[0].button("🛒 Kapan dan berapa banyak harus restock kardus?", use_container_width=True):
        quick_q = "Kapan saya harus restock kardus dan berapa lead time serta minimum ordernya?"
    if q_cols[1].button("🚀 Bagaimana strategi restock menghadapi Ramadhan?", use_container_width=True):
        quick_q = "Bagaimana strategi penyetokan bahan baku menjelang peak season Ramadhan dan Idul Fitri?"
    if q_cols[2].button("🚨 Apa yang harus dilakukan jika ada order >100 pax?", use_container_width=True):
        quick_q = "Apa SOP jika ada calon pembeli yang ingin memesan pesanan partai besar di atas 100 pax?"

    user_question = st.text_input(
        "Ajukan pertanyaan seputar inventaris, restock, atau kebijakan gudang:",
        value=quick_q or "Bahan baku apa saja yang kritis saat ini dan bagaimana rekomendasi tindakan pembeliannya?",
        help="Asisten akan mencari dokumen SOP terkait di ChromaDB dan membaca status stok langsung dari database."
    )

    ask_btn = st.button("💬 Konsultasikan dengan AI Advisor", type="primary")

    if ask_btn or quick_q:
        with st.spinner("Mengakses Vector Database ChromaDB & menganalisis status inventaris..."):
            rag_output = ask_firaza_advisor(user_question)

        st.markdown("### 📋 Rekomendasi Asisten Cerdas")
        st.markdown(rag_output["answer"])

        # Tampilkan Metadata Sumber RAG
        st.markdown("---")
        col_r1, col_r2 = st.columns(2)
        with col_r1:
            with st.expander("📚 Dokumen Referensi dari ChromaDB (Knowledge Base)"):
                for src in rag_output.get("retrieved_sources", []):
                    st.markdown(f"**• {src['title']}** (`{src['category']}`)")
                    st.caption(src["content"])
        with col_r2:
            with st.expander("📦 Status Konteks Gudang yang Disuntikkan (Real-Time Injected Context)"):
                st.text(rag_output["realtime_context"]["stock_summary"])
                st.caption(rag_output["realtime_context"]["forecast_summary"])

# ==========================================
# 4. HALAMAN: LOGISTIK & TRANSAKSI STOK
# ==========================================
elif menu == "📦 Logistik & Transaksi Stok":
    st.title("📦 Logistik & Pencatatan Transaksi Stok")
    st.markdown("Catat transaksi fisik harian (*Stock-In*, *Stock-Out*, atau *Stock Opname*) langsung ke database SQLite.")

    col_form, col_history = st.columns([1, 1])

    with col_form:
        st.subheader("📝 Input Form Transaksi")
        materials_df = get_materials_df()
        material_options = {row["material_name"]: row["material_id"] for _, row in materials_df.iterrows()}

        with st.form("trans_form", clear_on_submit=True):
            trans_type = st.selectbox(
                "Jenis Transaksi:",
                ["Stock-In (Penerimaan Barang / Restock)", "Stock-Out (Pemakaian Produksi / Keluar)", "Stock Opname (Penyesuaian Fisik Gudang)"]
            )
            selected_mat_name = st.selectbox("Pilih Material:", list(material_options.keys()))
            quantity = st.number_input("Jumlah Kuantitas (Unit / Meter / Pcs):", min_value=1, value=50, step=1)
            notes = st.text_input("Catatan / Keterangan Transaksi:", "Contoh: Penerimaan restock dari PT Kartona")

            submit_trans = st.form_submit_button("💾 Simpan Transaksi ke Database", use_container_width=True, type="primary")

            if submit_trans:
                mat_id = material_options[selected_mat_name]
                try:
                    res = record_transaction(trans_type, mat_id, quantity, notes)
                    st.success(
                        f"Berhasil mencatat transaksi!\n"
                        f"- Material: **{res['material_name']}**\n"
                        f"- Stok Lama: **{res['old_stock']}** -> Stok Baru: **{res['new_stock']}**"
                    )
                except Exception as e:
                    st.error(f"Gagal mencatat transaksi: {e}")

    with col_history:
        st.subheader("📜 Riwayat Transaksi Terkini")
        recent_trx = get_recent_transactions_df(limit=15)
        st.dataframe(recent_trx, use_container_width=True, hide_index=True)

# ==========================================
# 5. HALAMAN: MASTER DATA & RESEP BOM
# ==========================================
elif menu == "⚙️ Master Data & Resep BOM":
    st.title("⚙️ Master Data & Bill of Materials (BOM)")
    st.markdown("Daftar master produk hampers jadi dan resep komponen material dasar pendukung kemasan.")

    tab_mat, tab_prod, tab_bom = st.tabs(["📦 Master Material", "🎁 Master Produk Hampers", "🧾 Resep Bill of Materials (BOM)"])

    with tab_mat:
        st.subheader("Master Material Penunjang Packaging")
        mat_df = get_materials_df()
        st.dataframe(mat_df, use_container_width=True, hide_index=True)

    with tab_prod:
        st.subheader("Master Produk Hampers Firaza")
        prod_df = get_products_df()
        st.dataframe(prod_df, use_container_width=True, hide_index=True)

    with tab_bom:
        st.subheader("Resep Bill of Materials (BOM)")
        st.caption("Menunjukkan berapa banyak masing-masing material yang dibutuhkan untuk memproduksi 1 unit hampers jadi.")
        bom_df = get_bom_df()
        st.dataframe(bom_df[["product_name", "material_name", "quantity_required", "unit"]], use_container_width=True, hide_index=True)
