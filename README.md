# Firaza Smart Warehouse & Demand Forecasting System

**ID Tim Capstone:** `DB15-I028`  
**Tema:** Firaza: Smart Warehouse & Inventory Management  

---

## Ringkasan Eksekutif & Latar Belakang Masalah

**UMKM Firaza** bergerak di bidang penjualan *personalized hampers* dan bingkisan eksklusif (retail maupun *batched order*) dengan produk utama berupa **Hampers Sajadah Premium** dan **Hampers Handuk Seserahan**. Selain produk jadi, keberlangsungan operasional dan ketepatan waktu pengiriman sangat bergantung pada ketersediaan material penunjang kemasan (*packaging*), seperti **Kardus Box Ukuran M & L, Pita Emas Satin, Greeting Card Eksklusif, dan Plastik Wrapping**.

### Permasalahan Operasional:
1. **Pencatatan Manual & Tidak Terjadwal:** Pencatatan stok material masih dilakukan secara manual dan terpisah, sehingga sering terjadi ketidaksesuaian antara stok aktual di gudang dengan catatan pesanan masuk.
2. **Bottleneck saat Pesanan Partai Besar (*Batched Order*):** Ketika ada pesanan korporat atau pesanan dalam jumlah besar (50–150 pax), kekurangan stok material penunjang baru disadari di tengah proses perakitan (*fulfillment bottleneck*).
3. **Fluktuasi Permintaan Musiman (*Peak Season*):** Penjualan hampers sangat dipengaruhi oleh hari raya keagamaan (Ramadhan & Idul Fitri) dan musim pernikahan/akhir tahun, yang sering kali melonjak 2x hingga 3.5x lipat dari penjualan reguler.

---

## Solusi yang Dibangun

Aplikasi web terintegrasi berbasis **Streamlit** dengan arsitektur **Dual-Engine AI**:
1. **Supervised Machine Learning:**
   - Model **XGBoost Regressor** untuk *Demand Forecasting* harian dan multi-hari ke depan (7, 14, 30 hari).
   - Memproyeksikan kebutuhan masing-masing material pendukung secara otomatis berdasarkan kalkulasi **Bill of Materials (BOM)** dan **Reorder Point (ROP)**.
2. **Local Semantic NLP Order Parsing:**
   - Mengekstrak pesan chat konsultasi pelanggan yang tidak terstruktur (*unstructured text* dari WhatsApp) menjadi entitas pesanan terstruktur (nama pelanggan, produk, jumlah, tenggat waktu, tingkat *intent*, dan probabilitas order).
   - Berjalan 100% *on-premise* menggunakan *Deterministic Semantic NLP Engine* tanpa memerlukan dependensi API pihak ketiga.
   - Melakukan *real-time bottleneck detection* terhadap stok gudang.
3. **RAG System - Retrieval-Augmented Generation:**
   - Asisten cerdas penunjang keputusan restock (**Firaza Smart Restock Advisor**).
   - Menggunakan **ChromaDB Vector Database** yang menyimpan basis pengetahuan operasional UMKM Firaza (SOP buffer stock, lead time supplier, MOQ, kalender musiman, dan protokol bulk order).
   - Menyuntikkan status stok terkini dari database **SQLite** dan tren model ML langsung ke dalam sistem sintesis pengetahuan lokal untuk memberikan rekomendasi operasional yang *grounded*, presisi, dan dapat ditindaklanjuti (*actionable*).

---

## Arsitektur Sistem

```
                      +---------------------------------------+
                      |          Antarmuka Pengguna           |
                      |       (Streamlit Web Dashboard)       |
                      +-------------------+-------------------+
                                          |
        +---------------------------------+---------------------------------+
        |                                 |                                 |
        v                                 v                                 v
+---------------+                +----------------+                +-----------------+
| Modul Transaksi|                | Demand Forecast|                | GenAI Chat Parse|
|  & Logistik   |                |  (XGBoost ML)  |                |  & RAG Advisor  |
+-------+-------+                +--------+-------+                +--------+--------+
        |                                 |                                 |
        v                                 v                                 v
+---------------+                +----------------+                +-----------------+
| SQLite Database| <============== | BOM Projection | <============== | ChromaDB Vector |
| (smart_inv.db)|    Kalkulasi   |   Calculator   |    Retrieval    | Store & Gemini  |
+---------------+    Material    +----------------+   Knowledge     +-----------------+
```

---

## Spesifikasi Model & Pipeline Data

### 1. Dataset Sintetis (`synthetic_dataset.py`)
- Mencakup 731 hari data penjualan harian (2 tahun: 2024–2025) untuk produk Hampers Sajadah dan Hampers Handuk.
- Memodelkan distribusi Poisson harian dengan pengali musiman (*seasonal multiplier*):
  - **Ramadhan / Idul Fitri (Maret–April):** Pengali $3.5\times$.
  - **Akhir Tahun / Wedding Season (Nov–Des):** Pengali $2.0\times$.
  - **Akhir Pekan (Sabtu–Minggu):** Pengali $1.3\times$.

### 2. Rekayasa Fitur (`Data Preparation and Feature Engineering.py`)
- **Fitur Kalender:** `year`, `month`, `day`, `dayofweek`, `is_weekend`, `day_of_year`.
- **Fitur Musim:** `is_peak_season` (penanda jendela hari ke-90 s.d. 120 dan 330 s.d. 365).
- **Fitur Time-Series (Lag & Rolling):** `lag_7` (penjualan 7 hari sebelumnya) dan `rolling_mean_7` (rata-rata bergerak 7 hari).

### 3. Evaluasi Model Machine Learning (`train_model.py`)
- **Algoritma:** XGBoost Regressor (`n_estimators=200`, `learning_rate=0.05`, `max_depth=5`, `subsample=0.8`).
- **Skema Validasi:** *Chronological Time-Series Split* (80% latih, 20% uji) tanpa data leakage.
- **Hasil Metrik Evaluasi:**
  - **RMSE (Root Mean Squared Error):** `2.4718`
  - **MAE (Mean Absolute Error):** `1.8532`

---

## Struktur Direktori Proyek

```
GitHub Repository/
├── .streamlit/
│   └── config.toml             # Konfigurasi tema & server Streamlit
├── app.py                      # Aplikasi utama dashboard Streamlit
├── database.py                 # Modul koneksi & CRUD database SQLite
├── forecasting.py              # Layanan autoregressive demand forecasting
├── order_parser.py             # Parser pesan chat klien (Heuristic NLP)
├── rag_assistant.py            # Sistem RAG 
├── Data Base.py                # Skrip standalone pembuat skema database
├── synthetic_dataset.py        # Pembuat dataset penjualan historis realistis
├── Data Preparation and Feature Engineering.py # rekayasa fitur data
├── train_model.py              # Pelatihan & evaluasi model XGBoost
├── demand_forecast_model.pkl   # Model XGBoost terlatih (Joblib)
├── historical_sales.csv        # Data penjualan historis
├── processed_dataset.csv       # Dataset hasil feature engineering
├── smart_inventory.db          # Database SQLite operasional
├── requirements.txt            # Dependensi paket Python
└── README.md                   # Dokumentasi resmi repositori
```

---

## Panduan Menjalankan Aplikasi Secara Lokal

### Prasyarat
- Python versi 3.10 s.d. 3.13 terpasang di komputer.
- Git terpasang di komputer.

### Langkah Instalasi:

1. **Clone Repositori:**
   ```bash
   git clone https://github.com/dextergunawan/Dicoding-Capstone-DB15_Dexter.git
   cd "Dicoding-Capstone-DB15_Dexter/GitHub Repository"
   ```

2. **Buat dan Aktifkan Virtual Environment:**
   - **Windows:**
     ```bash
     python -m venv venv
     .\venv\Scripts\activate
     ```
   - **Linux / macOS:**
     ```bash
     python3 -m venv venv
     source venv/bin/activate
     ```

3. **Install Dependensi:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Jalankan Aplikasi Streamlit:**
   ```bash
   python -m streamlit run app.py
   ```
   *(atau `streamlit run app.py` jika folder Python Scripts sudah terdaftar di PATH).*
   Aplikasi akan terbuka otomatis di peramban pada alamat `http://localhost:8501`.

---


## Sitasi & Referensi Pustaka

Proyek ini menghormati hak cipta dan lisensi terbuka dengan menggunakan pustaka resmi:
1. **Streamlit:** *The fastest way to build and share data apps* (Apache-2.0 License).
2. **XGBoost:** Chen, T., & Guestrin, C. (2016). *XGBoost: A Scalable Tree Boosting System*. In KDD '16 (Apache-2.0 License).
3. **Scikit-Learn:** Pedregosa et al. (2011). *Scikit-learn: Machine Learning in Python*. JMLR 12 (BSD License).
4. **ChromaDB:** Chroma, Inc. *The AI-native open-source embedding database* (Apache-2.0 License).
5. **Pandas & NumPy:** Wes McKinney (2010) / Charles R. Harris et al. (2020) (BSD-3-Clause License).
