# Product Requirements Document (PRD)

> Dokumen ini adalah sumber kebenaran utama tentang APA yang dibangun dan KENAPA. Semua dokumen lain (arsitektur, ticket, wireframe) harus konsisten dengan PRD ini.

## 1. Ringkasan Produk
- **Nama Project**: Veridata (SaaS Data Quality & Entity Resolution)
- **Tanggal dibuat / diupdate**: 25 Juli 2026
- **Pemilik project (Product Owner)**:
- **Latar belakang**: Perusahaan sering bermasalah dengan data kotor, duplikasi, dan format yang tidak standar dari berbagai sumber. Tools data quality enterprise sangat mahal, sulit, dan kaku. Project ini (Veridata) hadir sebagai platform mandiri (self-serve) yang murah, didukung AI untuk kemudahan deduplikasi (Vector Embeddings) & deteksi (LLM rules), siap mengalahkan standar kompetitor lokal seperti Xeratic LinkR.

## 2. Tujuan & Sasaran
- **Tujuan utama**: Menjadi SaaS Data Quality dan Entity Resolution terbaik dan terlengkap untuk SME & Mid-Market, melebihi kemampuan platform kompetitor seperti Xeratic LinkR.
- **Sasaran terukur (metric of success)**:
  - [x] Metric 1 — target: Waktu setup & deteksi masalah data < 5 menit untuk dataset 100k row.
  - [x] Metric 2 — target: Duplicate Resolution Rate > 70% dari antrean dengan bantuan AI Embeddings.
  - [x] Metric 3 — target: Automasi penuh untuk Write-back Pipeline (Upsert 100% ke Data Warehouse target).

## 3. Target Pengguna
| Segmen | Kebutuhan Utama | Pain Point Saat Ini |
|---|---|---|
| | | |

## 4. Ruang Lingkup
### In Scope
- 

### Out of Scope
- 

## 5. Daftar Fitur (High Level)
| # | Fitur | Prioritas (Must/Should/Could/Won't) | Deskripsi Singkat |
|---|---|---|---|
| 1 | Automated Data Profiling & Outlier Detection | Must (Selesai) | Profiling statistik dan deteksi anomali (IQR+Z-score) |
| 2 | NL Rule Generation & Auto-Suggest (LLM) | Must (Selesai) | Pembuatan rule dari natural language dan rekomendasi skema |
| 3 | Smart Deduplication (AI Embeddings via pgvector) | Must (Fase 3) | Resolusi entitas semantik, melebihi fuzzy match biasa |
| 4 | Remediation Workflow (Collaborative Stewarding) | Must (Fase 3) | Assign tugas otomatis untuk resolusi anomali dengan sistem komentar/approval |
| 5 | Write-back Pipeline (Destination Connectors) | Must (Fase 3) | Sinkronisasi data (Golden Record) balik ke DB/Data Warehouse klien |
| 6 | Data Contract Monitoring | Should (Fase 3) | Deteksi breaking change pada skema antar jadwal upload/koneksi |
| 7 | Multi-User RBAC & API/Webhook | Should (Fase 3) | Hak akses granular, undangan tim, integrasi CI/CD/Data Pipeline |

> Detail tiap fitur dipecah lebih lanjut jadi user story & ticket di `05-project-management/`.

## 6. User Story Utama
- Sebagai [role], saya ingin [aksi], supaya [manfaat].
- Sebagai [role], saya ingin [aksi], supaya [manfaat].

## 7. Asumsi & Batasan
- **Asumsi**:
- **Batasan (constraint)**: (budget, waktu, teknologi wajib, dsb)

## 8. Risiko Awal
- Lihat detail di `01-planning/07-risk-register.md`

## 9. Timeline & Milestone
| Milestone | Target Tanggal | Deliverable |
|---|---|---|
| | | |

## 10. Stakeholder & Persetujuan
| Nama | Peran | Status Approve |
|---|---|---|
| | | |
