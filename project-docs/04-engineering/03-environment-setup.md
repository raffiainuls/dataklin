# Environment Setup Guide

## Prasyarat
- [ ] Node.js versi:
- [ ] Database (Postgres/MySQL/dsb) versi:
- [ ] Tools tambahan (Docker, Redis, dsb):

## Langkah Instalasi
```bash
# 1. Clone repository
git clone [url-repo]

# 2. Install dependencies
[perintah]

# 3. Copy environment file
cp .env.example .env
```

## Daftar Environment Variable
| Variable | Deskripsi | Contoh Nilai | Wajib? |
|---|---|---|---|
| DATABASE_URL | Koneksi ke database | postgres://... | Ya |
| JWT_SECRET | Secret untuk signing token | | Ya |
| PAYMENT_API_KEY | API key payment gateway | | Ya (production) |

## Menjalankan Database Migration
```bash
[perintah migration]
```

## Menjalankan Project Secara Lokal
```bash
[perintah run]
```
Akses di: `http://localhost:[port]`

## Troubleshooting Umum
| Masalah | Solusi |
|---|---|
| | |
