# Page Override — `landing`

> Aturan di file ini **menimpa** `../MASTER.md` khusus untuk halaman landing — rute `/`
> (root), diimplementasikan di `frontend/app/page.tsx`. Dashboard aplikasi ada di `/dashboard`.
> Semua yang tidak disebut di sini tetap mengikuti MASTER.

**Dibuat manual.** `--persist --page landing` menolak menulis karena MASTER.md sudah ada
(perilaku by-design skill: tidak menimpa keputusan desain sebelumnya tanpa `--force`).
Isi di bawah adalah hasil query skill yang dicatat ulang, bukan karangan:

- `--design-system --density 3 --motion 4` → spacing spacious + motion Standard
- `--domain landing "hero features social-proof how-it-works B2B SaaS"` → pattern Before-After
- `--domain chart "comparison funnel proportion before after pipeline"` → Funnel + Waffle

---

## Override 1 — Density: 3/10 (Spacious), bukan 8/10

MASTER memakai density 8 karena target utamanya app dashboard (data-dense). Halaman marketing
butuh ruang napas, jadi landing memakai skala spacious:

| Token | MASTER (dense) | Landing (spacious) |
|-------|----------------|--------------------|
| `--space-md` | `8px` | `24px` |
| `--space-lg` | `12px` | `32px` |
| `--space-xl` | `16px` | `48px` |
| `--space-2xl` | `24px` | `64px` |
| `--space-3xl` | `32px` | `96px` |

Implementasi: section padding vertikal `py-20 md:py-28`, bukan `p-6` seperti app.

## Override 2 — Page Pattern: gabungan dua pattern

MASTER: `Real-Time / Operations Landing`. Untuk landing dipakai kerangka itu, tapi bagian
use-case memakai `Before-After Transformation` dari `landing.csv` — pattern paling relevan
untuk produk data quality (nilai jualnya memang transformasi data kotor → bersih).

Catatan `landing.csv` untuk Before-After:
- **Color strategy:** muted/grey untuk state "before" vs vibrant untuk "after"; success green untuk hasil
- **CTA placement:** setelah reveal transformasi + bottom
- **Conversion:** bukti visual, metrik spesifik

**Urutan section final:**

1. Hero — problem state + live status preview (dari Operations Landing)
2. Key metrics / indicators — angka yang bisa dipindai
3. Fitur — daftar kemampuan produk
4. How it works — funnel 5 tahap pipeline
5. Use cases — before-after + infografis per skenario
6. CTA penutup

## Override 3 — Motion: 4/10 (Standard), tanpa GSAP

MASTER melampirkan snippet GSAP ScrollTrigger. **GSAP tidak dipasang** di project ini
(`grep gsap package.json` → 0) dan menambah dependensi animasi tidak sebanding untuk satu
halaman. Motion diimplementasikan CSS-only dengan perilaku setara:

- Scroll reveal: `opacity 0 → 1`, `translateY(12px → 0)`, `300–400ms`, `ease-out`
- Memakai `animation-timeline: view()` di browser yang mendukung
- **Wajib:** konten terlihat by default (`opacity: 1`). Animasi hanya progressive enhancement,
  supaya tidak melanggar aturan MASTER "jangan sembunyikan konten below-the-fold tanpa fallback"
- `@media (prefers-reduced-motion: reduce)` mematikan seluruh animasi

## Override 4 — Chart / infografis

Semua infografis inline SVG atau CSS Grid, tanpa library chart (project tidak punya Recharts/D3).

| Infografis | Tipe (dari `charts.csv`) | Kewajiban a11y dari database |
|---|---|---|
| Tahapan pipeline | Funnel Chart | Persen konversi eksplisit sebagai teks per tahap; label tahap selalu terlihat; **fallback list linear** |
| Proporsi data kotor | Waffle Chart (grid 10×10) | Teks persen selalu terlihat; `aria-label` per sel; sediakan legend; maks 3–5 kategori |
| Before-after use case | Comparison | Angka before & after sebagai teks, bukan hanya warna |

Aturan lintas-chart yang berlaku: **jangan mengandalkan warna saja** untuk menyampaikan makna —
setiap seri butuh label teks atau ikon pendamping.

## Yang TETAP dari MASTER

- Palette (Trust teal `#0F766E` + dark mode)
- Tipografi Fira Sans (body) / Fira Code (heading & angka)
- Semua anti-pattern & Pre-Delivery Checklist
