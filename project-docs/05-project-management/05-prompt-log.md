# Prompt / Instruction Log

> Catatan instruksi penting yang diberikan ke AI agent, supaya konsisten ke depannya dan bisa jadi referensi kalau ada masalah/bug yang berasal dari instruksi yang salah.

| Tanggal | Agent yang Diberi Instruksi | Ringkasan Instruksi | Ticket Terkait | Hasil/Catatan |
|---|---|---|---|---|
| | | | | |

## Prompt Template yang Sering Dipakai

### Generate ticket dari PRD
> Lihat template lengkap di percakapan/dokumentasi terpisah: "Prompt Generate Kanban Ticketing"

### Update status ticket
```
Buka kanban_board.html, cari ticket [ID], update status jadi [status], 
[jika Blocked: alasan blocker jelas dan actionable].
Tambahkan entry baru di log riwayat, jangan hapus log lama.
```

### Review kode sebelum merge
```
Review kode untuk ticket [ID] berdasarkan:
1. Acceptance criteria di ticket
2. Coding standards di 04-engineering/01-coding-standards.md
3. Definition of Done di 05-project-management/02-definition-of-done.md
Laporkan temuan dalam bentuk list, urutkan dari yang paling kritikal.
```
