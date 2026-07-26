"""LLM gateway provider-agnostic (OpenAI-compatible chat completions).

Dipakai untuk fitur AI Fase berikutnya (NL rule generation, root-cause explanation —
lihat docs/ENHANCEMENTS.md). Tanpa konfigurasi LLM_BASE_URL/LLM_API_KEY, fitur AI
dinonaktifkan secara graceful.
"""
from __future__ import annotations
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


RULE_GEN_SYSTEM = """Kamu adalah asisten data quality. Tugasmu mengubah instruksi validasi \
berbahasa natural (Indonesia/Inggris) menjadi rule terstruktur JSON.

Jenis rule yang tersedia:
- email_format: format email valid. params: {}
- phone_id: nomor HP Indonesia 10-13 digit awalan 08/+62. params: {}
- nik: NIK 16 digit numerik. params: {}
- not_null: kolom tidak boleh kosong. params: {}
- numeric_range: angka dalam rentang. params: {"min": <angka|null>, "max": <angka|null>}
- date_range: tanggal dalam rentang. params: {"min": "YYYY-MM-DD"|null, "max": "YYYY-MM-DD"|null}
- regex: pola regex kustom (Python re, full match dari awal string). params: {"pattern": "..."}
- cross_column: perbandingan antar kolom. params: {"left": "<kolom>", "op": ">|>=|<|<=|==|!=", "right": "<kolom>"}

Jawab HANYA dengan JSON valid tanpa teks lain, format:
{"column_name": "<nama kolom target, atau kolom kiri untuk cross_column>",
 "rule_type": "<salah satu di atas>",
 "params": {...},
 "description": "<deskripsi singkat bahasa Indonesia>"}

Pilih kolom dari daftar kolom yang diberikan (perhatikan ejaan persis). Jika instruksi paling
cocok dengan rule bawaan (email/phone/nik), gunakan itu alih-alih regex."""


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
             "content": f"Kolom dataset:\n{schema_desc}\n\nInstruksi: {instruction}"},
        ],
        temperature=0.0,
    )
    return _parse_json_response(content)


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
