# Edge Case Documentation

> Skenario tidak biasa yang sering terlewat kalau hanya fokus ke "happy path". Wajib diisi supaya AI agent tidak cuma implementasi kondisi ideal.

| # | Fitur Terkait | Skenario Edge Case | Perilaku yang Diharapkan | Prioritas |
|---|---|---|---|---|
| 1 | Login | Password salah 5x berturut-turut | Akun terkunci sementara 15 menit | High |
| 2 | Checkout | Stok produk habis saat proses bayar | Tampilkan pesan & batalkan transaksi otomatis | High |
| 3 | Upload File | File melebihi ukuran maksimal | Tolak upload, tampilkan pesan limit ukuran | Medium |
| 4 | | | | |

## Kategori Umum yang Perlu Dicek
- [ ] Input kosong / null
- [ ] Input dengan karakter khusus/emoji
- [ ] Koneksi terputus di tengah proses
- [ ] Race condition (dua aksi bersamaan)
- [ ] Data duplikat
- [ ] Permission/akses tidak sesuai
- [ ] Timezone & format tanggal berbeda
- [ ] Nilai ekstrem (angka sangat besar/kecil, teks sangat panjang)
