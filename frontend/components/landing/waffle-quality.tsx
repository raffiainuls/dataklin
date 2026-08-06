/* Waffle Chart — charts.csv, data type "Proportional / Percentage".
   Dipilih karena database menyebut waffle "better than pie for accessibility".
   Aturan yang dipenuhi: grid 10x10, maksimum 3-5 kategori, gap 2-3px antar sel,
   teks persen SELALU terlihat, ada legend.

   Deviasi yang disengaja: database menyarankan aria-label per sel. 100 aria-label
   justru membuat pembaca layar membacakan 100 item tanpa makna, jadi grid diberi
   role="img" dengan satu ringkasan lengkap. Efeknya lebih baik untuk tujuan sama. */

type Segment = {
  key: string;
  label: string;
  cells: number; // 1 sel = 1%
  color: string;
  note: string;
};

const SEGMENTS: Segment[] = [
  {
    key: "clean",
    label: "Sudah bersih",
    cells: 73,
    color: "var(--chart-1)",
    note: "Lolos semua rule",
  },
  {
    key: "dup",
    label: "Duplikat",
    cells: 12,
    color: "var(--chart-2)",
    note: "Terdeteksi entity resolution",
  },
  {
    key: "format",
    label: "Format tidak konsisten",
    cells: 9,
    color: "var(--chart-3)",
    note: "HP, tanggal, alamat",
  },
  {
    key: "missing",
    label: "Kosong / anomali",
    cells: 6,
    color: "var(--chart-5)",
    note: "IQR + z-score",
  },
];

const TOTAL = 100;

export function WaffleQuality() {
  /* Bangun 100 sel berurutan per kategori */
  const cells: Segment[] = SEGMENTS.flatMap((s) => Array.from({ length: s.cells }, () => s));
  const summary = SEGMENTS.map((s) => `${s.label} ${s.cells}%`).join(", ");
  const problematic = SEGMENTS.filter((s) => s.key !== "clean").reduce((a, s) => a + s.cells, 0);

  return (
    <div className="flex flex-col gap-6 sm:flex-row sm:items-start">
      <div
        role="img"
        aria-label={`Komposisi 100 baris dataset mentah yang khas: ${summary}.`}
        className="grid shrink-0 gap-[3px]"
        style={{
          gridTemplateColumns: "repeat(10, minmax(0, 1fr))",
          width: "min(260px, 100%)",
        }}
      >
        {cells.map((s, i) => (
          <span
            key={i}
            aria-hidden="true"
            className="aspect-square rounded-[2px]"
            style={{ backgroundColor: s.color }}
          />
        ))}
      </div>

      {/* Legend + persen sebagai teks: makna tidak bergantung pada warna saja */}
      <ul className="flex-1 space-y-2.5">
        {SEGMENTS.map((s) => (
          <li key={s.key} className="flex items-start gap-2.5 text-sm">
            <span
              className="mt-1 h-3 w-3 shrink-0 rounded-[2px]"
              style={{ backgroundColor: s.color }}
              aria-hidden="true"
            />
            <span className="flex-1">
              <span className="font-medium text-foreground">{s.label}</span>
              <span className="tabular ml-2 font-semibold text-foreground">{s.cells}%</span>
              <span className="block text-muted-foreground">{s.note}</span>
            </span>
          </li>
        ))}
        <li className="tabular border-t pt-2.5 text-sm text-muted-foreground">
          Total {TOTAL} baris ·{" "}
          <span className="font-medium text-foreground">{problematic}% bermasalah</span>
        </li>
      </ul>
    </div>
  );
}
