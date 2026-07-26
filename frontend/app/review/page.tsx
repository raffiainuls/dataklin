"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import Shell from "@/components/Shell";
import { api } from "@/lib/api";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { AlertCircle, CheckCircle2 } from "lucide-react";
import { ProgressBar } from "@/components/widgets";

export default function ReviewQueuePage() {
  const [queue, setQueue] = useState<any[]>([]);
  const [error, setError] = useState("");
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    api("/review-queue")
      .then((q) => {
        setQueue(q);
        setLoaded(true);
      })
      .catch((e) => setError(e.message));
  }, []);

  return (
    <Shell
      title="Review Queue"
      subtitle="Cluster kandidat duplikat yang menunggu keputusan manusia"
    >
      <div className="space-y-6 max-w-6xl">
        {error && (
          <div className="bg-destructive/15 text-destructive p-4 rounded-md border border-destructive/20 flex items-center gap-2">
            <AlertCircle className="h-5 w-5" />
            <p>{error}</p>
          </div>
        )}
        
        <Card>
          <CardHeader>
            <CardTitle>{queue.length} cluster menunggu review</CardTitle>
            <CardDescription>Periksa kecocokan data pada setiap cluster di bawah ini</CardDescription>
          </CardHeader>
          <CardContent>
            {queue.length ? (
              <div className="rounded-md border">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Cluster</TableHead>
                      <TableHead>Dataset</TableHead>
                      <TableHead>Jumlah Record</TableHead>
                      <TableHead className="w-[200px]">Cohesion Score</TableHead>
                      <TableHead className="text-right">Aksi</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {queue.map((c) => (
                      <TableRow key={c.id}>
                        <TableCell>
                          <code className="bg-muted px-2 py-1 rounded text-xs">{c.cluster_key}</code>
                        </TableCell>
                        <TableCell className="font-medium">{c.dataset_name}</TableCell>
                        <TableCell>{c.record_count} record</TableCell>
                        <TableCell>
                          <ProgressBar
                            label="Cohesion"
                            value={Math.round(c.cohesion * 100)}
                          />
                        </TableCell>
                        <TableCell className="text-right">
                          <Button variant="default" size="sm" render={<Link href={`/review/${c.id}`} />} nativeButton={false}>
                            Review →
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center p-8 text-center border rounded-md border-dashed h-[300px] bg-muted/5">
                {loaded ? (
                  <>
                    <CheckCircle2 className="h-10 w-10 text-emerald-500 mb-3" />
                    <p className="text-muted-foreground">Tidak ada cluster yang menunggu review 🎉</p>
                  </>
                ) : (
                  <>
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mb-4"></div>
                    <p className="text-muted-foreground">Memuat...</p>
                  </>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </Shell>
  );
}
