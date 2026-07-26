# User Flow / User Journey Map

> Alur langkah demi langkah yang dilalui user untuk mencapai tujuannya di dalam produk Veridata, direvisi untuk melampaui UX Xeratic LinkR.

## Flow Utama: End-to-End Data Quality Pipeline

Sesuai feedback UX terbaru, flow Veridata harus lebih modular dan logis layaknya SaaS Data Quality enterprise modern. Kita memisahkan antara **Data Sources** (Koneksi), **Configurations** (Rules & Job Settings), dan **Results** (Hasil proses).

### Aktor
- **Data Engineer / Ops Analyst**: Membuat koneksi, mengatur rule, dan memantau pipeline.
- **Data Steward**: Meninjau (review) anomali dan duplikat.

### Precondition
- User sudah login ke dashboard Veridata.

### Langkah-langkah (The "New" Flow)

**1. Membuat Sumber Data (Data Sources / Ingestion)**
1. User masuk ke tab `Data Sources` (Koneksi).
2. User bisa memilih: `Upload File (CSV/Excel)` ATAU `Connect Database` (Postgres, MySQL, Snowflake, dll).
3. Setelah dibuat, sumber data ini tersimpan sebagai "aset" yang bisa dipakai berulang kali. (Berbeda dengan sistem lama yang mana upload langsung memicu pemrosesan tanpa config terpisah).

**2. Membuat Konfigurasi (Pipeline / Job Config)**
1. User masuk ke tab `Configurations` atau `Pipelines`.
2. User membuat config baru dan memilih *Data Source* yang sudah dibuat di langkah 1.
3. Di dalam Config ini, user mengatur:
   - **Data Profiling**: Nyala/Mati
   - **Validation Rules**: Memilih atau membuat rule via AI (Rule Builder).
   - **Entity Resolution (Deduplication)**: Mengatur kolom apa yang dipakai untuk blocking/matching dan batas skor.
   - **Scheduling**: Mengatur seberapa sering job ini dijalankan (Hourly, Daily, dll).
   - **Alerting**: Siapa yang dihubungi jika terjadi anomali/drift.
4. User menyimpan Config dan menekan `Run Now` (atau menunggu jadwal).

**3. Melihat Hasil (Results & Stewarding)**
1. Job berjalan di *background*. Setelah selesai, user masuk ke tab `Runs` atau `Results`.
2. User memilih hasil eksekusi dari Config/Pipeline tertentu.
3. Di dalam halaman Hasil:
   - User melihat **Scorecard & Profiling** (Statistik data).
   - User melihat **Anomalies / Rule Violations** (Data yang kotor).
   - User masuk ke **Stewarding / Review Queue** untuk meninjau duplikat (Side-by-side diff view) dan menyetujui *Golden Record*.
4. Setelah *Golden Record* disetujui, data siap di-ekspor atau di-push balik via *Write-back Pipeline*.

### Diagram Flow (Pipeline-Based)
```
[Data Sources] 
      |
      v
[Configurations / Pipelines] ---> (Setup Rules, Deduplication, Schedule)
      |
      +---> (Klik Run / Auto-schedule)
      |
      v
[Runs / Results] ---> [Scorecard]
      |
      +-------------> [Stewarding (Review Anomalies & Duplicates)]
      |
      +-------------> [Golden Record Output / Write-back]
```

### Edge Case Terkait
- Jika skema tabel sumber berubah drastis (Data Contract Violation), eksekusi Pipeline digagalkan, Alert dikirim, dan Job ditandai `Failed`.
