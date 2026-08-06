"use client";

import { useEffect, useRef, useState } from "react";

/* Sebelumnya warna canvas hardcoded (#e2e8f0, #2563eb, #ef4444) sehingga grafik tidak
   pernah mengikuti tema — tak terbaca di dark mode. Sekarang warna dibaca dari CSS
   custom property, dan digambar ulang saat kelas .dark berubah. */
function cssVar(name: string, fallback: string): string {
  if (typeof window === "undefined") return fallback;
  const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return v || fallback;
}

export function LineChart({
  points,
  threshold,
  label = "Histori skor kualitas",
}: {
  points: { label: string; value: number }[];
  threshold: number;
  label?: string;
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [theme, setTheme] = useState(0);

  /* Gambar ulang saat tema berubah */
  useEffect(() => {
    const obs = new MutationObserver(() => setTheme((n) => n + 1));
    obs.observe(document.documentElement, { attributes: true, attributeFilter: ["class"] });
    return () => obs.disconnect();
  }, []);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const colors = {
      grid: cssVar("--border", "#99f6e4"),
      text: cssVar("--muted-foreground", "#5b6b7f"),
      line: cssVar("--chart-1", "#0f766e"),
      threshold: cssVar("--destructive", "#dc2626"),
      surface: cssVar("--card", "#ffffff"),
    };

    /* Skala DPR supaya garis tidak buram di layar retina */
    const dpr = window.devicePixelRatio || 1;
    const cssWidth = 800;
    const cssHeight = 300;
    canvas.width = cssWidth * dpr;
    canvas.height = cssHeight * dpr;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, cssWidth, cssHeight);

    const font = "12px 'Fira Code', ui-monospace, monospace";

    if (points.length === 0) {
      ctx.fillStyle = colors.text;
      ctx.font = "14px 'Fira Sans', sans-serif";
      ctx.textAlign = "center";
      ctx.fillText("Tidak ada data histori", cssWidth / 2, cssHeight / 2);
      return;
    }

    const padding = 40;
    const width = cssWidth - padding * 2;
    const height = cssHeight - padding * 2;

    ctx.strokeStyle = colors.grid;
    ctx.lineWidth = 1;
    ctx.beginPath();
    [0, 25, 50, 75, 100].forEach((val) => {
      const y = padding + height - (val / 100) * height;
      ctx.moveTo(padding, y);
      ctx.lineTo(padding + width, y);

      ctx.fillStyle = colors.text;
      ctx.font = font;
      ctx.textAlign = "right";
      ctx.fillText(val.toString(), padding - 10, y + 4);
    });
    ctx.stroke();

    /* Garis ambang: putus-putus + label teks, jadi tidak bergantung warna saja */
    const thresholdY = padding + height - (threshold / 100) * height;
    ctx.beginPath();
    ctx.strokeStyle = colors.threshold;
    ctx.setLineDash([5, 5]);
    ctx.moveTo(padding, thresholdY);
    ctx.lineTo(padding + width, thresholdY);
    ctx.stroke();
    ctx.setLineDash([]);

    ctx.fillStyle = colors.threshold;
    ctx.font = font;
    ctx.textAlign = "left";
    ctx.fillText(`ambang ${threshold}`, padding + 4, thresholdY - 6);

    const stepX = points.length > 1 ? width / (points.length - 1) : width;

    ctx.beginPath();
    ctx.strokeStyle = colors.line;
    ctx.lineWidth = 2;
    points.forEach((point, i) => {
      const x = padding + i * stepX;
      const y = padding + height - (point.value / 100) * height;
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);

      ctx.fillStyle = colors.text;
      ctx.textAlign = "center";
      ctx.font = font;
      ctx.fillText(point.label, x, padding + height + 20);
    });
    ctx.stroke();

    ctx.strokeStyle = colors.line;
    points.forEach((point, i) => {
      const x = padding + i * stepX;
      const y = padding + height - (point.value / 100) * height;
      ctx.beginPath();
      ctx.fillStyle = colors.surface;
      ctx.arc(x, y, 4, 0, Math.PI * 2);
      ctx.fill();
      ctx.stroke();
    });
  }, [points, threshold, theme]);

  return (
    <div style={{ width: "100%", overflowX: "auto" }}>
      <canvas
        ref={canvasRef}
        role="img"
        aria-label={`${label}. ${points.length} titik data, ambang batas ${threshold}. Tabel data tersedia di bawah grafik.`}
        style={{ width: "100%", minWidth: "600px", height: "auto" }}
      />

      {/* Fallback data untuk pembaca layar — canvas sendiri tidak bisa dibaca */}
      {points.length > 0 && (
        <details className="mt-2 text-sm">
          <summary className="cursor-pointer text-muted-foreground transition-colors duration-200 hover:text-foreground">
            Lihat data sebagai tabel
          </summary>
          <table className="mt-2 w-full text-left">
            <caption className="sr-only">{label}</caption>
            <thead>
              <tr className="text-muted-foreground">
                <th scope="col" className="py-1 font-medium">
                  Periode
                </th>
                <th scope="col" className="py-1 font-medium">
                  Skor
                </th>
              </tr>
            </thead>
            <tbody>
              {points.map((p, i) => (
                <tr key={`${p.label}-${i}`} className="border-t">
                  <td className="py-1">{p.label}</td>
                  <td className="tabular py-1" data-numeric="">
                    {p.value}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </details>
      )}
    </div>
  );
}
