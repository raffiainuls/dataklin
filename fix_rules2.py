with open("/Users/raffiainulafif/Documents/dataqc/frontend/app/rules/page.tsx", "r") as f:
    content = f.read()

import_str = 'import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";\n'
if "Tabs," not in content:
    content = content.replace('import { Button } from "@/components/ui/button";', 'import { Button } from "@/components/ui/button";\n' + import_str)

# Find the end of <Shell>
# The file ends with:
#       </div>
#     </Shell>
#   );
# }
# 
# export default function RulesPage() {
#   return (
#     <Suspense>
#       <RulesContent />
#     </Suspense>
#   );
# }

marker = """      </div>
    </Shell>
  );
}

export default function RulesPage() {"""

replacement = """          </TabsContent>
          <TabsContent value="dedup">
            <DedupBuilder datasetId={datasetId} columns={columns} />
          </TabsContent>
        </Tabs>
      </div>
    </Shell>
  );
}

function DedupBuilder({ datasetId, columns }: { datasetId: string, columns: string[] }) {
  const [threshold, setThreshold] = useState<number>(0.8);
  const [dedupRules, setDedupRules] = useState<any[]>([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  useEffect(() => {
    if (!datasetId) return;
    api(`/datasets/${datasetId}/dedup-config`).then(res => {
      setThreshold(res.threshold || 0.8);
      setDedupRules(res.rules || []);
    }).catch(e => console.error(e));
  }, [datasetId]);

  const saveConfig = async () => {
    setError("");
    setSuccess("");
    const totalWeight = dedupRules.reduce((acc, r) => acc + (Number(r.weight) || 0), 0);
    if (dedupRules.length > 0 && Math.abs(totalWeight - 100) > 0.01) {
      setError(`Total bobot harus tepat 100%. Saat ini: ${totalWeight}%`);
      return;
    }
    
    setSaving(true);
    try {
      await api(`/datasets/${datasetId}/dedup-config`, {
        method: "PUT",
        body: JSON.stringify({ threshold, rules: dedupRules })
      });
      setSuccess("Konfigurasi deduplikasi berhasil disimpan. Pipeline akan dijalankan ulang otomatis.");
    } catch (e: any) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  };

  if (!datasetId) {
    return <div className="text-center p-8 text-muted-foreground border rounded-md">Pilih dataset terlebih dahulu</div>;
  }

  return (
    <div className="space-y-6">
      {error && (
        <div className="bg-destructive/15 text-destructive p-4 rounded-md border border-destructive/20 flex items-center gap-2">
          <AlertCircle className="h-5 w-5 shrink-0" />
          <p>{error}</p>
        </div>
      )}
      {success && (
        <div className="bg-emerald-500/15 text-emerald-700 p-4 rounded-md border border-emerald-500/20 flex items-center gap-2">
          <AlertCircle className="h-5 w-5 shrink-0" />
          <p>{success}</p>
        </div>
      )}
      
      <Card>
        <CardHeader>
          <CardTitle>Aturan Pencocokan Data (Entity Resolution)</CardTitle>
          <CardDescription>
            Pilih kolom mana saja yang akan digunakan untuk mencari data ganda, metode algoritmanya, dan bobot masing-masing kolom (total harus 100%).
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="flex items-center gap-4 border-b pb-6">
            <div className="flex-1 space-y-1">
              <Label>Minimum Threshold Skor</Label>
              <p className="text-sm text-muted-foreground">Batas minimal total skor kemiripan (0.1 - 1.0) untuk dianggap sebagai duplikat.</p>
            </div>
            <div className="w-32">
              <Input 
                type="number" 
                min="0.1" max="1.0" step="0.05" 
                value={threshold} 
                onChange={(e) => setThreshold(parseFloat(e.target.value))} 
              />
            </div>
          </div>
          
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="font-semibold">Kolom Pencocokan</h3>
              <Button variant="outline" size="sm" onClick={() => setDedupRules([...dedupRules, { column: columns[0] || "", method: "exact", weight: 0 }])}>
                <Plus className="h-4 w-4 mr-2" /> Tambah Kolom
              </Button>
            </div>
            
            {dedupRules.length === 0 ? (
              <div className="text-center p-8 border border-dashed rounded-md text-muted-foreground">
                Belum ada kolom yang dipilih. Sistem akan menggunakan tebakan otomatis (auto-detect) jika kosong.
              </div>
            ) : (
              <div className="space-y-4">
                {dedupRules.map((rule, idx) => (
                  <div key={idx} className="flex gap-4 items-end bg-muted/10 p-4 rounded-md border">
                    <div className="flex-1 space-y-2">
                      <Label>Kolom</Label>
                      <Select value={rule.column} onValueChange={(v) => {
                        const newR = [...dedupRules];
                        newR[idx].column = v;
                        setDedupRules(newR);
                      }}>
                        <SelectTrigger className="bg-background">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {columns.map(c => <SelectItem key={c} value={c}>{c}</SelectItem>)}
                        </SelectContent>
                      </Select>
                    </div>
                    
                    <div className="flex-1 space-y-2">
                      <Label>Metode (Algoritma)</Label>
                      <Select value={rule.method} onValueChange={(v) => {
                        const newR = [...dedupRules];
                        newR[idx].method = v;
                        setDedupRules(newR);
                      }}>
                        <SelectTrigger className="bg-background">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="exact">Exact Match (Sama Persis)</SelectItem>
                          <SelectItem value="fuzzy_ratio">Fuzzy Ratio (Levenshtein)</SelectItem>
                          <SelectItem value="token_sort">Token Sort (Acak Kata, e.g. Nama)</SelectItem>
                          <SelectItem value="token_set">Token Set (Subset Kata, e.g. Alamat)</SelectItem>
                          <SelectItem value="phone">Phone Match (No. HP)</SelectItem>
                          <SelectItem value="email">Email Match</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    
                    <div className="w-24 space-y-2">
                      <Label>Bobot (%)</Label>
                      <Input 
                        type="number" min="0" max="100" 
                        value={rule.weight} 
                        onChange={(e) => {
                          const newR = [...dedupRules];
                          newR[idx].weight = parseFloat(e.target.value) || 0;
                          setDedupRules(newR);
                        }} 
                      />
                    </div>
                    
                    <Button variant="ghost" className="text-destructive mb-0.5" onClick={() => {
                      const newR = [...dedupRules];
                      newR.splice(idx, 1);
                      setDedupRules(newR);
                    }}>
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                ))}
                
                <div className="flex justify-between items-center px-2 py-1 bg-muted/30 rounded">
                  <span className="font-semibold text-sm">Total Bobot:</span>
                  <span className={`font-bold ${dedupRules.reduce((a, r) => a + (Number(r.weight) || 0), 0) !== 100 ? 'text-destructive' : 'text-emerald-600'}`}>
                    {dedupRules.reduce((a, r) => a + (Number(r.weight) || 0), 0)}%
                  </span>
                </div>
              </div>
            )}
          </div>
        </CardContent>
        <CardFooter className="bg-muted/10 border-t justify-between">
          <p className="text-sm text-muted-foreground">Perubahan ini akan otomatis memicu sistem mengecek ulang data ganda.</p>
          <Button onClick={saveConfig} disabled={saving}>
            {saving ? "Menyimpan..." : "Simpan Aturan Dedup"}
          </Button>
        </CardFooter>
      </Card>
    </div>
  );
}

export default function RulesPage() {"""

content = content.replace(marker, replacement)

split_marker = "</Card>\n\n        <div className=\"grid grid-cols-1 lg:grid-cols-2 gap-6 items-start\">"

parts = content.split(split_marker)
tabs_open = """</Card>\n\n        <Tabs defaultValue="validation" className="w-full">
          <TabsList className="grid w-full grid-cols-2 lg:w-[600px] mb-6">
            <TabsTrigger value="validation">Validasi Anomali</TabsTrigger>
            <TabsTrigger value="dedup">Deduplikasi (Entity Resolution)</TabsTrigger>
          </TabsList>
          
          <TabsContent value="validation">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">"""

content = parts[0] + tabs_open + parts[1]

with open("/Users/raffiainulafif/Documents/dataqc/frontend/app/rules/page.tsx", "w") as f:
    f.write(content)
