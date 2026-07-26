# Coding Standards / Style Guide

## Naming Convention
- Variable: 
- Function: 
- File & folder: 
- Database (tabel/kolom): 
- Environment variable: 

## Struktur Folder Project
```
src/
  components/
  pages/
  services/
  utils/
  hooks/
tests/
docs/
```
> Sesuaikan dengan struktur project sebenarnya.

## Aturan Umum
- [ ] Setiap fungsi punya satu tanggung jawab jelas (single responsibility)
- [ ] Tidak ada hardcoded value (gunakan config/env)
- [ ] Semua input dari user divalidasi
- [ ] Error di-handle secara eksplisit, tidak di-swallow diam-diam
- [ ] Komentar hanya untuk hal yang tidak jelas dari kode itu sendiri

## Linting & Formatting
- Tool yang dipakai (ESLint, Prettier, dsb):
- Config file lokasi:

## Git Workflow
- Branch naming: `feature/PROJ-001-nama-fitur`, `fix/PROJ-002-nama-bug`
- Format commit message: `[PROJ-001] Deskripsi singkat perubahan`
- Aturan pull request: 
  - [ ] Wajib ada review sebelum merge
  - [ ] Wajib lolos CI/test sebelum merge

## Larangan
- Library/pattern yang tidak boleh dipakai:
- Praktik yang harus dihindari:
