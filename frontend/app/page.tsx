"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import Shell from "@/components/Shell";
import { ScoreBadge, StatusPill } from "@/components/widgets";
import { api } from "@/lib/api";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Activity, Database, AlertCircle, Copy, ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function DashboardPage() {
  const [summary, setSummary] = useState<any>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api("/dashboard/summary").then(setSummary).catch((e) => setError(e.message));
    const t = setInterval(() => {
      api("/dashboard/summary").then(setSummary).catch(() => {});
    }, 10000);
    return () => clearInterval(t);
  }, []);

  return (
    <Shell title="Dashboard" subtitle="Ringkasan kualitas data organisasi Anda">
      {error && (
        /* role=alert: kegagalan polling diumumkan ke pembaca layar tanpa perlu fokus */
        <div
          role="alert"
          className="mb-4 flex items-center gap-2 rounded-md border border-destructive/20 bg-destructive-muted p-3 text-destructive"
        >
          <AlertCircle className="h-5 w-5 shrink-0" aria-hidden="true" />
          <p>{error}</p>
        </div>
      )}
      
      {/* Density 8/10: gap 12px antar KPI card */}
      <div className="mb-4 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Total Dataset</CardTitle>
            <Database className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{summary?.total_datasets ?? "—"}</div>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Rata-rata Skor Kualitas</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{summary?.avg_quality_score ?? "—"}</div>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Duplikat Terdeteksi</CardTitle>
            <Copy className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{summary?.duplicate_clusters ?? "—"}</div>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Alert Aktif</CardTitle>
            <AlertCircle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{summary?.active_alerts ?? "—"}</div>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Dataset Terbaru</CardTitle>
                <CardDescription>Dataset yang baru-baru ini diunggah atau diproses.</CardDescription>
              </div>
              <Button variant="outline" size="sm" render={<Link href="/datasets/upload" />} nativeButton={false}>
  Upload Baru
</Button>
            </div>
          </CardHeader>
          <CardContent>
            {summary?.recent_datasets?.length ? (
              <div className="rounded-md border">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Nama Dataset</TableHead>
                      <TableHead>Terakhir Update</TableHead>
                      <TableHead>Skor</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead className="text-right">Aksi</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {summary.recent_datasets.map((d: any) => (
                      <TableRow key={d.id} className="transition-colors duration-200 hover:bg-muted/50">
                        <TableCell className="font-medium">{d.name}</TableCell>
                        <TableCell className="text-muted-foreground text-sm">
                          {new Date(d.updated_at + "Z").toLocaleDateString("id-ID", { day: 'numeric', month: 'short' })}
                        </TableCell>
                        <TableCell>
                          <ScoreBadge score={d.quality_score} />
                        </TableCell>
                        <TableCell>
                          {d.pending_clusters > 0 ? (
                            <span className="inline-flex items-center rounded-full border border-warning/30 px-2.5 py-0.5 text-xs font-semibold text-warning">Butuh Review</span>
                          ) : (
                            <StatusPill status={d.status} />
                          )}
                        </TableCell>
                        <TableCell className="text-right">
                          <Button variant="ghost" size="sm"  className="h-8"render={<Link href={`/datasets/${d.id}`} />} nativeButton={false}>
  Lihat
                              <ArrowRight className="ml-2 h-3.5 w-3.5" />
</Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center p-8 text-center border rounded-md border-dashed">
                <Database className="h-10 w-10 text-muted-foreground mb-3 opacity-20" />
                <p className="text-muted-foreground mb-4">Belum ada dataset yang diunggah.</p>
                <Button render={<Link href="/datasets/upload" />} nativeButton={false}>
  Upload Dataset Pertama
</Button>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Aktivitas Terbaru</CardTitle>
            <CardDescription>Log sistem dan pemrosesan data.</CardDescription>
          </CardHeader>
          <CardContent>
            {summary?.recent_activity?.length ? (
              <div className="space-y-4">
                {summary.recent_activity.map((a: any, i: number) => (
                  <div key={i} className="flex flex-col gap-1 pb-4 border-b last:border-0 last:pb-0">
                    <p className="text-sm font-medium">{a.message}</p>
                    <p className="text-xs text-muted-foreground">
                      {new Date(a.created_at + "Z").toLocaleString("id-ID")}
                    </p>
                  </div>
                ))}
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center p-8 text-center border rounded-md border-dashed h-[300px]">
                <Activity className="h-10 w-10 text-muted-foreground mb-3 opacity-20" />
                <p className="text-muted-foreground text-sm">Belum ada aktivitas tercatat.</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </Shell>
  );
}
