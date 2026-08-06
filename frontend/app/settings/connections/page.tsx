"use client";

import { useEffect, useState } from "react";
import Shell from "@/components/Shell";
import { api } from "@/lib/api";
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { AlertCircle, Database, Trash2, PlugZap, CheckCircle2, Server, Lock } from "lucide-react";
import Link from "next/link";

const DB_TYPE_LABELS: Record<string, string> = {
  postgresql: "PostgreSQL",
  mysql: "MySQL",
};

export default function ConnectionsPage() {
  const [connections, setConnections] = useState<any[]>([]);
  const [available, setAvailable] = useState<boolean | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);

  const [name, setName] = useState("");
  const [dbType, setDbType] = useState("postgresql");
  const [host, setHost] = useState("");
  const [port, setPort] = useState(5432);
  const [database, setDatabase] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  function load() {
    api("/connections").then(setConnections).catch((e) => setError(e.message));
  }

  useEffect(() => {
    load();
    api("/connections/available").then((r) => setAvailable(r.available)).catch(() => {});
  }, []);

  async function createConnection(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setNotice("");
    setBusy(true);
    try {
      await api("/connections", {
        method: "POST",
        body: JSON.stringify({ name, db_type: dbType, host, port, database, username, password }),
      });
      setName("");
      setHost("");
      setDatabase("");
      setUsername("");
      setPassword("");
      setNotice("Koneksi berhasil diuji dan disimpan.");
      load();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function deleteConnection(id: number) {
    setError("");
    try {
      await api(`/connections/${id}`, { method: "DELETE" });
      load();
    } catch (e: any) {
      setError(e.message);
    }
  }

  return (
    <Shell
      title="Koneksi Database"
      subtitle="Sambungkan langsung ke database sebagai sumber dataset untuk sinkronisasi otomatis"
    >
      <div className="space-y-6 max-w-5xl">
        {error && (
          <div className="bg-destructive/15 text-destructive p-4 rounded-md border border-destructive/20 flex items-center gap-2">
            <AlertCircle className="h-5 w-5" />
            <p>{error}</p>
          </div>
        )}
        
        {notice && (
          <div className="bg-success/15 text-success p-4 rounded-md border border-success/20 flex items-center gap-2">
            <CheckCircle2 className="h-5 w-5" />
            <p>{notice}</p>
          </div>
        )}
        
        {available === false && (
          <div className="bg-warning/15 text-warning p-4 rounded-md border border-warning/20 flex items-center gap-2">
            <AlertCircle className="h-5 w-5 shrink-0" />
            <p>
              Fitur koneksi database belum dikonfigurasi sepenuhnya. Anda harus mengatur <code>ENCRYPTION_KEY</code> di
              <code>.env</code> backend untuk enkripsi kredensial, kemudian merestart server.
            </p>
          </div>
        )}

        <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
          <Card className="xl:col-span-1">
            <CardHeader>
              <CardTitle>Tambah Koneksi Baru</CardTitle>
              <CardDescription>
                Kredensial Anda akan dienkripsi di sisi server (AES-256) saat disimpan.
              </CardDescription>
            </CardHeader>
            <form onSubmit={createConnection}>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="name">Nama Koneksi</Label>
                  <Input
                    id="name"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="mis. Production DB"
                    required
                  />
                </div>
                
                <div className="space-y-2">
                  <Label htmlFor="db_type">Tipe Database</Label>
                  <Select
                    value={dbType}
                    onValueChange={(val) => {
                      setDbType(val || "postgresql");
                      setPort(val === "mysql" ? 3306 : 5432);
                    }}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Pilih mesin database" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="postgresql">PostgreSQL</SelectItem>
                      <SelectItem value="mysql">MySQL</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="grid grid-cols-3 gap-4">
                  <div className="space-y-2 col-span-2">
                    <Label htmlFor="host">Host / Alamat</Label>
                    <Input
                      id="host"
                      value={host}
                      onChange={(e) => setHost(e.target.value)}
                      placeholder="db.example.com"
                      required
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="port">Port</Label>
                    <Input
                      id="port"
                      type="number"
                      value={port}
                      onChange={(e) => setPort(Number(e.target.value))}
                      required
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="database">Nama Database</Label>
                  <Input
                    id="database"
                    value={database}
                    onChange={(e) => setDatabase(e.target.value)}
                    placeholder="nama_db"
                    required
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="username">Username</Label>
                  <Input
                    id="username"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    required
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="password">Password</Label>
                  <div className="relative">
                    <Lock className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                    <Input
                      id="password"
                      type="password"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      className="pl-9"
                      required
                    />
                  </div>
                </div>
              </CardContent>
              <CardFooter className="bg-muted/10 border-t p-6">
                <Button type="submit" disabled={busy || available === false} className="w-full">
                  <PlugZap className="h-4 w-4 mr-2" />
                  {busy ? "Menguji koneksi..." : "Uji & Simpan Koneksi"}
                </Button>
              </CardFooter>
            </form>
          </Card>

          <div className="xl:col-span-2 space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Koneksi Tersimpan</CardTitle>
                <CardDescription>Daftar server database yang sudah terhubung ke Dataklin.</CardDescription>
              </CardHeader>
              <CardContent>
                {connections.length ? (
                  <div className="rounded-md border">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Koneksi</TableHead>
                          <TableHead>Tipe</TableHead>
                          <TableHead>Server</TableHead>
                          <TableHead>Dibuat Oleh</TableHead>
                          <TableHead className="text-right">Aksi</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {connections.map((c) => (
                          <TableRow key={c.id}>
                            <TableCell className="font-medium">
                              <div className="flex items-center gap-2">
                                <Database className="h-4 w-4 text-muted-foreground" />
                                {c.name}
                              </div>
                            </TableCell>
                            <TableCell>
                              <span className="inline-flex items-center rounded-md bg-muted px-2 py-1 text-xs font-medium ring-1 ring-inset ring-muted-foreground/20">
                                {DB_TYPE_LABELS[c.db_type] || c.db_type}
                              </span>
                            </TableCell>
                            <TableCell>
                              <div className="flex flex-col">
                                <span className="text-sm font-medium">{c.database}</span>
                                <span className="text-xs text-muted-foreground flex items-center">
                                  <Server className="h-3 w-3 mr-1" />
                                  {c.host}:{c.port}
                                </span>
                              </div>
                            </TableCell>
                            <TableCell className="text-muted-foreground text-sm">{c.created_by}</TableCell>
                            <TableCell className="text-right">
                              <Button
                                variant="ghost"
                                size="sm"
                                className="text-destructive hover:text-destructive hover:bg-destructive/10"
                                onClick={() => {
                                  if (window.confirm(`Yakin ingin menghapus koneksi "${c.name}"? Dataset yang menggunakannya mungkin akan berhenti di-refresh.`)) {
                                    deleteConnection(c.id);
                                  }
                                }}
                              >
                                <Trash2 className="h-4 w-4" />
                              </Button>
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                ) : (
                  <div className="flex flex-col items-center justify-center p-8 text-center border rounded-md border-dashed h-[300px] bg-muted/5">
                    <PlugZap className="h-10 w-10 text-muted-foreground mb-3 opacity-20" />
                    <p className="text-muted-foreground">Belum ada koneksi database yang tersimpan.</p>
                  </div>
                )}
              </CardContent>
            </Card>
            
            <Card className="bg-primary/5 border-primary/20">
              <CardContent className="p-6 flex gap-4 items-start">
                <Database className="h-6 w-6 text-primary shrink-0" />
                <div className="space-y-2">
                  <h4 className="font-medium leading-none text-primary">Cara menggunakan koneksi</h4>
                  <p className="text-sm text-primary/80">
                    Setelah koneksi tersimpan, Anda bisa membuat dataset otomatis dari query ke koneksi ini. 
                    Tuju halaman Upload Dataset dan pilih tab "Sambungkan Database".
                  </p>
                  <Button variant="outline" size="sm" className="mt-2" render={<Link href="/datasets/upload" />} nativeButton={false}>
                    Pergi ke Upload Dataset
                  </Button>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </Shell>
  );
}
