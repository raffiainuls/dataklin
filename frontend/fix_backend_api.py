with open("backend/app/routers/rules.py", "r") as f:
    content = f.read()

import re

# Remove weight from DedupRule
content = content.replace("    weight: float\n", "")

old_validation = """    total_weight = sum(r.weight for r in body.rules)
    if body.rules and abs(total_weight - 100.0) > 0.01:
        raise HTTPException(400, "Total bobot rule deduplikasi harus tepat 100%")"""

content = content.replace(old_validation, "")

with open("backend/app/routers/rules.py", "w") as f:
    f.write(content)
