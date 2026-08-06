# Design System Master File

> **LOGIC:** When building a specific page, first check `design-system/pages/[page-name].md`.
> If that file exists, its rules **override** this Master file.
> If not, strictly follow the rules below.

---

**Project:** Dataklin
**Generated:** 2026-08-06 16:01:16
**Category:** Analytics Dashboard
**Design Dials:** Variance 4/10 (Balanced / Modern) | Motion 3/10 (Subtle) | Density 8/10 (Dense / Dashboard)

---

## Global Rules

### Color Palette

> **PALETTE OVERRIDE — dimensi ini diganti dari default generator.**
> Generator memilih baris `Analytics Dashboard` (primary `#1E40AF`, biru). Dataklin sudah punya
> ekuitas brand **teal**, jadi palette ditukar ke baris **`Trust teal + professional blue`**
> dari `colors.csv` (hasil `--domain color "teal cyan data trust enterprise"`).
> Semua dimensi lain (style, tipografi, spacing, motion, pattern) tetap seperti yang digenerate.
> Alasan teknis: teal lama `oklch(0.6 0.15 190)` ≈ `#00A6AD` hanya **2.98:1** dengan teks putih
> (gagal WCAG AA); `#0F766E` mencapai **5.47:1**.

| Role | Hex | CSS Variable | Kontras terukur |
|------|-----|--------------|-----------------|
| Primary | `#0F766E` | `--color-primary` | 5.47:1 vs putih ✅ AA |
| On Primary | `#FFFFFF` | `--color-on-primary` | — |
| Secondary | `#14B8A6` | `--color-secondary` | 7.17:1 vs `#0F172A` ✅ AA |
| Accent/CTA | `#0369A1` | `--color-accent` | 5.93:1 vs putih ✅ AA |
| Background | `#F0FDFA` | `--color-background` | — |
| Foreground | `#134E4A` | `--color-foreground` | 9.09:1 vs bg ✅ AA |
| Muted | `#E8F0F3` | `--color-muted` | — |
| Muted Foreground | `#5B6B7F` | `--color-muted-foreground` | 5.04:1 kasus terburuk ✅ AA (lihat catatan) |
| Border | `#99F6E4` | `--color-border` | dekoratif |
| Input (batas field) | `#828E9E` | `--color-input` | 3.33:1 vs putih ✅ WCAG 1.4.11 |
| Destructive | `#DC2626` | `--color-destructive` | 4.83:1 vs putih ✅ AA |
| Ring | `#0F766E` | `--color-ring` | — |

**Color Notes:** Trust teal + professional blue

> **Muted foreground digeser dari palette.** `#64748B` asli lolos di atas putih (4.76:1) tapi
> **gagal** di atas permukaan bernada yang benar-benar dipakai halaman: `bg-secondary/30`
> (4.47:1) dan `bg-muted/30` (4.40:1). `#5B6B7F` lolos di keempat permukaan
> (putih 5.45, background 5.22, secondary/30 5.12, muted/30 5.04).
> Ditemukan lewat audit kontras pada warna yang **ter-render**, bukan pada nilai token —
> pelajaran yang layak diingat: memeriksa token saja melewatkan permukaan bertumpuk.

> **Batas field** `--input` dinaikkan dari nilai palette ke `#828E9E` (light) / `#437D76` (dark)
> supaya memenuhi WCAG 1.4.11 (komponen non-teks butuh 3:1). Nilai `#CBD5E1` yang lazim
> dipakai hanya mencapai 1.48:1.

### Dark Mode Palette

Wajib per guideline shadcn `Theming / Support dark mode` (severity: High) — sebelumnya project
mendeklarasikan `@custom-variant dark` tanpa blok `.dark` sama sekali.

| Role | Hex | Kontras terukur |
|------|-----|-----------------|
| Background | `#0B1220` | — |
| Foreground | `#E2F5F1` | 16.55:1 vs bg ✅ AAA |
| Primary | `#2DD4BF` | 8.92:1 vs `#04231F` ✅ AA |
| Muted Foreground | `#94A3B8` | 7.30:1 vs bg ✅ AA |
| Border | `#274A47` | dekoratif; fokus dibawa oleh ring |
| Ring | `#2DD4BF` | 10.06:1 vs bg ✅ (indikator fokus) |
| Status: success / warn / error | `#34D399` / `#FBBF24` / `#FB7185` | 9.74 / 11.22 / 6.96 ✅ AA |

### Typography

- **Heading Font:** Fira Code
- **Body Font:** Fira Sans

> **Catatan implementasi.** Pasangan font dipakai, tapi pembagian perannya disesuaikan:
> heading prosa (h1–h4, CardTitle) memakai **Fira Sans**, dan **Fira Code** dipakai untuk
> angka & label data (kelas `.tabular`, teks di dalam chart, nilai KPI).
> Alasan: di project ini `--font-heading` hanya menyentuh `CardTitle`/`DialogTitle`/`SheetTitle`,
> sedangkan `h1`/`h2` mewarisi `font-sans` dari body — memetakan `--font-heading` ke mono
> menghasilkan judul card monospace berdampingan dengan judul section sans, jadi hierarkinya
> pecah. Tabular-nums Fira Code juga mencegah angka KPI bergeser saat dashboard polling 10 detik.
- **Mood:** dashboard, data, analytics, code, technical, precise
- **Google Fonts:** [Fira Code + Fira Sans](https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500;600;700&family=Fira+Sans:wght@300;400;500;600;700&display=swap)

**CSS Import:**
```css
@import url('https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500;600;700&family=Fira+Sans:wght@300;400;500;600;700&display=swap');
```

### Spacing Variables

*Density: 8/10 — Dense / Dashboard*

| Token | Value | Usage |
|-------|-------|-------|
| `--space-xs` | `2px` / `0.125rem` | Tight gaps |
| `--space-sm` | `4px` / `0.25rem` | Icon gaps, inline spacing |
| `--space-md` | `8px` / `0.5rem` | Standard padding |
| `--space-lg` | `12px` / `0.75rem` | Section padding |
| `--space-xl` | `16px` / `1rem` | Large gaps |
| `--space-2xl` | `24px` / `1.5rem` | Section margins |
| `--space-3xl` | `32px` / `2rem` | Hero padding |

### Shadow Depths

| Level | Value | Usage |
|-------|-------|-------|
| `--shadow-sm` | `0 1px 2px rgba(0,0,0,0.05)` | Subtle lift |
| `--shadow-md` | `0 4px 6px rgba(0,0,0,0.1)` | Cards, buttons |
| `--shadow-lg` | `0 10px 15px rgba(0,0,0,0.1)` | Modals, dropdowns |
| `--shadow-xl` | `0 20px 25px rgba(0,0,0,0.15)` | Hero images, featured cards |

---

## Component Specs

### Buttons

```css
/* Primary Button */
.btn-primary {
  background: #0F766E;
  color: white;
  padding: 12px 24px;
  border-radius: 8px;
  font-weight: 600;
  transition: all 200ms ease;
  cursor: pointer;
}

.btn-primary:hover {
  opacity: 0.9;
  transform: translateY(-1px);
}

/* Secondary Button */
.btn-secondary {
  background: transparent;
  color: #0F766E;
  border: 2px solid #0F766E;
  padding: 12px 24px;
  border-radius: 8px;
  font-weight: 600;
  transition: all 200ms ease;
  cursor: pointer;
}
```

### Cards

```css
.card {
  background: #FFFFFF;
  border-radius: 12px;
  padding: 24px;
  box-shadow: var(--shadow-md);
  transition: all 200ms ease;
  cursor: pointer;
}

.card:hover {
  box-shadow: var(--shadow-lg);
  transform: translateY(-2px);
}
```

### Inputs

```css
.input {
  padding: 12px 16px;
  border: 1px solid #99F6E4;
  border-radius: 8px;
  font-size: 16px;
  transition: border-color 200ms ease;
}

.input:focus {
  border-color: #0F766E;
  outline: none;
  box-shadow: 0 0 0 3px #0F766E20;
}
```

### Modals

```css
.modal-overlay {
  background: rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(4px);
}

.modal {
  background: white;
  border-radius: 16px;
  padding: 32px;
  box-shadow: var(--shadow-xl);
  max-width: 500px;
  width: 90%;
}
```

---

## Style Guidelines

**Style:** Data-Dense Dashboard

**Keywords:** Multiple charts/widgets, data tables, KPI cards, minimal padding, grid layout, space-efficient, maximum data visibility

**Best For:** Business intelligence dashboards, financial analytics, enterprise reporting, operational dashboards, data warehousing

**Key Effects:** Hover tooltips, chart zoom on click, row highlighting on hover, smooth filter animations, data loading spinners

### Page Pattern

**Pattern Name:** Real-Time / Operations Landing

- **Conversion Strategy:** For ops/security/iot products. Demo or sandbox link. Trust signals.
- **CTA Placement:** Primary CTA in nav + After metrics
- **Section Order:** 1. Hero (product + live preview or status), 2. Key metrics/indicators, 3. How it works, 4. CTA (Start trial / Contact)

---

## Motion

**Scroll Reveal** (Subtle) — Trigger: scroll (viewport enter) | Duration: 300-400ms | Easing: `power1.out`

```js
gsap.from(el, { opacity: 0, y: 12, duration: 0.35, ease: 'power1.out', scrollTrigger: { trigger: el, start: 'top 90%', toggleActions: 'play none none reverse' } });
```

**Framework notes:** Requires the ScrollTrigger plugin registered once via gsap.registerPlugin(ScrollTrigger)

- ✅ Keep the y offset small (8-16px) so it reads as a fade, not a slide
- ❌ Don't reveal below-the-fold content needed for SEO/crawlers as invisible-by-default without a no-JS fallback
- ⚡ toggleActions 'play none none reverse' avoids re-triggering on every scroll direction change

---

## Anti-Patterns (Do NOT Use)

- ❌ Ornate design
- ❌ No filtering

### Additional Forbidden Patterns

- ❌ **Emojis as icons** — Use SVG icons (Heroicons, Lucide, Simple Icons)
- ❌ **Missing cursor:pointer** — All clickable elements must have cursor:pointer
- ❌ **Layout-shifting hovers** — Avoid scale transforms that shift layout
- ❌ **Low contrast text** — Maintain 4.5:1 minimum contrast ratio
- ❌ **Instant state changes** — Always use transitions (150-300ms)
- ❌ **Invisible focus states** — Focus states must be visible for a11y

---

## Pre-Delivery Checklist

Before delivering any UI code, verify:

- [ ] No emojis used as icons (use SVG instead)
- [ ] All icons from consistent icon set (Heroicons/Lucide)
- [ ] `cursor-pointer` on all clickable elements
- [ ] Hover states with smooth transitions (150-300ms)
- [ ] Light mode: text contrast 4.5:1 minimum
- [ ] Focus states visible for keyboard navigation
- [ ] `prefers-reduced-motion` respected
- [ ] Responsive: 375px, 768px, 1024px, 1440px
- [ ] No content hidden behind fixed navbars
- [ ] No horizontal scroll on mobile
