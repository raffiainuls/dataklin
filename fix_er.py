import re

with open("backend/app/services/entity_resolution.py", "r") as f:
    content = f.read()

# Replace build_blocks
old_build_blocks = """def build_blocks(records: dict[int, dict], roles: dict) -> list[set[int]]:
    blocks: dict[str, set[int]] = {}

    def add(key: str, idx: int) -> None:
        if key:
            blocks.setdefault(key, set()).add(idx)

    for idx, rec in records.items():
        if roles.get("phone"):
            add("p:" + normalize_phone(rec.get(roles["phone"])), idx)
        if roles.get("email"):
            add("e:" + _norm(rec.get(roles["email"])), idx)
        if roles.get("name"):
            add("n:" + _name_block_key(rec.get(roles["name"], "")), idx)
    return [b for b in blocks.values() if 2 <= len(b) <= settings.er_max_block_size]"""

new_build_blocks = """def build_blocks(records: dict[int, dict], roles: dict, dedup_config: dict | None = None) -> list[set[int]]:
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
                
    return [b for b in blocks.values() if 2 <= len(b) <= settings.er_max_block_size]"""

# Replace pair_score
old_pair_score = """def pair_score(ra: dict, rb: dict, roles: dict) -> tuple[float, dict]:
    total_w, acc = 0.0, 0.0
    parts: dict[str, float] = {}
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
    if total_w < 0.4:  # sinyal terlalu sedikit untuk diputuskan
        return 0.0, parts
    return acc / total_w, parts"""

new_pair_score = """def pair_score(ra: dict, rb: dict, roles: dict, dedup_config: dict | None = None) -> tuple[float, dict]:
    total_w, acc = 0.0, 0.0
    parts: dict[str, float] = {}
    
    if dedup_config and dedup_config.get("rules"):
        for r in dedup_config["rules"]:
            col = r.get("column")
            method = r.get("method")
            weight = float(r.get("weight", 0)) / 100.0
            
            va, vb = ra.get(col), rb.get(col)
            if not va or not vb:
                continue
            
            if method == "exact":
                na, nb = _norm(va), _norm(vb)
                score = 1.0 if na and nb and na == nb else 0.0
            elif method == "phone":
                na, nb = normalize_phone(va), normalize_phone(vb)
                if not na or not nb:
                    continue
                score = 1.0 if na == nb else 0.0
            elif method == "email":
                na, nb = _norm(va), _norm(vb)
                if not na or not nb:
                    continue
                score = 1.0 if na == nb else (fuzz.ratio(na, nb) / 100) * 0.5
            elif method == "token_sort":
                na, nb = _norm(va), _norm(vb)
                if not na or not nb:
                    continue
                score = fuzz.token_sort_ratio(na, nb) / 100
            elif method == "token_set":
                na, nb = _norm(va), _norm(vb)
                if not na or not nb:
                    continue
                score = fuzz.token_set_ratio(na, nb) / 100
            elif method == "fuzzy_ratio":
                na, nb = _norm(va), _norm(vb)
                if not na or not nb:
                    continue
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
        return acc / total_w, parts"""

# Replace resolve_entities
old_resolve = """def resolve_entities(df: pd.DataFrame) -> dict:
    \"\"\"Kembalikan {roles, clusters:[{members:[idx], cohesion, pairs:[(a,b,score,parts)]}]}.\"\"\"
    roles = detect_roles([str(c) for c in df.columns])
    if not roles.get("name") and not roles.get("phone") and not roles.get("email"):
        return {"roles": roles, "clusters": []}

    subset = df.head(settings.er_max_rows)
    records = {int(idx): row for idx, row in subset.astype(object).iterrows()}
    records = {idx: {str(k): v for k, v in dict(row).items()} for idx, row in records.items()}

    scored: dict[tuple[int, int], tuple[float, dict]] = {}
    uf = UnionFind()
    pair_budget = settings.er_max_pairs

    for block in build_blocks(records, roles):
        for a, b in combinations(sorted(block), 2):
            key = (a, b)
            if key in scored:
                continue
            if pair_budget <= 0:
                break
            pair_budget -= 1
            score, parts = pair_score(records[a], records[b], roles)
            scored[key] = (score, parts)
            if score >= settings.er_pair_threshold:
                uf.union(a, b)"""

new_resolve = """def resolve_entities(df: pd.DataFrame, dedup_config: dict | None = None) -> dict:
    \"\"\"Kembalikan {roles, clusters:[{members:[idx], cohesion, pairs:[(a,b,score,parts)]}]}.\"\"\"
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

    for block in build_blocks(records, roles, dedup_config):
        for a, b in combinations(sorted(block), 2):
            key = (a, b)
            if key in scored:
                continue
            if pair_budget <= 0:
                break
            pair_budget -= 1
            score, parts = pair_score(records[a], records[b], roles, dedup_config)
            scored[key] = (score, parts)
            if score >= threshold:
                uf.union(a, b)"""

content = content.replace(old_build_blocks, new_build_blocks)
content = content.replace(old_pair_score, new_pair_score)
content = content.replace(old_resolve, new_resolve)

with open("backend/app/services/entity_resolution.py", "w") as f:
    f.write(content)
