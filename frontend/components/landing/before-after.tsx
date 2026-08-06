import { ArrowRight, MoveDown, MoveUp } from "lucide-react";

/* Infografis Before-After — pattern "Before-After Transformation" (landing.csv).
   Color strategy dari database: state "before" muted/grey, state "after" vibrant,
   success green untuk hasil. Angka before & after ditulis sebagai teks, jadi
   perbandingannya tidak bergantung pada panjang bar saja.

   Panjang bar mewakili BESARAN nilai, bukan "kebaikan". Untuk sebagian metrik
   besaran kecil justru lebih baik (mis. baris duplikat), jadi tiap baris membawa
   penanda arah eksplisit — tanpa itu bar hijau panjang dan bar hijau pendek
   sama-sama berarti "bagus" dan pembacanya jadi ambigu. */

export type Metric = {
  label: string;
  before: string;
  after: string;
  /* 0-100, panjang bar = besaran nilai (diskalakan relatif jika satuannya beda) */
  beforePct: number;
  afterPct: number;
  /* arah perbaikan: "lower" = makin rendah makin baik */
  better: "lower" | "higher";
};

export function BeforeAfter({ metrics }: { metrics: Metric[] }) {
  return (
    <table className="w-full border-collapse text-sm">
      <caption className="sr-only">
        Perbandingan kondisi data sebelum dan sesudah diproses Dataklin
      </caption>
      <thead>
        <tr className="text-left text-xs uppercase tracking-wide text-muted-foreground">
          <th scope="col" className="pb-2 font-medium">
            Metrik
          </th>
          <th scope="col" className="pb-2 font-medium">
            Sebelum
          </th>
          <th scope="col" className="pb-2 font-medium">
            Sesudah
          </th>
        </tr>
      </thead>
      <tbody>
        {metrics.map((m) => (
          <tr key={m.label} className="border-t align-middle">
            <th scope="row" className="py-3 pr-3 text-left font-normal text-foreground">
              {m.label}
              {/* Arah perbaikan sebagai teks + ikon, bukan hanya warna bar */}
              <span className="mt-0.5 flex items-center gap-1 text-xs font-normal text-muted-foreground">
                {m.better === "lower" ? (
                  <MoveDown className="h-3 w-3 shrink-0" aria-hidden="true" />
                ) : (
                  <MoveUp className="h-3 w-3 shrink-0" aria-hidden="true" />
                )}
                {m.better === "lower" ? "makin rendah makin baik" : "makin tinggi makin baik"}
              </span>
            </th>

            {/* Before: muted/grey */}
            <td className="py-3 pr-3" style={{ width: "32%" }}>
              <span className="tabular mb-1 block font-semibold text-muted-foreground">
                {m.before}
              </span>
              <span
                className="block h-1.5 rounded-full bg-muted-foreground/30"
                style={{ width: `${Math.max(m.beforePct, 4)}%` }}
                aria-hidden="true"
              />
            </td>

            {/* After: vibrant + success untuk hasil yang membaik */}
            <td className="py-3" style={{ width: "32%" }}>
              <span className="tabular mb-1 flex items-center gap-1.5 font-semibold text-success">
                <ArrowRight className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
                {m.after}
              </span>
              <span
                className="block h-1.5 rounded-full bg-success"
                style={{ width: `${Math.max(m.afterPct, 4)}%` }}
                aria-hidden="true"
              />
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
