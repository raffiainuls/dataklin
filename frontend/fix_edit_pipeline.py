with open("app/pipelines/[id]/page.tsx", "r") as f:
    content = f.read()

import re

# We can replace the whole block dynamically
pattern = re.compile(r'(<div className="pt-4 border-t space-y-4">\s*<h3 className="font-medium">Opsi Pemrosesan</h3>\s*<div className="flex flex-col sm:flex-row gap-6">.*?</div>\s*</div>)', re.DOTALL)

new_options = """<div className="pt-4 border-t space-y-4">
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

content = pattern.sub(new_options, content)

with open("app/pipelines/[id]/page.tsx", "w") as f:
    f.write(content)
