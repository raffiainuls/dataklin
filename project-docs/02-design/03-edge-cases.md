# Edge Case Documentation

> Skenario tidak biasa yang sering terlewat kalau hanya fokus ke "happy path". Wajib diisi supaya AI agent tidak cuma implementasi kondisi ideal.

| # | Fitur Terkait | Skenario Edge Case | Perilaku yang Diharapkan | Prioritas |
|---|---|---|---|---|
| 1 | Login | Password salah 5x berturut-turut | Akun terkunci sementara 15 menit | High |
| 2 | Checkout | Stok produk habis saat proses bayar | Tampilkan pesan & batalkan transaksi otomatis | High |
| 3 | Upload File | File melebihi ukuran maksimal | Tolak upload, tampilkan pesan limit ukuran | Medium |
| 4 | | | | |
| 5 | Entity Resolution | Typo menyebabkan dua record masuk exact block berbeda | Blocking fuzzy/phonetic/ngram tetap menghasilkan kandidat | High |
| 6 | Entity Resolution | A cocok B dan B cocok C, tetapi A tidak cocok C | Representative validation memecah/membuang rantai cluster lemah | High |
| 7 | Entity Resolution | Identifier wajib seperti NIK berbeda | Required evidence memveto pasangan walau nama/alamat mirip | High |
| 8 | Entity Resolution | Seluruh baris identik tetapi tidak ada kolom bernama nama/email/telepon | Exact-row fast path tetap menemukan cluster | Medium |
| 9 | Entity Resolution | Blocking menghasilkan blok terlalu besar | Blok di atas `ER_MAX_BLOCK_SIZE` dilewati untuk menjaga pair budget | High |
| 10 | Entity Resolution | Hanya ada label confirmed atau hanya split | Kalibrasi tidak mengubah threshold dan menjelaskan label yang kurang | Medium |

## Kategori Umum yang Perlu Dicek
- [ ] Input kosong / null
- [ ] Input dengan karakter khusus/emoji
- [ ] Koneksi terputus di tengah proses
- [ ] Race condition (dua aksi bersamaan)
- [ ] Data duplikat
- [ ] Permission/akses tidak sesuai
- [ ] Timezone & format tanggal berbeda
- [ ] Nilai ekstrem (angka sangat besar/kecil, teks sangat panjang)
