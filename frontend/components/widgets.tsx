"use client";

import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { CheckCircle2, CircleDashed, Loader2, TriangleAlert, XCircle } from "lucide-react";

/* Warna hardcoded (emerald/amber/rose-500) diganti token status semantik.
   Alasan: guideline shadcn "Use CSS variables for colors" (severity High) — nilai mentah
   tidak ikut berubah di dark mode, jadi kontrasnya jatuh. Token di globals.css punya
   nilai terpisah untuk light & dark yang sudah diukur >= 4.5:1. */

export function ScoreBadge({ score }: { score: number | null | undefined }) {
  if (score == null) return <span className="text-muted-foreground">—</span>;

  const formattedScore = score.toFixed(1).replace(/\.0$/, "");

  /* Ikon + teks mendampingi warna — "jangan mengandalkan warna saja untuk
     menyampaikan makna" (Charts & Data / Accessibility). */
  const tier =
    score >= 90
      ? {
          label: "Excellent",
          Icon: CheckCircle2,
          cls: "bg-success-muted text-success border-success/30",
        }
      : score >= 70
        ? {
            label: "Fair",
            Icon: TriangleAlert,
            cls: "bg-warning-muted text-warning border-warning/30",
          }
        : {
            label: "Poor",
            Icon: XCircle,
            cls: "bg-destructive-muted text-destructive border-destructive/30",
          };

  return (
    <Badge variant="outline" className={`gap-1 ${tier.cls}`}>
      <tier.Icon className="h-3 w-3 shrink-0" aria-hidden="true" />
      <span className="tabular">{formattedScore}%</span>
      <span className="font-normal">({tier.label})</span>
    </Badge>
  );
}

export function StatusPill({ status }: { status: string }) {
  if (status === "pending")
    return (
      <Badge variant="outline" className="gap-1 border-warning/30 text-warning">
        <CircleDashed className="h-3 w-3 shrink-0" aria-hidden="true" />
        Menunggu
      </Badge>
    );

  if (status === "processing")
    return (
      <Badge variant="outline" className="gap-1 border-info/30 text-info">
        {/* Loader mengikuti prefers-reduced-motion via aturan global di globals.css */}
        <Loader2 className="h-3 w-3 shrink-0 animate-spin" aria-hidden="true" />
        Diproses
      </Badge>
    );

  if (status === "completed")
    return (
      <Badge variant="outline" className="gap-1 border-success/30 text-success">
        <CheckCircle2 className="h-3 w-3 shrink-0" aria-hidden="true" />
        Selesai
      </Badge>
    );

  if (status === "failed")
    return (
      <Badge variant="outline" className="gap-1 border-destructive/30 text-destructive">
        <XCircle className="h-3 w-3 shrink-0" aria-hidden="true" />
        Gagal
      </Badge>
    );

  return <Badge variant="outline">{status}</Badge>;
}

export function ProgressBar({
  label,
  value,
  max = 100,
}: {
  label: string;
  value: number;
  max?: number;
}) {
  const percent = Math.min(Math.max((value / max) * 100, 0), 100);

  const tone =
    percent >= 90 ? "text-success" : percent >= 70 ? "text-warning" : "text-destructive";

  return (
    <div className="mb-2 w-full">
      <div className="mb-1.5 flex justify-between text-sm">
        <span className="text-muted-foreground">{label}</span>
        <span className={`tabular font-medium ${tone}`}>{percent.toFixed(1)}%</span>
      </div>
      <Progress value={percent} className="h-1.5" aria-label={`${label}: ${percent.toFixed(1)}%`} />
    </div>
  );
}
