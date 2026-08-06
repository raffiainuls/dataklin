"use client";

import { useCallback, useEffect, useState } from "react";
import Shell from "@/components/Shell";
import { LineChart } from "@/components/LineChart";
import { api } from "@/lib/api";
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { AlertCircle, LineChart as LineChartIcon, Activity, Bell, CheckCircle2, Save, Send } from "lucide-react";

export default function MonitoringPage() {
  const [datasets, setDatasets] = useState<any[]>([]);
  const [datasetId, setDatasetId] = useState<string>("");
  const [history, setHistory] = useState<any[]>([]);
  const [alerts, setAlerts] = useState<any[]>([]);
  const [threshold, setThreshold] = useState<number>(75);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [monitorEnabled, setMonitorEnabled] = useState(false);
  const [monitorInterval, setMonitorInterval] = useState(1440);
  const [monitorBusy, setMonitorBusy] = useState(false);
  const [webhookUrl, setWebhookUrl] = useState("");
  const [slackWebhookUrl, setSlackWebhookUrl] = useState("");
  const [notifyEmails, setNotifyEmails] = useState("");
  const [notifBusy, setNotifBusy] = useState(false);
  const [testResults, setTestResults] = useState<Record<string, string> | null>(null);

  function loadDatasets() {
    api("/datasets")
      .then((ds) => {
        setDatasets(ds);
        if (ds.length && !datasetId) setDatasetId(String(ds[0].id));
      })
      .catch((e) => setError(e.message));
  }

  useEffect(() => {
    loadDatasets();
    api("/alerts").then(setAlerts).catch(() => {});
    api("/settings")
      .then((s) => {
        setThreshold(s.alert_threshold);
        setWebhookUrl(s.webhook_url || "");
        setSlackWebhookUrl(s.slack_webhook_url || "");
        setNotifyEmails(s.notify_emails || "");
      })
      .catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const ds = datasets.find((d) => String(d.id) === datasetId);
    if (ds) {
      setMonitorEnabled(!!ds.monitoring_enabled);
      setMonitorInterval(ds.monitoring_interval_minutes || 1440);
    }
  }, [datasetId, datasets]);

  const loadHistory = useCallback(() => {
    if (!datasetId) return;
    api(`/datasets/${datasetId}/history`).then(setHistory).catch(() => {});
  }, [datasetId]);

  useEffect(() => {
    loadHistory();
  }, [loadHistory]);

  const showNotice = (msg: string) => {
    setNotice(msg);
    setTimeout(() => setNotice(""), 5000);
  };

  async function saveMonitoring(enabled: boolean) {
    if (!datasetId) return;
    setMonitorBusy(true);
    setError("");
    try {
      await api(`/datasets/${datasetId}/monitoring`, {
        method: "PUT",
        body: JSON.stringify({ enabled, interval_minutes: monitorInterval }),
      });
      setMonitorEnabled(enabled);
      showNotice(
        enabled
          ? `Pemantauan otomatis diaktifkan — validasi ulang setiap ${
              monitorInterval >= 1440 ? monitorInterval / 1440 + " hari" : monitorInterval + " menit"
            }.`
          : "Pemantauan otomatis dinonaktifkan."
      );
      loadDatasets();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setMonitorBusy(false);
    }
  }

  async function saveThreshold() {
    setError("");
    try {
      await api("/settings", {
        method: "PUT",
        body: JSON.stringify({ alert_threshold: Number(threshold) }),
      });
      showNotice("Threshold tersimpan. Alert baru dibuat saat skor di bawah threshold.");
    } catch (e: any) {
      setError(e.message);
    }
  }

  async function saveNotifications() {
    setNotifBusy(true);
    setError("");
    try {
      await api("/settings/notifications", {
        method: "PUT",
        body: JSON.stringify({
          webhook_url: webhookUrl,
          slack_webhook_url: slackWebhookUrl,
          notify_emails: notifyEmails,
        }),
      });
      showNotice("Pengaturan notifikasi tersimpan.");
    } catch (e: any) {
      setError(e.message);
    } finally {
      setNotifBusy(false);
    }
  }

  async function sendTestNotification() {
    setNotifBusy(true);
    setError("");
    setTestResults(null);
    try {
      setTestResults(await api("/settings/notifications/test", { method: "POST" }));
    } catch (e: any) {
      setError(e.message);
    } finally {
      setNotifBusy(false);
    }
  }

  async function resolveAlert(id: number) {
    try {
      await api(`/alerts/${id}/resolve`, { method: "POST" });
      setAlerts(await api("/alerts"));
    } catch (e: any) {
      setError(e.message);
    }
  }

  const points = history.map((h) => ({
    label: new Date(h.created_at + "Z").toLocaleDateString("id-ID", {
      day: "2-digit",
      month: "short",
    }),
    value: h.score,
  }));

  return (
    <Shell title="Monitoring & Alerts" subtitle="Histori skor kualitas dan notifikasi">
      <div className="space-y-6 max-w-6xl">
        {error && (
          <div className="bg-destructive/15 text-destructive p-4 rounded-md border border-destructive/20 flex items-center gap-2">
            <AlertCircle className="h-5 w-5 shrink-0" />
            <p>{error}</p>
          </div>
        )}
        {notice && (
          <div className="bg-success/15 text-success p-4 rounded-md border border-success/20 flex items-center gap-2">
            <CheckCircle2 className="h-5 w-5 shrink-0" />
            <p>{notice}</p>
          </div>
        )}

        <Card>
          <CardHeader className="pb-4">
            <div className="flex flex-col sm:flex-row gap-4 items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <LineChartIcon className="h-5 w-5 text-primary" />
                  Skor Kualitas dari Waktu ke Waktu
                </CardTitle>
                <CardDescription>
                  Garis putus-putus merah menunjukkan threshold alert ({threshold})
                </CardDescription>
              </div>
              <div className="w-full sm:w-auto min-w-[260px]">
                <Select value={datasetId} onValueChange={(val) => setDatasetId(val || "")}>
                  <SelectTrigger className="bg-background">
                    <SelectValue placeholder="Pilih dataset" />
                  </SelectTrigger>
                  <SelectContent>
                    {datasets.map((d) => (
                      <SelectItem key={d.id} value={String(d.id)}>
                        {d.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="h-[300px] w-full">
              <LineChart points={points} threshold={threshold} />
            </div>
            <p className="text-xs text-muted-foreground mt-4 italic">
              Setiap pemrosesan/validasi ulang akan menambah titik histori baru.
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity className="h-5 w-5 text-primary" />
              Pemantauan Terjadwal (Drift Monitoring)
            </CardTitle>
            <CardDescription>
              Validasi rule & skor kualitas dijalankan ulang otomatis pada interval yang ditentukan.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm text-muted-foreground">
              Alert dibuat otomatis bila skor turun di bawah threshold, turun tajam dibanding pemeriksaan sebelumnya, 
              ATAU pembaruan terlambat dari jadwal yang ditentukan (dimensi <span className="italic">Timeliness</span> baru 
              muncul setelah minimal dua kali siklus pemantauan).
            </p>
            
            <div className="flex flex-col sm:flex-row gap-6 items-center pt-4 border-t">
              <div className="flex items-center space-x-2">
                <Switch 
                  id="monitor-enable" 
                  checked={monitorEnabled}
                  disabled={monitorBusy || !datasetId}
                  onCheckedChange={saveMonitoring}
                />
                <Label htmlFor="monitor-enable" className="font-medium cursor-pointer">
                  Aktifkan untuk dataset ini
                </Label>
              </div>
              
              <div className="flex items-center gap-4 w-full sm:w-auto flex-1">
                <div className="w-full sm:w-[200px]">
                  <Select 
                    value={String(monitorInterval)} 
                    disabled={monitorBusy || !monitorEnabled}
                    onValueChange={(val) => setMonitorInterval(Number(val))}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Pilih interval" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="15">Setiap 15 menit</SelectItem>
                      <SelectItem value="60">Setiap 1 jam</SelectItem>
                      <SelectItem value="360">Setiap 6 jam</SelectItem>
                      <SelectItem value="1440">Setiap 24 jam</SelectItem>
                      <SelectItem value="10080">Setiap 7 hari</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                
                {monitorEnabled && (
                  <Button
                    variant="secondary"
                    disabled={monitorBusy}
                    onClick={() => saveMonitoring(true)}
                  >
                    Terapkan Interval
                  </Button>
                )}
              </div>
            </div>
          </CardContent>
        </Card>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">
          <Card>
            <CardHeader>
              <CardTitle>Konfigurasi Threshold</CardTitle>
              <CardDescription>Batas bawah skor kualitas sebelum mengirim alert</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label>Alert jika skor kualitas turun di bawah</Label>
                <div className="flex items-center gap-3">
                  <Input
                    type="number"
                    min={0}
                    max={100}
                    value={threshold}
                    onChange={(e) => setThreshold(Number(e.target.value))}
                    className="w-24"
                  />
                  <span className="text-xl font-medium">%</span>
                </div>
              </div>
            </CardContent>
            <CardFooter className="bg-muted/10 border-t p-4">
              <Button onClick={saveThreshold}>
                <Save className="h-4 w-4 mr-2" />
                Simpan Konfigurasi
              </Button>
            </CardFooter>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Bell className="h-5 w-5" />
                Pengaturan Notifikasi
              </CardTitle>
              <CardDescription>Saluran penerima alert</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label>Webhook URL (payload JSON generik)</Label>
                <Input
                  value={webhookUrl}
                  onChange={(e) => setWebhookUrl(e.target.value)}
                  placeholder="https://pipeline-anda.example.com/webhook"
                />
              </div>
              <div className="space-y-2">
                <Label>Slack Incoming Webhook URL</Label>
                <Input
                  value={slackWebhookUrl}
                  onChange={(e) => setSlackWebhookUrl(e.target.value)}
                  placeholder="https://hooks.slack.com/services/..."
                />
              </div>
              <div className="space-y-2">
                <Label>Email Penerima (pisahkan dengan koma)</Label>
                <Input
                  value={notifyEmails}
                  onChange={(e) => setNotifyEmails(e.target.value)}
                  placeholder="analyst@perusahaan.com, ops@perusahaan.com"
                />
              </div>
              
              {testResults && (
                <div className="bg-muted p-3 rounded-md text-sm mt-4">
                  <h4 className="font-semibold mb-2">Hasil Uji:</h4>
                  <ul className="space-y-1">
                    {Object.entries(testResults).map(([channel, status]) => (
                      <li key={channel} className="flex gap-2">
                        <span className="font-medium capitalize w-20">{channel}:</span> 
                        <span className={status.includes("berhasil") ? "text-success" : "text-muted-foreground"}>{status}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </CardContent>
            <CardFooter className="flex gap-3 bg-muted/10 border-t p-4">
              <Button disabled={notifBusy} onClick={saveNotifications}>
                <Save className="h-4 w-4 mr-2" />
                Simpan
              </Button>
              <Button variant="secondary" disabled={notifBusy} onClick={sendTestNotification}>
                <Send className="h-4 w-4 mr-2" />
                Kirim Uji
              </Button>
            </CardFooter>
          </Card>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Alert Terbaru</CardTitle>
            <CardDescription>Daftar pemberitahuan yang terpicu oleh pemantauan</CardDescription>
          </CardHeader>
          <CardContent>
            {alerts.length ? (
              <div className="rounded-md border">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Tanggal</TableHead>
                      <TableHead>Dataset</TableHead>
                      <TableHead>Pesan</TableHead>
                      <TableHead>Tingkat</TableHead>
                      <TableHead className="text-right">Aksi</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {alerts.map((a) => (
                      <TableRow key={a.id} className={a.status === "resolved" ? "opacity-60 bg-muted/20" : ""}>
                        <TableCell className="whitespace-nowrap">
                          {new Date(a.created_at + "Z").toLocaleDateString("id-ID", {
                            day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit"
                          })}
                        </TableCell>
                        <TableCell className="font-medium">{a.dataset_name}</TableCell>
                        <TableCell>{a.message}</TableCell>
                        <TableCell>
                          <Badge 
                            variant={a.severity === "tinggi" ? "destructive" : a.severity === "sedang" ? "default" : "secondary"}
                            className={a.severity === "sedang" ? "bg-warning hover:bg-warning" : ""}
                          >
                            {a.severity}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-right">
                          {a.status === "open" ? (
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => resolveAlert(a.id)}
                            >
                              <CheckCircle2 className="h-4 w-4 mr-2 text-success" />
                              Tandai Selesai
                            </Button>
                          ) : (
                            <div className="flex items-center justify-end text-success text-sm font-medium">
                              <CheckCircle2 className="h-4 w-4 mr-1" />
                              Selesai
                            </div>
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center p-8 text-center border rounded-md border-dashed h-48 bg-muted/5">
                <Bell className="h-8 w-8 text-muted-foreground mb-3 opacity-20" />
                <p className="text-muted-foreground">Belum ada alert</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </Shell>
  );
}
