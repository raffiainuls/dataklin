"use client";

import Link from "next/link";
import Shell from "@/components/Shell";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { GitBranch, Plus, FileText, Settings, Search, Play, Trash2 } from "lucide-react";
import { Input } from "@/components/ui/input";

const SCHEDULE_LABELS: Record<string, string> = {
  manual: "Manual",
  hourly: "Setiap Jam",
  daily: "Setiap Hari",
  weekly: "Setiap Minggu",
};

function modeLabel(p: any): string {
  if (p.enable_profiling && p.enable_deduplication) return "Profiling & Dedup";
  if (p.enable_deduplication) return "Dedup Saja";
  return "Profiling Saja";
}

export default function PipelinesPage() {
  const [pipelines, setPipelines] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [runningId, setRunningId] = useState<number | null>(null);

  function load() {
    api("/pipelines")
      .then((data) => {
        setPipelines(data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message || "Gagal memuat pipeline");
        setLoading(false);
      });
  }

  useEffect(() => {
    load();
  }, []);

  async function runNow(id: number) {
    setRunningId(id);
    try {
      await api(`/pipelines/${id}/run`, { method: "POST" });
      setTimeout(() => {
        load();
        setRunningId(null);
      }, 2500);
    } catch (err: any) {
      setError(err.message || "Gagal menjalankan pipeline");
      setRunningId(null);
    }
  }

  async function removePipeline(p: any) {
    if (!window.confirm(`Yakin ingin menghapus pipeline "${p.name}"?`)) return;
    try {
      await api(`/pipelines/${p.id}`, { method: "DELETE" });
      load();
    } catch (err: any) {
      setError(err.message || "Gagal menghapus pipeline");
    }
  }

  const filteredPipelines = pipelines.filter((p) =>
    p.name.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <Shell
      title="Configurations & Pipelines"
      subtitle="Atur rules data quality, deduplikasi, dan jadwal eksekusi"
    >
      <div className="flex justify-between items-center mb-6">
        <div>
          <h2 className="text-xl font-semibold">Pipelines</h2>
          <p className="text-muted-foreground">Kelola konfigurasi dan jadwal validasi data</p>
        </div>
        <Button render={<Link href="/pipelines/create" />} nativeButton={false}>
  <Plus className="mr-2 h-4 w-4" />
            Create Pipeline
</Button>
      </div>

      {error && (
        <div className="bg-destructive/15 text-destructive p-3 rounded-md border border-destructive/20 mb-4 text-sm">
          {error}
        </div>
      )}

      <Card>
        <CardHeader>
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
            <div>
              <CardTitle>Pipeline Tersimpan</CardTitle>
              <CardDescription>Semua konfigurasi pipeline yang berjalan untuk memvalidasi dataset.</CardDescription>
            </div>
            <div className="relative w-full sm:w-64">
              <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input
                type="search"
                placeholder="Cari pipeline..."
                className="pl-8"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex flex-col items-center justify-center p-8 h-48">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mb-4"></div>
              <p className="text-muted-foreground">Memuat pipelines...</p>
            </div>
          ) : pipelines.length > 0 ? (
            filteredPipelines.length > 0 ? (
              <div className="rounded-md border">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Nama Pipeline</TableHead>
                      <TableHead>Sumber Data</TableHead>
                      <TableHead>Opsi Pemrosesan</TableHead>
                      <TableHead>Jadwal</TableHead>
                      <TableHead>Run Terakhir</TableHead>
                      <TableHead className="text-right">Aksi</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filteredPipelines.map((p) => (
                      <TableRow key={p.id}>
                        <TableCell>
                          <div className="font-medium flex items-center gap-2">
                            <GitBranch className="h-4 w-4 text-muted-foreground" />
                            {p.name}
                          </div>
                        </TableCell>
                        <TableCell className="text-muted-foreground">
                          {p.dataset_name || "-"} <span className="text-xs">({p.dataset_id})</span>
                        </TableCell>
                        <TableCell className="text-muted-foreground">{modeLabel(p)}</TableCell>
                        <TableCell>
                          <span className="inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold text-muted-foreground">
                            {SCHEDULE_LABELS[p.schedule] || p.schedule}
                          </span>
                        </TableCell>
                        <TableCell>
                          {p.last_run_at ? (
                            <span className={p.last_run_status === "error" ? "text-destructive text-xs" : "text-xs text-muted-foreground"}>
                              {p.last_run_status === "error" ? "Gagal" : "Berhasil"} · {new Date(p.last_run_at).toLocaleString("id-ID")}
                            </span>
                          ) : (
                            <span className="text-xs text-muted-foreground">Belum pernah dijalankan</span>
                          )}
                        </TableCell>
                        <TableCell className="text-right space-x-1">
                          <Button variant="outline" size="sm" className="h-8" disabled={runningId === p.id}
                                 onClick={() => runNow(p.id)}>
                            <Play className="h-3.5 w-3.5 mr-2" />
                            {runningId === p.id ? "Menjalankan..." : "Run Now"}
                          </Button>
                          <Button variant="outline" size="sm" className="h-8" render={<Link href={`/rules?dataset_id=${p.dataset_id}`} />} nativeButton={false}>
  <FileText className="h-3.5 w-3.5 mr-2" />
                              Kelola Rules
</Button>
                          <Button variant="ghost" size="sm" render={<Link href={`/pipelines/${p.id}`} />} nativeButton={false}>
  <Settings className="h-4 w-4" />
</Button>
                          <Button variant="ghost" size="sm" className="text-destructive hover:text-destructive hover:bg-destructive/10"
                                 onClick={() => removePipeline(p)}>
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center p-8 text-center border rounded-md border-dashed h-48">
                <Search className="h-8 w-8 text-muted-foreground mb-3 opacity-20" />
                <p className="text-muted-foreground">Tidak ada pipeline yang cocok dengan "{search}"</p>
                <Button variant="link" onClick={() => setSearch("")}>Hapus pencarian</Button>
              </div>
            )
          ) : (
            <div className="flex flex-col items-center justify-center p-12 text-center border rounded-md border-dashed h-64 bg-muted/5">
              <GitBranch className="h-12 w-12 text-muted-foreground mb-4 opacity-20" />
              <h3 className="text-lg font-medium mb-2">Belum ada pipeline</h3>
              <p className="text-muted-foreground mb-6 max-w-md">
                Pipeline digunakan untuk mengatur validasi data otomatis dan memantau kualitasnya secara berkala.
              </p>
              <Button render={<Link href="/pipelines/create" />} nativeButton={false}>
  <Plus className="mr-2 h-4 w-4" />
                  Create Pipeline Baru
</Button>
            </div>
          )}
        </CardContent>
      </Card>
    </Shell>
  );
}
