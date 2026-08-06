"use client";

import { useEffect, useState } from "react";
import Shell from "@/components/Shell";
import { API_URL, api } from "@/lib/api";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { AlertCircle, Key, Trash2, Copy, CheckCircle2 } from "lucide-react";

export default function ApiKeysPage() {
  const [keys, setKeys] = useState<any[]>([]);
  const [name, setName] = useState("");
  const [newKey, setNewKey] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [copied, setCopied] = useState(false);

  function load() {
    api("/api-keys").then(setKeys).catch((e) => setError(e.message));
  }

  useEffect(load, []);

  async function createKey(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setBusy(true);
    setCopied(false);
    try {
      const result = await api("/api-keys", { method: "POST", body: JSON.stringify({ name }) });
      setNewKey(result.key);
      setName("");
      load();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function revoke(id: number) {
    setError("");
    try {
      await api(`/api-keys/${id}`, { method: "DELETE" });
      load();
    } catch (e: any) {
      setError(e.message);
    }
  }

  const copyToClipboard = () => {
    if (newKey) {
      navigator.clipboard.writeText(newKey);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <Shell
      title="Integrasi API"
      subtitle="Kunci akses programatik untuk pipeline data scientist/analyst menarik data tanpa login interaktif"
    >
      <div className="space-y-6 max-w-5xl">
        {error && (
          <div className="bg-destructive/15 text-destructive p-4 rounded-md border border-destructive/20 flex items-center gap-2">
            <AlertCircle className="h-5 w-5" />
            <p>{error}</p>
          </div>
        )}

        {newKey && (
          <Card className="border-primary/50 bg-primary/5">
            <CardHeader className="pb-3">
              <CardTitle className="flex items-center gap-2 text-primary">
                <CheckCircle2 className="h-5 w-5" />
                API Key Berhasil Dibuat
              </CardTitle>
              <CardDescription className="text-primary/80">
                Salin sekarang — kunci lengkap tidak akan ditampilkan lagi setelah Anda menutup halaman ini.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-2 mt-2">
                <code className="flex-1 bg-background border rounded-md p-3 font-mono text-sm break-all">
                  {newKey}
                </code>
                <Button 
                  variant="outline" 
                  className="shrink-0 h-[46px]" 
                  onClick={copyToClipboard}
                >
                  {copied ? <CheckCircle2 className="h-4 w-4 mr-2 text-success" /> : <Copy className="h-4 w-4 mr-2" />}
                  {copied ? "Disalin!" : "Salin Key"}
                </Button>
              </div>
              <Button 
                variant="default" 
                className="mt-6" 
                onClick={() => setNewKey(null)}
              >
                Saya sudah menyimpannya
              </Button>
            </CardContent>
          </Card>
        )}

        <Card>
          <CardHeader>
            <CardTitle>Buat API Key Baru</CardTitle>
            <CardDescription>Berikan nama yang deskriptif untuk mengidentifikasi tujuan penggunaan key ini.</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={createKey} className="flex flex-col sm:flex-row gap-4 items-end">
              <div className="flex-1 space-y-2 w-full">
                <Label htmlFor="name">Nama (mis. "pipeline-notebook-DS")</Label>
                <Input
                  id="name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Masukkan nama key..."
                  required
                />
              </div>
              <Button type="submit" disabled={busy || !name} className="w-full sm:w-auto">
                <Key className="h-4 w-4 mr-2" />
                Generate Key
              </Button>
            </form>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>API Key Aktif</CardTitle>
            <CardDescription>Daftar kunci yang pernah Anda atau tim Anda buat.</CardDescription>
          </CardHeader>
          <CardContent>
            {keys.length > 0 ? (
              <div className="rounded-md border">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Nama</TableHead>
                      <TableHead>Prefix</TableHead>
                      <TableHead>Dibuat Oleh</TableHead>
                      <TableHead>Terakhir Dipakai</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead className="text-right">Aksi</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {keys.map((k) => (
                      <TableRow key={k.id} className={k.revoked ? "opacity-50" : ""}>
                        <TableCell className="font-medium">{k.name}</TableCell>
                        <TableCell>
                          <code className="bg-muted px-2 py-1 rounded text-xs">{k.key_prefix}…</code>
                        </TableCell>
                        <TableCell className="text-muted-foreground">{k.created_by}</TableCell>
                        <TableCell className="text-muted-foreground text-sm">
                          {k.last_used_at
                            ? new Date(k.last_used_at + "Z").toLocaleString("id-ID", {
                                day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit'
                              })
                            : "Belum pernah"}
                        </TableCell>
                        <TableCell>
                          {k.revoked ? (
                            <Badge variant="outline" className="text-muted-foreground">Dicabut</Badge>
                          ) : (
                            <Badge variant="outline" className="text-success border-success/30">Aktif</Badge>
                          )}
                        </TableCell>
                        <TableCell className="text-right">
                          {!k.revoked && (
                            <Button
                              variant="ghost"
                              size="sm"
                              className="text-destructive hover:text-destructive hover:bg-destructive/10"
                              onClick={() => {
                                if (window.confirm(`Yakin ingin mencabut akses untuk key "${k.name}"?`)) {
                                  revoke(k.id);
                                }
                              }}
                            >
                              <Trash2 className="h-4 w-4 mr-2" />
                              Cabut
                            </Button>
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center p-8 text-center border rounded-md border-dashed h-48 bg-muted/5">
                <Key className="h-8 w-8 text-muted-foreground mb-3 opacity-20" />
                <p className="text-muted-foreground">Belum ada API key yang dibuat.</p>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Cara Penggunaan</CardTitle>
            <CardDescription>Sertakan key dalam header request HTTP.</CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground mb-4">
              Kirim header <code>X-API-Key</code> pada request ke endpoint konsumsi data (dataset,
              clean.csv, dictionary.csv, scorecard, histori skor) — tidak perlu login JWT.
            </p>
            <div className="bg-muted p-4 rounded-md overflow-x-auto relative">
              <pre className="text-sm font-mono text-foreground">
{`curl -H "X-API-Key: vd_xxxxx" \\
  ${API_URL}/datasets/1/clean.csv -o clean.csv`}
              </pre>
            </div>
          </CardContent>
        </Card>
      </div>
    </Shell>
  );
}
