# Testing Strategy

## Jenis Testing yang Dibutuhkan
| Jenis Test | Cakupan | Tool | Target Coverage |
|---|---|---|---|
| Unit Test | Fungsi/logic individual | | ≥ 80% |
| Integration Test | Interaksi antar modul/API | | Endpoint kritikal 100% |
| End-to-End (E2E) Test | Flow utama dari sisi user | | Semua flow "Must Have" |
| Performance Test | Beban & waktu respons | | Sesuai NFR |

## Kriteria Wajib Test
- [ ] Setiap fungsi business logic wajib punya unit test
- [ ] Setiap endpoint API wajib punya test untuk kasus sukses & error
- [ ] Setiap flow di user flow (`02-design/01-user-flow.md`) wajib punya E2E test

## Cara Menjalankan Test
```bash
[perintah unit test]
[perintah e2e test]
```

## Pelaporan Bug
| Field | Keterangan |
|---|---|
| Severity | Critical / High / Medium / Low |
| Steps to reproduce | Wajib diisi jelas |
| Expected vs Actual | Wajib diisi |
| Environment | Dev/Staging/Production |

## Kriteria Rilis (Go/No-Go)
- [ ] Tidak ada bug Critical/High yang open
- [ ] Semua test otomatis lolos di CI
- [ ] Sudah lolos review manual minimal 1 reviewer
