"use client";

import Shell from "@/components/Shell";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { AlertCircle, UploadCloud, FileType, CheckCircle2 } from "lucide-react";
import { Progress } from "@/components/ui/progress";

export default function UploadPage() {
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [progress, setProgress] = useState(0);

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return;

    setLoading(true);
    setError("");
    setProgress(10);
    
    // Simulate progress bar for better UX since fetch API doesn't support upload progress easily natively
    const progressInterval = setInterval(() => {
      setProgress((prev) => {
        if (prev >= 90) {
          clearInterval(progressInterval);
          return 90;
        }
        return prev + 10;
      });
    }, 500);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await api("/datasets/upload", {
        method: "POST",
        body: formData,
        headers: {
          // Remove default application/json header so browser sets multipart/form-data
        },
      });
      clearInterval(progressInterval);
      setProgress(100);
      
      // Delay sedikit agar user melihat progress 100%
      setTimeout(() => {
        router.push(`/datasets/${res.id}`);
      }, 500);
    } catch (err: any) {
      clearInterval(progressInterval);
      setError(err.message);
      setLoading(false);
      setProgress(0);
    }
  };

  return (
    <Shell title="Upload Data Source" subtitle="Unggah dataset lokal sebagai sumber data">
      <div className="max-w-2xl mx-auto mt-6">
        <form onSubmit={handleUpload}>
          <Card>
            <CardHeader>
              <CardTitle>Unggah Berkas Baru</CardTitle>
              <CardDescription>Sistem secara otomatis akan mendeteksi delimiter dan format encoding dari file yang Anda unggah.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {error && (
                <div className="bg-destructive/15 text-destructive p-4 rounded-md border border-destructive/20 flex items-center gap-2">
                  <AlertCircle className="h-5 w-5" />
                  <p className="text-sm">{error}</p>
                </div>
              )}
              
              <div className="space-y-4">
                <Label htmlFor="file-upload" className="text-base font-semibold">Pilih Berkas Dataset</Label>
                
                <div className={`relative border-2 border-dashed rounded-lg p-10 flex flex-col items-center justify-center transition-colors ${file ? 'border-primary/50 bg-primary/5' : 'border-muted-foreground/25 hover:border-primary/50 hover:bg-muted/50'} ${loading ? 'opacity-50 pointer-events-none' : ''}`}>
                  
                  <input
                    id="file-upload"
                    type="file"
                    accept=".csv,.xlsx"
                    onChange={(e) => setFile(e.target.files?.[0] || null)}
                    className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                    disabled={loading}
                  />
                  
                  {file ? (
                    <div className="flex flex-col items-center text-center space-y-2">
                      <div className="h-12 w-12 rounded-full bg-primary/10 flex items-center justify-center mb-2">
                        <CheckCircle2 className="h-6 w-6 text-primary" />
                      </div>
                      <p className="font-medium text-lg">{file.name}</p>
                      <p className="text-sm text-muted-foreground">
                        {(file.size / (1024 * 1024)).toFixed(2)} MB • {file.name.split('.').pop()?.toUpperCase()}
                      </p>
                      <Button type="button" variant="link" size="sm" onClick={() => setFile(null)} className="mt-2" disabled={loading}>
                        Ganti berkas
                      </Button>
                    </div>
                  ) : (
                    <div className="flex flex-col items-center text-center space-y-2">
                      <div className="h-12 w-12 rounded-full bg-muted flex items-center justify-center mb-2">
                        <UploadCloud className="h-6 w-6 text-muted-foreground" />
                      </div>
                      <p className="font-medium text-lg">Klik untuk memilih atau seret berkas ke sini</p>
                      <div className="flex items-center gap-2 text-sm text-muted-foreground mt-2">
                        <FileType className="h-4 w-4" />
                        <span>Mendukung CSV, Excel (.xlsx) hingga 100MB</span>
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {loading && (
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Mengunggah dan memproses...</span>
                    <span className="font-medium">{progress}%</span>
                  </div>
                  <Progress value={progress} className="h-2" />
                </div>
              )}
            </CardContent>
            <CardFooter className="flex justify-between border-t p-6 bg-muted/10">
              <Button type="button" variant="outline" onClick={() => router.back()} disabled={loading}>
                Batal
              </Button>
              <Button type="submit" disabled={!file || loading}>
                {loading ? "Memproses..." : "Mulai Upload & Proses"}
              </Button>
            </CardFooter>
          </Card>
        </form>
      </div>
    </Shell>
  );
}
