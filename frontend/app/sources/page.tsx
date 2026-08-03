"use client";

import Link from "next/link";
import Shell from "@/components/Shell";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { ScoreBadge, StatusPill } from "@/components/widgets";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Database, FileUp, PlugZap, Search, AlertCircle, ArrowRight } from "lucide-react";
import { Input } from "@/components/ui/input";

export default function SourcesPage() {
  const [datasets, setDatasets] = useState<any[]>([]);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");

  useEffect(() => {
    api("/datasets").then(setDatasets).catch((e) => setError(e.message));
  }, []);

  const filteredDatasets = datasets.filter((d) => 
    d.name.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <Shell 
      title="Data Sources" 
      subtitle="Kelola koneksi dan sumber data untuk dianalisis"
    >
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
        <Card className="bg-primary/5 border-primary/20">
          <CardHeader>
            <CardTitle className="text-lg flex items-center">
              <FileUp className="mr-2 h-5 w-5 text-primary" />
              Upload File Lokal
            </CardTitle>
            <CardDescription>Unggah dataset berupa file CSV atau Excel untuk dianalisis dan diprofiling.</CardDescription>
          </CardHeader>
          <CardContent>
            <Button  className="w-full sm:w-auto"render={<Link href="/datasets/upload" />} nativeButton={false}>
  Upload File
</Button>
          </CardContent>
        </Card>
        
        <Card className="bg-muted/30">
          <CardHeader>
            <CardTitle className="text-lg flex items-center">
              <PlugZap className="mr-2 h-5 w-5 text-muted-foreground" />
              Koneksi Database
            </CardTitle>
            <CardDescription>Hubungkan ke PostgreSQL, MySQL, SQL Server, atau Data Warehouse lainnya.</CardDescription>
          </CardHeader>
          <CardContent>
            <Button variant="outline" className="w-full sm:w-auto" onClick={() => alert("Fitur connect database sedang dalam pengembangan.")}>
              Setup Koneksi Baru
            </Button>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
            <div>
              <CardTitle>Aset Data Tersimpan</CardTitle>
              <CardDescription>Semua dataset dan koneksi yang telah dikonfigurasi.</CardDescription>
            </div>
            <div className="relative w-full sm:w-64">
              <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input
                type="search"
                placeholder="Cari sumber data..."
                className="pl-8"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {error && (
            <div className="bg-destructive/15 text-destructive p-4 rounded-md border border-destructive/20 mb-6 flex items-center gap-2">
              <AlertCircle className="h-5 w-5" />
              <p>{error}</p>
            </div>
          )}
          
          {datasets.length > 0 ? (
            filteredDatasets.length > 0 ? (
              <div className="rounded-md border">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Nama Dataset</TableHead>
                      <TableHead>Terakhir Diperbarui</TableHead>
                      <TableHead>Baris</TableHead>
                      <TableHead>Skor Kualitas</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead className="text-right">Aksi</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filteredDatasets.map((d) => (
                      <TableRow key={d.id}>
                        <TableCell>
                          <div className="font-medium flex items-center gap-2">
                            <Database className="h-4 w-4 text-muted-foreground" />
                            {d.name}
                          </div>
                          <div className="text-xs text-muted-foreground mt-1 ml-6">
                            {d.columns?.length || 0} Kolom
                          </div>
                        </TableCell>
                        <TableCell className="text-sm text-muted-foreground">
                          {new Date(d.updated_at + "Z").toLocaleString("id-ID", { 
                            day: 'numeric', month: 'short', year: 'numeric', 
                            hour: '2-digit', minute: '2-digit' 
                          })}
                        </TableCell>
                        <TableCell className="font-medium">
                          {d.total_rows ? d.total_rows.toLocaleString('id-ID') : "—"}
                        </TableCell>
                        <TableCell>
                          <ScoreBadge score={d.quality_score} />
                        </TableCell>
                        <TableCell>
                          <StatusPill status={d.status} />
                        </TableCell>
                        <TableCell className="text-right">
                          <Button variant="ghost" size="sm" render={<Link href={`/datasets/${d.id}`} />} nativeButton={false}>
  Detail
                              <ArrowRight className="ml-2 h-3.5 w-3.5" />
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
                <p className="text-muted-foreground">Tidak ada sumber data yang cocok dengan "{search}"</p>
                <Button variant="link" onClick={() => setSearch("")}>Hapus pencarian</Button>
              </div>
            )
          ) : (
            <div className="flex flex-col items-center justify-center p-12 text-center border rounded-md border-dashed h-64 bg-muted/5">
              <Database className="h-12 w-12 text-muted-foreground mb-4 opacity-20" />
              <h3 className="text-lg font-medium mb-2">Belum ada sumber data</h3>
              <p className="text-muted-foreground mb-6 max-w-md">
                Silakan upload file CSV/Excel atau hubungkan database untuk memulai profiling dan memantau kualitas data Anda.
              </p>
              <Button render={<Link href="/datasets/upload" />} nativeButton={false}>
  <FileUp className="mr-2 h-4 w-4" />
                  Upload Dataset Pertama
</Button>
            </div>
          )}
        </CardContent>
      </Card>
    </Shell>
  );
}
