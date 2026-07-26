"use client";

import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";

export function ScoreBadge({ score }: { score: number | null | undefined }) {
  if (score == null) return <span className="text-muted-foreground">—</span>;
  
  // Bulatkan skor ke 1 angka di belakang koma (atau 0 jika bulat)
  const formattedScore = score.toFixed(1).replace(/\.0$/, '');
  
  if (score >= 90) return <Badge variant="default" className="bg-emerald-500/15 text-emerald-600 hover:bg-emerald-500/25 border-emerald-500/20">{formattedScore}% (Excellent)</Badge>;
  if (score >= 70) return <Badge variant="secondary" className="bg-amber-500/15 text-amber-600 hover:bg-amber-500/25 border-amber-500/20">{formattedScore}% (Fair)</Badge>;
  return <Badge variant="destructive" className="bg-rose-500/15 text-rose-600 hover:bg-rose-500/25 border-rose-500/20">{formattedScore}% (Poor)</Badge>;
}

export function StatusPill({ status }: { status: string }) {
  if (status === "pending") return <Badge variant="outline" className="text-amber-500 border-amber-500/30">Menunggu</Badge>;
  if (status === "processing") return (
    <Badge variant="outline" className="text-blue-500 border-blue-500/30">
      <span className="mr-1.5 flex h-2 w-2">
        <span className="animate-ping absolute inline-flex h-2 w-2 rounded-full bg-blue-400 opacity-75"></span>
        <span className="relative inline-flex rounded-full h-2 w-2 bg-blue-500"></span>
      </span>
      Diproses
    </Badge>
  );
  if (status === "completed") return <Badge variant="outline" className="text-emerald-500 border-emerald-500/30">Selesai</Badge>;
  if (status === "failed") return <Badge variant="outline" className="text-rose-500 border-rose-500/30">Gagal</Badge>;
  
  return <Badge variant="outline">{status}</Badge>;
}

export function ProgressBar({ label, value, max = 100 }: { label: string, value: number, max?: number }) {
  const percent = Math.min(Math.max((value / max) * 100, 0), 100);

  let indicatorClassName = "bg-emerald-500";
  if (percent < 90) indicatorClassName = "bg-amber-500";
  if (percent < 70) indicatorClassName = "bg-rose-500";

  return (
    <div className="w-full mb-2">
      <div className="flex justify-between mb-1.5 text-sm">
        <span className="text-muted-foreground">{label}</span>
        <span className="font-medium">{percent.toFixed(1)}%</span>
      </div>
      <Progress value={percent} className="h-1.5" />
    </div>
  );
}
