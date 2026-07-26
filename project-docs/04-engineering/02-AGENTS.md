# AGENTS.md

> File ini dibaca otomatis oleh banyak AI coding tool (Claude Code, dsb) sebagai konteks utama project. Taruh file ini di root repository.

## Tentang Project Ini
[Deskripsi singkat 2-3 kalimat tentang project ini, lihat detail lengkap di `01-planning/01-PRD.md`]

## Dokumen Referensi Wajib Dibaca
- PRD: `01-planning/01-PRD.md`
- Arsitektur: `01-planning/02-architecture.md`
- Tech stack: `01-planning/03-tech-stack.md`
- Data model: `01-planning/04-data-model.md`
- API spec: `01-planning/05-api-spec.md`
- Coding standards: `04-engineering/01-coding-standards.md`

## Cara Menjalankan Project
```bash
# install dependencies
[perintah install]

# jalankan development server
[perintah run dev]

# jalankan test
[perintah test]
```

## Aturan Kerja untuk Agent
1. **BACA DULU**: Wajib membaca panduan di `project-docs/05-project-management/06-agent-ticket-rules.md` sebelum mengerjakan apapun. Ini adalah SOP mutlak.
2. Selalu baca ticket di `05-project-management/kanban_board.html` sebelum mulai kerja.
3. Update status ticket (In Progress/Blocked/Done) SETIAP kali status berubah — jangan menunggu sampai selesai semua.
4. Ikuti coding standards di `04-engineering/01-coding-standards.md` tanpa terkecuali.
5. Jangan mengubah struktur data/API tanpa update `04-data-model.md` dan `05-api-spec.md` juga.
6. Setiap fitur baru wajib disertai unit test minimal sesuai `04-engineering/04-testing-strategy.md`.
7. Jika menemukan ambiguitas requirement, tulis pertanyaan di ticket terkait (kolom blocker) daripada menebak.
8. Jangan hardcode credential/API key — selalu pakai environment variable.

## Batasan yang Tidak Boleh Dilanggar
- [ ] Tidak boleh mengubah skema database production tanpa migration script
- [ ] Tidak boleh menghapus data user tanpa soft-delete
- [ ] Tidak boleh commit langsung ke branch `main`/`production`

## Definition of Done
Lihat `05-project-management/03-definition-of-done.md` — sebuah ticket TIDAK dianggap selesai kalau kriteria di sana belum terpenuhi.

## Kontak Eskalasi
- Kalau agent stuck/blocked lebih dari [durasi], eskalasi ke: [nama/role]
