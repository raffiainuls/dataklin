"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useState } from "react";
import Shell from "@/components/Shell";
import { api } from "@/lib/api";
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { AlertCircle, Wand2, Plus, Play, Trash2, PowerOff, Power, Loader2 } from "lucide-react";
import { Textarea } from "@/components/ui/textarea";

function RulesContent() {
  const search = useSearchParams();
  const [datasets, setDatasets] = useState<any[]>([]);
  const [datasetId, setDatasetId] = useState<string>(search.get("dataset_id") || "");
  const [rules, setRules] = useState<any[]>([]);
  const [ruleTypes, setRuleTypes] = useState<any[]>([]);
  const [columns, setColumns] = useState<string[]>([]);
  const [datasetStatus, setDatasetStatus] = useState<string>("ready");
  const [datasetError, setDatasetError] = useState<string>("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [validationPipelineId, setValidationPipelineId] = useState<number | null>(null);

  const [newColumn, setNewColumn] = useState("");
  const [newType, setNewType] = useState("not_null");
  const [newParams, setNewParams] = useState("");
  const [newDesc, setNewDesc] = useState("");

  const [nlText, setNlText] = useState("");
  const [nlBusy, setNlBusy] = useState(false);
  const [proposal, setProposal] = useState<any>(null);
  const [llmAvailable, setLlmAvailable] = useState<boolean | null>(null);

  const [suggestions, setSuggestions] = useState<any[] | null>(null);
  const [suggestBusy, setSuggestBusy] = useState(false);
  const validationRunning = datasetStatus === "processing" || datasetStatus === "queued";

  useEffect(() => {
    api("/datasets")
      .then((ds) => {
        setDatasets(ds);
        if (!datasetId && ds.length) setDatasetId(String(ds[0].id));
      })
      .catch((e) => setError(e.message));
    api("/rule-types").then(setRuleTypes).catch(() => {});
    api("/llm-status").then((s) => setLlmAvailable(s.available)).catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const loadRules = useCallback(() => {
    if (!datasetId) return;
    api(`/datasets/${datasetId}/rules`).then(setRules).catch((e) => setError(e.message));
    api(`/datasets/${datasetId}`)
      .then((d) => {
        setColumns((d.columns || []).map((c: any) => c.name));
        setDatasetStatus(d.status || "ready");
        setDatasetError(d.error_message || "");
      })
      .catch(() => {});
  }, [datasetId]);

  useEffect(() => {
    loadRules();
  }, [loadRules]);

  useEffect(() => {
    if (!datasetId || (datasetStatus !== "processing" && datasetStatus !== "queued")) return;
    const interval = setInterval(() => {
      api(`/datasets/${datasetId}`).then((d) => {
        setDatasetStatus(d.status || "ready");
        setDatasetError(d.error_message || "");
        if (d.status === "ready") {
          // Reload rules kalau sudah siap untuk menampilkan RuleResult terbaru.
          loadRules();
          setNotice("Validasi selesai. Hasil terbaru sudah ditampilkan di setiap rule.");
          setTimeout(() => setNotice(""), 7000);
        } else if (d.status === "error") {
          setError(d.error_message || "Validasi gagal diproses.");
          setNotice("");
        }
      }).catch(() => {});
    }, 3000);
    return () => clearInterval(interval);
  }, [datasetId, datasetStatus, loadRules]);

  async function toggle(rule: any) {
    try {
      await api(`/rules/${rule.id}`, {
        method: "PATCH",
        body: JSON.stringify({ enabled: !rule.enabled }),
      });
      loadRules();
    } catch (e: any) {
      setError(e.message);
    }
  }

  async function removeRule(rule: any) {
    if (!window.confirm("Yakin ingin menghapus rule ini?")) return;
    try {
      await api(`/rules/${rule.id}`, { method: "DELETE" });
      loadRules();
    } catch (e: any) {
      setError(e.message);
    }
  }

  async function createRule(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    let params: any = {};
    if (newParams.trim()) {
      try {
        params = JSON.parse(newParams);
      } catch {
        setError('Params harus JSON valid, contoh: {"min": 0, "max": 100}');
        return;
      }
    }
    try {
      await api(`/datasets/${datasetId}/rules`, {
        method: "POST",
        body: JSON.stringify({
          column_name: newColumn,
          rule_type: newType,
          params,
          description: newDesc,
        }),
      });
      setNewColumn("");
      setNewParams("");
      setNewDesc("");
      setNotice("Rule dibuat. Jalankan ulang validasi untuk melihat hasilnya.");
      loadRules();
      setTimeout(() => setNotice(""), 5000);
    } catch (err: any) {
      setError(err.message);
    }
  }

  async function rerun() {
    setError("");
    try {
      const result = await api(`/datasets/${datasetId}/rules/rerun`, { method: "POST" });
      setValidationPipelineId(result.pipeline_id || null);
      setDatasetStatus("queued");
      setNotice("Validasi sedang diproses. Hasil akan diperbarui otomatis setelah selesai.");
    } catch (e: any) {
      setError(e.message);
    }
  }

  async function generateFromNL() {
    setError("");
    setProposal(null);
    setNlBusy(true);
    try {
      const p = await api(`/datasets/${datasetId}/rules/generate`, {
        method: "POST",
        body: JSON.stringify({ instruction: nlText }),
      });
      setProposal(p);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setNlBusy(false);
    }
  }

  async function activateProposal() {
    if (!proposal) return;
    setError("");
    try {
      await api(`/datasets/${datasetId}/rules`, {
        method: "POST",
        body: JSON.stringify({ ...proposal, source: "ai" }),
      });
      setProposal(null);
      setNlText("");
      setNotice("Rule AI diaktifkan. Jalankan ulang validasi untuk melihat hasilnya.");
      loadRules();
      setTimeout(() => setNotice(""), 5000);
    } catch (e: any) {
      setError(e.message);
    }
  }

  function editProposal() {
    if (!proposal) return;
    setNewColumn(proposal.column_name);
    setNewType(proposal.rule_type);
    setNewParams(Object.keys(proposal.params || {}).length ? JSON.stringify(proposal.params) : "");
    setNewDesc(proposal.description || "");
    setProposal(null);
  }

  async function fetchSuggestions() {
    setError("");
    setSuggestBusy(true);
    setSuggestions(null);
    try {
      setSuggestions(await api(`/datasets/${datasetId}/rules/suggest`, { method: "POST" }));
    } catch (e: any) {
      setError(e.message);
    } finally {
      setSuggestBusy(false);
    }
  }

  async function activateSuggestion(s: any, index: number) {
    setError("");
    try {
      await api(`/datasets/${datasetId}/rules`, {
        method: "POST",
        body: JSON.stringify({ ...s, source: "ai" }),
      });
      setSuggestions((prev) => (prev ? prev.filter((_, i) => i !== index) : prev));
      setNotice("Rule AI diaktifkan. Jalankan ulang validasi untuk melihat hasilnya.");
      loadRules();
      setTimeout(() => setNotice(""), 5000);
    } catch (e: any) {
      setError(e.message);
    }
  }

  function dismissSuggestion(index: number) {
    setSuggestions((prev) => (prev ? prev.filter((_, i) => i !== index) : prev));
  }

  const needsParams = ["numeric_range", "date_range", "starts_with", "regex", "cross_column"].includes(newType);

  return (
    <Shell title="Rule Builder" subtitle="Aturan validasi per kolom — bawaan, manual, atau AI">
      <div className="space-y-6 max-w-6xl">
        {error && (
          <div className="bg-destructive/15 text-destructive p-4 rounded-md border border-destructive/20 flex items-center gap-2">
            <AlertCircle className="h-5 w-5 shrink-0" />
            <p>{error}</p>
          </div>
        )}
        {notice && (
          <div className="bg-emerald-500/15 text-emerald-700 p-4 rounded-md border border-emerald-500/20 flex items-center gap-2">
            <AlertCircle className="h-5 w-5 shrink-0" />
            <p>{notice}</p>
            {validationPipelineId && (
              <Link href={`/pipelines/${validationPipelineId}`} className="ml-auto whitespace-nowrap font-medium underline">
                Lihat pipeline
              </Link>
            )}
          </div>
        )}

        <Card className="border-primary/20 bg-primary/5">
          <CardHeader className="py-4">
            <div className="flex flex-col sm:flex-row gap-4 items-center justify-between">
              <div>
                <CardTitle className="text-base">Pilih Pipeline / Dataset</CardTitle>
                <CardDescription>Tentukan dataset mana yang ingin diatur rule-nya</CardDescription>
              </div>
              <div className="w-full sm:w-auto min-w-[300px]">
                {datasets.length > 0 ? (
                  <Select value={datasetId} onValueChange={(val) => setDatasetId(val || "")}>
                    <SelectTrigger className="bg-background">
                      <SelectValue placeholder="Pilih dataset">
                        {datasets.find((d) => String(d.id) === datasetId)?.name || "Pilih dataset"}
                      </SelectValue>
                    </SelectTrigger>
                    <SelectContent>
                      {datasets.map((d) => (
                        <SelectItem key={d.id} value={String(d.id)}>
                          {d.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                ) : (
                  <Select disabled value={datasetId}>
                    <SelectTrigger className="bg-background opacity-50">
                      <SelectValue placeholder="Memuat dataset..." />
                    </SelectTrigger>
                  </Select>
                )}
              </div>
            </div>
          </CardHeader>
        </Card>

        <Tabs defaultValue="validation" className="w-full">
          <TabsList className="grid w-full grid-cols-2 lg:w-[600px] mb-6">
            <TabsTrigger value="validation">Validasi Anomali</TabsTrigger>
            <TabsTrigger value="dedup">Deduplikasi (Entity Resolution)</TabsTrigger>
          </TabsList>
          
          <TabsContent value="validation">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">
          <div className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Wand2 className="h-5 w-5 text-primary" />
                  Buat Rule Baru (Bahasa Natural)
                </CardTitle>
                <CardDescription>Jelaskan aturan dengan kata-kata Anda sendiri</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <Textarea
                  rows={3}
                  value={nlText}
                  onChange={(e) => setNlText(e.target.value)}
                  placeholder="Contoh: nomor HP harus 10-13 digit dan diawali 08"
                  className="resize-none"
                />
                <Button
                  className="w-full"
                  disabled={nlBusy || !datasetId || !nlText.trim()}
                  onClick={generateFromNL}
                >
                  {nlBusy ? (
                    <div className="flex items-center gap-2">
                      <div className="animate-spin h-4 w-4 border-2 border-primary-foreground border-t-transparent rounded-full" />
                      AI sedang memproses...
                    </div>
                  ) : (
                    <>
                      <Wand2 className="h-4 w-4 mr-2" />
                      Generate Rule dengan AI
                    </>
                  )}
                </Button>
                
                {llmAvailable === false && (
                  <p className="text-xs text-amber-600 bg-amber-50 p-2 rounded">
                    LLM gateway belum dikonfigurasi — isi LLM_BASE_URL / LLM_API_KEY / LLM_MODEL di .env lalu restart backend.
                  </p>
                )}

                {proposal && (
                  <div className="bg-primary/5 border border-primary/20 rounded-md p-4 space-y-4 mt-4">
                    <div className="flex items-center gap-2 border-b border-primary/10 pb-2">
                      <span className="text-xl">🤖</span>
                      <h4 className="font-semibold text-primary">Saran Rule AI</h4>
                    </div>
                    
                    <div className="space-y-2 text-sm">
                      <div className="flex">
                        <span className="text-muted-foreground w-20">Kolom:</span>
                        <Badge variant="secondary" className="font-mono">{proposal.column_name}</Badge>
                      </div>
                      <div className="flex">
                        <span className="text-muted-foreground w-20">Jenis:</span>
                        <span className="font-medium">{proposal.rule_label}</span>
                      </div>
                      {Object.keys(proposal.params || {}).length > 0 && (
                        <div className="flex">
                          <span className="text-muted-foreground w-20">Params:</span>
                          <code className="bg-muted px-2 py-0.5 rounded text-xs text-primary">
                            {JSON.stringify(proposal.params)}
                          </code>
                        </div>
                      )}
                      <div className="bg-muted p-2 rounded-md italic text-muted-foreground mt-2 text-xs">
                        "{proposal.description}"
                      </div>
                    </div>
                    
                    <div className="flex flex-wrap gap-2 justify-end pt-2">
                      <Button variant="ghost" size="sm" className="text-destructive hover:bg-destructive/10 hover:text-destructive" onClick={() => setProposal(null)}>
                        Tolak
                      </Button>
                      <Button variant="outline" size="sm" onClick={editProposal}>
                        Edit Manual
                      </Button>
                      <Button size="sm" onClick={activateProposal}>
                        Aktifkan Rule
                      </Button>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Wand2 className="h-5 w-5 text-amber-500" />
                  Sarankan Rule Otomatis
                </CardTitle>
                <CardDescription>LLM menyarankan rule dari skema & sample data</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <Button
                  variant="secondary"
                  className="w-full"
                  disabled={suggestBusy || !datasetId || llmAvailable === false}
                  onClick={fetchSuggestions}
                >
                  <Wand2 className="h-4 w-4 mr-2" />
                  {suggestBusy ? "Menganalisis skema..." : "Sarankan Rule dari Skema"}
                </Button>
                
                {suggestions && (
                  <div className="space-y-3 mt-4">
                    {suggestions.length === 0 ? (
                      <div className="p-6 text-center border rounded-md border-dashed text-muted-foreground italic text-sm">
                        Tidak ada saran tambahan yang relevan saat ini
                      </div>
                    ) : (
                      suggestions.map((s, i) => (
                        <div key={i} className="border rounded-md p-3 space-y-2 text-sm bg-card hover:bg-muted/30 transition-colors">
                          <div>
                            <span className="font-semibold">{s.column_name}</span> — <span>{s.rule_label}</span>
                          </div>
                          <div className="text-xs text-muted-foreground">
                            {s.description}
                          </div>
                          <div className="flex gap-2 justify-end pt-1">
                            <Button variant="ghost" size="sm" className="h-7 px-2 text-xs" onClick={() => dismissSuggestion(i)}>
                              Lewati
                            </Button>
                            <Button size="sm" className="h-7 px-3 text-xs" onClick={() => activateSuggestion(s, i)}>
                              Aktifkan
                            </Button>
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Buat Rule Manual</CardTitle>
                <CardDescription>Atur konfigurasi aturan secara manual</CardDescription>
              </CardHeader>
              <form onSubmit={createRule}>
                <CardContent className="space-y-4">
                  <div className="space-y-2">
                    <Label>Kolom</Label>
                    {columns.length ? (
                      <Select value={newColumn} onValueChange={(val) => setNewColumn(val || "")} required>
                        <SelectTrigger>
                          <SelectValue placeholder="Pilih kolom" />
                        </SelectTrigger>
                        <SelectContent>
                          {columns.map((c) => (
                            <SelectItem key={c} value={c}>{c}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    ) : (
                      <Input
                        value={newColumn}
                        onChange={(e) => setNewColumn(e.target.value)}
                        placeholder="Nama kolom"
                        required
                      />
                    )}
                  </div>
                  
                  <div className="space-y-2">
                    <Label>Jenis Rule</Label>
                    <Select value={newType} onValueChange={(val) => setNewType(val || "")}>
                      <SelectTrigger>
                        <SelectValue placeholder="Pilih jenis rule" />
                      </SelectTrigger>
                      <SelectContent>
                        {ruleTypes.map((rt) => (
                          <SelectItem key={rt.type} value={rt.type}>{rt.label}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  
                  {needsParams && (
                    <div className="space-y-2">
                      <div className="flex justify-between items-baseline">
                        <Label>Params (JSON)</Label>
                        <span className="text-xs text-muted-foreground">
                          {newType === "starts_with"
                            ? 'contoh: {"prefix": "Jl.", "case_sensitive": false}'
                            : newType === "regex"
                            ? 'contoh: {"pattern": "^08[0-9]+$"}'
                            : newType === "cross_column"
                              ? 'contoh: {"left": "tanggal_checkout", "op": ">", "right": "tanggal_checkin"}'
                              : 'contoh: {"min": 0, "max": 100}'}
                        </span>
                      </div>
                      <Input
                        value={newParams}
                        onChange={(e) => setNewParams(e.target.value)}
                        placeholder='{"key": "value"}'
                        className="font-mono text-sm"
                      />
                    </div>
                  )}
                  
                  <div className="space-y-2">
                    <Label>Deskripsi (opsional)</Label>
                    <Input
                      value={newDesc}
                      onChange={(e) => setNewDesc(e.target.value)}
                      placeholder="mis. nomor HP harus valid format Indonesia"
                    />
                  </div>
                </CardContent>
                <CardFooter className="bg-muted/10 border-t p-6">
                  <Button type="submit" disabled={!datasetId} className="w-full">
                    <Plus className="h-4 w-4 mr-2" />
                    Simpan Rule Manual
                  </Button>
                </CardFooter>
              </form>
            </Card>
          </div>

          <div className="space-y-6">
            <Card className="sticky top-6">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
                <div>
                  <CardTitle>Rule Aktif</CardTitle>
                  <CardDescription>Daftar validasi untuk dataset ini</CardDescription>
                </div>
                <div className="flex items-center gap-2">
                  {validationRunning && (
                    <Badge variant="outline" className="animate-pulse bg-blue-50 text-blue-700">
                      <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                      Sedang diproses
                    </Badge>
                  )}
                  {datasetStatus === "error" && (
                    <Badge variant="destructive" title={datasetError}>
                      Failed
                    </Badge>
                  )}
                  <Button variant="secondary" size="sm" onClick={rerun} disabled={!datasetId || validationRunning}>
                    {validationRunning ? (
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    ) : (
                      <Play className="h-4 w-4 mr-2" />
                    )}
                    {validationRunning ? "Memvalidasi..." : "Jalankan Validasi"}
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                {rules.length ? (
                  <div className="space-y-3">
                    {rules.map((r) => (
                      <div 
                        key={r.id} 
                        className={`border rounded-lg p-4 transition-all ${
                          r.enabled ? "bg-card shadow-sm" : "bg-muted/30 opacity-60"
                        }`}
                      >
                        <div className="flex justify-between items-start mb-2">
                          <div className="font-semibold">{r.column_name}</div>
                          <Badge 
                            variant="secondary" 
                            className={`text-[10px] uppercase tracking-wider ${
                              r.source === "builtin" ? "bg-muted" : r.source === "ai" ? "bg-blue-100 text-blue-700" : "bg-slate-100"
                            }`}
                          >
                            {r.source === "builtin" ? "Bawaan" : r.source === "ai" ? "AI" : "Manual"}
                          </Badge>
                        </div>
                        
                        <div className="text-sm text-muted-foreground mb-3">
                          {r.description || r.rule_label}
                        </div>
                        
                        <div className="flex justify-between items-center pt-3 border-t border-dashed">
                          <div className="text-sm">
                            <span className="text-muted-foreground mr-1">Pelanggaran:</span>
                            {r.last_result ? (
                              <span className={`font-semibold ${r.last_result.violations > 0 ? "text-destructive" : "text-emerald-600"}`}>
                                {r.last_result.violations.toLocaleString("id-ID")} / {r.last_result.checked.toLocaleString("id-ID")}
                              </span>
                            ) : (
                              <span className="text-muted-foreground italic">—</span>
                            )}
                          </div>
                          
                          <div className="flex gap-2">
                            <Button 
                              variant="ghost" 
                              size="icon"
                              className={`h-8 w-8 ${r.enabled ? 'text-amber-600 hover:text-amber-700 hover:bg-amber-100' : 'text-emerald-600 hover:text-emerald-700 hover:bg-emerald-100'}`} 
                              onClick={() => toggle(r)}
                              title={r.enabled ? "Nonaktifkan" : "Aktifkan"}
                            >
                              {r.enabled ? <PowerOff className="h-4 w-4" /> : <Power className="h-4 w-4" />}
                            </Button>
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-8 w-8 text-destructive hover:bg-destructive/10 hover:text-destructive"
                              onClick={() => removeRule(r)}
                              title="Hapus"
                            >
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          </div>
                        </div>
                        
                        {r.last_result?.violations > 0 && r.enabled && (
                          <div className="mt-3 flex items-center justify-between rounded-md border border-destructive/10 bg-destructive/5 p-3 text-xs">
                            <span className="font-semibold text-destructive">
                              {r.last_result.violations.toLocaleString("id-ID")} baris melanggar
                            </span>
                            <Button
                              variant="outline"
                              size="sm"
                              render={<Link href={`/datasets/${datasetId}/rules/${r.id}/violations`} />}
                              nativeButton={false}
                            >
                              Lihat Semua Data
                            </Button>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="flex flex-col items-center justify-center p-8 text-center border rounded-md border-dashed h-48 bg-muted/5">
                    <p className="text-muted-foreground">Belum ada rule untuk dataset/pipeline ini</p>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </div>
          </TabsContent>
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
  const [priorProbability, setPriorProbability] = useState<number>(0.05);
  const [exactRowMatch, setExactRowMatch] = useState(true);
  const [dedupRules, setDedupRules] = useState<any[]>([]);
  const [blockingRules, setBlockingRules] = useState<any[]>([]);
  const [exactMatchRules, setExactMatchRules] = useState<any[]>([]);
  const [clusterValidation, setClusterValidation] = useState<any>({
    enabled: true,
    method: "representative",
    min_cohesion: 0.7,
    min_representative_score: 0.75,
  });
  const [saving, setSaving] = useState(false);
  const [calibrating, setCalibrating] = useState(false);
  const [calibration, setCalibration] = useState<any>(null);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  useEffect(() => {
    if (!datasetId) return;
    api(`/datasets/${datasetId}/dedup-config`).then(res => {
      setThreshold(res.threshold ?? 0.8);
      setPriorProbability(res.prior_probability ?? 0.05);
      setExactRowMatch(res.exact_row_match ?? true);
      setDedupRules((res.rules || []).map((rule: any) => ({
        weight: 2,
        normalizers: [],
        mismatch_penalty: 0,
        mismatch_threshold: 0.2,
        required: false,
        required_threshold: 0.999,
        ...rule,
      })));
      setBlockingRules(res.blocking_rules || []);
      setExactMatchRules(res.exact_match_rules || []);
      setClusterValidation(res.cluster_validation || {
        enabled: true,
        method: "representative",
        min_cohesion: 0.7,
        min_representative_score: 0.75,
      });
    }).catch(e => console.error(e));
  }, [datasetId]);

  const saveConfig = async () => {
    setError("");
    setSuccess("");
    setSaving(true);
    try {
      await api(`/datasets/${datasetId}/dedup-config`, {
        method: "PUT",
        body: JSON.stringify({
          version: 2,
          threshold,
          prior_probability: priorProbability,
          exact_row_match: exactRowMatch,
          rules: dedupRules,
          blocking_rules: blockingRules,
          exact_match_rules: exactMatchRules,
          cluster_validation: clusterValidation,
        })
      });
      setSuccess("Konfigurasi deduplikasi berhasil disimpan. Pipeline akan dijalankan ulang otomatis.");
    } catch (e: any) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  };

  const calibrate = async () => {
    setError("");
    setCalibrating(true);
    try {
      const result = await api(`/datasets/${datasetId}/dedup-config/calibration`);
      setCalibration(result);
      if (result.available) setThreshold(result.recommended_threshold);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setCalibrating(false);
    }
  };

  if (!datasetId) {
    return <div className="text-center p-8 text-muted-foreground border rounded-md">Pilih dataset terlebih dahulu</div>;
  }

  const updateMatchingRule = (index: number, changes: any) => {
    setDedupRules(dedupRules.map((rule, position) => position === index ? { ...rule, ...changes } : rule));
  };
  const updateBlockingRule = (index: number, changes: any) => {
    setBlockingRules(blockingRules.map((rule, position) => position === index ? { ...rule, ...changes } : rule));
  };
  const selectedColumns = (rule: any) => rule.columns?.length ? rule.columns : (rule.column ? [rule.column] : []);

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
            Candidate generation, pencocokan, bukti negatif, dan validasi cluster dapat diatur terpisah. Konfigurasi lama tetap didukung.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="grid grid-cols-1 gap-4 border-b pb-6 md:grid-cols-3">
            <div className="space-y-2">
              <Label>Minimum Match Score</Label>
              <Input type="number" min="0.1" max="1" step="0.05" value={threshold}
                onChange={(event) => setThreshold(Number(event.target.value))} />
              <p className="text-xs text-muted-foreground">Pasangan di atas batas ini membentuk koneksi cluster.</p>
              <Button type="button" variant="outline" size="sm" className="w-full" onClick={calibrate} disabled={calibrating}>
                {calibrating ? "Menghitung..." : "Kalibrasi dari Hasil Review"}
              </Button>
              {calibration && (
                <p className={`rounded p-2 text-xs ${calibration.available ? "bg-emerald-500/10 text-emerald-700" : "bg-amber-500/10 text-amber-700"}`}>
                  {calibration.available
                    ? `Threshold ${calibration.recommended_threshold} · balanced accuracy ${(calibration.balanced_accuracy * 100).toFixed(1)}% dari ${calibration.positive_pairs + calibration.negative_pairs} pasangan.`
                    : calibration.reason}
                </p>
              )}
            </div>
            <div className="space-y-2">
              <Label>Prior Probability</Label>
              <Input type="number" min="0.001" max="0.5" step="0.01" value={priorProbability}
                onChange={(event) => setPriorProbability(Number(event.target.value))} />
              <p className="text-xs text-muted-foreground">Peluang awal dua record merupakan entitas yang sama.</p>
            </div>
            <label className="flex cursor-pointer items-start gap-3 rounded-md border p-3">
              <input type="checkbox" className="mt-1" checked={exactRowMatch}
                onChange={(event) => setExactRowMatch(event.target.checked)} />
              <span><span className="block text-sm font-medium">Exact-row fast path</span>
                <span className="text-xs text-muted-foreground">Gabungkan baris identik tanpa fuzzy scoring.</span></span>
            </label>
          </div>

          <div className="space-y-4 border-b pb-6">
            <div className="flex items-center justify-between gap-3">
              <div>
                <h3 className="font-semibold">1. Candidate Generation (Blocking)</h3>
                <p className="text-xs text-muted-foreground">Menentukan pasangan yang layak dibandingkan. Jika kosong, sistem menurunkannya dari matching rules.</p>
              </div>
              <Button variant="outline" size="sm" onClick={() => setBlockingRules([...blockingRules, {
                column: columns[0] || "", method: "prefix", normalizers: [], length: 3,
              }])}><Plus className="mr-2 h-4 w-4" />Tambah Blocking</Button>
            </div>
            {blockingRules.length === 0 ? (
              <div className="rounded-md border border-dashed p-4 text-sm text-muted-foreground">Mode otomatis aktif: phone suffix, email local/ngram, phonetic, prefix, atau n-gram dipilih sesuai metode matching.</div>
            ) : blockingRules.map((rule, index) => {
              const composite = rule.method === "composite_exact";
              return (
                <div key={index} className="grid grid-cols-1 gap-3 rounded-md border bg-muted/10 p-4 md:grid-cols-[1fr_1fr_1fr_90px_auto] md:items-end">
                  <div className="space-y-2">
                    <Label>{composite ? "Kolom gabungan" : "Kolom"}</Label>
                    {composite ? (
                      <select multiple value={selectedColumns(rule)} onChange={(event) => updateBlockingRule(index, {
                        column: null, columns: Array.from(event.target.selectedOptions, option => option.value),
                      })} className="min-h-24 w-full rounded-md border bg-background p-2 text-sm">
                        {columns.map(column => <option key={column} value={column}>{column}</option>)}
                      </select>
                    ) : (
                      <Select value={rule.column || ""} onValueChange={(value) => updateBlockingRule(index, { column: value, columns: [] })}>
                        <SelectTrigger><SelectValue placeholder="Pilih kolom" /></SelectTrigger>
                        <SelectContent>{columns.map(column => <SelectItem key={column} value={column}>{column}</SelectItem>)}</SelectContent>
                      </Select>
                    )}
                  </div>
                  <div className="space-y-2"><Label>Metode blocking</Label>
                    <Select value={rule.method} onValueChange={(value) => updateBlockingRule(index, { method: value })}>
                      <SelectTrigger><SelectValue /></SelectTrigger><SelectContent>
                        <SelectItem value="exact">Exact</SelectItem><SelectItem value="composite_exact">Composite Exact</SelectItem>
                        <SelectItem value="prefix">Prefix</SelectItem><SelectItem value="token_prefix">Token Prefix</SelectItem>
                        <SelectItem value="phonetic">Phonetic Indonesia</SelectItem><SelectItem value="ngram">Character N-gram</SelectItem>
                        <SelectItem value="email_local">Email Local Prefix</SelectItem><SelectItem value="phone_suffix">Phone Suffix</SelectItem>
                      </SelectContent></Select>
                  </div>
                  <div className="space-y-2"><Label>Normalizer</Label>
                    <Select value={rule.normalizers?.[0] || "auto"} onValueChange={(value) => updateBlockingRule(index, { normalizers: value === "auto" ? [] : [value] })}>
                      <SelectTrigger><SelectValue /></SelectTrigger><SelectContent>
                        <SelectItem value="auto">Otomatis</SelectItem><SelectItem value="basic">Basic</SelectItem><SelectItem value="name">Nama</SelectItem>
                        <SelectItem value="phone">Telepon</SelectItem><SelectItem value="email">Email</SelectItem><SelectItem value="address">Alamat</SelectItem>
                        <SelectItem value="identifier">Identifier</SelectItem><SelectItem value="date">Tanggal</SelectItem>
                      </SelectContent></Select>
                  </div>
                  <div className="space-y-2"><Label>Panjang</Label><Input type="number" min="1" max="20" value={rule.length || 3}
                    onChange={(event) => updateBlockingRule(index, { length: Number(event.target.value) })} /></div>
                  <Button variant="ghost" className="text-destructive" onClick={() => setBlockingRules(blockingRules.filter((_, position) => position !== index))}><Trash2 className="h-4 w-4" /></Button>
                </div>
              );
            })}
          </div>

          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div><h3 className="font-semibold">2. Matching dan Evidence</h3>
                <p className="text-xs text-muted-foreground">Similarity menjadi bukti probabilistik; required mismatch dapat memveto false positive.</p></div>
              <Button variant="outline" size="sm" onClick={() => setDedupRules([...dedupRules, {
                column: columns[0] || "", columns: [], method: "exact", weight: 2,
                normalizers: [], mismatch_penalty: 0, mismatch_threshold: 0.2,
                required: false, required_threshold: 0.999,
              }])}>
                <Plus className="h-4 w-4 mr-2" /> Tambah Matching
              </Button>
            </div>
            
            {dedupRules.length === 0 ? (
              <div className="text-center p-8 border border-dashed rounded-md text-muted-foreground">
                Belum ada kolom yang dipilih. Sistem menggunakan deteksi nama/telepon/email/alamat otomatis.
              </div>
            ) : (
              <div className="space-y-4">
                {dedupRules.map((rule, idx) => (
                  <div key={idx} className="space-y-4 rounded-md border bg-muted/10 p-4">
                    <div className="grid grid-cols-1 gap-3 md:grid-cols-[1fr_1fr_1fr_100px_auto] md:items-end">
                      <div className="space-y-2"><Label>{rule.method === "composite_exact" ? "Kolom gabungan" : "Kolom"}</Label>
                        {rule.method === "composite_exact" ? (
                          <select multiple value={selectedColumns(rule)} onChange={(event) => updateMatchingRule(idx, {
                            column: null, columns: Array.from(event.target.selectedOptions, option => option.value),
                          })} className="min-h-24 w-full rounded-md border bg-background p-2 text-sm">
                            {columns.map(column => <option key={column} value={column}>{column}</option>)}
                          </select>
                        ) : (
                          <Select value={rule.column || ""} onValueChange={(value) => updateMatchingRule(idx, { column: value, columns: [] })}>
                            <SelectTrigger><SelectValue placeholder="Pilih kolom" /></SelectTrigger><SelectContent>
                              {columns.map(column => <SelectItem key={column} value={column}>{column}</SelectItem>)}
                            </SelectContent></Select>
                        )}
                      </div>
                      <div className="space-y-2"><Label>Algoritma</Label>
                        <Select value={rule.method} onValueChange={(value) => updateMatchingRule(idx, { method: value })}>
                          <SelectTrigger><SelectValue /></SelectTrigger><SelectContent>
                            <SelectItem value="exact">Exact Match</SelectItem><SelectItem value="composite_exact">Composite Exact</SelectItem>
                            <SelectItem value="jaro_winkler">Jaro-Winkler</SelectItem><SelectItem value="phonetic">Phonetic Indonesia</SelectItem>
                            <SelectItem value="fuzzy_ratio">Fuzzy Ratio</SelectItem><SelectItem value="token_sort">Token Sort</SelectItem>
                            <SelectItem value="token_set">Token Set</SelectItem><SelectItem value="phone">Phone Match</SelectItem><SelectItem value="email">Email Match</SelectItem>
                          </SelectContent></Select>
                      </div>
                      <div className="space-y-2"><Label>Normalizer</Label>
                        <Select value={rule.normalizers?.[0] || "auto"} onValueChange={(value) => updateMatchingRule(idx, { normalizers: value === "auto" ? [] : [value] })}>
                          <SelectTrigger><SelectValue /></SelectTrigger><SelectContent>
                            <SelectItem value="auto">Otomatis</SelectItem><SelectItem value="basic">Basic</SelectItem><SelectItem value="name">Nama</SelectItem>
                            <SelectItem value="phone">Telepon</SelectItem><SelectItem value="email">Email</SelectItem><SelectItem value="address">Alamat</SelectItem>
                            <SelectItem value="identifier">Identifier</SelectItem><SelectItem value="date">Tanggal</SelectItem>
                          </SelectContent></Select>
                      </div>
                      <div className="space-y-2"><Label>Bobot</Label><Input type="number" min="0" max="5" step="0.1" value={rule.weight ?? 2}
                        onChange={(event) => updateMatchingRule(idx, { weight: Number(event.target.value) })} /></div>
                      <Button variant="ghost" className="text-destructive" onClick={() => setDedupRules(dedupRules.filter((_, position) => position !== idx))}><Trash2 className="h-4 w-4" /></Button>
                    </div>
                    <div className="grid grid-cols-1 gap-3 border-t pt-3 md:grid-cols-3">
                      <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={Boolean(rule.required)}
                        onChange={(event) => updateMatchingRule(idx, { required: event.target.checked })} />Wajib cocok (mismatch = veto)</label>
                      <div className="space-y-1"><Label>Mismatch penalty</Label><Input type="number" min="0" max="1" step="0.1" value={rule.mismatch_penalty ?? 0}
                        onChange={(event) => updateMatchingRule(idx, { mismatch_penalty: Number(event.target.value) })} /></div>
                      <div className="space-y-1"><Label>Mismatch threshold</Label><Input type="number" min="0" max="1" step="0.05" value={rule.mismatch_threshold ?? 0.2}
                        onChange={(event) => updateMatchingRule(idx, { mismatch_threshold: Number(event.target.value) })} /></div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="space-y-4 border-t pt-6">
            <div className="flex items-center justify-between gap-3">
              <div><h3 className="font-semibold">3. Deterministic Identity Keys</h3><p className="text-xs text-muted-foreground">Kecocokan lengkap pada kombinasi ini langsung dianggap duplikat.</p></div>
              <Button variant="outline" size="sm" onClick={() => setExactMatchRules([...exactMatchRules, { columns: columns.slice(0, 1), normalizers: ["basic"] }])}><Plus className="mr-2 h-4 w-4" />Tambah Identity Key</Button>
            </div>
            {exactMatchRules.map((rule, index) => (
              <div key={index} className="flex items-start gap-3 rounded-md border p-4">
                <div className="flex-1 space-y-2"><Label>Pilih satu atau beberapa kolom</Label>
                  <select multiple value={rule.columns || []} onChange={(event) => setExactMatchRules(exactMatchRules.map((item, position) => position === index ? {
                    ...item, columns: Array.from(event.target.selectedOptions, option => option.value),
                  } : item))} className="min-h-24 w-full rounded-md border bg-background p-2 text-sm">
                    {columns.map(column => <option key={column} value={column}>{column}</option>)}
                  </select>
                </div>
                <Button variant="ghost" className="text-destructive" onClick={() => setExactMatchRules(exactMatchRules.filter((_, position) => position !== index))}><Trash2 className="h-4 w-4" /></Button>
              </div>
            ))}
          </div>

          <div className="space-y-4 border-t pt-6">
            <div><h3 className="font-semibold">4. Cluster Validation</h3><p className="text-xs text-muted-foreground">Memastikan setiap anggota cukup mirip dengan representative dan cluster tidak terbentuk hanya karena chaining.</p></div>
            <div className="grid grid-cols-1 gap-4 rounded-md border p-4 md:grid-cols-4 md:items-end">
              <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={clusterValidation.enabled}
                onChange={(event) => setClusterValidation({ ...clusterValidation, enabled: event.target.checked })} />Aktifkan validasi</label>
              <div className="space-y-2"><Label>Metode</Label><Select value={clusterValidation.method} onValueChange={(value) => setClusterValidation({ ...clusterValidation, method: value })}>
                <SelectTrigger><SelectValue /></SelectTrigger><SelectContent><SelectItem value="representative">Representative/Medoid</SelectItem><SelectItem value="connected">Connected (legacy)</SelectItem></SelectContent>
              </Select></div>
              <div className="space-y-2"><Label>Min. cohesion</Label><Input type="number" min="0" max="1" step="0.05" value={clusterValidation.min_cohesion}
                onChange={(event) => setClusterValidation({ ...clusterValidation, min_cohesion: Number(event.target.value) })} /></div>
              <div className="space-y-2"><Label>Min. representative score</Label><Input type="number" min="0" max="1" step="0.05" value={clusterValidation.min_representative_score}
                onChange={(event) => setClusterValidation({ ...clusterValidation, min_representative_score: Number(event.target.value) })} /></div>
            </div>
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

export default function RulesPage() {
  return (
    <Suspense>
      <RulesContent />
    </Suspense>
  );
}
