"use client";

import Shell from "@/components/Shell";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { api } from "@/lib/api";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Download, AlertCircle } from "lucide-react";

export default function GoldenRecordPage() {
  const params = useParams<{ id: string }>();
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    // Simulasi pengambilan data golden record
    // Idealnya ada endpoint khusus untuk paginated golden record
    api(`/datasets/${params.id}/golden/export`)
      .then(() => {
        // Karena endpoint export mengembalikan binary CSV,
        // Untuk UI kita simulasikan data dummy dulu sambil menunggu API golden record JSON
        setTimeout(() => {
          setData([
            { id: 1, name: "John Doe", email: "john@example.com", status: "Clean" },
            { id: 2, name: "Jane Smith", email: "jane@example.com", status: "Merged" }
          ]);
          setLoading(false);
        }, 1000);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }, [params.id]);

  return (
    <Shell title="Golden Record" subtitle="Hasil akhir data bersih setelah melalui pipeline">
      <div className="space-y-6 max-w-6xl">
        {error && (
          <div className="bg-destructive/15 text-destructive p-4 rounded-md border border-destructive/20 flex items-center gap-2">
            <AlertCircle className="h-5 w-5" />
            <p>{error}</p>
          </div>
        )}
        
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
            <div>
              <CardTitle>Preview Data Bersih</CardTitle>
              <CardDescription>Menampilkan sampel data yang telah dibersihkan dan disatukan.</CardDescription>
            </div>
            <Button 
              variant="default"
              onClick={() => {
                api(`/datasets/${params.id}/golden/export`)
                  .then((b) => {
                    const url = window.URL.createObjectURL(b);
                    const a = document.createElement("a");
                    a.href = url;
                    a.download = `golden_record_${params.id}.csv`;
                    a.click();
                  })
                  .catch((e) => alert("Export gagal: " + e.message));
              }}
            >
              <Download className="h-4 w-4 mr-2" />
              Download CSV
            </Button>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="flex flex-col items-center justify-center p-8 text-center border rounded-md border-dashed h-[300px] bg-muted/5">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mb-4"></div>
                <p className="text-muted-foreground">Memuat golden record...</p>
              </div>
            ) : (
              <div className="rounded-md border">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Record ID</TableHead>
                      <TableHead>Nama</TableHead>
                      <TableHead>Email</TableHead>
                      <TableHead>Keterangan</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {data.map((row: any, i) => (
                      <TableRow key={i}>
                        <TableCell className="font-mono text-muted-foreground">{row.id}</TableCell>
                        <TableCell className="font-medium">{row.name}</TableCell>
                        <TableCell>{row.email}</TableCell>
                        <TableCell>
                          <Badge 
                            variant="secondary" 
                            className={row.status === "Merged" ? "bg-info-muted text-info hover:bg-info-muted" : "bg-success-muted text-success hover:bg-success-muted"}
                          >
                            {row.status}
                          </Badge>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </Shell>
  );
}
