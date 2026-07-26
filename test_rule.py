import sys
import os

sys.path.append(os.path.join(os.getcwd(), 'backend'))

from app.services.llm import generate_rule

try:
    rule = generate_rule("Kolom NIK harus berupa angka 16 digit", [{"name": "nik", "inferred_type": "string"}])
    print(rule)
except Exception as e:
    print(f"Error: {e}")
