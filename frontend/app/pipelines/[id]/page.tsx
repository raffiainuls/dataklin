"use client";

import Shell from "@/components/Shell";
import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";

import { AlertCircle, PlayCircle, Settings, FileText } from "lucide-react";

export default function EditPipelinePage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const [pipeline, setPipeline] = useState<any>(null);
  const [datasets, setDatasets] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  
  const [form, setForm] = useState({
    name: "",
    dataset_id: "",
    enable_profiling: true,
    enable_deduplication: false,
    schedule: "manual"
  });

  useEffect(() => {
    // Di MVP ini, ID Pipeline sebenarnya adalah Dataset ID
    // jadi kita ambil dataset sebagai pipeline
    Promise.all([
      api(`/datasets/${params.id}`),
      api("/datasets")
    ]).then(([ds, allDs]) => {
      setPipeline(ds);
      setDatasets(allDs);
      setForm({
        name: `Pipeline for ${ds.name}`,
        dataset_id: String(ds.id),
        enable_profiling: true,
        enable_deduplication: false,
        schedule: "manual"
      });
      setLoading(false);
    }).catch((e) => {
      console.error(e);
      setError(e.message);
      setLoading(false);
    });
  }, [params.id]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    
    // Simulasi update
    setTimeout(() => {
      router.push(`/rules?dataset_id=${form.dataset_id}`);
    }, 1000);
  };

  if (loading) {
    return (
      <Shell title="Edit Pipeline">
        <div className="flex flex-col items-center justify-center p-8 text-center border rounded-md border-dashed h-[300px] bg-muted/5">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mb-4"></div>
          <p className="text-muted-foreground">Memuat konfigurasi pipeline...</p>
        </div>
      </Shell>
    );
  }
  
  if (!pipeline && !error) {
    return (
      <Shell title="Error">
        <div className="bg-destructive/15 text-destructive p-4 rounded-md border border-destructive/20 flex items-center gap-2">
          <AlertCircle className="h-5 w-5" />
          <p>Pipeline tidak ditemukan</p>
        </div>
      </Shell>
    );
  }

  return (
    <Shell title="Edit Pipeline" subtitle={pipeline ? `Konfigurasi aliran data untuk: ${pipeline.name}` : ""}>
      <div className="space-y-6 max-w-3xl">
        {error && (
          <div className="bg-destructive/15 text-destructive p-4 rounded-md border border-destructive/20 flex items-center gap-2">
            <AlertCircle className="h-5 w-5" />
            <p>{error}</p>
          </div>
        )}
        
        <Card>
          <CardHeader>
            <CardTitle>Pengaturan Pipeline</CardTitle>
            <CardDescription>Sesuaikan bagaimana data diproses dan divalidasi</CardDescription>
          </CardHeader>
          <form onSubmit={handleSubmit}>
            <CardContent className="space-y-6">
              <div className="space-y-2">
                <Label htmlFor="name">Nama Pipeline</Label>
                <Input 
                  id="name"
                  type="text" 
                  required
                  value={form.name}
                  onChange={e => setForm({...form, name: e.target.value})}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="dataset">Sumber Data (Data Source)</Label>
                <div className="flex h-10 w-full rounded-md border border-input bg-muted px-3 py-2 text-sm ring-offset-background disabled:cursor-not-allowed disabled:opacity-50">
                  {pipeline ? `${pipeline.name} (ID: ${pipeline.id})` : "Memuat..."}
                </div>
                <p className="text-xs text-muted-foreground">Sumber data tidak bisa diubah setelah pipeline dibuat.</p>
              </div>

              <div className="pt-4 border-t space-y-4">
                <h3 className="font-medium">Opsi Pemrosesan</h3>
                
                <RadioGroup 
                  value={(form.enable_profiling && form.enable_deduplication) ? "both" : form.enable_deduplication ? "dedup" : "profiling"}
                  onValueChange={(val) => {
                    if (val === "both") setForm({...form, enable_profiling: true, enable_deduplication: true});
                    if (val === "dedup") setForm({...form, enable_profiling: false, enable_deduplication: true});
                    if (val === "profiling") setForm({...form, enable_profiling: true, enable_deduplication: false});
                  }}
                  className="flex flex-col space-y-2"
                >
                  <div className="flex items-center space-x-3">
                    <RadioGroupItem value="profiling" id="r-profiling" />
                    <Label htmlFor="r-profiling" className="font-normal cursor-pointer">Jalankan Data Profiling Saja</Label>
                  </div>
                  <div className="flex items-center space-x-3">
                    <RadioGroupItem value="dedup" id="r-dedup" />
                    <Label htmlFor="r-dedup" className="font-normal cursor-pointer">Entity Resolution (Deduplikasi) Saja</Label>
                  </div>
                  <div className="flex items-center space-x-3">
                    <RadioGroupItem value="both" id="r-both" />
                    <Label htmlFor="r-both" className="font-normal cursor-pointer font-medium text-primary">Jalankan Keduanya Sekaligus (Profiling & Deduplikasi)</Label>
                  </div>
                </RadioGroup>
              </div>
              
              <div className="pt-4 border-t space-y-2">
                <Label htmlFor="schedule">Jadwal Eksekusi</Label>
                <Select 
                  value={form.schedule}
                  onValueChange={(val) => setForm({...form, schedule: val || ""})}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Pilih jadwal" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="manual">Manual (Hanya saat menekan "Run Now")</SelectItem>
                    <SelectItem value="hourly">Setiap Jam</SelectItem>
                    <SelectItem value="daily">Setiap Hari (Tengah Malam)</SelectItem>
                    <SelectItem value="weekly">Setiap Minggu</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </CardContent>
            <CardFooter className="flex flex-wrap items-center justify-between gap-4 border-t bg-muted/10 p-6">
              <Button type="button" variant="outline" onClick={() => router.back()}>
                Batal
              </Button>
              <div className="flex gap-2">
                <Button type="button" variant="secondary" onClick={() => router.push(`/rules?dataset_id=${form.dataset_id}`)}>
                  <FileText className="h-4 w-4 mr-2" />
                  Kelola Rules
                </Button>
                <Button type="submit" disabled={saving}>
                  <Settings className="h-4 w-4 mr-2" />
                  {saving ? "Menyimpan..." : "Simpan Konfigurasi"}
                </Button>
              </div>
            </CardFooter>
          </form>
        </Card>
      </div>
    </Shell>
  );
}
