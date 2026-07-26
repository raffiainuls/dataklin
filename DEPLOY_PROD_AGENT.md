# Panduan Deployment Produksi Dataklin (Agent Guide)

Dokumen ini berisi instruksi langkah demi langkah (SOP) untuk Agent AI atau tim DevOps yang akan melakukan deployment aplikasi Dataklin di server produksi (VPS / Cloud VM).

## 1. Persiapan Repositori
Pastikan Anda sudah berada di direktori proyek pada server produksi.
```bash
# Jika belum di-clone:
git clone https://github.com/raffiainuls/dataklin.git
cd dataklin
```

## 2. Setup File `.env` (Sangat Penting)
Server produksi **wajib** memiliki konfigurasi kredensial rahasia yang aman. Buat file `.env` (bisa salin dari `.env.example`).
Pastikan Agent menjalankan perintah berikut untuk men-generate kunci rahasia yang kuat untuk produksi:

- **JWT_SECRET**:
  Gunakan perintah bash: `openssl rand -hex 32`
- **ENCRYPTION_KEY**:
  Gunakan perintah Python: `python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`

Ubah konfigurasi berikut di file `.env`:
1. `JWT_SECRET` = (hasil generate di atas)
2. `ENCRYPTION_KEY` = (hasil generate di atas)
3. `POSTGRES_PASSWORD` = (ganti dengan password yang kuat, sesuaikan juga di `DATABASE_URL` jika di-hardcode)
4. `S3_ACCESS_KEY` & `S3_SECRET_KEY` = (buat kredensial yang lebih kuat dari minioadmin)
5. `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL` = (isi sesuai kredensial API LLM OpenCode/OpenAI)
6. `SMTP_*` = (Konfigurasi layanan SMTP sungguhan seperti SendGrid/AWS SES. Di production kita tidak menggunakan Mailhog).

## 3. Jalankan Docker Compose Mode Produksi
Di production, kita menggunakan 2 file Compose sekaligus:
1. `docker-compose.yml` (sebagai basis)
2. `docker-compose.prod.yml` (sebagai *override* untuk mematikan hot-reload frontend dan uvicorn, serta mengoptimalkan build).

Instruksikan agent untuk menjalankan perintah ini:
```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build \
  postgres redis minio backend worker scheduler frontend
```
*(Catatan: Perintah di atas secara sengaja **tidak meng-include `mailhog`** karena di produksi kita memakai SMTP sungguhan).*

## 4. Verifikasi Inisialisasi Database & Migrasi
Saat container `backend` menyala, script `startup()` otomatis akan:
1. Membuat ekstensi `pgvector`.
2. Menjalankan `Base.metadata.create_all()` untuk membuat tabel-tabel jika belum ada.
3. Melakukan injeksi user Admin awal jika tabel kosong (email dan pass dari `.env`).

Minta agent mengecek log backend untuk memastikan inisialisasi aman dan tidak ada crash:
```bash
docker compose logs backend --tail=50
```

## 5. Pengecekan Kesehatan
- **Frontend** dapat diakses di port `3000` host.
- **Backend API** dapat diakses di port `8000` host.
- **MinIO Dashboard** dapat diakses di port `9011` host.
- Direktori persisten penyimpanan (Database, Cache, Object Storage) akan terbentuk otomatis di folder lokal `./docker_data/` pada server.

Jika server berada di belakang Reverse Proxy (Nginx/Traefik), pastikan port `3000` diarahkan ke domain utama, dan port `8000` diarahkan ke path `/api` atau subdomain API.
