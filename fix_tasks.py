import re

with open("backend/app/worker/tasks.py", "r") as f:
    content = f.read()

old = """        er = resolve_entities(df)"""
new = """        er = resolve_entities(df, dedup_config=dataset.dedup_config)"""

content = content.replace(old, new)

with open("backend/app/worker/tasks.py", "w") as f:
    f.write(content)
