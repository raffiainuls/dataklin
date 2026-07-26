with open("frontend/app/rules/page.tsx", "r") as f:
    content = f.read()

import re

# Remove the weight input in the UI
weight_input_block = """                    <div className="w-24 space-y-2">
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
                    </div>"""

# Remove the total weight display
total_weight_block = """                <div className="flex justify-between items-center px-2 py-1 bg-muted/30 rounded">
                  <span className="font-semibold text-sm">Total Bobot:</span>
                  <span className={`font-bold ${dedupRules.reduce((a, r) => a + (Number(r.weight) || 0), 0) !== 100 ? 'text-destructive' : 'text-emerald-600'}`}>
                    {dedupRules.reduce((a, r) => a + (Number(r.weight) || 0), 0)}%
                  </span>
                </div>"""

# Update validation logic in saveConfig
old_save_config = """    const totalWeight = dedupRules.reduce((acc, r) => acc + (Number(r.weight) || 0), 0);
    if (dedupRules.length > 0 && Math.abs(totalWeight - 100) > 0.01) {
      setError(`Total bobot harus tepat 100%. Saat ini: ${totalWeight}%`);
      return;
    }"""

new_save_config = """    if (dedupRules.length === 0) {
      // Allow empty rules to fallback to auto
    }"""

content = content.replace(weight_input_block, "")
content = content.replace(total_weight_block, "")
content = content.replace(old_save_config, new_save_config)

# Also replace the rule addition to not include weight
content = content.replace('{ column: columns[0] || "", method: "exact", weight: 0 }', '{ column: columns[0] || "", method: "exact" }')

# Update description
old_desc = "Pilih kolom mana saja yang akan digunakan untuk mencari data ganda, metode algoritmanya, dan bobot masing-masing kolom (total harus 100%)."
new_desc = "Pilih kolom yang akan digunakan untuk mencari data ganda dan metode algoritmanya. Sistem akan secara otomatis menghitung probabilitas tiap kolom (Term Frequency & Expectation-Maximization ala Splink) untuk menentukan bobot secara cerdas."

content = content.replace(old_desc, new_desc)

with open("frontend/app/rules/page.tsx", "w") as f:
    f.write(content)
