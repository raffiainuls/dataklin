import re

with open("backend/app/services/entity_resolution.py", "r") as f:
    content = f.read()

# Add get_term_frequencies function
new_funcs = """
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
"""

# Replace pair_score to accept u_probs
old_pair_score = """def pair_score(ra: dict, rb: dict, roles: dict, dedup_config: dict | None = None) -> tuple[float, dict]:
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
        return acc / total_w, parts"""

new_pair_score = """def pair_score(ra: dict, rb: dict, roles: dict, dedup_config: dict | None = None, u_probs: dict = None) -> tuple[float, dict]:
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
        return final_prob, parts"""

# We also need to fix resolve_entities to call get_term_frequencies and pass u_probs
old_resolve = """    scored: dict[tuple[int, int], tuple[float, dict]] = {}
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
            score, parts = pair_score(records[a], records[b], roles, dedup_config)"""

new_resolve = """    scored: dict[tuple[int, int], tuple[float, dict]] = {}
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
            score, parts = pair_score(records[a], records[b], roles, dedup_config, u_probs)"""

content = content.replace(old_pair_score, new_pair_score)
content = content.replace(old_resolve, new_resolve)

# insert get_term_frequencies before pair_score
content = content.replace('def pair_score', new_funcs + '\ndef pair_score')

with open("backend/app/services/entity_resolution.py", "w") as f:
    f.write(content)
