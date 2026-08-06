"use client";

import { useEffect, useState } from "react";
import Shell from "@/components/Shell";
import { api } from "@/lib/api";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { AlertCircle, PlayCircle, Trash2, Link as LinkIcon, HelpCircle } from "lucide-react";

export default function IntegrityPage() {
  const [datasets, setDatasets] = useState<any[]>([]);
  const [rules, setRules] = useState<any[]>([]);
  const [checkTypes, setCheckTypes] = useState<any[]>([]);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [runningId, setRunningId] = useState<number | null>(null);

  const [name, setName] = useState("");
  const [checkType, setCheckType] = useState("referential_integrity");
  const [primaryId, setPrimaryId] = useState("");
  const [primaryColumn, setPrimaryColumn] = useState("");
  const [primaryValueColumn, setPrimaryValueColumn] = useState("");
  const [referenceId, setReferenceId] = useState("");
  const [referenceColumn, setReferenceColumn] = useState("");
  const [referenceValueColumn, setReferenceValueColumn] = useState("");
  const [primaryColumns, setPrimaryColumns] = useState<string[]>([]);
  const [referenceColumns, setReferenceColumns] = useState<string[]>([]);

  const isConsistency = checkType === "consistency";

  function load() {
    api("/cross-dataset-rules").then(setRules).catch((e) => setError(e.message));
  }

  useEffect(() => {
    api("/datasets")
      .then((ds) => {
        const ready = ds.filter((d: any) => d.status === "ready");
        setDatasets(ready);
        if (ready.length) {
          setPrimaryId(String(ready[0].id));
          setReferenceId(String(ready[0].id));
        }
      })
      .catch((e) => setError(e.message));
    api("/cross-dataset-check-types").then(setCheckTypes).catch(() => {});
    load();
  }, []);

  useEffect(() => {
    if (!primaryId) return;
    api(`/datasets/${primaryId}`)
      .then((d) => setPrimaryColumns((d.columns || []).map((c: any) => c.name)))
      .catch(() => {});
  }, [primaryId]);

  useEffect(() => {
    if (!referenceId) return;
    api(`/datasets/${referenceId}`)
      .then((d) => setReferenceColumns((d.columns || []).map((c: any) => c.name)))
      .catch(() => {});
  }, [referenceId]);

  async function createRule(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      await api("/cross-dataset-rules", {
        method: "POST",
        body: JSON.stringify({
          name,
          check_type: checkType,
          primary_dataset_id: Number(primaryId),
          primary_column: primaryColumn,
          reference_dataset_id: Number(referenceId),
          reference_column: referenceColumn,
          primary_value_column: isConsistency ? primaryValueColumn : null,
          reference_value_column: isConsistency ? referenceValueColumn : null,
        }),
      });
      setName("");
      setPrimaryColumn("");
      setReferenceColumn("");
      setPrimaryValueColumn("");
      setReferenceValueColumn("");
      setNotice('Rule dibuat. Klik "Jalankan Cek" untuk melihat hasilnya.');
      load();
      setTimeout(() => setNotice(""), 5000);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function runRule(id: number) {
    setError("");
    setRunningId(id);
    try {
      await api(`/cross-dataset-rules/${id}/run`, { method: "POST" });
      load();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setRunningId(null);
    }
  }

  async function deleteRule(id: number) {
    if (!window.confirm("Yakin ingin menghapus cek ini?")) return;
    setError("");
    try {
      await api(`/cross-dataset-rules/${id}`, { method: "DELETE" });
      load();
    } catch (e: any) {
      setError(e.message);
    }
  }

  return (
    <Shell
      title="Cek Lintas Dataset"
      subtitle="Validasi Referential Integrity (FK) dan Consistency antar dataset"
    >
      <div className="space-y-6 max-w-6xl">
        {error && (
          <div className="bg-destructive/15 text-destructive p-4 rounded-md border border-destructive/20 flex items-center gap-2">
            <AlertCircle className="h-5 w-5 shrink-0" />
            <p>{error}</p>
          </div>
        )}
        {notice && (
          <div className="bg-success/15 text-success p-4 rounded-md border border-success/20 flex items-center gap-2">
            <AlertCircle className="h-5 w-5 shrink-0" />
            <p>{notice}</p>
          </div>
        )}

        <Card>
          <CardHeader>
            <CardTitle>Buat Cek Baru</CardTitle>
            <CardDescription>Bandingkan data antara dua dataset berbeda</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={createRule} className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-2">
                  <Label>Nama</Label>
                  <Input
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="mis. Setiap order harus punya customer valid"
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label>Jenis Cek</Label>
                  <Select value={checkType} onValueChange={(val) => setCheckType(val || "")}>
                    <SelectTrigger>
                      <SelectValue placeholder="Pilih Jenis Cek" />
                    </SelectTrigger>
                    <SelectContent>
                      {checkTypes.map((c) => (
                        <SelectItem key={c.type} value={c.type}>{c.label}</SelectItem>
                      ))}
                      {checkTypes.length === 0 && (
                        <>
                          <SelectItem value="referential_integrity">Referential Integrity</SelectItem>
                          <SelectItem value="consistency">Data Consistency</SelectItem>
                        </>
                      )}
                    </SelectContent>
                  </Select>
                  <p className="text-xs text-muted-foreground flex items-start gap-1">
                    <HelpCircle className="h-3 w-3 mt-0.5 shrink-0" />
                    {isConsistency
                      ? "Join dua dataset lewat kolom kunci, lalu bandingkan kolom nilai untuk baris yang cocok."
                      : "Cek apakah setiap nilai kolom anak (FK) ada di kolom induk (PK) dataset lain."}
                  </p>
                </div>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 bg-muted/20 p-4 rounded-lg border">
                {/* Dataset Utama */}
                <div className="space-y-4">
                  <div className="font-semibold text-sm border-b pb-2 flex items-center gap-2">
                    <div className="bg-primary/10 text-primary w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold">1</div>
                    Dataset Utama {isConsistency ? "" : "(Anak / FK)"}
                  </div>
                  
                  <div className="space-y-2">
                    <Label>Pilih Dataset</Label>
                    <Select value={primaryId} onValueChange={(val) => setPrimaryId(val || "")}>
                      <SelectTrigger>
                        <SelectValue placeholder="Pilih Dataset" />
                      </SelectTrigger>
                      <SelectContent>
                        {datasets.map((d) => (
                          <SelectItem key={d.id} value={String(d.id)}>{d.name}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  
                  <div className="space-y-2">
                    <Label>{isConsistency ? "Kolom Kunci Join" : "Kolom Foreign Key"}</Label>
                    <Select value={primaryColumn} onValueChange={(val) => setPrimaryColumn(val || "")} required>
                      <SelectTrigger>
                        <SelectValue placeholder="Pilih Kolom" />
                      </SelectTrigger>
                      <SelectContent>
                        {primaryColumns.map((c) => (
                          <SelectItem key={c} value={c}>{c}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  {isConsistency && (
                    <div className="space-y-2 pt-2">
                      <Label>Kolom Nilai (Value)</Label>
                      <Select value={primaryValueColumn} onValueChange={(val) => setPrimaryValueColumn(val || "")} required>
                        <SelectTrigger>
                          <SelectValue placeholder="Pilih Kolom untuk Dibandingkan" />
                        </SelectTrigger>
                        <SelectContent>
                          {primaryColumns.map((c) => (
                            <SelectItem key={c} value={c}>{c}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                  )}
                </div>

                {/* Dataset Referensi */}
                <div className="space-y-4">
                  <div className="font-semibold text-sm border-b pb-2 flex items-center gap-2">
                    <div className="bg-secondary text-secondary-foreground w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold">2</div>
                    Dataset Referensi {isConsistency ? "" : "(Induk / PK)"}
                  </div>
                  
                  <div className="space-y-2">
                    <Label>Pilih Dataset</Label>
                    <Select value={referenceId} onValueChange={(val) => setReferenceId(val || "")}>
                      <SelectTrigger>
                        <SelectValue placeholder="Pilih Dataset" />
                      </SelectTrigger>
                      <SelectContent>
                        {datasets.map((d) => (
                          <SelectItem key={d.id} value={String(d.id)}>{d.name}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  
                  <div className="space-y-2">
                    <Label>{isConsistency ? "Kolom Kunci Join" : "Kolom Primary Key"}</Label>
                    <Select value={referenceColumn} onValueChange={(val) => setReferenceColumn(val || "")} required>
                      <SelectTrigger>
                        <SelectValue placeholder="Pilih Kolom" />
                      </SelectTrigger>
                      <SelectContent>
                        {referenceColumns.map((c) => (
                          <SelectItem key={c} value={c}>{c}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  {isConsistency && (
                    <div className="space-y-2 pt-2">
                      <Label>Kolom Nilai (Value)</Label>
                      <Select value={referenceValueColumn} onValueChange={(val) => setReferenceValueColumn(val || "")} required>
                        <SelectTrigger>
                          <SelectValue placeholder="Pilih Kolom untuk Dibandingkan" />
                        </SelectTrigger>
                        <SelectContent>
                          {referenceColumns.map((c) => (
                            <SelectItem key={c} value={c}>{c}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                  )}
                </div>
              </div>

              <div className="pt-2">
                <Button type="submit" disabled={busy || datasets.length < 1}>
                  <LinkIcon className="h-4 w-4 mr-2" />
                  Simpan Aturan Lintas Dataset
                </Button>
                {datasets.length < 1 && (
                  <p className="text-sm text-warning mt-2">
                    Butuh minimal 1 dataset berstatus "Aktif" untuk membuat cek.
                  </p>
                )}
              </div>
            </form>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Cek Tersimpan</CardTitle>
            <CardDescription>Daftar aturan lintas dataset yang sudah dibuat</CardDescription>
          </CardHeader>
          <CardContent>
            {rules.length ? (
              <div className="rounded-md border">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Nama</TableHead>
                      <TableHead>Jenis</TableHead>
                      <TableHead>Relasi</TableHead>
                      <TableHead>Hasil Terakhir</TableHead>
                      <TableHead className="text-right">Aksi</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {rules.map((r) => (
                      <TableRow key={r.id}>
                        <TableCell className="font-medium">{r.name}</TableCell>
                        <TableCell>
                          <Badge variant="secondary">
                            {r.check_type === "consistency" ? "Consistency" : "Ref. Integrity"}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-xs space-y-1">
                          {r.check_type === "consistency" ? (
                            <>
                              <div className="font-medium">
                                {r.primary_dataset_name}.{r.primary_value_column} ↔{" "}
                                {r.reference_dataset_name}.{r.reference_value_column}
                              </div>
                              <div className="text-muted-foreground">
                                join: {r.primary_column} = {r.reference_column}
                              </div>
                            </>
                          ) : (
                            <div className="font-medium flex items-center gap-1">
                              {r.primary_dataset_name}.{r.primary_column} <ArrowRight className="h-3 w-3" /> {r.reference_dataset_name}.{r.reference_column}
                            </div>
                          )}
                        </TableCell>
                        <TableCell className="text-xs">
                          {r.last_checked_at ? (
                            <div className="space-y-1">
                              <Badge variant={r.last_violations > 0 ? "destructive" : "default"} className={r.last_violations === 0 ? "bg-success hover:bg-success" : ""}>
                                {r.last_violations} / {r.last_checked_count} tidak cocok
                              </Badge>
                              {r.last_samples?.length > 0 && (
                                <div className="text-muted-foreground truncate max-w-[200px]" title={r.last_samples.join("; ")}>
                                  contoh: {r.last_samples.slice(0, 3).join(", ")}
                                </div>
                              )}
                            </div>
                          ) : (
                            <span className="text-muted-foreground italic">Belum dijalankan</span>
                          )}
                        </TableCell>
                        <TableCell className="text-right">
                          <div className="flex justify-end gap-2">
                            <Button
                              variant="outline"
                              size="sm"
                              disabled={runningId === r.id}
                              onClick={() => runRule(r.id)}
                            >
                              {runningId === r.id ? (
                                <div className="animate-spin h-3 w-3 border-b-2 border-primary mr-2 rounded-full" />
                              ) : (
                                <PlayCircle className="h-4 w-4 mr-1" />
                              )}
                              Run
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              className="text-destructive hover:bg-destructive/10 hover:text-destructive"
                              onClick={() => deleteRule(r.id)}
                            >
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center p-8 text-center border rounded-md border-dashed h-48 bg-muted/5">
                <LinkIcon className="h-8 w-8 text-muted-foreground mb-3 opacity-20" />
                <p className="text-muted-foreground">Belum ada cek lintas dataset</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </Shell>
  );
}

// ArrowRight component yang tidak di-import di atas
function ArrowRight({ className }: { className?: string }) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
      <path d="M5 12h14" />
      <path d="m12 5 7 7-7 7" />
    </svg>
  );
}
