import os

def fix_file(filepath):
    with open(filepath, "r") as f:
        content = f.read()

    # Add RadioGroup import
    if "RadioGroup" not in content:
        import_str = 'import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";\n'
        content = content.replace('import { Checkbox } from "@/components/ui/checkbox";', import_str)
        # remove Checkbox import if still there
        content = content.replace('import { Checkbox } from "@/components/ui/checkbox";\n', '')
    
    # Replace the Processing Options block
    # We'll find the <h3 className="font-medium">Opsi Pemrosesan</h3> block
    import re
    
    # Need to handle state
    # from:
    # enable_profiling: true,
    # enable_deduplication: false,
    # to using a combined state or just deriving them
    # Wait, the backend might expect enable_profiling and enable_deduplication.
    # We can use a derived state for the radio group:
    # const processingMode = (form.enable_profiling && form.enable_deduplication) ? "both" : form.enable_deduplication ? "dedup" : "profiling";
    # const setProcessingMode = (mode) => {
    #    if (mode === "both") setForm({...form, enable_profiling: true, enable_deduplication: true});
    #    if (mode === "dedup") setForm({...form, enable_profiling: false, enable_deduplication: true});
    #    if (mode === "profiling") setForm({...form, enable_profiling: true, enable_deduplication: false});
    # }

    old_options = """              <div className="pt-4 border-t space-y-4">
                <h3 className="font-medium">Opsi Pemrosesan</h3>
                
                <div className="flex flex-col sm:flex-row gap-6">
                  <div className="flex items-center space-x-2">
                    <Checkbox 
                      id="profiling" 
                      checked={form.enable_profiling}
                      onCheckedChange={(checked) => setForm({...form, enable_profiling: checked as boolean})}
                    />
                    <Label htmlFor="profiling" className="font-normal cursor-pointer">
                      Jalankan Data Profiling
                    </Label>
                  </div>
                  
                  <div className="flex items-center space-x-2">
                    <Checkbox 
                      id="dedup" 
                      checked={form.enable_deduplication}
                      onCheckedChange={(checked) => setForm({...form, enable_deduplication: checked as boolean})}
                    />
                    <Label htmlFor="dedup" className="font-normal cursor-pointer">
                      Entity Resolution (Smart Deduplication)
                    </Label>
                  </div>
                </div>
              </div>"""
              
    new_options = """              <div className="pt-4 border-t space-y-4">
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
              </div>"""

    content = content.replace(old_options, new_options)
    
    # In [id]/page.tsx, the dataset dropdown is disabled. 
    # The user complained about it showing number instead of name.
    # Let's replace the dropdown with a read-only input if it's disabled.
    if "[id]" in filepath:
        old_ds = """                <Select disabled value={form.dataset_id}>
                  <SelectTrigger className="bg-muted">
                    <SelectValue placeholder="Pilih dataset" />
                  </SelectTrigger>
                  <SelectContent>
                    {datasets.map(d => (
                      <SelectItem key={d.id} value={String(d.id)}>{d.name} (ID: {d.id})</SelectItem>
                    ))}
                  </SelectContent>
                </Select>"""
        new_ds = """                <div className="flex h-10 w-full rounded-md border border-input bg-muted px-3 py-2 text-sm ring-offset-background disabled:cursor-not-allowed disabled:opacity-50">
                  {pipeline ? `${pipeline.name} (ID: ${pipeline.id})` : "Memuat..."}
                </div>"""
        content = content.replace(old_ds, new_ds)
    elif "create" in filepath:
        # If it's create page, ensure the SelectValue correctly maps to dataset name.
        # Sometimes SelectValue needs a clear display text.
        # But Radix UI Select automatically handles it if the children is text.
        # We can just change {d.name} (ID: {d.id}) to just {d.name}
        old_item = "{d.name} (ID: {d.id})"
        new_item = "{d.name}"
        content = content.replace(old_item, new_item)

    with open(filepath, "w") as f:
        f.write(content)

fix_file("frontend/app/pipelines/create/page.tsx")
fix_file("frontend/app/pipelines/[id]/page.tsx")
