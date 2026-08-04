"""LLM gateway provider-agnostic (OpenAI-compatible chat completions).

Dipakai untuk fitur AI Fase berikutnya (NL rule generation, root-cause explanation —
lihat docs/ENHANCEMENTS.md). Tanpa konfigurasi LLM_BASE_URL/LLM_API_KEY, fitur AI
dinonaktifkan secara graceful.
"""
from __future__ import annotations

from datetime import date

import httpx

from ..config import settings


def llm_available() -> bool:
    return bool(settings.llm_base_url and settings.llm_api_key and settings.llm_model)


class LLMNotConfigured(RuntimeError):
    pass


def chat(messages: list[dict], temperature: float = 0.2, max_tokens: int = 1024) -> str:
    if not llm_available():
        raise LLMNotConfigured(
            "LLM belum dikonfigurasi — isi LLM_BASE_URL, LLM_API_KEY, dan LLM_MODEL di .env"
        )
    resp = httpx.post(
        settings.llm_base_url.rstrip("/") + "/chat/completions",
        headers={"Authorization": f"Bearer {settings.llm_api_key}"},
        json={
            "model": settings.llm_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        },
        timeout=120,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


RULE_GEN_SYSTEM = """Kamu adalah compiler rule data-quality. Ubah SATU instruksi pengguna
berbahasa Indonesia atau Inggris menjadi SATU proposal rule JSON yang dapat dieksekusi. Pengguna
akan meninjau proposal sebelum mengaktifkannya. Jika input kurang jelas, buat interpretasi terbaik
dengan memakai nama kolom, tipe data, contoh nilai, dan konteks instruksi; jangan menolak input.

RULE TYPE DAN SCHEMA PARAMETER YANG DIIZINKAN:
- email_format: format email valid. params HARUS {}
- phone_id: nomor HP Indonesia 10-13 digit, awalan 08/+62. params HARUS {}
- nik: NIK 16 digit numerik. params HARUS {}
- not_null: nilai tidak boleh null/kosong. params HARUS {}
- numeric_range: rentang angka. params: {"min": number|null, "max": number|null}; minimal satu batas
- date_range: rentang tanggal. params: {"min": "YYYY-MM-DD"|null, "max": "YYYY-MM-DD"|null}; minimal satu batas
- starts_with: teks harus diawali literal. params: {"prefix": string, "case_sensitive": boolean}
- regex: pola Python regex untuk constraint teks yang tidak dapat direpresentasikan tipe lain.
  params: {"pattern": string}. Evaluator menggunakan re.match pada nilai non-kosong.
- cross_column: perbandingan dua kolom. params:
  {"left": "nama_kolom", "op": ">|>=|<|<=|==|!=", "right": "nama_kolom"}

KONTRAK WAJIB:
1. Pilih nama kolom PERSIS dari daftar kolom. Jangan membuat atau memperbaiki nama kolom.
2. Pilih tipe berdasarkan intent, bukan berdasarkan kata kunci tunggal.
3. Seluruh logika eksekusi WAJIB ada dalam rule_type dan params. Description hanya label UI dan
   TIDAK pernah digunakan evaluator.
4. Isi params hanya dengan key pada schema tipe terpilih dan gunakan tipe JSON yang benar.
5. Pertahankan literal pengguna persis, termasuk titik, tanda hubung, kapitalisasi, dan batas.
6. Gunakan tipe khusus bila tersedia; regex hanya pilihan terakhir.
7. Jika ada beberapa constraint, pilih constraint utama yang paling eksplisit dan paling relevan
   dengan kolom. Jelaskan interpretasi yang dipilih dalam description agar pengguna dapat meninjau.
8. Nilai kosong hanya diperiksa oleh not_null, kecuali starts_with yang juga menolak nilai kosong.
9. Jika kolom tidak disebut jelas, pilih kolom yang paling cocok berdasarkan nama, tipe, dan contoh
   nilai. Jika constraint tidak memiliki tipe khusus, representasikan dengan regex yang valid.
10. Jangan pernah mengembalikan error hanya karena bahasa pengguna singkat, informal, typo ringan,
    ambigu, atau tidak menyebut tipe rule. Selalu hasilkan proposal terbaik yang masih executable.

PEMETAAN CONTOH:
- "alamat harus diawali Jl." -> starts_with, {"prefix":"Jl.","case_sensitive":false}
- "kode harus diawali huruf kapital ABC" -> starts_with,
  {"prefix":"ABC","case_sensitive":true}
- "umur minimal 18 maksimal 60" -> numeric_range, {"min":18,"max":60}
- "tanggal lahir setelah 1900-01-01" -> date_range, {"min":"1900-01-01","max":null}
- "tanggal selesai harus lebih besar dari tanggal mulai" -> cross_column
- "status hanya aktif atau nonaktif" -> regex, {"pattern":"^(aktif|nonaktif)$"}
- "email harus valid" -> email_format
- "email wajib diisi" -> not_null

OUTPUT — jawab HANYA satu object JSON valid:
{"column_name":"<nama persis>","rule_type":"<tipe>","params":{},
 "description":"<ringkasan bahasa Indonesia yang menyatakan interpretasi rule_type+params>"}
"""


def _parse_json_response(content: str):
    import json

    text = content.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text.strip())


def generate_rule(instruction: str, columns: list[dict]) -> dict:
    """NL -> rule terstruktur. columns: [{name, inferred_type, sample_values}]."""
    schema_desc = "\n".join(
        f"- {c['name']} (tipe {c['inferred_type']}, contoh: {c.get('sample_values', [])})"
        for c in columns
    )
    content = chat(
        [
            {"role": "system", "content": RULE_GEN_SYSTEM},
            {"role": "user",
             "content": (
                 f"Tanggal hari ini: {date.today().isoformat()}\n"
                 f"Kolom dataset:\n{schema_desc}\n\n"
                 f"Instruksi pengguna:\n{instruction.strip()}"
             )},
        ],
        temperature=0.0,
    )
    proposal = _parse_json_response(content)
    if not isinstance(proposal, dict):
        raise ValueError("LLM harus mengembalikan satu object rule")
    return proposal


RULE_SUGGEST_SYSTEM = """Kamu adalah asisten data quality. Tugasmu MENYARANKAN rule validasi
yang relevan untuk sebuah dataset berdasarkan skema kolom & contoh nilainya SAJA — tanpa
diminta instruksi spesifik oleh pengguna (auto-suggest).

Jenis rule yang tersedia:
- email_format: format email valid. params: {}
- phone_id: nomor HP Indonesia 10-13 digit awalan 08/+62. params: {}
- nik: NIK 16 digit numerik. params: {}
- not_null: kolom tidak boleh kosong (sarankan hanya untuk kolom yang tampak wajib, mis.
  ID, kunci utama, atau kolom penting yang sample-nya selalu terisi).
- numeric_range: angka dalam rentang wajar berdasarkan contoh nilai. params: {"min", "max"}
- date_range: tanggal dalam rentang wajar (mis. tanggal lahir 1900-sekarang). params:
  {"min": "YYYY-MM-DD"|null, "max": "YYYY-MM-DD"|null}
- cross_column: hanya sarankan bila ada dua kolom yang JELAS berelasi logis dari
  namanya (mis. tanggal_checkin/tanggal_checkout, tanggal_mulai/tanggal_selesai).
  params: {"left", "op", "right"}

ATURAN PENTING:
- JANGAN sarankan rule untuk kombinasi kolom+jenis yang sudah ada di daftar "Rule aktif".
- JANGAN sarankan regex kustom — hanya jenis di atas.
- Maksimal 5 saran, urutkan dari yang paling bernilai/jelas.
- Jika tidak ada saran yang benar-benar relevan, kembalikan array kosong — jangan memaksakan.

Jawab HANYA dengan JSON array valid tanpa teks lain, tiap elemen:
{"column_name": "...", "rule_type": "...", "params": {...}, "description": "..."}"""


def suggest_rules(columns: list[dict], existing: list[tuple[str, str]]) -> list[dict]:
    """Auto-suggest (F4): sarankan rule dari skema & sample TANPA instruksi pengguna.
    columns: [{name, inferred_type, sample_values}]. existing: [(column_name, rule_type)]
    yang sudah aktif, supaya tidak disarankan ulang."""
    schema_desc = "\n".join(
        f"- {c['name']} (tipe {c['inferred_type']}, contoh: {c.get('sample_values', [])})"
        for c in columns
    )
    existing_desc = ("\n".join(f"- {col} ({rt})" for col, rt in existing)
                     or "(belum ada rule aktif)")
    content = chat(
        [
            {"role": "system", "content": RULE_SUGGEST_SYSTEM},
            {"role": "user",
             "content": f"Kolom dataset:\n{schema_desc}\n\nRule aktif:\n{existing_desc}"},
        ],
        temperature=0.2,
        max_tokens=1500,
    )
    result = _parse_json_response(content)
    return result if isinstance(result, list) else []
