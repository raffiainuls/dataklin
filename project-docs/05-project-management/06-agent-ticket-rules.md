# 🤖 Aturan Kerja Agent untuk Mengerjakan Ticket

> Dokumen ini adalah panduan **wajib** bagi seluruh AI Agent (seperti Claude) ketika diinstruksikan untuk mengerjakan atau memproses sebuah ticket dari Kanban Board. 
> Pelanggaran terhadap aturan ini akan menyebabkan ticket ditolak (dikembalikan ke status "Blocked" atau "To Do").

## 1. Persiapan Sebelum Mengubah Kode (Pre-Flight)
Setiap agent **dilarang langsung mengedit kode**. Langkah yang harus dilakukan:
1. **Pahami Konteks**: Buka dan baca `kanban_board.html`. Cari ID ticket yang ditugaskan.
2. **Baca Acceptance Criteria**: Pahami bagian *Acceptance Criteria (AC)* dari ticket. Kode hanya dianggap selesai jika AC terpenuhi seluruhnya.
3. **Cek Dokumen Perencanaan**:
   - Apakah tiket ini merubah skema DB? Jika ya, perbarui `01-planning/04-data-model.md`.
   - Apakah tiket ini merubah/menambah Endpoint API? Jika ya, perbarui `01-planning/05-api-spec.md`.
4. **Update Status Awal**: Buka file `kanban_board.html`, ubah status ticket menjadi **"In Progress"**, dan tambahkan Log Entry dengan timestamp yang sesuai (contoh: `[2026-07-25 10:15] Mulai mengimplementasikan fitur XYZ`).

## 2. Proses Development & Koding
1. **Taati Coding Standards**: Pastikan mengikuti panduan yang ada di `project-docs/04-engineering/01-coding-standards.md`.
2. **Single Responsibility Principle**: Jangan ubah kode atau file yang tidak ada hubungannya dengan ticket ini. Jika Anda melihat bug kecil di tempat lain, buatkan log baru di board, jangan digabung dalam satu kali pengerjaan kecuali diinstruksikan.
3. **Buat Plan Dulu (Khusus Sistem Kompleks)**: Untuk tiket skala besar (seperti "VD-301: Smart Deduplication"), gunakan tool `EnterPlanMode` terlebih dahulu. Tunjukkan rencana ke User sebelum mengetik kode.

## 3. Penanganan Blocker (Hambatan)
Jika agent menemui jalan buntu (misal: gagal parsing dependencies, library bentrok, file tidak ada, tidak punya API key eksternal):
1. **Jangan Berhenti Tanpa Jejak**: Segera hentikan koding.
2. **Update Status Blocker**: Buka `kanban_board.html`, ubah status tiket menjadi **"Blocked"**.
3. **Isi Alasan Blocker**: Tuliskan alasan spesifik di tag `blocker: "..."`. Contoh: *"Blocked: Butuh credential untuk koneksi LLM Gateway"*.
4. Laporkan status ini ke User di jendela chat.

## 4. Pengujian (Testing)
1. Setiap kode yang ditambahkan/dirubah wajib diuji (Unit Test/Integration Test). 
2. Pastikan test lolos sebelum memindahkan ticket ke In Review/Done. Lihat panduan di `project-docs/04-engineering/04-testing-strategy.md`.

## 5. Post-Flight (Setelah Koding Selesai)
1. **Self-Review terhadap DoD**: Cek kembali `project-docs/05-project-management/02-definition-of-done.md`. Pastikan semua kotak centang terpenuhi.
2. **Update Kanban Board**:
   - Ubah status menjadi **"In Review"** atau **"Done"** (sesuai instruksi User).
   - Kosongkan isi `blocker` (jika sebelumnya blocked).
   - Tambahkan log di `kanban_board.html`: *"Moved to Done by Agent-Backend. AC fulfilled."*
3. **Update Changelog**: Jika ini adalah fitur utama, tambahkan ringkasannya di `project-docs/05-project-management/03-changelog.md`.
4. **Berikan Laporan ke User**: Berikan penjelasan singkat ke User apa saja file yang telah diubah dan bahwa Kanban Board sudah diupdate.
