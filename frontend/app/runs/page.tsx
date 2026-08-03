"use client";

import Link from "next/link";
import Shell from "@/components/Shell";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { StatusPill } from "@/components/widgets";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Activity, Clock, Database, AlertCircle, FileSearch } from "lucide-react";
import { Badge } from "@/components/ui/badge";

export default function RunsPage() {
  const [datasets, setDatasets] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    // For MVP, datasets act as "runs" since upload triggers processing
    api("/datasets")
      .then(ds => {
        setDatasets(ds);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  return (
    <Shell 
      title="Runs & Results" 
      subtitle="Pantau eksekusi pipeline dan review anomali (Stewarding)"
    >
      <div className="space-y-6 max-w-6xl">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity className="h-5 w-5 text-primary" />
              Riwayat Eksekusi Job
            </CardTitle>
            <CardDescription>Daftar eksekusi pipeline yang memproses dan memvalidasi dataset</CardDescription>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="flex flex-col items-center justify-center p-8 text-center border rounded-md border-dashed h-48 bg-muted/5">
                <div className="animate-spin h-8 w-8 border-b-2 border-primary rounded-full mb-4"></div>
                <p className="text-muted-foreground">Memuat riwayat...</p>
              </div>
            ) : datasets.length > 0 ? (
              <div className="rounded-md border">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Job ID (Dataset)</TableHead>
                      <TableHead>Waktu Mulai</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Anomali Ditemukan</TableHead>
                      <TableHead>Stewarding</TableHead>
                      <TableHead className="text-right">Aksi</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {datasets.map((d) => (
                      <TableRow key={d.id}>
                        <TableCell>
                          <div className="font-medium text-foreground">{d.name}</div>
                          <div className="flex items-center text-xs text-muted-foreground mt-1">
                            <Database className="h-3 w-3 mr-1" />
                            ID: {d.id}
                          </div>
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center text-sm">
                            <Clock className="h-4 w-4 mr-1 text-muted-foreground" />
                            {new Date(d.created_at + "Z").toLocaleDateString("id-ID", {
                              day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit'
                            })}
                          </div>
                        </TableCell>
                        <TableCell>
                          <StatusPill status={d.status} />
                        </TableCell>
                        <TableCell>
                          {d.total_anomalies > 0 ? (
                            <div className="flex items-center text-destructive font-medium text-sm">
                              <AlertCircle className="h-4 w-4 mr-1" />
                              {d.total_anomalies} Issues
                            </div>
                          ) : (
                            <span className="text-emerald-600 font-medium text-sm flex items-center">
                              <svg className="w-4 h-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" /></svg>
                              Bersih
                            </span>
                          )}
                        </TableCell>
                        <TableCell>
                          {d.pending_clusters > 0 ? (
                            <Button 
                              variant="outline" 
                              size="sm" 
                              className="h-8 border-amber-500/30 text-amber-600 hover:bg-amber-50 hover:text-amber-700 bg-amber-500/5"
                              render={<Link href={`/review`} />}
                              nativeButton={false}
                            >
                              Review {d.pending_clusters} Clusters
                            </Button>
                          ) : (
                            <span className="text-muted-foreground text-sm italic">Tidak Ada</span>
                          )}
                        </TableCell>
                        <TableCell className="text-right">
                          <Button 
                            variant="default" 
                            size="sm" 
                            render={<Link href={`/datasets/${d.id}`} />}
                            nativeButton={false}
                          >
                            Lihat Scorecard
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center p-8 text-center border rounded-md border-dashed h-48 bg-muted/5">
                <FileSearch className="h-8 w-8 text-muted-foreground mb-3 opacity-20" />
                <p className="text-muted-foreground">Belum ada eksekusi pipeline yang tercatat.</p>
                <Button 
                  variant="outline" 
                  className="mt-4"
                  render={<Link href="/datasets/upload" />}
                  nativeButton={false}
                >
                  Upload Dataset Baru
                </Button>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </Shell>
  );
}
