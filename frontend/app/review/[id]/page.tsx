"use client";

import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import Shell from "@/components/Shell";
import { StatusPill } from "@/components/widgets";
import { api } from "@/lib/api";
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { AlertCircle, SplitSquareHorizontal, Merge, ArrowLeft, SkipForward } from "lucide-react";

export default function ClusterReviewPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const [cluster, setCluster] = useState<any>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => {
    api(`/clusters/${params.id}`).then(setCluster).catch((e) => setError(e.message));
  }, [params.id]);

  useEffect(() => {
    load();
  }, [load]);

  async function act(action: () => Promise<any>, after?: () => void) {
    setBusy(true);
    setError("");
    try {
      await action();
      if (after) after();
      else load();
    } catch (e: any) {
      setError(e.message);
      load();
    } finally {
      setBusy(false);
    }
  }

  const confirm = () =>
    act(
      () => api(`/clusters/${params.id}/confirm`, { method: "POST" }),
      () => router.push(`/golden/${params.id}`)
    );
  const split = () =>
    act(
      () => api(`/clusters/${params.id}/split`, { method: "POST" }),
      () => router.push("/review")
    );
  const exclude = (memberId: number) =>
    act(() =>
      api(`/clusters/${params.id}/exclude-member`, {
        method: "POST",
        body: JSON.stringify({ member_id: memberId }),
      })
    );

  const pending = cluster?.status === "pending";
  const columns: string[] = cluster?.members?.length
    ? Array.from(
        new Set(cluster.members.flatMap((m: any) => Object.keys(m.record_data)))
      )
    : [];

  return (
    <Shell
      title={`Review Duplikat — ${cluster?.dataset_name || ""}`}
      subtitle={
        cluster
          ? `Cluster ID: ${cluster.cluster_key} · Ditemukan ${cluster.record_count} record kandidat terdeteksi sebagai entitas yang sama`
          : ""
      }
    >
      <div className="space-y-6">
        {error && (
          <div className="bg-destructive/15 text-destructive p-4 rounded-md border border-destructive/20 flex items-center gap-2">
            <AlertCircle className="h-5 w-5" />
            <p>{error}</p>
          </div>
        )}
        
        <div className="flex items-center">
          <Button variant="outline" size="sm" onClick={() => router.back()}>
            <ArrowLeft className="h-4 w-4 mr-2" />
            Kembali ke Daftar Review
          </Button>
        </div>

        {cluster && (
          <>
            {!pending && (
              <div className="bg-primary/10 text-primary p-4 rounded-md border border-primary/20 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <span>Cluster ini sudah direview:</span>
                  <StatusPill status={cluster.status} />
                  {cluster.reviewed_by && <span className="text-sm opacity-80">oleh {cluster.reviewed_by}</span>}
                </div>
                {cluster.status === "confirmed" && (
                  <Button variant="outline" size="sm" onClick={() => router.push(`/golden/${cluster.id}`)}>
                    Lihat Golden Record →
                  </Button>
                )}
              </div>
            )}

            <Card className="overflow-hidden">
              <CardHeader className="bg-muted/30 border-b pb-4">
                <CardTitle>Perbandingan Data</CardTitle>
                <CardDescription>Kolom yang disorot kuning memiliki nilai yang berbeda antar record.</CardDescription>
              </CardHeader>
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="bg-muted/10 min-w-[200px] border-r">Record ID</TableHead>
                      {columns.map(col => {
                        const isDiff = cluster.diff_columns?.includes(col);
                        return (
                          <TableHead key={col} className={`whitespace-nowrap ${isDiff ? 'bg-amber-500/10 text-amber-700' : 'bg-muted/10'}`}>
                            {col}
                            {isDiff && <span className="ml-2 text-[10px] uppercase tracking-wider text-amber-600 font-bold">(Berbeda)</span>}
                          </TableHead>
                        );
                      })}
                      {pending && cluster.members.length > 2 && (
                        <TableHead className="bg-muted/10 min-w-[150px]">Aksi</TableHead>
                      )}
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {cluster.members.map((m: any, i: number) => (
                      <TableRow key={m.id}>
                        <TableCell className="font-medium whitespace-nowrap border-r bg-muted/5 align-top">
                          <div className="flex flex-col">
                            <span className="font-semibold text-foreground">Record {i + 1}</span>
                            <span className="text-xs font-normal font-mono text-muted-foreground mt-1">ID: r-{m.record_index}</span>
                          </div>
                        </TableCell>
                        {columns.map(col => {
                          const isDiff = cluster.diff_columns?.includes(col);
                          const value = m.record_data[col];
                          const isEmpty = value === null || value === "";
                          return (
                            <TableCell key={col} className={isDiff ? "bg-amber-500/5 text-amber-700 font-medium align-top" : "align-top"}>
                              <div className={`break-words ${isEmpty ? 'text-muted-foreground/50 italic' : ''}`}>
                                {isEmpty ? "(kosong)" : String(value)}
                              </div>
                            </TableCell>
                          );
                        })}
                        {pending && cluster.members.length > 2 && (
                          <TableCell className="align-middle">
                            <Button
                              variant="outline"
                              size="sm"
                              className="text-destructive border-destructive/30 hover:bg-destructive/10 hover:text-destructive whitespace-nowrap"
                              disabled={busy}
                              onClick={() => exclude(m.id)}
                            >
                              <SplitSquareHorizontal className="h-4 w-4 mr-2 shrink-0" />
                              Keluarkan
                            </Button>
                          </TableCell>
                        )}
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </Card>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-6">
              <Card>
                <CardHeader>
                  <CardTitle>Status Kepastian (Confidence Score)</CardTitle>
                  <CardDescription>Tingkat kemiripan rata-rata antar record dalam cluster ini.</CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                  <div>
                    <div className="flex justify-between mb-2">
                      <span className="text-sm font-medium">Cluster Cohesion Score</span>
                      <span className="font-bold">{Math.round(cluster.cohesion * 100)}%</span>
                    </div>
                    <div className="w-full h-2.5 bg-secondary rounded-full overflow-hidden">
                      <div 
                        className={`h-full transition-all duration-500 ${
                          cluster.cohesion > 0.8 ? "bg-emerald-500" : 
                          cluster.cohesion > 0.5 ? "bg-amber-500" : "bg-destructive"
                        }`}
                        style={{ width: `${Math.round(cluster.cohesion * 100)}%` }} 
                      />
                    </div>
                  </div>

                  {cluster.pairs?.length > 0 && (
                    <div className="pt-4 border-t">
                      <h4 className="text-sm font-semibold mb-3">Detail Kemiripan Pasangan</h4>
                      <div className="space-y-2">
                        {cluster.pairs.map((p: any, i: number) => (
                          <div key={i} className="flex justify-between items-center bg-muted/50 p-2 px-3 rounded-md text-sm">
                            <span className="text-muted-foreground">r-{p.record_a} <span className="mx-2">↔</span> r-{p.record_b}</span>
                            <span className="font-medium">{Math.round(p.score * 100)}%</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>

              {pending && (
                <Card className="border-primary/20 bg-primary/5">
                  <CardHeader>
                    <CardTitle className="text-primary">Tindakan Stewarding</CardTitle>
                    <CardDescription>Putuskan apakah record-record ini merujuk ke entitas yang sama.</CardDescription>
                  </CardHeader>
                  <CardContent className="flex flex-col gap-3">
                    <Button 
                      size="lg" 
                      className="w-full justify-start h-auto py-4" 
                      disabled={busy} 
                      onClick={confirm}
                    >
                      <Merge className="h-5 w-5 mr-3 shrink-0" />
                      <div className="flex flex-col items-start text-left">
                        <span className="font-semibold text-base">Konfirmasi (Merge)</span>
                        <span className="text-xs opacity-90 font-normal">Gabungkan record ini menjadi satu Golden Record</span>
                      </div>
                    </Button>
                    
                    <Button 
                      variant="outline" 
                      size="lg" 
                      className="w-full justify-start h-auto py-4 border-destructive/50 text-destructive hover:bg-destructive/10 hover:text-destructive" 
                      disabled={busy} 
                      onClick={split}
                    >
                      <SplitSquareHorizontal className="h-5 w-5 mr-3 shrink-0" />
                      <div className="flex flex-col items-start text-left">
                        <span className="font-semibold text-base">Tolak (Split Semua)</span>
                        <span className="text-xs opacity-80 font-normal">Record ini adalah entitas yang berbeda</span>
                      </div>
                    </Button>
                    
                    <Button 
                      variant="secondary" 
                      size="lg" 
                      className="w-full justify-start h-auto py-4" 
                      disabled={busy} 
                      onClick={() => router.push("/review")}
                    >
                      <SkipForward className="h-5 w-5 mr-3 text-muted-foreground shrink-0" />
                      <div className="flex flex-col items-start text-left">
                        <span className="font-semibold text-base">Lewati Sementara</span>
                        <span className="text-xs text-muted-foreground font-normal">Kembali ke antrian review</span>
                      </div>
                    </Button>
                  </CardContent>
                </Card>
              )}
            </div>
          </>
        )}
      </div>
    </Shell>
  );
}
