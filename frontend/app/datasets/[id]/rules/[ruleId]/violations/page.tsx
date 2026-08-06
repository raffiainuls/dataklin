"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { AlertCircle, ArrowLeft } from "lucide-react";

import Shell from "@/components/Shell";
import { api } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

const PAGE_SIZE = 50;

function displayValue(value: unknown): string {
  if (value === null || value === undefined || value === "") return "(kosong)";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

export default function RuleViolationsPage() {
  const params = useParams<{ id: string; ruleId: string }>();
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState("");
  const [page, setPage] = useState(1);

  useEffect(() => {
    api(`/datasets/${params.id}/rules/${params.ruleId}/violations?page=${page}&page_size=${PAGE_SIZE}`)
      .then(setResult)
      .catch((err) => setError(err.message));
  }, [params.id, params.ruleId, page]);

  if (error) {
    return (
      <Shell title="Data Pelanggaran">
        <div className="flex items-center gap-2 rounded-md border border-destructive/20 bg-destructive/15 p-4 text-destructive">
          <AlertCircle className="h-5 w-5" />
          <p>{error}</p>
        </div>
      </Shell>
    );
  }

  if (!result) {
    return (
      <Shell title="Memuat Data Pelanggaran...">
        <div className="flex h-64 flex-col items-center justify-center rounded-lg border border-dashed">
          <div className="mb-4 h-8 w-8 animate-spin rounded-full border-b-2 border-primary" />
          <p className="text-muted-foreground">Memuat seluruh data yang melanggar...</p>
        </div>
      </Shell>
    );
  }

  const rows = result.rows || [];
  const totalPages = result.total_pages || 1;

  return (
    <Shell
      title="Data Pelanggaran Aturan"
      subtitle={`${result.dataset.name} — ${result.rule.description}`}
    >
      <div className="mb-6 flex flex-wrap items-center gap-3">
        <Button
          variant="outline"
          size="sm"
          render={<Link href={`/datasets/${params.id}`} />}
          nativeButton={false}
        >
          <ArrowLeft className="mr-2 h-4 w-4" /> Kembali ke Dataset
        </Button>
        <Badge variant="outline">Kolom: {result.rule.column_name}</Badge>
        <Badge variant="destructive">
          {result.total.toLocaleString("id-ID")} baris gagal
        </Badge>
      </div>

      {result.stored_total < result.total && (
        <div className="mb-4 rounded-md border border-warning/30 bg-warning-muted p-3 text-sm text-warning">
          Hasil ini dibuat sebelum penyimpanan seluruh pelanggaran diaktifkan. Jalankan validasi
          ulang untuk menampilkan semua {result.total.toLocaleString("id-ID")} baris.
        </div>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Seluruh Baris yang Melanggar</CardTitle>
          <CardDescription>
            Hasil validasi {result.run_at ? new Date(result.run_at).toLocaleString("id-ID") : "belum tersedia"}.
            Kolom yang diperiksa ditandai dengan warna merah.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {rows.length ? (
            <>
              <div className="overflow-x-auto rounded-md border">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="sticky left-0 z-10 min-w-20 bg-background">Baris</TableHead>
                      {result.columns.map((column: string) => (
                        <TableHead
                          key={column}
                          className={column === result.rule.column_name ? "min-w-40 bg-destructive/10 text-destructive" : "min-w-40"}
                        >
                          {column}
                        </TableHead>
                      ))}
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {rows.map((row: any) => (
                      <TableRow key={row.row}>
                        <TableCell className="sticky left-0 z-10 bg-background font-medium">
                          {row.row}
                        </TableCell>
                        {result.columns.map((column: string) => (
                          <TableCell
                            key={column}
                            className={column === result.rule.column_name ? "bg-destructive/5 font-medium text-destructive" : ""}
                          >
                            <span className="whitespace-nowrap font-mono text-xs">
                              {displayValue(row.data[column])}
                            </span>
                          </TableCell>
                        ))}
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>

              <div className="mt-4 flex items-center justify-between gap-4">
                <p className="text-sm text-muted-foreground">
                  Menampilkan {(page - 1) * PAGE_SIZE + 1}–{Math.min(page * PAGE_SIZE, result.stored_total)} dari {result.stored_total.toLocaleString("id-ID")} baris
                </p>
                <div className="flex items-center gap-2">
                  <Button variant="outline" size="sm" disabled={page === 1} onClick={() => setPage((value) => value - 1)}>
                    Sebelumnya
                  </Button>
                  <span className="text-sm">Halaman {page} dari {totalPages}</span>
                  <Button variant="outline" size="sm" disabled={page === totalPages} onClick={() => setPage((value) => value + 1)}>
                    Berikutnya
                  </Button>
                </div>
              </div>
            </>
          ) : (
            <div className="flex h-48 items-center justify-center rounded-md border border-dashed text-muted-foreground">
              Tidak ada data pelanggaran pada hasil validasi ini.
            </div>
          )}
        </CardContent>
      </Card>
    </Shell>
  );
}
