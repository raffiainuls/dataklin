"use client";

import { useEffect, useRef } from "react";

export function LineChart({ points, threshold }: { points: { label: string; value: number }[]; threshold: number }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    // Bersihkan canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    if (points.length === 0) {
      ctx.fillStyle = "#94a3b8";
      ctx.font = "14px sans-serif";
      ctx.textAlign = "center";
      ctx.fillText("Tidak ada data histori", canvas.width / 2, canvas.height / 2);
      return;
    }

    const padding = 40;
    const width = canvas.width - padding * 2;
    const height = canvas.height - padding * 2;

    // Gambar grid vertikal (skor 0 - 100)
    ctx.strokeStyle = "#e2e8f0";
    ctx.beginPath();
    [0, 25, 50, 75, 100].forEach((val) => {
      const y = padding + height - (val / 100) * height;
      ctx.moveTo(padding, y);
      ctx.lineTo(padding + width, y);
      
      ctx.fillStyle = "#64748b";
      ctx.font = "12px sans-serif";
      ctx.textAlign = "right";
      ctx.fillText(val.toString(), padding - 10, y + 4);
    });
    ctx.stroke();

    // Gambar garis threshold merah
    const thresholdY = padding + height - (threshold / 100) * height;
    ctx.beginPath();
    ctx.strokeStyle = "#ef4444";
    ctx.setLineDash([5, 5]);
    ctx.moveTo(padding, thresholdY);
    ctx.lineTo(padding + width, thresholdY);
    ctx.stroke();
    ctx.setLineDash([]);

    // Gambar data
    const stepX = points.length > 1 ? width / (points.length - 1) : width;
    
    ctx.beginPath();
    ctx.strokeStyle = "#2563eb";
    ctx.lineWidth = 2;
    
    points.forEach((point, i) => {
      const x = padding + i * stepX;
      const y = padding + height - (point.value / 100) * height;
      
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
      
      // Label sumbu X
      ctx.fillStyle = "#64748b";
      ctx.textAlign = "center";
      ctx.fillText(point.label, x, padding + height + 20);
    });
    ctx.stroke();

    // Gambar titik data
    points.forEach((point, i) => {
      const x = padding + i * stepX;
      const y = padding + height - (point.value / 100) * height;
      
      ctx.beginPath();
      ctx.fillStyle = "#ffffff";
      ctx.arc(x, y, 4, 0, Math.PI * 2);
      ctx.fill();
      ctx.stroke();
    });

  }, [points, threshold]);

  return (
    <div style={{ width: "100%", overflowX: "auto" }}>
      <canvas 
        ref={canvasRef} 
        width={800} 
        height={300} 
        style={{ width: "100%", minWidth: "600px", height: "auto" }}
      />
    </div>
  );
}
