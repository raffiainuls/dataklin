import type { Metadata } from "next";
import Link from "next/link";
import {
  Activity,
  ArrowRight,
  Bell,
  CheckCircle2,
  Clock,
  Database,
  FileCheck2,
  Fingerprint,
  GitMerge,
  KeyRound,
  Plug,
  ScanSearch,
  ShieldCheck,
  SlidersHorizontal,
  Sparkles,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { LandingNav } from "@/components/landing/landing-nav";
import { FunnelPipeline } from "@/components/landing/funnel-pipeline";
import { WaffleQuality } from "@/components/landing/waffle-quality";
import { BeforeAfter, type Metric } from "@/components/landing/before-after";

/* Halaman ini mengikuti design-system/dataklin/pages/landing.md (override MASTER):
   density 3/10 spacious, pattern Real-Time/Operations + Before-After Transformation.
   Server Component sepenuhnya — konten statis, tidak ada 'use client'. */

export const metadata: Metadata = {
  title: "Dataklin — Siapkan Data Bersih Sebelum Diserahkan ke Tim Data",
  description:
    "Platform data quality & entity resolution: profiling otomatis, rule engine, deduplikasi, golden record, PII masking, dan monitoring drift. Untuk data engineer yang menyiapkan data bagi data scientist dan analyst.",
};

/* ---------------------------------------------------------------- Fitur ---- */

const FEATURE_GROUPS = [
  {
    icon: ScanSearch,
    title: "Profiling & Scorecard",
    items: [
      "Profiling otomatis: statistik lengkap per kolom",
      "Skor kualitas 0–100 dengan histori tren",
      "Scorecard siap ekspor PDF/CSV",
      "Data dictionary: skema + rule aktif per kolom",
    ],
  },
  {
    icon: ShieldCheck,
    title: "Rule Engine & Validasi",
    items: [
      "Rule siap pakai: email, HP Indonesia, NIK, tanggal, rentang angka",
      "Regex kustom & aturan antar kolom",
      "Halaman violation: lihat baris mana yang gagal",
      "Referential integrity: deteksi foreign key terputus",
    ],
  },
  {
    icon: Sparkles,
    title: "Rule dari Bahasa Natural (AI)",
    items: [
      "Tulis aturan dalam bahasa sehari-hari → rule terstruktur",
      "Auto-suggest rule proaktif dari skema dataset",
      "Selalu lewat review Anda sebelum aktif",
      "Nonaktif secara graceful jika LLM belum dikonfigurasi",
    ],
  },
  {
    icon: GitMerge,
    title: "Entity Resolution & Golden Record",
    items: [
      "Blocking key + fuzzy match → cluster duplikat",
      "Review queue: konfirmasi, split, atau keluarkan record",
      "Cluster cohesion scoring",
      "Survivorship configurable per kolom + pratinjau live",
    ],
  },
  {
    icon: SlidersHorizontal,
    title: "Standardisasi & Anomali",
    items: [
      "Normalisasi HP, email, nama, alamat, tanggal",
      "Pratinjau sebelum apply — tidak ada perubahan diam-diam",
      "Deteksi outlier IQR + z-score dengan penjelasan",
      "Consistency check nilai yang sama antar dua sistem",
    ],
  },
  {
    icon: Bell,
    title: "Monitoring & Alert",
    items: [
      "Drift monitoring terjadwal: re-validasi otomatis",
      "Alert saat skor kualitas turun melewati ambang",
      "Timeliness/freshness check + alert keterlambatan",
      "Notifikasi Email, Slack, dan Webhook",
    ],
  },
  {
    icon: Fingerprint,
    title: "PII & Governance",
    items: [
      "Deteksi PII: NIK, nomor HP, email, nama, alamat",
      "Opsi masking saat ekspor",
      "Autentikasi JWT + role admin/analyst/viewer",
      "Audit trail pada golden record",
    ],
  },
  {
    icon: Plug,
    title: "Sumber Data & Ekspor",
    items: [
      "Upload CSV/XLSX: delimiter, encoding, tipe terdeteksi otomatis",
      "Koneksi langsung PostgreSQL & MySQL",
      "Clean dataset export: terstandardisasi + terdedup",
      "API key per organisasi untuk akses programatik",
    ],
  },
];

/* ------------------------------------------------------------- Use case ---- */

type UseCase = {
  id: string;
  sector: string;
  title: string;
  problem: string;
  approach: string[];
  metrics: Metric[];
};

const USE_CASES: UseCase[] = [
  {
    id: "uc-faskes",
    sector: "Kesehatan / Layanan Publik",
    title: "Satu identitas pasien dari banyak faskes",
    problem:
      "Pasien yang sama terdaftar berulang di beberapa fasilitas dengan ejaan nama berbeda, NIK tidak lengkap, dan format nomor HP campur-campur. Laporan cakupan jadi menggelembung.",
    approach: [
      "Blocking key pada NIK + tanggal lahir, fuzzy match pada nama & alamat",
      "Rule NIK 16 digit dan normalisasi HP ke format +62",
      "Review queue untuk cluster yang skor kohesinya rendah",
      "Golden record dengan survivorship 'data terbaru menang'",
    ],
    metrics: [
      {
        label: "Baris duplikat",
        before: "12,4%",
        after: "0,3%",
        beforePct: 100,
        afterPct: 3,
        better: "lower",
      },
      {
        label: "NIK valid",
        before: "78%",
        after: "99,1%",
        beforePct: 78,
        afterPct: 99,
        better: "higher",
      },
      {
        label: "Format HP seragam",
        before: "61%",
        after: "100%",
        beforePct: 61,
        afterPct: 100,
        better: "higher",
      },
    ],
  },
  {
    id: "uc-crm",
    sector: "Ritel / Multi-cabang",
    title: "Konsolidasi CRM dari 30 cabang",
    problem:
      "Tiap cabang punya spreadsheet sendiri. Nama pelanggan sama muncul di beberapa cabang, kolom wajib banyak yang kosong, dan tidak ada yang tahu versi mana yang benar.",
    approach: [
      "Tarik langsung dari PostgreSQL tiap cabang, bukan ekspor manual",
      "Auto-suggest rule dari skema untuk kolom yang belum punya aturan",
      "Consistency check: nilai berbeda untuk kunci pelanggan yang sama",
      "Clean dataset export untuk dipakai tim analitik",
    ],
    metrics: [
      {
        label: "Skor kualitas",
        before: "54/100",
        after: "93/100",
        beforePct: 54,
        afterPct: 93,
        better: "higher",
      },
      {
        label: "Kolom wajib kosong",
        before: "18%",
        after: "1,2%",
        beforePct: 100,
        afterPct: 7,
        better: "lower",
      },
      {
        label: "Waktu konsolidasi",
        before: "3 minggu",
        after: "2 hari",
        beforePct: 100,
        afterPct: 10,
        better: "lower",
      },
    ],
  },
  {
    id: "uc-ml",
    sector: "Data Science / ML",
    title: "Data siap latih tanpa pembersihan ulang",
    problem:
      "Data scientist menghabiskan sebagian besar waktu membersihkan ulang data yang sama setiap kali ada permintaan baru — dan tiap orang membersihkannya dengan cara berbeda.",
    approach: [
      "Rule & standardisasi dijalankan sekali di hulu, dipakai semua konsumen",
      "Data dictionary sebagai kontrak skema yang bisa dibaca mesin",
      "PII di-mask saat ekspor, jadi dataset aman dibagikan",
      "Drift monitoring memberi tahu saat distribusi berubah",
    ],
    metrics: [
      {
        label: "Waktu data prep",
        before: "60% waktu kerja",
        after: "15% waktu kerja",
        beforePct: 100,
        afterPct: 25,
        better: "lower",
      },
      {
        label: "Dataset punya kontrak skema",
        before: "0%",
        after: "100%",
        beforePct: 4,
        afterPct: 100,
        better: "higher",
      },
      {
        label: "Kebocoran PII ke notebook",
        before: "Tidak terkontrol",
        after: "Ter-mask",
        beforePct: 100,
        afterPct: 8,
        better: "lower",
      },
    ],
  },
];

const KEY_METRICS = [
  /* Angka diverifikasi dari kode backend, bukan perkiraan:
     5 = scorecard.py DIMENSIONS (completeness, validity, uniqueness, consistency, timeliness)
     9 = rule_engine.py RULE_TYPES
     2 = db_connector.py DB_TYPES (postgresql, mysql)
     3 = notifier.py (Email, Slack, Webhook) */
  { value: "5", label: "dimensi kualitas diukur" },
  { value: "9", label: "tipe rule bawaan" },
  { value: "2", label: "database terhubung langsung" },
  { value: "3", label: "kanal notifikasi" },
];

const TRUST_POINTS = [
  "Tanpa kode untuk rule dasar",
  "Audit trail penuh",
  "PII ter-mask saat ekspor",
];

const PIPELINE_NOTES = [
  {
    icon: FileCheck2,
    title: "Setiap keputusan tercatat",
    body: "Golden record menyimpan asal nilai dan siapa yang menyetujuinya.",
  },
  {
    icon: Clock,
    title: "Berjalan terjadwal",
    body: "Scheduler mengulang validasi dan memberi tahu saat skor turun.",
  },
  {
    icon: KeyRound,
    title: "Siap dikonsumsi",
    body: "API key per organisasi untuk mengambil data bersih secara programatik.",
  },
];

/* ------------------------------------------------------------- Halaman ---- */

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-background">
      <a href="#konten" className="dk-skip-link">
        Lompat ke konten utama
      </a>
      <LandingNav />

      <main id="konten">
        {/* ---- 1. Hero: problem state + live status preview ------------------ */}
        <section className="border-b bg-secondary/30">
          <div className="mx-auto grid max-w-6xl items-center gap-12 px-4 py-20 sm:px-6 md:py-28 lg:grid-cols-2">
            <div className="dk-reveal">
              <p className="mb-4 inline-flex items-center gap-2 rounded-full border border-primary/25 bg-card px-3 py-1 text-xs font-medium text-primary">
                <Database className="h-3.5 w-3.5" aria-hidden="true" />
                Data Quality &amp; Entity Resolution
              </p>
              <h1 className="text-4xl font-bold leading-tight tracking-tight text-foreground md:text-5xl">
                Berhenti menyerahkan data kotor ke tim data Anda
              </h1>
              <p className="mt-5 text-lg leading-relaxed text-muted-foreground">
                Dataklin dipakai{" "}
                <strong className="font-semibold text-foreground">data engineer</strong> untuk
                memprofilkan, memvalidasi, mendeduplikasi, dan menstandardisasi data{" "}
                <em>sebelum</em> diserahkan ke data scientist dan analyst — supaya beban
                pembersihan tidak terus berpindah ke hilir.
              </p>

              <div className="mt-8 flex flex-wrap gap-3">
                <Button size="lg" render={<Link href="/login" />} nativeButton={false}>
                  Masuk ke Dataklin
                  <ArrowRight className="ml-2 h-4 w-4" aria-hidden="true" />
                </Button>
                <Button
                  size="lg"
                  variant="outline"
                  render={<Link href="#cara-kerja" />}
                  nativeButton={false}
                >
                  Lihat cara kerjanya
                </Button>
              </div>

              <ul className="mt-8 flex flex-wrap gap-x-6 gap-y-2 text-sm text-muted-foreground">
                {TRUST_POINTS.map((t) => (
                  <li key={t} className="flex items-center gap-1.5">
                    <CheckCircle2 className="h-4 w-4 shrink-0 text-success" aria-hidden="true" />
                    {t}
                  </li>
                ))}
              </ul>
            </div>

            {/* Live status preview — elemen khas pattern Operations Landing */}
            <div className="dk-reveal">
              <Card className="shadow-lg">
                <CardHeader className="border-b">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-base">Komposisi khas dataset mentah</CardTitle>
                    <span className="inline-flex items-center gap-1.5 rounded-full border border-success/30 px-2.5 py-0.5 text-xs font-medium text-success">
                      <Activity className="h-3 w-3" aria-hidden="true" />
                      Terpantau
                    </span>
                  </div>
                </CardHeader>
                <CardContent className="pt-6">
                  <WaffleQuality />
                  <p className="mt-5 border-t pt-4 text-sm text-muted-foreground">
                    Setiap kotak mewakili 1% baris. Bagian yang bermasalah inilah yang biasanya
                    baru ketahuan setelah data sampai ke tim analitik.
                  </p>
                </CardContent>
              </Card>
            </div>
          </div>
        </section>

        {/* ---- 2. Key metrics / indicators ---------------------------------- */}
        <section aria-label="Ringkasan kemampuan" className="border-b">
          <div className="mx-auto grid max-w-6xl grid-cols-2 gap-px px-4 py-12 sm:px-6 lg:grid-cols-4">
            {KEY_METRICS.map((s) => (
              <div key={s.label} className="px-4 py-4 text-center">
                <div className="tabular text-4xl font-bold text-primary">{s.value}</div>
                <div className="mt-1 text-sm text-muted-foreground">{s.label}</div>
              </div>
            ))}
          </div>
        </section>

        {/* ---- 3. Fitur ---------------------------------------------------- */}
        <section id="fitur" className="scroll-mt-20 border-b">
          <div className="mx-auto max-w-6xl px-4 py-20 sm:px-6 md:py-28">
            <div className="mb-14 max-w-2xl">
              <h2 className="text-3xl font-bold tracking-tight text-foreground md:text-4xl">
                Semua yang dibutuhkan untuk menyiapkan data
              </h2>
              <p className="mt-4 text-lg text-muted-foreground">
                Dari profiling awal sampai monitoring setelah data dipakai — satu tempat, satu
                audit trail.
              </p>
            </div>

            <ul className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
              {FEATURE_GROUPS.map((g) => (
                <li key={g.title}>
                  {/* Hover: shadow saja, tanpa transform yang menggeser layout */}
                  <Card className="dk-reveal h-full transition-shadow duration-200 hover:shadow-md">
                    <CardHeader>
                      <span
                        className="mb-2 inline-flex h-10 w-10 items-center justify-center rounded-lg bg-secondary text-secondary-foreground"
                        aria-hidden="true"
                      >
                        <g.icon className="h-5 w-5" />
                      </span>
                      <CardTitle className="text-base">{g.title}</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <ul className="space-y-2">
                        {g.items.map((it) => (
                          <li key={it} className="flex gap-2 text-sm text-muted-foreground">
                            <CheckCircle2
                              className="mt-0.5 h-3.5 w-3.5 shrink-0 text-primary"
                              aria-hidden="true"
                            />
                            <span>{it}</span>
                          </li>
                        ))}
                      </ul>
                    </CardContent>
                  </Card>
                </li>
              ))}
            </ul>
          </div>
        </section>

        {/* ---- 4. How it works: funnel ------------------------------------- */}
        <section id="cara-kerja" className="scroll-mt-20 border-b bg-muted/30">
          <div className="mx-auto max-w-4xl px-4 py-20 sm:px-6 md:py-28">
            <div className="mb-12 max-w-2xl">
              <h2 className="text-3xl font-bold tracking-tight text-foreground md:text-4xl">
                Cara kerjanya
              </h2>
              <p className="mt-4 text-lg text-muted-foreground">
                Data mengalir lewat lima tahap. Setiap tahap menyisakan jejak: baris mana yang
                gugur, karena rule apa, dan siapa yang menyetujui penggabungan.
              </p>
            </div>

            <FunnelPipeline />

            <div className="mt-12 grid gap-4 sm:grid-cols-3">
              {PIPELINE_NOTES.map((c) => (
                <div key={c.title} className="dk-reveal rounded-lg border bg-card p-5">
                  <c.icon className="mb-3 h-5 w-5 text-primary" aria-hidden="true" />
                  <h3 className="text-sm font-semibold text-foreground">{c.title}</h3>
                  <p className="mt-1.5 text-sm text-muted-foreground">{c.body}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ---- 5. Use case: Before-After Transformation --------------------- */}
        <section id="use-case" className="scroll-mt-20 border-b">
          <div className="mx-auto max-w-6xl px-4 py-20 sm:px-6 md:py-28">
            <div className="mb-14 max-w-2xl">
              <h2 className="text-3xl font-bold tracking-tight text-foreground md:text-4xl">
                Contoh use case
              </h2>
              <p className="mt-4 text-lg text-muted-foreground">
                Tiga skenario yang paling sering muncul, dengan kondisi data sebelum dan sesudah
                diproses.
              </p>
              <p className="mt-3 text-sm text-muted-foreground">
                Angka pada bagian ini <strong>ilustratif</strong> — dibuat untuk menggambarkan
                bentuk masalah dan hasilnya, bukan hasil pengukuran pelanggan.
              </p>
            </div>

            <div className="space-y-8">
              {USE_CASES.map((uc) => (
                <article
                  key={uc.id}
                  className="dk-reveal grid gap-8 rounded-xl border bg-card p-6 md:p-8 lg:grid-cols-2"
                >
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-wide text-primary">
                      {uc.sector}
                    </p>
                    <h3 className="mt-2 text-xl font-bold tracking-tight text-foreground">
                      {uc.title}
                    </h3>
                    <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
                      {uc.problem}
                    </p>

                    <h4 className="mt-6 text-sm font-semibold text-foreground">
                      Yang dilakukan Dataklin
                    </h4>
                    <ul className="mt-2.5 space-y-2">
                      {uc.approach.map((a) => (
                        <li key={a} className="flex gap-2 text-sm text-muted-foreground">
                          <ArrowRight
                            className="mt-0.5 h-3.5 w-3.5 shrink-0 text-primary"
                            aria-hidden="true"
                          />
                          <span>{a}</span>
                        </li>
                      ))}
                    </ul>
                  </div>

                  <div className="rounded-lg border bg-background p-5">
                    <h4 className="mb-4 text-sm font-semibold text-foreground">
                      Sebelum &rarr; Sesudah
                    </h4>
                    <BeforeAfter metrics={uc.metrics} />
                  </div>
                </article>
              ))}
            </div>
          </div>
        </section>

        {/* ---- 6. CTA penutup ---------------------------------------------- */}
        <section className="bg-primary">
          <div className="mx-auto max-w-3xl px-4 py-20 text-center sm:px-6 md:py-24">
            <h2 className="text-3xl font-bold tracking-tight text-primary-foreground md:text-4xl">
              Bersihkan data di hulu, sekali saja
            </h2>
            <p className="mx-auto mt-4 max-w-xl text-lg text-primary-foreground/90">
              Mulai dari satu dataset: unggah, lihat skornya, dan biarkan Dataklin menunjukkan apa
              yang perlu diperbaiki.
            </p>
            <div className="mt-8 flex flex-wrap justify-center gap-3">
              <Button
                size="lg"
                variant="secondary"
                render={<Link href="/login" />}
                nativeButton={false}
              >
                Masuk ke Dataklin
                <ArrowRight className="ml-2 h-4 w-4" aria-hidden="true" />
              </Button>
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t">
        <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-3 px-4 py-8 text-sm text-muted-foreground sm:flex-row sm:px-6">
          <p>Dataklin — AI-Powered Data Quality &amp; Entity Resolution Platform</p>
          <Link href="/login" className="inline-flex h-11 items-center px-3 font-medium">
            Masuk
          </Link>
        </div>
      </footer>
    </div>
  );
}
