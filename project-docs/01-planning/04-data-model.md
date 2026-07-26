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

## 4. Indexing & Performance
- Kolom yang perlu index:
- Kolom yang sering dipakai untuk filter/search:

## 5. Data Retention & Privacy
- Data sensitif (PII) yang perlu perhatian khusus:
- Kebijakan retensi/penghapusan data:
