# Data Model / Database Schema

> Struktur data inti aplikasi. AI agent memakai ini sebagai referensi tunggal saat generate query/model, supaya tidak menebak-nebak nama kolom atau relasi.

## 1. Entity Relationship Diagram (ERD)
```
[User] 1---* [Order] *---1 [Product]
   |
   *---1 [Role]
```
> Ganti dengan diagram ERD sebenarnya.

## 2. Daftar Tabel/Entity

### Tabel: users
| Kolom | Tipe Data | Constraint | Deskripsi |
|---|---|---|---|
| id | UUID | PK | |
| email | varchar | unique, not null | |
| password_hash | varchar | not null | |
| role_id | UUID | FK -> roles.id | |
| created_at | timestamp | default now() | |

### Tabel: [tambahkan tabel lain sesuai kebutuhan]
| Kolom | Tipe Data | Constraint | Deskripsi |
|---|---|---|---|
| | | | |

## 3. Relasi Antar Tabel
| Tabel A | Relasi | Tabel B | Keterangan |
|---|---|---|---|
| users | many-to-one | roles | satu role banyak user |

## Konfigurasi Entity Resolution

`datasets.dedup_config` adalah JSON versioned. Versi 2 menyimpan:

- `blocking_rules`: candidate generation yang terpisah dari matching.
- `rules`: metode similarity, normalizer, bobot probabilistik, dan negative evidence.
- `exact_match_rules` serta `exact_row_match`: deterministic duplicate fast path.
- `cluster_validation`: strategi representative/connected beserta batas cohesion.

Tidak ada perubahan kolom database untuk VD-314; JSON lama tetap dapat dibaca.

Hasil pair disimpan pada `record_match_scores` (`score` dan evidence per kolom di
`features`) dan hasil pengelompokan disimpan pada `entity_clusters` serta
`cluster_members`. Status `confirmed` dan `split` menjadi label untuk kalibrasi threshold.

## 4. Indexing & Performance
- Kolom yang perlu index:
- Kolom yang sering dipakai untuk filter/search:

## 5. Data Retention & Privacy
- Data sensitif (PII) yang perlu perhatian khusus:
- Kebijakan retensi/penghapusan data:
