/* Funnel Chart — charts.csv, data type "Funnel / Flow".
   Kewajiban dari database yang dipenuhi di sini:
   - persen konversi eksplisit sebagai TEKS per tahap (bukan hanya lebar bentuk)
   - label tahap selalu terlihat
   - penurunan terbesar di-highlight
   - gradasi satu warna dari start ke end
   - fallback list linear + traversal keyboard
   Server Component: murni SVG, tidak perlu 'use client'. */

export type FunnelStage = {
  name: string;
  detail: string;
  rows: number;
};

/* Angka ilustratif untuk menjelaskan alur, bukan benchmark hasil produksi. */
const STAGES: FunnelStage[] = [
  {
    name: "Baris mentah masuk",
    detail: "Upload CSV/XLSX atau tarik dari PostgreSQL/MySQL",
    rows: 1_000_000,
  },
  {
    name: "Lolos parsing & standardisasi",
    detail: "Normalisasi HP, email, nama, alamat, tanggal",
    rows: 987_000,
  },
  {
    name: "Lolos validasi rule",
    detail: "Rule engine + rule hasil generate LLM",
    rows: 912_000,
  },
  {
    name: "Unik setelah entity resolution",
    detail: "Blocking key + fuzzy match → cluster",
    rows: 847_000,
  },
  {
    name: "Golden record siap konsumsi",
    detail: "Survivorship + audit trail",
    rows: 841_000,
  },
];

const fmt = (n: number) => n.toLocaleString("id-ID");

export function FunnelPipeline() {
  const total = STAGES[0].rows;

  const rows = STAGES.map((s, i) => {
    const prev = i === 0 ? s.rows : STAGES[i - 1].rows;
    return {
      ...s,
      ofTotal: (s.rows / total) * 100,
      stepPct: (s.rows / prev) * 100,
      dropAbs: prev - s.rows,
    };
  });

  /* Penurunan terbesar wajib ditandai (color_guidance: "Highlight biggest drop") */
  const biggestDropIdx = rows.reduce(
    (best, r, i) => (i > 0 && r.dropAbs > rows[best].dropAbs ? i : best),
    0,
  );

  const W = 720;
  const stageH = 62;
  const gap = 8;
  const H = STAGES.length * stageH + (STAGES.length - 1) * gap;

  return (
    <div>
      {/* overflow-x-auto: chart lebar scroll di containernya, tidak membuat body scroll */}
      <div className="overflow-x-auto">
        <svg
          viewBox={`0 0 ${W} ${H}`}
          width="100%"
          style={{ minWidth: 520, height: "auto" }}
          role="img"
          aria-label={`Funnel pipeline Dataklin, ${STAGES.length} tahap. Dari ${fmt(total)} baris mentah menjadi ${fmt(STAGES[STAGES.length - 1].rows)} golden record. Rincian tersedia sebagai daftar di bawah grafik.`}
        >
          <defs>
            {/* Gradasi satu warna start → end, sesuai color_guidance funnel */}
            <linearGradient id="dk-funnel" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="var(--chart-1)" stopOpacity="0.95" />
              <stop offset="100%" stopColor="var(--chart-2)" stopOpacity="0.75" />
            </linearGradient>
          </defs>

          {rows.map((r, i) => {
            const y = i * (stageH + gap);
            const wTop = (r.ofTotal / 100) * W;
            const next = rows[i + 1];
            const wBot = next ? (next.ofTotal / 100) * W : wTop;
            const xTop = (W - wTop) / 2;
            const xBot = (W - wBot) / 2;
            const isBiggestDrop = i === biggestDropIdx && i > 0;

            return (
              <g key={r.name}>
                {/* Trapesium: lebar bawah = lebar tahap berikutnya, jadi bentuk menyempit */}
                <path
                  d={`M ${xTop} ${y} L ${xTop + wTop} ${y} L ${xBot + wBot} ${y + stageH} L ${xBot} ${y + stageH} Z`}
                  fill="url(#dk-funnel)"
                  stroke={isBiggestDrop ? "var(--chart-3)" : "transparent"}
                  strokeWidth={isBiggestDrop ? 2 : 0}
                  strokeDasharray={isBiggestDrop ? "6 4" : undefined}
                />
                {/* --primary-foreground ikut membalik di dark mode: putih di light (5.47:1
                    di atas chart-1) dan tinta gelap di dark (8.92:1). */}
                <text
                  x={W / 2}
                  y={y + 24}
                  textAnchor="middle"
                  fill="var(--primary-foreground)"
                  style={{ fontSize: 14, fontWeight: 600 }}
                >
                  {r.name}
                </text>
                <text
                  x={W / 2}
                  y={y + 44}
                  textAnchor="middle"
                  fill="var(--primary-foreground)"
                  style={{
                    fontSize: 12,
                    fontFamily: "var(--font-mono), monospace",
                    fillOpacity: 0.95,
                  }}
                >
                  {fmt(r.rows)} baris · {r.ofTotal.toFixed(1)}% dari total
                  {i > 0 ? ` · ${r.stepPct.toFixed(1)}% lolos tahap ini` : ""}
                </text>
              </g>
            );
          })}
        </svg>
      </div>

      <p className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-muted-foreground">
        <span className="inline-flex items-center gap-2">
          {/* Legend: garis putus-putus + teks, tidak hanya warna */}
          <span
            className="inline-block h-0 w-6 border-t-2 border-dashed"
            style={{ borderColor: "var(--chart-3)" }}
            aria-hidden="true"
          />
          Penurunan terbesar: {rows[biggestDropIdx].name} (&minus;
          {fmt(rows[biggestDropIdx].dropAbs)} baris)
        </span>
        <span>Angka ilustratif untuk menjelaskan alur.</span>
      </p>

      {/* Fallback linear wajib untuk funnel: bisa ditelusuri keyboard & pembaca layar */}
      <details className="mt-4 rounded-lg border bg-card p-4">
        <summary className="cursor-pointer text-sm font-medium transition-colors duration-200 hover:text-primary">
          Lihat tahapan sebagai daftar
        </summary>
        <ol className="mt-3 space-y-3">
          {rows.map((r, i) => (
            <li key={r.name} className="flex gap-3 text-sm">
              <span
                className="tabular mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-secondary text-xs font-semibold text-secondary-foreground"
                aria-hidden="true"
              >
                {i + 1}
              </span>
              <span>
                <span className="font-medium text-foreground">{r.name}</span>
                <span className="block text-muted-foreground">{r.detail}</span>
                <span className="tabular block text-muted-foreground">
                  {fmt(r.rows)} baris · {r.ofTotal.toFixed(1)}% dari total
                  {i > 0 && (
                    <>
                      {" "}
                      · {r.stepPct.toFixed(1)}% lolos · turun {fmt(r.dropAbs)} baris
                    </>
                  )}
                </span>
              </span>
            </li>
          ))}
        </ol>
      </details>
    </div>
  );
}
