# Definition of Done (DoD)

> Sebuah ticket TIDAK dianggap "Done" kalau salah satu kriteria di bawah belum terpenuhi.

## Kriteria Umum (Berlaku untuk Semua Ticket)
- [ ] Kode sudah di-review minimal 1 reviewer (manusia atau agent QA)
- [ ] Semua acceptance criteria di ticket terpenuhi
- [ ] Unit test ditulis dan lolos
- [ ] Tidak ada error/warning baru di linter
- [ ] Dokumentasi terkait (API spec/data model) sudah diupdate jika ada perubahan
- [ ] Sudah ditest manual di environment staging
- [ ] Tidak menimbulkan regresi pada fitur lain

## Kriteria Tambahan per Tipe Ticket

### Fitur Baru (Feature)
- [ ] Edge case relevan sudah dicek (`02-design/03-edge-cases.md`)
- [ ] Responsive di mobile & desktop (jika UI)

### Perbaikan Bug (Bugfix)
- [ ] Root cause sudah diidentifikasi dan dicatat
- [ ] Ada test yang mencegah bug yang sama terulang

### Perubahan Infrastruktur (DevOps)
- [ ] Sudah ditest di environment staging sebelum production
- [ ] Ada rollback plan
