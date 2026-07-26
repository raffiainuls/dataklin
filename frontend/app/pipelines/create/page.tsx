"use client";

import Shell from "@/components/Shell";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";

import { ArrowRight } from "lucide-react";

export default function CreatePipelinePage() {
  const router = useRouter();
  const [datasets, setDatasets] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  
  const [form, setForm] = useState({
    name: "",
    dataset_id: "",
    enable_profiling: true,
    enable_deduplication: false,
    schedule: "manual"
  });

  useEffect(() => {
    api("/datasets/").then(setDatasets).catch(console.error);
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    
    // Simulasikan create pipeline dan trigger run
    // Pada versi saat ini, kita baru punya endpoint dataset yang berjalan otomatis
    // Jadi kita hanya akan meredirect ke halaman rules untuk dataset yang dipilih
    
    setTimeout(() => {
      router.push(`/rules?dataset_id=${form.dataset_id}`);
    }, 1000);
  };

  return (
    <Shell title="Buat Pipeline Baru" subtitle="Konfigurasi aliran data dan validasi">
      <div className="space-y-6 max-w-3xl">
        <Card>
          <CardHeader>
            <CardTitle>Konfigurasi Pipeline</CardTitle>
            <CardDescription>Tentukan sumber data dan pengaturan pemrosesan</CardDescription>
          </CardHeader>
          <form onSubmit={handleSubmit}>
            <CardContent className="space-y-6">
              <div className="space-y-2">
                <Label htmlFor="name">Nama Pipeline</Label>
                <Input 
                  id="name"
                  type="text" 
                  required
                  placeholder="Contoh: Validasi Data Pelanggan Harian"
                  value={form.name}
                  onChange={e => setForm({...form, name: e.target.value})}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="dataset">Sumber Data (Data Source)</Label>
                {datasets.length > 0 ? (
                  <Select
                    required
                    value={form.dataset_id}
                    onValueChange={(val) => setForm({...form, dataset_id: val || ""})}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Pilih Sumber Data...">
                        {datasets.find((d) => String(d.id) === form.dataset_id)?.name || "Pilih Sumber Data..."}
                      </SelectValue>
                    </SelectTrigger>
                    <SelectContent>
                      {datasets.map(d => (
                        <SelectItem key={d.id} value={String(d.id)}>{d.name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                ) : (
                  <Select disabled value={form.dataset_id}>
                    <SelectTrigger className="opacity-50">
                      <SelectValue placeholder="Memuat Sumber Data..." />
                    </SelectTrigger>
                  </Select>
                )}
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
            <CardFooter className="flex justify-between border-t bg-muted/10 p-6">
              <Button type="button" variant="outline" onClick={() => router.back()}>
                Batal
              </Button>
              <Button type="submit" disabled={loading || !form.dataset_id}>
                {loading ? "Menyimpan..." : "Lanjut ke Konfigurasi Rule"}
                {!loading && <ArrowRight className="h-4 w-4 ml-2" />}
              </Button>
            </CardFooter>
          </form>
        </Card>
      </div>
    </Shell>
  );
}
