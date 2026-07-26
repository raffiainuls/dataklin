# 📁 Project Documentation — Peta Navigasi

Struktur dokumen ini dirancang supaya AI agent dan tim punya konteks lengkap saat mengerjakan project, dari perencanaan sampai eksekusi harian.

## Urutan Pengisian yang Disarankan
1. **01-planning/** — isi dulu semua ini sebelum mulai development
2. **02-design/** — isi bareng/setelah planning, sebelum development
3. **03-team/** — tentukan role & stage di awal project
4. **04-engineering/** — disiapkan sebelum AI agent mulai coding
5. **05-project-management/** — dipakai terus-menerus selama project berjalan (kanban board diupdate harian)

## Struktur Folder

```
project-docs/
├── 00-README.md                          (file ini)
│
├── 01-planning/
│   ├── 01-PRD.md                         → Apa & kenapa project ini dibuat
│   ├── 02-architecture.md                → Bagaimana sistem dibangun
│   ├── 03-tech-stack.md                  → Teknologi yang dipakai
│   ├── 04-data-model.md                  → Struktur database
│   ├── 05-api-spec.md                    → Kontrak API
│   ├── 06-non-functional-requirements.md → Standar performa, keamanan, dsb
│   ├── 07-risk-register.md               → Risiko project
│   └── 08-glossary.md                    → Istilah khusus project
│
├── 02-design/
│   ├── 01-user-flow.md                   → Alur pengguna
│   ├── 02-wireframe-notes.md             → Referensi teks untuk wireframe
│   ├── 03-edge-cases.md                  → Skenario tidak biasa
│   └── 04-design-system.md               → Warna, tipografi, komponen UI
│
├── 03-team/
│   └── 01-roles-and-stages.md            → Tahapan project & pembagian role (manusia + AI agent)
│
├── 04-engineering/
│   ├── 01-coding-standards.md            → Aturan penulisan kode
│   ├── 02-AGENTS.md                      → Konteks utama untuk AI coding agent (taruh di root repo!)
│   ├── 03-environment-setup.md           → Cara install & jalankan project
│   └── 04-testing-strategy.md            → Strategi & standar testing
│
└── 05-project-management/
    ├── kanban_board.html                 → Board ticket interaktif (buka di browser)
    ├── 02-definition-of-done.md          → Kriteria ticket dianggap selesai
    ├── 03-changelog.md                   → Riwayat rilis
    ├── 04-acceptance-criteria-template.md→ Format acceptance criteria per ticket
    ├── 05-prompt-log.md                  → Riwayat instruksi ke AI agent
    └── 06-agent-ticket-rules.md          → Aturan ketat untuk AI agent saat memproses tiket
```

## Cara Pakai Bareng AI Agent
1. Taruh folder ini di root repository project kamu.
2. Pastikan `04-engineering/02-AGENTS.md` ada di root (atau di-symlink), karena banyak AI coding tool otomatis membacanya.
3. Isi `01-PRD.md` dulu paling lengkap — dokumen lain akan merujuk ke sini.
4. Setelah PRD & arsitektur fix, minta agent generate ticket ke `kanban_board.html` berdasarkan PRD.
5. Selama development, agent wajib update `kanban_board.html` (status, blocker, log) dan `03-changelog.md` setiap ada progress.

## Catatan
- Semua file `.md` bisa langsung diedit sebagai teks biasa (Markdown).
- File yang wajib selalu up-to-date: `kanban_board.html`, `03-changelog.md`, `07-risk-register.md`.
- Dokumen lain (PRD, arsitektur, dsb) sebaiknya di-review ulang tiap ada perubahan besar scope.
