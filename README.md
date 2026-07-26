# Dataklin (dataqc)

AI-Powered Data Quality & Entity Resolution Platform — implementasi MVP (Fase 1) dari
[PRD_DataQuality_SaaS.docx](PRD_DataQuality_SaaS.docx).

Dataklin dipakai **data engineer untuk menyiapkan data** sebelum diserahkan ke role data lain
(data scientist, analyst, dsb) — mengurangi beban data preparation di hilir dengan memastikan
data yang di-serve sudah terprofilkan, tervalidasi, terdedup, dan konsisten formatnya.

## Fitur MVP yang sudah diimplementasikan

| Fitur | Status |
|---|---|
| F1 Upload Dataset (CSV/XLSX) — deteksi delimiter/encoding/tipe otomatis | ✅ |
| F2 Automated Data Profiling — statistik per kolom + skor 0-100 | ✅ |
| F3 Rule Engine — email, HP Indonesia, NIK, tanggal, rentang angka, regex, antar kolom | ✅ |
| F4 NL Rule Generation (LLM) — bahasa natural → rule terstruktur, dengan review user | ✅* |
| F4 Auto-Suggest Rule dari Skema (LLM) — saran proaktif tanpa instruksi, dengan review user | ✅* |
| Referential Integrity Check — deteksi FK terputus antar dua dataset, on-demand | ✅ |
| Consistency Check antar sistem — bandingkan nilai untuk kunci yang sama di dua dataset | ✅ |
| F5 Entity Resolution — blocking key + fuzzy match (rapidfuzz) → union-find cluster | ✅ |
| F6 Human Review Queue per cluster — konfirmasi / split / keluarkan record / gabung | ✅ |
| Cluster Cohesion Scoring | ✅ |
| F7 Golden Record dasar — survivorship "update terbaru menang" + audit trail | ✅ |
| F8 Anomaly/Outlier Detection — IQR + z-score per kolom numerik, dengan penjelasan | ✅ |
| Standardization & Parsing — normalisasi HP/email/nama/alamat/tanggal + preview/apply | ✅ |
| Survivorship Rule Configurable per kolom (F7) — dengan pratinjau live per cluster | ✅ |
| Clean Dataset Export — standardisasi + dedup collapse ke golden record, siap konsumsi | ✅ |
| Data Dictionary Export — skema & statistik profiling + rule aktif per kolom (CSV) | ✅ |
| API Key per Organisasi — akses programatik ke data tanpa login JWT (backlog #28) | ✅ |
| PII Detection & Masking — deteksi NIK/HP/email/nama/alamat + opsi mask saat export (F11) | ✅ |
| Drift Monitoring & Alerting Terjadwal — re-validasi otomatis + alert drift skor (F10) | ✅ |
| Notifikasi Multi-Channel — Email/Slack/Webhook otomatis saat alert & proses selesai | ✅ |
| Koneksi Database Langsung — PostgreSQL/MySQL sebagai sumber dataset selain upload | ✅ |
| Timeliness/Freshness Check — dimensi skor + alert keterlambatan jadwal pemantauan | ✅ |
| F9 Scorecard & Export PDF/CSV | ✅ |
| Dashboard & Ringkasan | ✅ |
| Autentikasi JWT + role admin/analyst/viewer | ✅ |
| Histori skor + alert threshold (dasar monitoring) | ✅ |

\* F4 butuh LLM gateway dikonfigurasi di `.env` (lihat bagian Konfigurasi LLM); tanpa itu
tombol AI menampilkan status nonaktif secara graceful.

Fitur lanjutan lain (drift alerting multi-channel, PII masking, survivorship configurable,
dsb) didokumentasikan di [docs/ENHANCEMENTS.md](docs/ENHANCEMENTS.md).

## Arsitektur

Sesuai `Architecture_Diagram.svg`:

- **frontend** — Next.js 14 (App Router), 6 layar sesuai `Wireframes.html`
- **backend** — FastAPI (REST API, OAuth2/JWT)
- **worker** — RQ worker async (profiling, rule engine, entity resolution, scoring)
- **postgres** — PostgreSQL 16 + pgvector (metadata, rule, cluster, skor)
- **redis** — queue broker
- **minio** — object storage S3-compatible (file mentah)
- **scheduler** — `rqscheduler`, memoles jadwal drift monitoring per dataset & meng-enqueue
  job ke worker saat waktunya tiba
- **mailhog** — SMTP server dev untuk uji notifikasi email tanpa provider asli

## Menjalankan

Prasyarat: Docker Desktop.

```bash
cp .env.example .env        # sesuaikan JWT_SECRET dll bila perlu
docker compose up --build
```

Lalu buka:

- Aplikasi: http://localhost:3000 — login `admin@dataklin.local` / `admin123`
- API docs (Swagger): http://localhost:8000/docs
- MinIO console: http://localhost:9011 (`minioadmin`/`minioadmin`)
- Mailhog (inbox email dev): http://localhost:8025

Coba upload [samples/customers_sample.csv](samples/customers_sample.csv) — berisi data pelanggan
dummy Indonesia dengan 4 kelompok duplikat non-eksak (termasuk cluster 3-record "Siti Nur Aini"
seperti contoh di wireframe), nomor HP tak standar, email invalid, tanggal di luar rentang,
satu outlier numerik ekstrem (`total_belanja_juta` = 950), dan satu baris yang melanggar rule
antar kolom (`tanggal_update` sebelum `tanggal_lahir`).

## Deployment produksi (ringan)

`docker compose up` di atas menjalankan mode **development** (`next dev`, `uvicorn
--reload`) — cocok untuk kerja lokal tapi boros dibanding kebutuhan sebenarnya. Untuk
produksi, pakai override `docker-compose.prod.yml` (production build, tanpa hot-reload,
tanpa Mailhog):

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build \
  backend worker scheduler frontend postgres redis minio
```

**Kebutuhan resource** (diukur langsung dari stack ini saat idle: ~400MB total untuk
8 service — jauh lebih ringan dari perkiraan kasar berbasis skenario terburuk):

| Skala | Spesifikasi | Estimasi biaya/bulan |
|---|---|---|
| Validasi awal (±10 organisasi) | 2 vCPU, 4GB RAM, 40GB SSD | ~$10–24 (Hetzner/DigitalOcean/Linode) |
| Traksi bertambah / dataset besar rutin | 4 vCPU, 8GB RAM, worker discale terpisah | ~$40–80 |

Komponen yang paling menentukan kebutuhan RAM adalah **worker** — memuat seluruh dataset
ke memori untuk profiling & entity resolution. Selama dataset harian tidak rutin
mendekati batas MVP (1 juta baris, lihat NFR di PRD), 4GB total sudah nyaman; sisakan
headroom lebih untuk dataset yang jauh lebih besar atau volume upload bersamaan yang tinggi.
Untuk produksi sungguhan: ganti MinIO dengan S3 asli, SMTP asli (bukan Mailhog), dan
`JWT_SECRET`/`ENCRYPTION_KEY` yang baru (lihat `.env.example`).

## Alur pemrosesan (sesuai Data_Flow_Diagram.svg)

1. Upload → file mentah disimpan ke MinIO, job masuk Redis queue
2. Worker: ingestion & parsing (deteksi delimiter/encoding)
3. Profiling per kolom (completeness, uniqueness, konsistensi pola)
4. Rule bawaan otomatis terpasang berdasar nama kolom (email/HP/NIK/tanggal lahir) lalu dieksekusi
5. Entity resolution: blocking (HP/email/nama) → skor pairwise → union-find → cluster + cohesion
6. Review manusia per cluster di UI (konfirmasi / split / keluarkan / gabung)
7. Konfirmasi cluster → golden record + provenance + audit trail
8. Skor kualitas per dimensi tersimpan ke histori; alert dibuat bila di bawah threshold
9. Scorecard dapat diexport PDF/CSV

## Akses programatik (API key)

Untuk pipeline data scientist/analyst yang perlu menarik data tanpa login interaktif: buka
halaman **Integrasi API** di UI, buat key baru (kunci lengkap hanya ditampilkan sekali), lalu
kirim sebagai header `X-API-Key` ke endpoint konsumsi data:

```bash
curl -H "X-API-Key: vd_xxxxx" http://localhost:8000/datasets/1/clean.csv -o clean.csv
curl -H "X-API-Key: vd_xxxxx" http://localhost:8000/datasets/1/dictionary.csv -o dictionary.csv
```

API key hanya berlaku untuk endpoint baca/export (`/datasets`, `clean.csv`, `dictionary.csv`,
`scorecard`, `history`, `anomalies`, dsb). Endpoint yang mengubah data (upload, konfirmasi
cluster, dll.) tetap mewajibkan login JWT agar audit trail selalu mencatat nama pengguna asli.

## Konfigurasi LLM (opsional)

Layer AI dibuat provider-agnostic (format OpenAI-compatible). Isi di `.env`:

```
LLM_BASE_URL=https://gateway-anda.example.com/v1
LLM_API_KEY=...
LLM_MODEL=...
```

Tanpa konfigurasi ini fitur AI nonaktif secara graceful. Fitur NL rule generation memakai
layer ini — lihat `backend/app/services/llm.py` dan docs/ENHANCEMENTS.md.

## Struktur proyek

```
backend/
  app/
    main.py            # FastAPI app, seed admin, startup, migrasi ringan
    config.py          # semua env settings
    models.py          # entity sesuai PRD bab 9 + ApiKey, DataConnection
    security.py        # JWT + API key (Actor/get_org_reader) + require_writer
    routers/           # auth, datasets, rules, clusters, scorecard, monitoring,
                       # api_keys, connections
    services/          # loader, profiling, rule_engine, entity_resolution,
                       # scoring, golden_record, standardization, anomaly, pii,
                       # clean_export, db_connector, notifier, storage, llm
    worker/            # RQ tasks (process_dataset, rerun_rules, refresh_dataset,
                       # refresh_from_database) + scheduler.py (rq-scheduler)
frontend/
  app/                 # dashboard, upload (file + koneksi database), dataset
                       # detail, rules, review (+detail), golden, monitoring,
                       # settings/api-keys, settings/connections
docs/ENHANCEMENTS.md   # backlog fitur Should/Could Fase 1-3 + catatan bug ditemukan
samples/               # data uji
```
