# Entity Resolution Test Dataset

Dataset sintetis untuk "menyiksa" algoritma entity resolution, lengkap dengan
ground truth sehingga precision/recall bisa diukur tanpa labeling manual.

Generate:

```bash
python generate_er_dataset.py                                          # 1.000.000 baris + subset 200k
python generate_er_dataset.py --rows 10000 --out samples/x.csv --no-subset
```

| File | Baris | Ukuran | Catatan |
|---|---|---|---|
| `samples/er_dataset_1k.csv` | 1.000 | 246 KB | uji cepat / debugging aturan |
| `samples/er_dataset_10k.csv` | 10.000 | 2,4 MB | iterasi tuning threshold, scorer selesai dalam detik |
| `samples/er_dataset_100k.csv` | 100.000 | 24 MB | uji skala menengah, masih di bawah semua limit |
| `samples/er_dataset_200k.csv` | ~199.600 | 48 MB | tiap grup pasangan utuh, pas dengan `er_max_rows=200.000` |
| `samples/er_dataset_500k.csv` | 500.000 | 120 MB | uji beban; resolver hanya memproses 200k baris pertama |
| `samples/er_dataset_1m.csv` | 1.000.000 | 241 MB | acak penuh; **melebihi** `max_upload_mb=200`, pakai lewat CLI |

Semua di-`.gitignore` — regenerate saja (deterministik, `--seed 42`; yang 1 juta
±18 detik). Proporsi tiap `use_case` identik di semua ukuran, jadi hasil scorer
bisa dibandingkan lintas ukuran.

> **Penting:** baca NIK & nomor HP sebagai teks, jangan biarkan pandas menebak:
> `pd.read_csv(path, dtype={"nik": str, "phone_number": str})`.
> Tanpa ini NIK 16 digit jadi float dan tampil `3.17123456789e+15` / `...001.0`.

## Kamus kolom

| Kolom | Isi |
|---|---|
| `source_system` | 10 sistem sumber (`web_app`, `crm`, `billing`, `legacy_erp`, …). Tiap sistem punya gaya `record_id`, kode gender, dan format tanggal sendiri |
| `record_id` | ID unik per baris, formatnya beda per sistem (`WEB-00001234`, `ERP000001234`, `OFF-0001234-9A3F`) |
| `nik` | 16 digit realistis: 4 prov+kota, 2 kecamatan, DDMMYY (hari +40 untuk perempuan), 4 serial. Kosong pada 16,6% baris |
| `full_name` | Nama Indonesia; dirusak dengan typo, ejaan fonetik, singkatan, gelar, urutan terbalik |
| `gender` | Sengaja tidak konsisten antar sistem: `M`/`F`, `L`/`P`, `Laki-laki`/`Perempuan` |
| `dob` | 7 format campur: `1996-04-12`, `12/04/1996`, `04/12/1996` (ambigu MDY), `12 April 1996`, `19960412`, `12.04.1996`, `12-04-1996` |
| `alamat` | Dirender 3 gaya dari satu alamat terstruktur: `abbrev` (Jl./Kav./Kel./JKT), `expanded` (Jalan/Kavling Satu/Kelurahan/Jakarta Selatan), `plain` |
| `phone_number` | 8 format: `081234567890`, `+62812…`, `+62812-3456-7890`, `62812…`, `812…` (nol hilang), `(0812)…`, spasi, titik |
| `last_updated` | Untuk survivorship berbasis recency; formatnya ikut gaya sistem sumber |
| **`use_case`** | Skenario baris ini — `normal_data` kalau bukan bagian skenario apa pun |
| **`expected_match`** | `MATCH` / `NO_MATCH` / `SINGLE` |
| **`true_entity_id`** | **Ground truth.** Baris dengan ID sama = orang yang sama |
| **`pair_group_id`** | Grup skenario. Pada UC4 satu grup memuat beberapa `true_entity_id` (satu rumah tangga, orang berbeda) |
| **`variant`** | Perturbasi spesifik, mis. `same_nik+name_phonetic+dob_slash_mdy+phone_e164` — untuk tahu varian mana yang bikin algoritma gagal |

Empat kolom terakhir + `use_case` adalah label, **buang sebelum data masuk resolver.**

## Komposisi (contoh: 1 juta baris)

| `use_case` | Baris | Entitas | Ekspektasi | Yang diuji |
|---|---|---|---|---|
| `uc1_fuzzy_typo_format` | 120.001 | 56.649 | MATCH | NIK identik, nama typo/fonetik, format dob & telepon beda |
| `uc2_missing_nik` | 90.000 | 45.000 | MATCH | NIK hilang di satu sisi (18% grup: hilang di kedua sisi) → harus match dari nama+dob+telepon |
| `uc3_address_variation` | 80.000 | 40.000 | MATCH | NIK kosong keduanya, hanya beda gaya penulisan alamat; sebagian dob/telepon ikut hilang |
| `uc4_family_false_positive` | 85.000 | 85.000 | **NO_MATCH** | Satu rumah tangga: kakak-adik, **kembar (dob identik)**, ayah-anak, plus *namesake* (nama persis sama, orang lain) |
| `uc5_entity_evolution` | 85.000 | 35.135 | MATCH | 2–3 snapshot 2021–2026: pindah alamat, ganti nomor, sebagian ganti nama belakang (menikah) |
| `normal_data` | 539.999 | 539.999 | SINGLE | Singleton; tetap kotor (6% tanpa NIK, 8% tanpa telepon) agar false positive terukur |

Total 801.784 entitas unik. UC4 memakai prefiks NIK 6 digit yang sama untuk satu
rumah tangga, dan 70% anggota memakai nomor telepon rumah yang sama — jadi hanya
`nik` dan `dob` yang membedakan (dan pada kasus kembar, hanya `nik`).

## Mengukur hasil

```bash
python evaluate_er_dataset.py                                     # default: 10k, config referensi
python evaluate_er_dataset.py --input samples/er_dataset_1k.csv
python evaluate_er_dataset.py --threshold 0.85
python evaluate_er_dataset.py --config my_config.json
```

Skor **satu file utuh**, jangan `--rows N` di atas file besar yang teracak: potongan
itu memutus pasangan (partner-nya ada di baris ke-600.000) sehingga presisi
terlihat jauh lebih buruk dari sebenarnya. Itu gunanya tangga ukuran di atas.

Output: precision/recall/F1 pairwise, recall per use case, false-merge rate UC4,
dan 10 `variant` yang paling sering gagal.

`REFERENCE_CONFIG` di skrip itu titik awal yang masuk akal. Kuncinya
`{"column": "nik", "method": "exact", "required": true}`: kalau **kedua** baris
punya NIK, keduanya wajib identik (memisahkan kakak-adik di UC4); kalau salah
satu kosong, rule-nya dilewati sehingga UC2/UC3 masih bisa match dari kolom
sekunder.

Baseline file utuh, threshold 0.8, `REFERENCE_CONFIG`, setelan default:

| File | Precision | Recall | F1 | UC4 salah gabung |
|---|---|---|---|---|
| 1k | 0,9909 | 1,0000 | 0,9954 | 0 dari 40 |
| 10k | 0,7424 | 0,7753 | 0,7585 | 1 dari 402 |
| 100k | 0,2904 | 0,2624 | 0,2757 | 8 dari 4.034 |

Tiga temuan dari angka ini:

1. **Kualitas runtuh karena `er_max_pairs=200.000`, bukan karena logika
   matching.** Pagu itu habis sebelum semua blok tersentuh, jadi mayoritas
   pasangan benar tidak pernah diskor. Dengan pagu dinaikkan ke 5 juta, recall
   10k naik 0,7753 → **0,9469** dan pada potongan 20k naik 0,6104 → **0,8958**.
   Ini bottleneck pertama yang harus dibereskan sebelum menyetel bobot apa pun.
2. **Tanpa validasi cluster, connected-component menyatukan orang tak
   berhubungan** lewat satu link lemah (cluster berisi 12 baris padahal ground
   truth-nya 2–3). Mengaktifkan `cluster_validation` menaikkan presisi
   0,4167 → 0,6158 pada uji yang sama, dan menurunkan salah gabung UC4 dari 10
   jadi 1 dari 793 rumah tangga.
3. **UC5 paling sering gagal** (`same_nik+moved+new_phone`): NIK identik, tapi
   ketidakcocokan telepon **dan** alamat secara agregat mengalahkan bukti NIK.
   Perbaikannya bukan menurunkan threshold — turunkan `weight` alamat/telepon,
   atau beri NIK jalur deterministik lewat `exact_match_rules`, karena alamat dan
   telepon memang *diharapkan* berubah untuk orang yang sama.

## Survivorship Rules — menentukan data mana yang menang

Entity resolution hanya menjawab *"baris-baris ini orang yang sama"*. Setelah itu
Anda masih harus membangun satu **golden record**. Itu tugas survivorship, dan
aturannya **per kolom**, bukan per baris — memilih "baris paling lengkap" lalu
menyalinnya utuh adalah kesalahan klasik, karena baris terbaru bisa punya alamat
paling baru tapi nama paling salah ketik.

Lima strategi, dari yang paling kuat:

1. **Trust-based / source authority.** Beri peringkat sistem sumber per kolom.
   Untuk `nik` dan `full_name`, sistem yang verifikasi KTP (mis. `billing`,
   `legacy_erp`) menang atas `web_app` yang diisi sendiri oleh user. Untuk
   `alamat`, `shipping` justru lebih dipercaya — di sanalah paket benar-benar
   dikirim. Ini aturan paling berguna dan paling sering dilewatkan.
2. **Most recent (recency).** Untuk atribut yang memang berubah — `alamat`,
   `phone_number` — ambil nilai dengan `last_updated` terbaru. Ini yang menjawab
   UC5: entitas digabung, alamat 2026 menang, alamat 2023 disimpan sebagai
   riwayat, bukan dibuang.
3. **Most complete / longest.** Untuk `full_name`, pilih yang paling informatif:
   `Raffi Ainul Afif` mengalahkan `Raffi A. Afif` dan `Rafi Ainul Afiv`. Panjang
   saja rawan salah (kolom bergelar `Bpk. Raffi …` jadi menang), jadi
   normalisasi gelar dulu.
4. **Most frequent (voting).** Untuk kolom berkode rendah kardinalitas seperti
   `gender` dan `dob`: normalisasi dulu (`L`/`M`/`Laki-laki` → satu nilai), lalu
   ambil modus dari semua baris. Ini yang menetralkan satu sistem yang salah
   parsing `04/12/1996` sebagai 4 Desember.
5. **Deterministik / paling ketat.** Untuk `nik`: hanya terima nilai yang lolos
   validasi format (16 digit, DDMMYY konsisten dengan `dob`, kode wilayah
   dikenal). Nilai tidak valid kalah walaupun sumbernya paling terpercaya.

Contoh untuk skenario UC5 di dataset ini:

| Kolom | Aturan | Alasan |
|---|---|---|
| `nik` | deterministik → trust | identifier, tidak boleh ikut-ikutan berubah |
| `full_name` | trust → most complete | nama itu stabil; yang berbeda biasanya kualitas input |
| `dob` | voting setelah normalisasi | melawan salah parsing format, bukan perubahan nilai |
| `gender` | voting setelah normalisasi | sama |
| `alamat` | recency (trust sebagai tie-break) | memang berubah saat pindah |
| `phone_number` | recency, simpan yang lama sebagai alternatif | nomor lama sering masih dipakai untuk verifikasi |

Dua hal yang wajib ada saat mengimplementasikan:

- **Lineage.** Setiap kolom golden record simpan `record_id` + `source_system`
  asalnya. Tanpa ini golden record tidak bisa diaudit dan tidak bisa di-rollback
  saat ternyata dua entitas salah gabung.
- **Jangan hapus baris sumber.** Golden record adalah tampilan (view) di atas
  cluster. Kalau merge-nya salah — dan pada UC4 pasti ada yang salah — Anda perlu
  bisa memecahnya kembali (unmerge).
