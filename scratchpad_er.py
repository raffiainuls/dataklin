import re
from rapidfuzz import fuzz
from backend.app.services.rule_engine import normalize_phone
import pandas as pd

def _norm(value) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    return re.sub(r"\s+", " ", str(value)).strip().lower()

def _name_block_key(name: str) -> str:
    tokens = _norm(name).split()
    if not tokens:
        return ""
    return "".join(sorted(t[:3] for t in tokens[:2]))

def build_blocks_new(records: dict[int, dict], roles: dict, dedup_config: dict | None = None) -> list[set[int]]:
    blocks: dict[str, set[int]] = {}
    def add(key: str, idx: int) -> None:
        if key:
            blocks.setdefault(key, set()).add(idx)

    if dedup_config and dedup_config.get("rules"):
        for idx, rec in records.items():
            for r in dedup_config["rules"]:
                col = r["column"]
                method = r["method"]
                val = rec.get(col)
                if not val:
                    continue
                if method == "exact" or method == "email":
                    add(f"{col}:{_norm(val)}", idx)
                elif method == "phone":
                    add(f"{col}:" + normalize_phone(val), idx)
                elif method in ("token_sort", "token_set", "fuzzy_ratio"):
                    add(f"{col}:" + _name_block_key(str(val)), idx)
        return [b for b in blocks.values() if 2 <= len(b)]
    else:
        # old logic
        pass

def pair_score_new(ra: dict, rb: dict, roles: dict, dedup_config: dict | None = None) -> tuple[float, dict]:
    total_w, acc = 0.0, 0.0
    parts: dict[str, float] = {}
    
    if dedup_config and dedup_config.get("rules"):
        for r in dedup_config["rules"]:
            col = r["column"]
            method = r["method"]
            weight = float(r.get("weight", 0)) / 100.0
            
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
                
            total_w += weight
            acc += weight * score
            parts[col] = round(score, 3)
            
        if total_w == 0:
            return 0.0, parts
        return acc / total_w, parts
    else:
        # old logic
        pass
