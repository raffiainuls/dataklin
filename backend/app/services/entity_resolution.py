"""Configurable entity resolution: normalization, blocking, scoring, and clustering."""
from __future__ import annotations

import math
import re
import unicodedata
from collections import defaultdict
from itertools import combinations
from typing import Callable

import pandas as pd
from rapidfuzz import fuzz
from rapidfuzz.distance import JaroWinkler

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

DEFAULT_WEIGHTS = {"phone": 0.35, "email": 0.25, "name": 0.25, "address": 0.15}
DEFAULT_PRIOR_PROBABILITY = 0.05
DEFAULT_MATCH_PROBABILITY = 0.95
MAX_CLUSTER_MEMBERS = 20

TITLE_WORDS = {
    "bapak", "bp", "ibu", "bu", "mr", "mrs", "ms", "dr", "drs", "dra",
    "h", "hj", "ir", "prof", "sdr", "sdri",
}
EMAIL_DOMAIN_CORRECTIONS = {
    "gmail.co": "gmail.com",
    "gmail.con": "gmail.com",
    "gmial.com": "gmail.com",
    "gmai.com": "gmail.com",
    "hotmial.com": "hotmail.com",
    "yaho.com": "yahoo.com",
    "yahoo.co": "yahoo.com",
}
ADDRESS_REPLACEMENTS = {
    "jl": "jalan",
    "jln": "jalan",
    "gg": "gang",
    "kec": "kecamatan",
    "kel": "kelurahan",
    "kab": "kabupaten",
    "no": "nomor",
}


def detect_roles(columns: list[str]) -> dict[str, str]:
    roles: dict[str, str] = {}
    for role, hints in ROLE_HINTS.items():
        for column in columns:
            if any(hint in str(column).lower() for hint in hints):
                roles[role] = str(column)
                break
    return roles


def _is_missing(value: object) -> bool:
    if value is None:
        return True
    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False


def _ascii(value: object) -> str:
    if _is_missing(value):
        return ""
    return unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode()


def _norm(value: object) -> str:
    return re.sub(r"\s+", " ", _ascii(value)).strip().lower()


def normalize_name(value: object) -> str:
    tokens = re.findall(r"[a-z0-9]+", _norm(value))
    while tokens and tokens[0] in TITLE_WORDS:
        tokens.pop(0)
    return " ".join(tokens)


def normalize_email(value: object) -> str:
    email = re.sub(r"\s+", "", _norm(value))
    if email.count("@") != 1:
        return email
    local, domain = email.split("@", 1)
    return f"{local}@{EMAIL_DOMAIN_CORRECTIONS.get(domain, domain)}"


def normalize_address(value: object) -> str:
    tokens = re.findall(r"[a-z0-9]+", _norm(value))
    return " ".join(ADDRESS_REPLACEMENTS.get(token, token) for token in tokens)


def normalize_identifier(value: object) -> str:
    return re.sub(r"[^a-z0-9]", "", _norm(value))


def normalize_date(value: object) -> str:
    if _is_missing(value) or not str(value).strip():
        return ""
    try:
        parsed = pd.to_datetime(str(value), errors="coerce", dayfirst=True)
    except (TypeError, ValueError):
        return _norm(value)
    return str(parsed.date()) if pd.notna(parsed) else _norm(value)


NORMALIZERS: dict[str, Callable[[object], str]] = {
    "basic": _norm,
    "name": normalize_name,
    "phone": lambda value: normalize_phone(value) or "",
    "email": normalize_email,
    "address": normalize_address,
    "identifier": normalize_identifier,
    "date": normalize_date,
}


def normalize_for_rule(value: object, rule: dict) -> str:
    normalizers = rule.get("normalizers") or []
    if not normalizers:
        method = rule.get("method")
        if method == "phone":
            normalizers = ["phone"]
        elif method == "email":
            normalizers = ["email"]
        else:
            normalizers = ["basic"]
    normalized: object = value
    for name in normalizers:
        normalizer = NORMALIZERS.get(name)
        if normalizer:
            normalized = normalizer(normalized)
    return str(normalized)


def indonesian_phonetic_key(value: object) -> str:
    """Conservative Indonesian-oriented phonetic key for names and organizations."""
    text = normalize_name(value)
    replacements = (
        ("oe", "u"), ("dj", "j"), ("tj", "c"), ("nj", "ny"),
        ("sj", "sy"), ("ch", "h"), ("ph", "f"), ("th", "t"),
        ("kh", "h"), ("q", "k"), ("v", "f"), ("x", "ks"), ("z", "s"),
    )
    for source, target in replacements:
        text = text.replace(source, target)
    encoded = []
    for token in text.split():
        if not token:
            continue
        first = token[0]
        tail = re.sub(r"[aiueoy]", "", token[1:])
        encoded.append(re.sub(r"(.)\1+", r"\1", first + tail))
    return " ".join(encoded)


def _rule_columns(rule: dict) -> list[str]:
    columns = rule.get("columns") or []
    if columns:
        return [str(column) for column in columns]
    column = rule.get("column")
    return [str(column)] if column else []


def _rule_key(rule: dict) -> str:
    return "+".join(_rule_columns(rule)) or "unknown"


def _values_for_rule(record: dict, rule: dict) -> tuple[str, ...]:
    return tuple(normalize_for_rule(record.get(column), rule) for column in _rule_columns(rule))


def _method_score(ra: dict, rb: dict, rule: dict) -> float | None:
    values_a = _values_for_rule(ra, rule)
    values_b = _values_for_rule(rb, rule)
    if not values_a or any(not value for value in values_a + values_b):
        return None
    method = rule.get("method", "exact")
    if method == "composite_exact":
        return 1.0 if values_a == values_b else 0.0

    value_a, value_b = values_a[0], values_b[0]
    if method in ("exact", "phone"):
        return 1.0 if value_a == value_b else 0.0
    if method == "email":
        return 1.0 if value_a == value_b else (fuzz.ratio(value_a, value_b) / 100) * 0.5
    if method == "token_sort":
        return fuzz.token_sort_ratio(value_a, value_b) / 100
    if method == "token_set":
        return fuzz.token_set_ratio(value_a, value_b) / 100
    if method == "fuzzy_ratio":
        return fuzz.ratio(value_a, value_b) / 100
    if method == "jaro_winkler":
        return float(JaroWinkler.normalized_similarity(value_a, value_b))
    if method == "phonetic":
        key_a, key_b = indonesian_phonetic_key(value_a), indonesian_phonetic_key(value_b)
        if not key_a or not key_b:
            return None
        return float(JaroWinkler.normalized_similarity(key_a, key_b))
    return 0.0


def get_term_frequencies(records: dict[int, dict], dedup_config: dict) -> dict[str, dict]:
    frequencies: dict[str, dict] = {}
    for rule in dedup_config.get("rules", []):
        key = _rule_key(rule)
        values = [_values_for_rule(record, rule) for record in records.values()]
        present = [value for value in values if value and all(value)]
        if not present:
            frequencies[key] = {}
            continue
        counts: dict[tuple[str, ...], int] = defaultdict(int)
        for value in present:
            counts[value] += 1
        frequencies[key] = {value: count / len(present) for value, count in counts.items()}
    return frequencies


def _probabilistic_score(ra: dict, rb: dict, config: dict,
                         frequencies: dict[str, dict] | None) -> tuple[float, dict]:
    prior = float(config.get("prior_probability", DEFAULT_PRIOR_PROBABILITY))
    odds = prior / (1 - prior)
    parts: dict[str, float] = {}
    evidence_count = 0
    vetoed = False

    for position, rule in enumerate(config.get("rules", [])):
        score = _method_score(ra, rb, rule)
        if score is None:
            continue
        evidence_count += 1
        key = _rule_key(rule)
        part_key = key if key not in parts else f"{key}#{position + 1}"
        parts[part_key] = round(score, 4)

        required_threshold = float(rule.get("required_threshold", 0.999))
        if rule.get("required") and score < required_threshold:
            vetoed = True

        normalized_a = _values_for_rule(ra, rule)
        normalized_b = _values_for_rule(rb, rule)
        rule_frequencies = frequencies.get(key, {}) if frequencies else {}
        u_probability = max(
            rule_frequencies.get(normalized_a, 0.01),
            rule_frequencies.get(normalized_b, 0.01),
            0.0001,
        )
        # Small datasets make duplicates look artificially common. Cap u while still
        # allowing rare values to contribute stronger evidence than common values.
        u_probability = min(u_probability, float(rule.get("max_u_probability", 0.25)))
        if normalized_a != normalized_b:
            # Exact-value frequency is not a valid estimate for fuzzy agreement.
            # Without this floor, two unique-but-similar sequential IDs can receive
            # enormous evidence simply because each exact string is rare.
            u_probability = max(
                u_probability, float(rule.get("fuzzy_u_probability", 0.25)))
        m_probability = float(rule.get("m_probability", DEFAULT_MATCH_PROBABILITY))
        match_bf = m_probability / u_probability
        non_match_bf = (1 - m_probability) / max(1 - u_probability, 0.0001)
        # Smooth similarity in log space so fuzzy evidence is calibrated, not averaged.
        log_bf = math.log(match_bf) * score + math.log(non_match_bf) * (1 - score)
        # Two is the compatibility/calibration default: two strong independent
        # signals should normally clear an 0.8 decision threshold.
        weight = max(float(rule.get("weight", 2.0)), 0.0)
        odds *= math.exp(log_bf * weight)

        mismatch_threshold = float(rule.get("mismatch_threshold", 0.2))
        penalty = float(rule.get("mismatch_penalty", 0.0))
        if score <= mismatch_threshold and penalty > 0:
            odds *= max(1 - penalty, 0.001)

    if not evidence_count or vetoed:
        return 0.0, parts
    probability = odds / (1 + odds)
    return max(0.0, min(probability, 1.0)), parts


def _default_rules(roles: dict[str, str]) -> list[dict]:
    methods = {"phone": "phone", "email": "email", "name": "token_sort", "address": "token_set"}
    normalizers = {"phone": ["phone"], "email": ["email"], "name": ["name"], "address": ["address"]}
    return [
        {
            "column": column,
            "method": methods[role],
            "normalizers": normalizers[role],
            "weight": DEFAULT_WEIGHTS[role] * 4,
        }
        for role, column in roles.items() if role in methods
    ]


def pair_score(ra: dict, rb: dict, roles: dict, dedup_config: dict | None = None,
               u_probs: dict | None = None) -> tuple[float, dict]:
    """Return calibrated match probability and per-rule similarities."""
    if dedup_config and dedup_config.get("rules"):
        return _probabilistic_score(ra, rb, dedup_config, u_probs)

    # Preserve the intuitive weighted-score fallback for auto-detected legacy mode.
    total_weight = 0.0
    accumulated = 0.0
    parts: dict[str, float] = {}
    for rule in _default_rules(roles):
        score = _method_score(ra, rb, rule)
        if score is None:
            continue
        role = next(key for key, column in roles.items() if column == rule["column"])
        weight = DEFAULT_WEIGHTS[role]
        total_weight += weight
        accumulated += weight * score
        parts[role] = round(score, 4)
    if total_weight < 0.4:
        return 0.0, parts
    return accumulated / total_weight, parts


def _name_block_key(value: object) -> str:
    tokens = normalize_name(value).split()
    return "".join(sorted(token[:3] for token in tokens[:2])) if tokens else ""


def _ngrams(value: str, size: int) -> list[str]:
    compact = re.sub(r"\s+", "", value)
    if len(compact) <= size:
        return [compact] if compact else []
    return sorted({compact[index:index + size] for index in range(len(compact) - size + 1)})[:8]


def _derived_blocking_rules(matching_rules: list[dict]) -> list[dict]:
    blocking: list[dict] = []
    for rule in matching_rules:
        method = rule.get("method")
        base = {"column": rule.get("column"), "columns": rule.get("columns", []),
                "normalizers": rule.get("normalizers", [])}
        if method in ("exact", "composite_exact"):
            blocking.append({**base, "method": "composite_exact" if len(_rule_columns(rule)) > 1 else "exact"})
        elif method == "phone":
            blocking.append({**base, "method": "phone_suffix", "length": 7})
        elif method == "email":
            blocking.extend([
                {**base, "method": "email_local", "length": 4},
                {**base, "method": "ngram", "length": 3},
            ])
        elif method in ("token_sort", "token_set", "fuzzy_ratio", "jaro_winkler", "phonetic"):
            blocking.extend([
                {**base, "method": "phonetic"},
                {**base, "method": "prefix", "length": 3},
                {**base, "method": "ngram", "length": 3},
            ])
    return blocking


def _block_keys(record: dict, rule: dict) -> list[str]:
    columns = _rule_columns(rule)
    if not columns:
        return []
    values = _values_for_rule(record, rule)
    if any(not value for value in values):
        return []
    method = rule.get("method", "exact")
    namespace = "+".join(columns)
    if method in ("exact", "composite_exact"):
        return [f"{namespace}:exact:{'|'.join(values)}"]

    value = values[0]
    length = max(int(rule.get("length", 3)), 1)
    if method == "prefix":
        compact = re.sub(r"\s+", "", value)
        return [f"{namespace}:prefix:{compact[:length]}"] if compact else []
    if method == "token_prefix":
        key = _name_block_key(value)
        return [f"{namespace}:token:{key}"] if key else []
    if method == "phonetic":
        key = indonesian_phonetic_key(value)
        return [f"{namespace}:phonetic:{key}"] if key else []
    if method == "ngram":
        return [f"{namespace}:ngram:{gram}" for gram in _ngrams(value, length)]
    if method == "email_local":
        local = value.split("@", 1)[0]
        return [f"{namespace}:email-local:{local[:length]}"] if local else []
    if method == "phone_suffix":
        digits = re.sub(r"\D", "", value)
        return [f"{namespace}:phone-suffix:{digits[-length:]}"] if digits else []
    return []


def build_blocks(records: dict[int, dict], roles: dict,
                 dedup_config: dict | None = None) -> list[set[int]]:
    blocks: dict[str, set[int]] = defaultdict(set)
    if dedup_config and dedup_config.get("rules"):
        rules = dedup_config.get("blocking_rules") or _derived_blocking_rules(dedup_config["rules"])
    else:
        rules = _derived_blocking_rules(_default_rules(roles))
    for index, record in records.items():
        for rule in rules:
            for key in _block_keys(record, rule):
                blocks[key].add(index)
    unique_blocks = {
        frozenset(block) for block in blocks.values()
        if 2 <= len(block) <= settings.er_max_block_size
    }
    return [set(block) for block in unique_blocks]


class UnionFind:
    def __init__(self) -> None:
        self.parent: dict[int, int] = {}

    def find(self, value: int) -> int:
        self.parent.setdefault(value, value)
        while self.parent[value] != value:
            self.parent[value] = self.parent[self.parent[value]]
            value = self.parent[value]
        return value

    def union(self, left: int, right: int) -> None:
        root_left, root_right = self.find(left), self.find(right)
        if root_left != root_right:
            self.parent[root_right] = root_left


def _exact_groups(records: dict[int, dict], config: dict | None) -> list[set[int]]:
    rules = list((config or {}).get("exact_match_rules") or [])
    if (config or {}).get("exact_row_match", True):
        all_columns = sorted({column for record in records.values() for column in record})
        rules.append({
            "columns": all_columns,
            "normalizers": ["basic"],
            "_allow_missing": True,
        })
    groups: list[set[int]] = []
    for rule in rules:
        buckets: dict[tuple[str, ...], set[int]] = defaultdict(set)
        for index, record in records.items():
            values = _values_for_rule(record, rule)
            if values and (all(values) or (rule.get("_allow_missing") and any(values))):
                buckets[values].add(index)
        groups.extend(group for group in buckets.values()
                      if 2 <= len(group) <= settings.er_max_block_size)
    return groups


def _all_pair_scores(members: list[int], records: dict[int, dict], roles: dict,
                     config: dict | None, frequencies: dict | None,
                     scored: dict[tuple[int, int], tuple[float, dict]]) -> list[dict]:
    pairs = []
    for left, right in combinations(sorted(members), 2):
        key = (left, right)
        if key not in scored:
            scored[key] = pair_score(records[left], records[right], roles, config, frequencies)
        score, parts = scored[key]
        pairs.append({"a": left, "b": right, "score": round(score, 4), "parts": parts})
    return pairs


def _representative_clusters(members: list[int], records: dict[int, dict], roles: dict,
                             config: dict, frequencies: dict | None,
                             scored: dict[tuple[int, int], tuple[float, dict]]) -> list[list[int]]:
    validation = config.get("cluster_validation") or {}
    if not validation.get("enabled", False) or validation.get("method") == "connected":
        return [members]
    minimum = float(validation.get("min_representative_score", config.get("threshold", 0.8)))
    minimum_cohesion = float(validation.get("min_cohesion", 0.7))
    remaining = set(members)
    validated: list[list[int]] = []
    while len(remaining) >= 2:
        averages: dict[int, float] = {}
        for candidate in remaining:
            candidate_scores = []
            for other in remaining - {candidate}:
                key = tuple(sorted((candidate, other)))
                if key not in scored:
                    scored[key] = pair_score(
                        records[key[0]], records[key[1]], roles, config, frequencies)
                candidate_scores.append(scored[key][0])
            averages[candidate] = sum(candidate_scores) / len(candidate_scores)
        representative = max(averages, key=averages.get)
        group = [representative]
        for candidate in sorted(remaining - {representative}):
            key = tuple(sorted((representative, candidate)))
            if scored[key][0] >= minimum:
                group.append(candidate)
        if len(group) < 2:
            remaining.remove(representative)
            continue
        pairs = _all_pair_scores(group, records, roles, config, frequencies, scored)
        cohesion = sum(pair["score"] for pair in pairs) / len(pairs)
        if cohesion >= minimum_cohesion:
            validated.append(group)
            remaining.difference_update(group)
        else:
            # Remove the weakest member and try the remaining candidates again.
            weakest = min(group, key=lambda member: averages.get(member, 0.0))
            remaining.remove(weakest)
    return validated


def _bounded_graph_clusters(members: list[int], records: dict[int, dict], roles: dict,
                            config: dict, frequencies: dict | None,
                            scored: dict[tuple[int, int], tuple[float, dict]]) -> list[list[int]]:
    """Linear-in-scored-edges fallback for unusually large transitive components."""
    validation = config.get("cluster_validation") or {}
    minimum = float(validation.get("min_representative_score", config.get("threshold", 0.8)))
    minimum_cohesion = float(validation.get("min_cohesion", 0.7))
    member_set = set(members)
    adjacency: dict[int, dict[int, float]] = defaultdict(dict)
    for (left, right), (score, _) in scored.items():
        if left in member_set and right in member_set and score >= minimum:
            adjacency[left][right] = score
            adjacency[right][left] = score

    remaining = set(members)
    validated: list[list[int]] = []
    while len(remaining) >= 2:
        representative = max(
            remaining,
            key=lambda item: sum(neighbor in remaining for neighbor in adjacency.get(item, {})),
        )
        neighbors = sorted(
            (neighbor for neighbor in adjacency.get(representative, {}) if neighbor in remaining),
            key=lambda neighbor: adjacency[representative][neighbor],
            reverse=True,
        )
        group = [representative, *neighbors[:MAX_CLUSTER_MEMBERS - 1]]
        if len(group) < 2:
            remaining.remove(representative)
            continue
        pairs = _all_pair_scores(group, records, roles, config, frequencies, scored)
        cohesion = sum(pair["score"] for pair in pairs) / len(pairs)
        if cohesion >= minimum_cohesion:
            validated.append(group)
            remaining.difference_update(group)
        else:
            remaining.remove(representative)
    return validated


def resolve_entities(df: pd.DataFrame, dedup_config: dict | None = None) -> dict:
    """Resolve dataframe rows into reviewable clusters with auditable pair scores."""
    roles = detect_roles([str(column) for column in df.columns])
    if not dedup_config or not dedup_config.get("rules"):
        deterministic_enabled = bool(
            dedup_config is None
            or dedup_config.get("exact_row_match", True)
            or dedup_config.get("exact_match_rules")
        )
        if (not deterministic_enabled
                and not any(roles.get(role) for role in ("name", "phone", "email"))):
            return {"roles": roles, "clusters": []}

    threshold = float((dedup_config or {}).get("threshold", settings.er_pair_threshold))
    subset = df.head(settings.er_max_rows)
    records = {
        position: {str(column): value for column, value in row.items()}
        for position, (_, row) in enumerate(subset.astype(object).iterrows())
    }
    frequencies = get_term_frequencies(records, dedup_config) if dedup_config else None
    scored: dict[tuple[int, int], tuple[float, dict]] = {}
    union_find = UnionFind()

    # Deterministic fast path for complete row duplicates and explicit identity keys.
    for group in _exact_groups(records, dedup_config):
        anchor = min(group)
        for left, right in combinations(sorted(group), 2):
            key = (left, right)
            scored[key] = (1.0, {"exact_fast_path": 1.0})
            union_find.union(anchor, right)

    pair_budget = settings.er_max_pairs
    for block in build_blocks(records, roles, dedup_config):
        for left, right in combinations(sorted(block), 2):
            key = (left, right)
            if key in scored:
                continue
            if pair_budget <= 0:
                break
            pair_budget -= 1
            scored[key] = pair_score(records[left], records[right], roles,
                                     dedup_config, frequencies)
            if scored[key][0] >= threshold:
                union_find.union(left, right)

    connected: dict[int, list[int]] = defaultdict(list)
    for index in union_find.parent:
        connected[union_find.find(index)].append(index)

    clusters = []
    for component in connected.values():
        if len(component) < 2:
            continue
        if dedup_config:
            validation_limit = max(settings.er_max_block_size, MAX_CLUSTER_MEMBERS)
            if len(component) > validation_limit:
                validated_groups = _bounded_graph_clusters(
                    component, records, roles, dedup_config, frequencies, scored)
            else:
                validated_groups = _representative_clusters(
                    component, records, roles, dedup_config, frequencies, scored)
        else:
            validated_groups = [component]
        for members in validated_groups:
            members = sorted(members)[:MAX_CLUSTER_MEMBERS]
            pairs = _all_pair_scores(members, records, roles, dedup_config,
                                     frequencies, scored)
            cohesion = sum(pair["score"] for pair in pairs) / len(pairs) if pairs else 0.0
            clusters.append({
                "members": members,
                "cohesion": round(cohesion, 4),
                "pairs": pairs,
                "records": {member: records[member] for member in members},
            })
    clusters.sort(key=lambda cluster: -cluster["cohesion"])
    return {"roles": roles, "clusters": clusters}


def calibrate_threshold(labeled_scores: list[tuple[float, bool]]) -> dict:
    """Recommend a threshold maximizing balanced accuracy on human-reviewed pairs."""
    positives = [score for score, is_match in labeled_scores if is_match]
    negatives = [score for score, is_match in labeled_scores if not is_match]
    if not positives or not negatives:
        return {
            "available": False,
            "reason": "Kalibrasi membutuhkan review confirmed dan split.",
            "positive_pairs": len(positives),
            "negative_pairs": len(negatives),
        }

    candidates = sorted({0.1, 1.0, *[round(score, 4) for score, _ in labeled_scores]})
    best: dict | None = None
    for threshold in candidates:
        true_positive = sum(score >= threshold for score in positives)
        true_negative = sum(score < threshold for score in negatives)
        sensitivity = true_positive / len(positives)
        specificity = true_negative / len(negatives)
        balanced_accuracy = (sensitivity + specificity) / 2
        candidate = {
            "recommended_threshold": round(threshold, 4),
            "balanced_accuracy": round(balanced_accuracy, 4),
            "sensitivity": round(sensitivity, 4),
            "specificity": round(specificity, 4),
        }
        if best is None or (
            candidate["balanced_accuracy"], candidate["specificity"], threshold
        ) > (
            best["balanced_accuracy"], best["specificity"], best["recommended_threshold"]
        ):
            best = candidate
    return {
        "available": True,
        "positive_pairs": len(positives),
        "negative_pairs": len(negatives),
        **(best or {}),
    }


def json_safe_record(record: dict) -> dict:
    output = {}
    for key, value in record.items():
        if _is_missing(value):
            output[key] = None
        elif isinstance(value, float):
            output[key] = int(value) if value.is_integer() else value
        elif isinstance(value, (int, str, bool)):
            output[key] = value
        else:
            output[key] = str(value)
    return output
