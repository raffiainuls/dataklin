"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import Shell from "@/components/Shell";
import { ScoreBadge, StatusPill, ProgressBar } from "@/components/widgets";
import { api } from "@/lib/api";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ArrowLeft, Settings, Search, Download, AlertCircle, FileText, BarChart3, Database, ChevronDown, ChevronRight } from "lucide-react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";

export default function DatasetDetail() {
  const params = useParams<{ id: string }>();
  const [data, setData] = useState<any>(null);
  const [clusters, setClusters] = useState<any[]>([]);
  const [expandedClusters, setExpandedClusters] = useState<Record<string, boolean>>({});
  const [error, setError] = useState("");
  const router = useRouter();

  useEffect(() => {
    fetchData();
    const t = setInterval(fetchData, 5000);
    return () => clearInterval(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params.id]);

  function fetchData() {
    api(`/datasets/${params.id}`).then(setData).catch((e) => setError(e.message));
    api(`/datasets/${params.id}/clusters?with_members=true`).then(setClusters).catch(console.error);
  }

  const toggleCluster = (id: string) => {
    setExpandedClusters(prev => ({ ...prev, [id]: !prev[id] }));
  };

  if (error) {
    return (
      <Shell title="Error">
        <div className="bg-destructive/15 text-destructive p-4 rounded-md border border-destructive/20 flex items-center gap-2">
          <AlertCircle className="h-5 w-5" />
          <p>{error}</p>
        </div>
      </Shell>
    );
  }
  
  if (!data) {
    return (
      <Shell title="Memuat Data...">
        <div className="flex flex-col items-center justify-center h-64 border rounded-lg border-dashed">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mb-4"></div>
          <p className="text-muted-foreground">Memuat profil dataset...</p>
        </div>
      </Shell>
    );
  }

  const cols = data.columns || [];
  const rules = data.rules || [];
  const totalAnomalies = data.total_anomalies || 0;

  return (
    <Shell
      title={data.name}
      subtitle={`Diupload pada ${new Date(data.created_at + "Z").toLocaleString("id-ID", { dateStyle: 'full', timeStyle: 'short' })}`}
    >
      <div className="flex flex-wrap items-center gap-2 mb-8">
        <Button variant="outline" size="sm" onClick={() => router.back()}>
          <ArrowLeft className="h-4 w-4 mr-2" />
          Kembali
        </Button>
        <Button variant="outline" size="sm" render={<Link href={`/pipelines/${data.id}`} />} nativeButton={false}>
  <Settings className="h-4 w-4 mr-2" />
            Edit Pipeline
</Button>
        <Button variant="outline" size="sm" render={<Link href={`/rules?dataset_id=${data.id}`} />} nativeButton={false}>
  <FileText className="h-4 w-4 mr-2" />
            Kelola Aturan
</Button>
        
        {data.pending_clusters > 0 && (
          <Button size="sm" className="bg-amber-600 hover:bg-amber-700 text-white" render={<Link href={`/review`} />} nativeButton={false}>
  <Search className="h-4 w-4 mr-2" />
              Review {data.pending_clusters} Cluster
</Button>
        )}
        
        <Button 
          variant="secondary" 
          size="sm"
          className="ml-auto"
          onClick={() => {
            api(`/datasets/${data.id}/golden/export`)
              .then((b) => {
                const url = window.URL.createObjectURL(b);
                const a = document.createElement("a");
                a.href = url;
                a.download = `golden_record_${data.id}.csv`;
                a.click();
              })
              .catch((e) => alert("Export gagal: " + e.message));
          }}
        >
          <Download className="h-4 w-4 mr-2" />
          Export Golden Record
        </Button>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Data Quality Score</CardTitle>
            <BarChart3 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold mt-1">
              <ScoreBadge score={data.quality_score} />
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Total Baris Data</CardTitle>
            <Database className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{data.total_rows?.toLocaleString("id-ID") || 0}</div>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Total Pelanggaran</CardTitle>
            <AlertCircle className={`h-4 w-4 ${totalAnomalies > 0 ? 'text-destructive' : 'text-muted-foreground'}`} />
          </CardHeader>
          <CardContent>
            <div className={`text-3xl font-bold ${totalAnomalies > 0 ? 'text-destructive' : ''}`}>
              {totalAnomalies.toLocaleString("id-ID")}
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Cluster Perlu Review</CardTitle>
            <Search className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{data.pending_clusters}</div>
          </CardContent>
        </Card>
      </div>

      <Tabs defaultValue="profiling" className="w-full">
        <TabsList className="grid w-full grid-cols-3 lg:w-[600px]">
          <TabsTrigger value="profiling">Profil Kolom</TabsTrigger>
          <TabsTrigger value="rules">Hasil Validasi Aturan</TabsTrigger>
          <TabsTrigger value="clusters">Hasil Temuan Cluster</TabsTrigger>
        </TabsList>
        
        <TabsContent value="profiling" className="mt-4">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {cols.length ? (
              cols.map((c: any) => (
                <Card key={c.name} className="flex flex-col h-full border-muted/50 hover:border-border transition-colors shadow-sm">
                  <CardHeader className="bg-muted/10 border-b pb-4">
                    <div className="flex justify-between items-start gap-2">
                      <div className="space-y-1">
                        <CardTitle className="text-base text-primary/90 break-all">{c.name}</CardTitle>
                        <CardDescription className="text-xs">Profil Kualitas Data Kolom</CardDescription>
                      </div>
                      <Badge variant="secondary" className="font-mono text-xs font-normal">
                        {c.inferred_type}
                      </Badge>
                    </div>
                  </CardHeader>
                  <CardContent className="p-4 flex-1 space-y-5">
                    <div className="space-y-2">
                      <div className="flex justify-between items-center text-sm">
                        <span className="text-muted-foreground font-medium flex items-center gap-1.5">
                          <div className="w-2 h-2 rounded-full bg-emerald-500"></div>
                          Kelengkapan (Terisi)
                        </span>
                        <span className="font-semibold">{c.completeness ? (c.completeness * 100).toFixed(1) : "0"}%</span>
                      </div>
                      <div className="w-full h-1.5 bg-secondary rounded-full overflow-hidden">
                        <div
                          className="h-full bg-emerald-500 transition-all duration-500"
                          style={{ width: `${c.completeness ? c.completeness * 100 : 0}%` }}
                        />
                      </div>
                    </div>

                    <div className="space-y-2">
                      <div className="flex justify-between items-center text-sm">
                        <span className="text-muted-foreground font-medium flex items-center gap-1.5">
                          <div className="w-2 h-2 rounded-full bg-blue-500"></div>
                          Keunikan (Unique)
                        </span>
                        <span className="font-semibold">{c.uniqueness ? (c.uniqueness * 100).toFixed(1) : "0"}%</span>
                      </div>
                      <div className="w-full h-1.5 bg-secondary rounded-full overflow-hidden">
                        <div
                          className="h-full bg-blue-500 transition-all duration-500"
                          style={{ width: `${c.uniqueness ? c.uniqueness * 100 : 0}%` }}
                        />
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))
            ) : (
              <div className="col-span-full flex flex-col items-center justify-center p-8 text-center border rounded-md border-dashed h-48 bg-muted/5">
                <BarChart3 className="h-8 w-8 text-muted-foreground mb-3 opacity-20" />
                <p className="text-muted-foreground">Belum ada hasil profil (proses mungkin masih berjalan)</p>
              </div>
            )}
          </div>
        </TabsContent>
        
        <TabsContent value="rules" className="mt-4">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle>Pelanggaran Aturan (Anomali)</CardTitle>
                  <CardDescription>Baris data yang tidak sesuai dengan aturan kualitas yang ditetapkan.</CardDescription>
                </div>
                <Button variant="outline" size="sm" render={<Link href={`/rules?dataset_id=${data.id}`} />} nativeButton={false}>
  Atur Rule
</Button>
              </div>
            </CardHeader>
            <CardContent>
              {rules.length ? (
                <div className="rounded-md border">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Kolom</TableHead>
                        <TableHead>Aturan (Rule)</TableHead>
                        <TableHead>Status</TableHead>
                        <TableHead>Semua Data Gagal</TableHead>
                        <TableHead className="text-right">Baris Gagal</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {rules.map((r: any) => {
                        const hasViolations = r.last_result?.violations > 0;
                        return (
                          <TableRow key={r.id} className={hasViolations ? "bg-destructive/5" : ""}>
                            <TableCell className="font-medium">{r.column_name}</TableCell>
                            <TableCell>{r.description || r.rule_label}</TableCell>
                            <TableCell>
                              {r.enabled ? (
                                <Badge variant="outline" className="text-emerald-600 border-emerald-600/30">Aktif</Badge>
                              ) : (
                                <Badge variant="outline" className="text-muted-foreground">Nonaktif</Badge>
                              )}
                            </TableCell>
                            <TableCell>
                              {r.last_result?.samples?.length ? (
                                <div className="flex max-h-48 max-w-md flex-wrap gap-1.5 overflow-y-auto pr-1">
                                  {r.last_result.samples.map((sample: any, index: number) => (
                                    <span
                                      key={`${sample.row}-${index}`}
                                      className="inline-flex rounded border border-destructive/20 bg-destructive/5 px-2 py-1 text-xs"
                                      title={`Baris ${sample.row}`}
                                    >
                                      <span className="mr-1 text-muted-foreground">Baris {sample.row}:</span>
                                      <span className="max-w-48 truncate font-mono">
                                        {sample.value === null ? "(kosong)" : String(sample.value)}
                                      </span>
                                    </span>
                                  ))}
                                </div>
                              ) : (
                                <span className="text-xs text-muted-foreground">—</span>
                              )}
                            </TableCell>
                            <TableCell className={`text-right font-medium ${hasViolations ? 'text-destructive' : 'text-muted-foreground'}`}>
                              {r.last_result ? r.last_result.violations.toLocaleString('id-ID') : "—"}
                            </TableCell>
                          </TableRow>
                        );
                      })}
                    </TableBody>
                  </Table>
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center p-8 text-center border rounded-md border-dashed h-48">
                  <FileText className="h-8 w-8 text-muted-foreground mb-3 opacity-20" />
                  <p className="text-muted-foreground mb-4">Belum ada aturan validasi yang diatur.</p>
                  <Button variant="secondary" size="sm" render={<Link href={`/rules?dataset_id=${data.id}`} />} nativeButton={false}>
                    Atur Rule Sekarang
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
        <TabsContent value="clusters" className="mt-4">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle>Temuan Cluster Duplikat</CardTitle>
                  <CardDescription>Record data yang terdeteksi sebagai entitas yang sama (kandidat duplikat).</CardDescription>
                </div>
                {data.pending_clusters > 0 && (
                  <Button variant="outline" size="sm" render={<Link href={`/review`} />} nativeButton={false}>
                    Review Semua Cluster
                  </Button>
                )}
              </div>
            </CardHeader>
            <CardContent>
              {clusters.length > 0 ? (
                <div className="rounded-md border">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead className="w-[50px]"></TableHead>
                        <TableHead>Cluster ID</TableHead>
                        <TableHead>Status</TableHead>
                        <TableHead>Jumlah Record</TableHead>
                        <TableHead>Cohesion</TableHead>
                        <TableHead className="text-right">Aksi</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {clusters.map((c) => {
                        const isExpanded = expandedClusters[c.id];
                        const columns = c.members?.length ? Object.keys(c.members[0].record_data) : [];
                        return (
                          <React.Fragment key={c.id}>
                            <TableRow className={isExpanded ? "bg-muted/20" : ""}>
                              <TableCell>
                                <Button variant="ghost" size="sm" className="h-8 w-8 p-0" onClick={() => toggleCluster(c.id)}>
                                  {isExpanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                                </Button>
                              </TableCell>
                              <TableCell className="font-medium"><code className="bg-muted px-2 py-1 rounded text-xs">{c.cluster_key}</code></TableCell>
                              <TableCell><StatusPill status={c.status} /></TableCell>
                              <TableCell>{c.record_count} record</TableCell>
                              <TableCell>
                                <ProgressBar label="Cohesion" value={Math.round(c.cohesion * 100)} />
                              </TableCell>
                              <TableCell className="text-right">
                                {c.status === "pending" && (
                                  <Button variant="default" size="sm" render={<Link href={`/review/${c.id}`} />} nativeButton={false}>
                                    Review →
                                  </Button>
                                )}
                              </TableCell>
                            </TableRow>
                            {isExpanded && c.members && (
                              <TableRow className="bg-muted/5">
                                <TableCell colSpan={6} className="p-4">
                                  <div className="border rounded-md bg-background overflow-x-auto">
                                    <Table>
                                      <TableHeader>
                                        <TableRow>
                                          <TableHead className="bg-muted/20">Record ID</TableHead>
                                          {columns.map(col => (
                                            <TableHead key={col} className="bg-muted/20 whitespace-nowrap">{col}</TableHead>
                                          ))}
                                        </TableRow>
                                      </TableHeader>
                                      <TableBody>
                                        {c.members.map((m: any, i: number) => (
                                          <TableRow key={m.id}>
                                            <TableCell className="font-medium whitespace-nowrap border-r bg-muted/10">
                                              r-{m.record_index}
                                            </TableCell>
                                            {columns.map(col => {
                                              const isDiff = c.diff_columns?.includes(col);
                                              return (
                                                <TableCell key={col} className={isDiff ? "bg-amber-500/5 text-amber-700 font-medium" : ""}>
                                                  {m.record_data[col] === null || m.record_data[col] === "" ? (
                                                    <span className="text-muted-foreground/50 italic">(kosong)</span>
                                                  ) : (
                                                    String(m.record_data[col])
                                                  )}
                                                </TableCell>
                                              )
                                            })}
                                          </TableRow>
                                        ))}
                                      </TableBody>
                                    </Table>
                                  </div>
                                </TableCell>
                              </TableRow>
                            )}
                          </React.Fragment>
                        );
                      })}
                    </TableBody>
                  </Table>
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center p-8 text-center border rounded-md border-dashed h-48">
                  <Search className="h-8 w-8 text-muted-foreground mb-3 opacity-20" />
                  <p className="text-muted-foreground mb-4">Tidak ada cluster duplikat yang ditemukan.</p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

      </Tabs>
    </Shell>
  );
}
