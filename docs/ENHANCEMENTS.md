# Dataklin — Enhancement Backlog

Fitur di luar build MVP pertama, diurutkan dari backlog `Feature_Backlog.xlsx` (prioritas
MoSCoW). Build pertama mencakup seluruh item **Must Fase 1** + golden record dasar. Dokumen ini
mencatat sisanya beserta arahan implementasi di codebase yang sudah ada.

## Sudah diimplementasikan (update 12 Juli 2026)

- ✅ **NL Rule Generation (LLM)** — backlog #8, F4. Endpoint
  `POST /datasets/{id}/rules/generate` + UI di Rule Builder. Proposal divalidasi terhadap
  `RULE_TYPES` & daftar kolom, user meninjau sebelum aktif (source="ai"). Butuh
  `LLM_BASE_URL`/`LLM_API_KEY`/`LLM_MODEL`; tanpa itu graceful 503 + tombol nonaktif.
- ✅ **Anomaly / Outlier Detection** — backlog #20, F8. `services/anomaly.py` (IQR 1.5× +
  z-score>3, skip kolom identitas), tabel `anomalies`, panel di halaman detail dataset.
- ✅ **Custom Business Rule antar kolom** — backlog #7. `rule_type="cross_column"` dengan
  params `{left, op, right}` (op: > >= < <= == !=); baris tak terbandingkan dilewati.
- ✅ **Standardization & Parsing** — backlog #4. `services/standardization.py`: normalisasi
  HP (+62/strip-0 → 08x), email lowercase, nama/alamat (spasi, kapitalisasi, singkatan
  Jl./No./RT/RW), tanggal → ISO, kolom ID float → integer. Alur: preview perubahan →
  unduh CSV bersih → atau `standardize/apply` membuat dataset baru yang diproses ulang penuh.

Seluruh item Should Fase 1 selesai.

- ✅ **Drift Monitoring & Alerting Terjadwal** — backlog #22, F10. Dua bagian:
  1. *Alert berbasis drift* (`worker/tasks.py: _check_and_alert`) — selain threshold
     statis (`skor_rendah`), sekarang membandingkan skor & completeness run ini vs
     `QualityScoreHistory` run SEBELUMNYA untuk dataset yang sama; drop skor >= 10 poin
     → alert `drift_skor`, drop completeness >= 10 poin → alert `kolom_kosong_naik`
     (persis sesuai jenis alert di wireframe layar 6). Berlaku di `process_dataset`
     maupun `rerun_rules` (sebelumnya `rerun_rules` tidak membuat alert sama sekali —
     celah yang ikut ditutup).
  2. *Penjadwalan nyata* — `worker/scheduler.py` + `rq-scheduler` + service Docker baru
     `scheduler` (`rqscheduler`). Endpoint `PUT /datasets/{id}/monitoring
     {enabled, interval_minutes}` mendaftarkan job berulang yang memanggil
     `worker/tasks.refresh_dataset` — dispatcher source-aware (lihat item Koneksi Database
     di bawah): untuk dataset upload cukup re-validasi (`rerun_rules`); untuk dataset dari
     koneksi database, tarik ulang data terbaru dulu baru diproses penuh. UI toggle di
     halaman Monitoring.
- ✅ **Notifikasi Multi-Channel Email/Slack/Webhook** — backlog #29 (+ bagian akhir #28).
  `services/notifier.py`: setiap channel independen & gagal senyap (log saja, tidak
  menggagalkan pipeline); channel kosong dilewati graceful. Dipicu otomatis saat `Alert`
  dibuat (termasuk `drift_skor`/`kolom_kosong_naik` yang baru) dan saat dataset selesai
  diproses (sukses maupun gagal) — payload webhook generik berisi `event`, alert/dataset
  detail, siap dikonsumsi pipeline eksternal. Pengaturan per-organisasi (bukan env) di
  `PUT /settings/notifications`, endpoint `POST /settings/notifications/test` melaporkan
  status per-channel JUJUR (bukan asal "sent: true" — lihat catatan bug di bawah). SMTP
  lokal dev pakai Mailhog (`docker-compose.yml`, UI di :8025); produksi tinggal isi
  `SMTP_HOST` dkk di `.env`.

### Bug ditemukan & diperbaiki saat membangun notifikasi
`httpx.post()` tidak melempar exception untuk respons 4xx/5xx — endpoint webhook/Slack
yang gagal (mis. HTTP 500) akan tetap dilaporkan "berhasil" jika responsnya tidak dicek.
Ini merusak tujuan fitur "Kirim Uji" yang secara eksplisit harus jujur soal status
pengiriman. Diperbaiki dengan `.raise_for_status()` di `_send_webhook`/`_send_slack`.
Diverifikasi: kegagalan asli (404 dari Slack, 422 dari endpoint yang salah format)
sekarang benar dilaporkan gagal, bukan "berhasil" secara diam-diam.

## Fase 2 — dikerjakan lebih awal karena selaras dengan positioning inti produk

Dataklin dipakai data engineer untuk menyiapkan data bagi role data lain (data scientist dkk),
jadi dua item ini diprioritaskan lebih dulu daripada urutan default Fase 2:

- ✅ **Survivorship Rule Configurable per kolom** — backlog #17, F7.
  `services/golden_record.py` mendukung 5 strategi (`latest_update`, `first_non_null`,
  `most_frequent`, `longest`, `source_priority`). Endpoint `POST .../golden/preview` (hitung
  tanpa simpan) dan `PUT .../golden` (simpan + jadi default `datasets.survivorship_config`
  untuk konfirmasi cluster berikutnya). UI di halaman Golden Record: dropdown strategi per
  kolom + kolom prioritas sumber, dengan pratinjau live sebelum simpan.
- ✅ **Clean Dataset Export & Data Dictionary** (memperluas cakupan asli backlog) —
  `services/clean_export.py` menggabungkan standardisasi dengan hasil entity resolution:
  cluster yang sudah dikonfirmasi di-collapse jadi satu baris golden record (kolom
  `_dq_status`/`_dq_cluster_id`/`_dq_source_rows` menandai asal, tidak menyembunyikan apa
  pun). `GET /datasets/{id}/clean.csv` & `/clean/preview`, plus
  `GET /datasets/{id}/dictionary.csv` (skema + statistik profiling + rule aktif per kolom)
  supaya konsumen hilir tidak perlu re-derive statistik dari nol.

### Bug ditemukan & diperbaiki selama pengerjaan di atas
Saat menguji clean export, kolom ID numerik (NIK, no HP setelah standardisasi) kehilangan
nol di depan atau tampil sebagai `...001.0` — root cause: `pd.read_csv`/`pd.read_excel`
otomatis meng-infer kolom all-digit sebagai int/float saat load ulang. Diperbaiki di
`services/loader.py` (baca sebagai `dtype=str` dulu, baru dikonversi ke numerik per kolom
kecuali ada nilai berawalan nol) dan `services/entity_resolution.json_safe_record` (float
bulat → int sebelum disimpan ke `ClusterMember`/`GoldenRecord`). Ini perbaikan struktural,
bukan cuma di fitur baru — turut memperbaiki tampilan di Cluster Review & Rule Builder untuk
kolom sejenis.

- ✅ **API Key per organisasi** (bagian dari backlog #28, F12) — `models.ApiKey` (hash
  SHA-256 tersimpan, kunci lengkap ditampilkan sekali), `security.get_org_reader` (dependency
  yang menerima header `X-API-Key` ATAU JWT). Berlaku pada endpoint baca/export saja
  (`/datasets`, `clean.csv`, `dictionary.csv`, `scorecard`, `history`, `anomalies`,
  `standardize/preview`); endpoint mutasi tetap JWT-only demi audit trail (NFR
  Auditabilitas). UI kelola key di `/settings/api-keys`.
- ✅ **PII Detection & Masking** — backlog #23, F11. `services/pii.py`: deteksi berbasis
  konten (regex NIK/HP/email) + heuristik nama kolom (nama/alamat), bukan NER (konsisten
  dengan pendekatan rule-based lain di codebase ini). Rekomendasi masking otomatis
  (`partial` untuk NIK/HP, `email_mask`, `hash` untuk nama/alamat). Dihitung saat
  profiling & disimpan di `datasets.pii_findings`. Terintegrasi ke `GET .../pii`,
  `clean.csv?mask_pii=true`, dan `dictionary.csv` (nilai contoh kolom PII selalu disamarkan
  di dictionary — file metadata tidak seharusnya membocorkan data mentah). UI: panel
  peringatan + checkbox "Samarkan PII" di halaman detail dataset.
  **Belum tercakup**: NER untuk PII tak terstruktur dalam teks bebas (di luar kolom
  terstruktur) — di luar cakupan MVP, butuh model ML terpisah.

### Bug ditemukan & diperbaiki (lanjutan) saat membangun PII masking
Pola bug yang sama (float bulat → tampil "...001.0") muncul LAGI di dua tempat baru:
`pii.detect_pii` saat membuat sample masking (fixed dengan konversi ke `Int64` sebelum
`astype(str)`, sama seperti di `profiling.py`), dan yang lebih halus — `Series.map()` pada
kolom ber-dtype `Int64` (nullable) ternyata mengonversi elemen ke Python `float` biasa
(kuirk pandas, bukan bug kita), sehingga `apply_mask` menerima `3273014501900001.0`
walau kolom sumbernya sudah `Int64`. Diperbaiki dengan guard `is_integer()` di
`apply_mask` sendiri — pola yang sama persis dengan fix di `rule_engine.py` sebelumnya.
Ini kali ketiga isu representasi float-vs-int muncul di jalur berbeda; kalau ada
penambahan jalur baru yang menampilkan kolom ID numerik, periksa pola ini lebih dulu.

- ✅ **Koneksi Database Langsung PostgreSQL/MySQL** — backlog #2, item terakhir Fase 2.
  `models.DataConnection` (kredensial dienkripsi Fernet at-rest, `ENCRYPTION_KEY` di
  `.env`; kosong = fitur nonaktif graceful), `services/db_connector.py` (test-before-save,
  `pandas.read_sql` via SQLAlchemy, driver `psycopg2`/`pymysql`). Dataset dari koneksi
  disimpan sebagai snapshot CSV di MinIO (reuse seluruh pipeline yang sudah ada tanpa
  perubahan) via `POST /datasets/from-connection`. `worker/tasks.refresh_dataset`
  (dispatcher) membuat drift monitoring terjadwal GENUINELY bermakna untuk sumber ini:
  tiap siklus benar-benar query ulang database sumber, bukan cache statis. UI: halaman
  `/settings/connections` (kelola koneksi) + tab "Sambungkan Database" di halaman Upload.
  **Diverifikasi end-to-end** dengan Postgres & MySQL sungguhan (container sementara):
  baris baru yang di-INSERT langsung ke MySQL berhasil muncul otomatis di dataset lewat
  siklus terjadwal, tanpa aksi manual.

### Bug ditemukan & diperbaiki saat membangun koneksi database
Query dengan hasil 1 baris (umum untuk tabel kecil/agregat) memicu `numeric.std()` bernilai
`NaN` (standar deviasi 1 sampel tidak terdefinisi). Kode lama `float(x.std() or 0)` gagal
menangkap ini karena `NaN` itu *truthy* di Python (`nan or 0` tetap `nan`, bukan `0`) — nilai
`NaN` lalu gagal disimpan sebagai kolom JSON di Postgres ("Token NaN is invalid"),
menggagalkan seluruh pemrosesan dataset. Diperbaiki di `services/profiling.py` dan
`services/anomaly.py` dengan `pd.notna()` eksplisit alih-alih idiom `or 0`. Ditemukan lewat
query nyata (`SELECT * FROM organizations`, 1 baris) — mengonfirmasi nilai pengujian dengan
data database sungguhan, bukan cuma file sample yang sudah dirancang "aman".

**Seluruh item Fase 2 kini selesai.** Sisa pekerjaan ada di Fase 3 dan beberapa item
tambahan berikut.

- ✅ **Timeliness/Freshness Check** — backlog #5. `services/timeliness.py` (fungsi murni):
  deteksi apakah dataset dengan pemantauan terjadwal aktif (F10) benar-benar diperbarui
  sesuai jadwalnya — gap waktu sejak run sebelumnya dibandingkan `monitoring_interval_minutes`
  (skor turun linear setelah 2× interval terlewati). Terintegrasi penuh ke sistem yang
  sudah ada: dimensi `timeliness` masuk ke `score["dimensions"]` & skor keseluruhan (hanya
  muncul bila monitoring aktif DAN sudah ada run sebelumnya — run pertama tidak relevan),
  alert `data_terlambat` lewat `_check_and_alert` yang sama dengan drift alert lainnya
  (jadi otomatis ikut ter-notifikasi Email/Slack/Webhook). **Diverifikasi**: simulasi gap
  30 menit vs interval 5 menit → timeliness turun ke 0, alert `data_terlambat` severity
  "tinggi" terpicu dengan pesan yang benar, efek berantai wajar ke skor keseluruhan (ikut
  memicu `drift_skor`/`skor_rendah` karena satu dimensi anjlok ke 0).

- ✅ **Auto-Suggest Rule dari skema (LLM)** — backlog #9, melengkapi acceptance criteria
  F4 yang sebelumnya sengaja dilewati saat membangun NL Rule Generation ("LLM turut
  menyarankan rule ... tanpa diminta"). `services/llm.suggest_rules` (system prompt
  terpisah dari `generate_rule`): input skema + rule aktif (supaya tidak menyarankan
  duplikat), output array proposal (maks 5). `POST /datasets/{id}/rules/suggest` —
  validasi proposal di-refactor jadi helper bersama `_validate_proposal` (dipakai NL
  generation maupun auto-suggest), proposal yang gagal validasi dilewati satu-satu (tidak
  menggagalkan seluruh batch). Proposal tidak langsung disimpan — user meninjau &
  mengaktifkan satu per satu, sama seperti NL generation. UI: tombol "✨ Sarankan Rule
  dari Skema" di Rule Builder, hasil tampil sebagai kartu dengan tombol Aktifkan/Lewati.
  **Diverifikasi**: endpoint 503 graceful tanpa `LLM_BASE_URL` dikonfigurasi (lingkungan
  ini belum ada gateway asli); logika validasi diuji langsung dengan 6 kasus proposal
  palsu (rule_type/kolom valid & tidak valid, termasuk `cross_column`) — semua benar.
  **Belum terverifikasi**: kualitas saran LLM sungguhan (butuh gateway asli untuk diuji).

- ✅ **Referential Integrity Check** — backlog #10, perluasan arsitektur pertama yang
  melibatkan DUA dataset sekaligus (semua fitur sebelumnya per-dataset tunggal).
  `models.CrossDatasetRule` (hanya simpan hasil cek TERBARU, tanpa tabel histori
  terpisah — cukup untuk kebutuhan saat ini), `services/cross_dataset_checks.py`
  (fungsi murni: nilai kolom anak yang tidak ditemukan di kolom induk dataset lain, pakai
  guard `Int64` yang sama untuk hindari bug "...001.0" — lihat memori
  `dataklin-numeric-id-display-bug`). Dijalankan **on-demand** (`POST
  /cross-dataset-rules/{id}/run`), bukan bagian pipeline background — konsisten dengan
  operasi berat lain di codebase ini (clean.csv, standardize preview) yang juga sinkron.
  Pelanggaran ditemukan → `Alert` dibuat via infrastruktur yang sama dengan drift/timeliness
  (otomatis ikut ter-notifikasi Email/Slack/Webhook). Validasi kolom terjadi DUA kali:
  saat rule dibuat (respons cepat, error jelas) dan saat dijalankan (jaga-jaga kolom
  dihapus setelahnya). UI: halaman baru `/integrity`.
  **Diverifikasi**: dataset "orders" (5 baris, 2 `customer_id` yatim piatu) vs "customers"
  (3 baris) → terdeteksi tepat 2/5 pelanggaran, sample bersih tanpa artefak `.0`; alert
  `integritas_referensial` severity "tinggi" (rasio 40% > 10%) dibuat otomatis; kasus
  sebaliknya (semua ID cocok) benar melaporkan 0 pelanggaran; validasi kolom tidak ada
  ditolak 400 saat pembuatan rule.
- ✅ **Consistency Check antar sistem/tabel** — backlog #11, dibangun di atas fondasi
  `CrossDatasetRule` yang sama (field `check_type` diskriminator: `referential_integrity`
  vs `consistency`, plus `primary_value_column`/`reference_value_column` untuk varian
  ini). `services/cross_dataset_checks.check_consistency`: join dua dataset lewat kolom
  kunci (`primary_column`=`reference_column`), bandingkan kolom nilai untuk baris yang
  cocok — perbandingan case-insensitive & whitespace-trimmed (perbedaan format murni
  tidak dianggap inkonsistensi data). UI di halaman `/integrity` yang sama, dengan
  selector jenis cek + field kolom nilai tambahan saat "Consistency" dipilih.
  **Diverifikasi**: dataset "CRM" (status pelanggan) vs "Billing" (status_billing) untuk
  5 `customer_id`, 2 baris sengaja dibuat tidak konsisten (`Aktif` vs `Nonaktif`, `Aktif`
  vs `Suspended`) dan 2 baris beda kapitalisasi tapi SAMA maknanya (`aktif`/`Aktif`,
  `NONAKTIF`/`Nonaktif`) — hasil tepat: checked=4 (2 ID lain tidak join karena hanya ada
  di satu sisi, benar dikecualikan), violations=2 (persis 2 yang sengaja beda), 2 baris
  beda kapitalisasi benar TIDAK dianggap pelanggaran; validasi kolom nilai wajib diisi
  untuk consistency ditolak 400 bila kosong.

## Prioritas berikutnya

- **Konfigurasi Kredensial LLM (Base URL, API Key, Model)** — Mengisi `LLM_BASE_URL`, `LLM_API_KEY`, dan `LLM_MODEL` (baik via `.env` ataupun UI Settings) agar fitur AI (seperti NL Rule Generation) yang saat ini mati/graceful fallback bisa diaktifkan kembali.
- 🚨 **[URGENT] Pembuatan Comprehensive Test Dataset** — Buat dataset *dummy/mock* yang secara sengaja mencakup *seluruh* *use case* platform ini: entitas duplikat (exact & fuzzy), anomali (outlier statistik), missing values, *PII leakage*, referential integrity (lintas-dataset), drift data, dan pelanggaran berbagai tipe *business rules* (lintas-kolom, regex, range). Dataset ini sangat mendesak/urgent dibutuhkan untuk simulasi demo, E2E testing di frontend (Playwright), serta memvalidasi unjuk kerja algoritma probabilitas *Fellegi-Sunter* Dataklin secara menyeluruh tanpa harus menyusun dataset *dummy* baru secara manual setiap pengujian.
- **Golden record embedding via pgvector** — pgvector sudah terpasang di image Postgres;
  embedding similarity dapat menggantikan/melengkapi rapidfuzz di
  `services/entity_resolution.py`. Butuh keputusan sumber embedding (model lokal berat
  vs endpoint embedding dari LLM gateway opsional yang sudah ada).

## Fase 3 (Ekspansi)

- Data Contract Monitoring (backlog #24) — deteksi breaking change skema antar upload.
- Remediation Workflow (backlog #25) — auto-fix kasus jelas + assignment reviewer.
- Kolaborasi Multi-User penuh (backlog #30) — model `users.role` sudah mendukung
  admin/analyst/viewer; tinggal UI manajemen user + undangan.
- Integrasi Google Sheets / Salesforce; RBAC granular.

## Catatan teknis lain

- **Skala 1 juta baris**: entity resolution saat ini dibatasi `ER_MAX_ROWS` (default 200rb) dan
  budget pasangan `ER_MAX_PAIRS`; untuk 1 juta baris pertimbangkan blocking bertingkat + worker
  paralel per-block.
- **Keamanan produksi**: ganti `JWT_SECRET`, aktifkan TLS di depan (reverse proxy), enkripsi
  at-rest MinIO/Postgres, masking PII di log.
- **Re-profiling dataset yang sama**: saat ini cluster lama di-reset ketika dataset diproses
  ulang penuh; untuk drift monitoring perlu strategi mempertahankan keputusan review
  (feedback loop backlog F6 acceptance #3).
