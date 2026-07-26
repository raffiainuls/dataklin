"use client";

import Link from "next/link";
import Shell from "@/components/Shell";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { GitBranch, Plus, FileText, Settings, Search } from "lucide-react";
import { Input } from "@/components/ui/input";

export default function PipelinesPage() {
  const [datasets, setDatasets] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");

  useEffect(() => {
    // Di MVP, datasets juga bertindak sebagai representasi pipeline/job
    api("/datasets/")
      .then((data) => {
        setDatasets(data);
        setLoading(false);
      })
      .catch((err) => {
        console.error(err);
        setLoading(false);
      });
  }, []);

  const filteredDatasets = datasets.filter((d) => 
    d.name.toLowerCase().includes(search.toLowerCase())
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
          ) : datasets.length > 0 ? (
            filteredDatasets.length > 0 ? (
              <div className="rounded-md border">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Nama Pipeline</TableHead>
                      <TableHead>Sumber Data</TableHead>
                      <TableHead>Jadwal</TableHead>
                      <TableHead>Aturan (Rules)</TableHead>
                      <TableHead className="text-right">Aksi</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filteredDatasets.map((d) => (
                      <TableRow key={d.id}>
                        <TableCell>
                          <div className="font-medium flex items-center gap-2">
                            <GitBranch className="h-4 w-4 text-muted-foreground" />
                            Pipeline for {d.name}
                          </div>
                        </TableCell>
                        <TableCell className="text-muted-foreground">
                          {d.name} <span className="text-xs">({d.id})</span>
                        </TableCell>
                        <TableCell>
                          <span className="inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold text-muted-foreground">
                            Manual
                          </span>
                        </TableCell>
                        <TableCell>
                          <Button variant="outline" size="sm"  className="h-8"render={<Link href={`/rules?dataset_id=${d.id}`} />} nativeButton={false}>
  <FileText className="h-3.5 w-3.5 mr-2" />
                              Kelola Rules
</Button>
                        </TableCell>
                        <TableCell className="text-right">
                          <Button variant="ghost" size="sm" render={<Link href={`/pipelines/${d.id}`} />} nativeButton={false}>
  <Settings className="h-4 w-4 mr-2" />
                              Edit Config
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
