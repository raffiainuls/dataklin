"""Entity resolution (F5): blocking key + fuzzy similarity -> RecordMatchScore -> union-find cluster."""
from __future__ import annotations
import re
from itertools import combinations

import pandas as pd
from rapidfuzz import fuzz

from ..config import settings
from .rule_engine import normalize_phone

ROLE_HINTS = {
    "name": ("nama", "name"),
    "phone": ("hp", "phone", "telp", "telepon", "handphone", "msisdn"),
    "email": ("email", "mail"),
    "address": ("alamat", "address", "addr"),
    "updated": ("update", "updated", "modified", "last_modified"),
    "source": ("sumber", "source", "asal_data"),
}

# bobot sinyal kemiripan; sinyal yang tidak tersedia di-renormalisasi
WEIGHTS = {"phone": 0.35, "email": 0.25, "name": 0.25, "address": 0.15}


def detect_roles(columns: list[str]) -> dict:
    roles: dict[str, str] = {}
    for role, hints in ROLE_HINTS.items():
        for col in columns:
            low = str(col).lower()
            if any(h in low for h in hints):
                roles[role] = str(col)
                break
    return roles


def _norm(value) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    return re.sub(r"\s+", " ", str(value)).strip().lower()



def get_term_frequencies(records: dict[int, dict], dedup_config: dict) -> dict:
    u_probs = {}
    total = len(records)
    if total == 0 or not dedup_config.get("rules"): 
        return u_probs
        
    for r in dedup_config["rules"]:
        col = r.get("column")
        counts = {}
        for rec in records.values():
            val = _norm(rec.get(col))
            if val:
                counts[val] = counts.get(val, 0) + 1
        u_probs[col] = {k: v / total for k, v in counts.items()}
    return u_probs

def pair_score(ra: dict, rb: dict, roles: dict, dedup_config: dict | None = None, u_probs: dict = None) -> tuple[float, dict]:
    parts: dict[str, float] = {}
    
    if dedup_config and dedup_config.get("rules"):
        import math
        prior_prob = 0.001
        odds = prior_prob / (1.0 - prior_prob)
        
        m_prob = 0.95
        
        for r in dedup_config["rules"]:
            col = r.get("column")
            method = r.get("method")
            
            va, vb = ra.get(col), rb.get(col)
            if not va or not vb:
                continue
                
            na, nb = _norm(va), _norm(vb)
            if not na or not nb:
                continue
                
            if method == "exact":
                score = 1.0 if na == nb else 0.0
            elif method == "phone":
                pa, pb = normalize_phone(va), normalize_phone(vb)
                score = 1.0 if pa and pb and pa == pb else 0.0
            elif method == "email":
                score = 1.0 if na == nb else (fuzz.ratio(na, nb) / 100) * 0.5
            elif method == "token_sort":
                score = fuzz.token_sort_ratio(na, nb) / 100
            elif method == "token_set":
                score = fuzz.token_set_ratio(na, nb) / 100
            elif method == "fuzzy_ratio":
                score = fuzz.ratio(na, nb) / 100
            else:
                score = 0.0
                
            # Splink-like Probabilistic Update with Term Frequency
            freq_a = u_probs.get(col, {}).get(na, 0.01) if u_probs else 0.01
            freq_b = u_probs.get(col, {}).get(nb, 0.01) if u_probs else 0.01
            u_prob = max(freq_a, freq_b)
            u_prob = max(u_prob, 0.0001)  # floor
            
            # Bayes Factor interpolation
            bf = (m_prob * score + (1.0 - m_prob) * (1.0 - score)) / (u_prob * score + (1.0 - u_prob) * (1.0 - score))
            odds *= bf
            parts[col] = round(score, 3)
            
        final_prob = odds / (1.0 + odds)
        return final_prob, parts
    else:
        total_w = 0.0
        acc = 0.0
        for role, weight in WEIGHTS.items():
            col = roles.get(role)
            if not col:
                continue
            va, vb = ra.get(col), rb.get(col)
            if role == "phone":
                na, nb = normalize_phone(va), normalize_phone(vb)
                if not na or not nb:
                    continue
                score = 1.0 if na == nb else 0.0
            elif role == "email":
                na, nb = _norm(va), _norm(vb)
                if not na or not nb:
                    continue
                score = 1.0 if na == nb else (fuzz.ratio(na, nb) / 100) * 0.5
            elif role == "name":
                na, nb = _norm(va), _norm(vb)
                if not na or not nb:
                    continue
                score = fuzz.token_sort_ratio(na, nb) / 100
            else:  # address
                na, nb = _norm(va), _norm(vb)
                if not na or not nb:
                    continue
                score = fuzz.token_set_ratio(na, nb) / 100
            total_w += weight
            acc += weight * score
            parts[role] = round(score, 3)
        if total_w < 0.4:
            return 0.0, parts
        return acc / total_w, parts


def _name_block_key(name: str) -> str:
    tokens = _norm(name).split()
    if not tokens:
        return ""
    return "".join(sorted(t[:3] for t in tokens[:2]))


def build_blocks(records: dict[int, dict], roles: dict, dedup_config: dict | None = None) -> list[set[int]]:
    blocks: dict[str, set[int]] = {}

    def add(key: str, idx: int) -> None:
        if key:
            blocks.setdefault(key, set()).add(idx)

    if dedup_config and dedup_config.get("rules"):
        for idx, rec in records.items():
            for r in dedup_config["rules"]:
                col = r.get("column")
                method = r.get("method")
                val = rec.get(col)
                if not val:
                    continue
                if method == "exact" or method == "email":
                    add(f"{col}:{_norm(val)}", idx)
                elif method == "phone":
                    add(f"{col}:" + (normalize_phone(val) or ""), idx)
                elif method in ("token_sort", "token_set", "fuzzy_ratio"):
                    add(f"{col}:" + _name_block_key(str(val)), idx)
    else:
        for idx, rec in records.items():
            if roles.get("phone"):
                add("p:" + (normalize_phone(rec.get(roles["phone"])) or ""), idx)
            if roles.get("email"):
                add("e:" + _norm(rec.get(roles["email"])), idx)
            if roles.get("name"):
                add("n:" + _name_block_key(rec.get(roles["name"], "")), idx)
                
    return [b for b in blocks.values() if 2 <= len(b) <= settings.er_max_block_size]


class UnionFind:
    def __init__(self):
        self.parent: dict[int, int] = {}

    def find(self, x: int) -> int:
        self.parent.setdefault(x, x)
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[rb] = ra


def resolve_entities(df: pd.DataFrame, dedup_config: dict | None = None) -> dict:
    """Kembalikan {roles, clusters:[{members:[idx], cohesion, pairs:[(a,b,score,parts)]}]}."""
    roles = detect_roles([str(c) for c in df.columns])
    
    if not dedup_config or not dedup_config.get("rules"):
        if not roles.get("name") and not roles.get("phone") and not roles.get("email"):
            return {"roles": roles, "clusters": []}
    
    threshold = settings.er_pair_threshold
    if dedup_config and "threshold" in dedup_config:
        threshold = float(dedup_config["threshold"])

    subset = df.head(settings.er_max_rows)
    records = {int(idx): row for idx, row in subset.astype(object).iterrows()}
    records = {idx: {str(k): v for k, v in dict(row).items()} for idx, row in records.items()}

    scored: dict[tuple[int, int], tuple[float, dict]] = {}
    uf = UnionFind()
    pair_budget = settings.er_max_pairs
    
    u_probs = get_term_frequencies(records, dedup_config) if dedup_config else None

    for block in build_blocks(records, roles, dedup_config):
        for a, b in combinations(sorted(block), 2):
            key = (a, b)
            if key in scored:
                continue
            if pair_budget <= 0:
                break
            pair_budget -= 1
            score, parts = pair_score(records[a], records[b], roles, dedup_config, u_probs)
            scored[key] = (score, parts)
            if score >= threshold:
                uf.union(a, b)

    groups: dict[int, list[int]] = {}
    for idx in uf.parent:
        groups.setdefault(uf.find(idx), []).append(idx)

    clusters = []
    for members in groups.values():
        if len(members) < 2:
            continue
        members = sorted(members)[:20]
        pairs = []
        for a, b in combinations(members, 2):
            if (a, b) in scored:
                score, parts = scored[(a, b)]
                pairs.append({"a": a, "b": b, "score": round(score, 4), "parts": parts})
        cohesion = sum(p["score"] for p in pairs) / len(pairs) if pairs else 0.0
        clusters.append({
            "members": members,
            "cohesion": round(cohesion, 4),
            "pairs": pairs,
            "records": {m: records[m] for m in members},
        })
    clusters.sort(key=lambda c: -c["cohesion"])
    return {"roles": roles, "clusters": clusters}


def json_safe_record(record: dict) -> dict:
    out = {}
    for key, value in record.items():
        if value is None or (isinstance(value, float) and pd.isna(value)):
            out[key] = None
        elif isinstance(value, float):
            # kolom ID numerik (NIK dsb) tidak boleh tampil sebagai "...001.0"
            out[key] = int(value) if value.is_integer() else value
        elif isinstance(value, (int, str, bool)):
            out[key] = value
        else:
            out[key] = str(value)
    return out
