import pandas as pd

from app.services.entity_resolution import (
    build_blocks,
    calibrate_threshold,
    get_term_frequencies,
    indonesian_phonetic_key,
    normalize_address,
    normalize_email,
    normalize_identifier,
    normalize_name,
    normalize_date,
    pair_score,
    resolve_entities,
)


def test_type_specific_normalization_is_conservative_and_repeatable():
    assert normalize_name("Dr.  Budi Santóso") == "budi santoso"
    assert normalize_email(" BUDI@Gmial.com ") == "budi@gmail.com"
    assert normalize_address("Jl. Merdeka No. 10") == "jalan merdeka nomor 10"
    assert normalize_identifier("00-123.45") == "0012345"
    assert normalize_date("31/12/2025") == "2025-12-31"
    assert indonesian_phonetic_key("Muhammad") == indonesian_phonetic_key("Mohamad")


def test_derived_fuzzy_blocks_find_typo_candidates_without_exact_values():
    records = {
        0: {"name": "Siti Nuraini"},
        1: {"name": "Sitti Nuraini"},
        2: {"name": "Andi Wijaya"},
    }
    config = {
        "rules": [{
            "column": "name", "method": "jaro_winkler", "normalizers": ["name"],
        }],
    }

    blocks = build_blocks(records, {}, config)

    assert any({0, 1}.issubset(block) for block in blocks)
    assert not any({0, 2}.issubset(block) for block in blocks)


def test_rule_weight_and_negative_required_evidence_affect_probability():
    records = {
        0: {"name": "Budi Santoso", "birth_date": "1990-01-01", "nik": "001"},
        1: {"name": "Budi Santos", "birth_date": "1990-01-01", "nik": "999"},
        2: {"name": "Other", "birth_date": "1980-01-01", "nik": "777"},
    }
    base_rules = [
        {"column": "name", "method": "jaro_winkler", "normalizers": ["name"], "weight": 2},
        {"column": "birth_date", "method": "exact", "normalizers": ["date"], "weight": 2},
    ]
    base_config = {"prior_probability": 0.05, "rules": base_rules}
    frequencies = get_term_frequencies(records, base_config)
    positive_score, _ = pair_score(records[0], records[1], {}, base_config, frequencies)

    veto_config = {
        "prior_probability": 0.05,
        "rules": [*base_rules, {
            "column": "nik", "method": "exact", "normalizers": ["identifier"],
            "required": True,
        }],
    }
    veto_frequencies = get_term_frequencies(records, veto_config)
    veto_score, parts = pair_score(records[0], records[1], {}, veto_config, veto_frequencies)

    assert positive_score > 0.8
    assert veto_score == 0.0
    assert parts["nik"] == 0.0


def test_rare_sequential_values_do_not_get_an_artificial_term_frequency_boost():
    records = {
        index: {
            "name": f"Customer {index:05d}",
            "email": f"user{index:05d}@example.com",
        }
        for index in range(100)
    }
    config = {
        "prior_probability": 0.05,
        "rules": [
            {"column": "name", "method": "jaro_winkler", "weight": 2},
            {"column": "email", "method": "email", "weight": 2},
        ],
    }
    frequencies = get_term_frequencies(records, config)

    score, _ = pair_score(records[1], records[2], {}, config, frequencies)

    assert score < 0.8


def test_exact_row_fast_path_detects_duplicates_without_matching_rules():
    frame = pd.DataFrame([
        {"name": "Rina", "phone": "0812"},
        {"name": "Rina", "phone": "0812"},
        {"name": "Rina", "phone": "0899"},
    ])

    result = resolve_entities(frame, {"threshold": 0.8, "rules": [], "exact_row_match": True})

    assert len(result["clusters"]) == 1
    assert result["clusters"][0]["members"] == [0, 1]
    assert result["clusters"][0]["cohesion"] == 1.0


def test_exact_row_fast_path_works_without_recognized_role_columns():
    frame = pd.DataFrame([
        {"field_a": "same", "field_b": 10, "optional": None},
        {"field_a": "same", "field_b": 10, "optional": None},
        {"field_a": "same", "field_b": 10, "optional": None},
    ])
    config = {
        "threshold": 0.8,
        "rules": [],
        "exact_row_match": True,
        "cluster_validation": {
            "enabled": True, "method": "representative",
            "min_cohesion": 0.9, "min_representative_score": 0.9,
        },
    }

    result = resolve_entities(frame, config)

    assert result["clusters"][0]["members"] == [0, 1, 2]
    assert result["clusters"][0]["cohesion"] == 1.0


def test_legacy_threshold_and_rules_configuration_remains_effective():
    frame = pd.DataFrame([
        {"nama": "Budi Santoso", "email": "budi@example.com"},
        {"nama": "Budi Santos", "email": "budi@example.com"},
        {"nama": "Siti Nuraini", "email": "siti@example.com"},
    ])
    legacy_config = {
        "threshold": 0.8,
        "rules": [
            {"column": "nama", "method": "token_sort"},
            {"column": "email", "method": "email"},
        ],
    }

    result = resolve_entities(frame, legacy_config)

    assert result["clusters"][0]["members"] == [0, 1]
    assert result["clusters"][0]["cohesion"] >= 0.8


def test_representative_validation_prevents_weak_transitive_chaining():
    frame = pd.DataFrame({"name": ["abcd", "abce", "abde"]})
    config = {
        "threshold": 0.7,
        "prior_probability": 0.2,
        "exact_row_match": False,
        "blocking_rules": [{"column": "name", "method": "prefix", "length": 2}],
        "rules": [{
            "column": "name", "method": "jaro_winkler", "weight": 1,
            "normalizers": ["name"],
        }],
        "cluster_validation": {
            "enabled": True,
            "method": "representative",
            "min_representative_score": 0.78,
            "min_cohesion": 0.78,
        },
    }

    result = resolve_entities(frame, config)

    assert all(cluster["cohesion"] >= 0.78 for cluster in result["clusters"])
    assert all(len(cluster["members"]) < 3 for cluster in result["clusters"])


def test_large_transitive_component_uses_bounded_cluster_validation():
    frame = pd.DataFrame([
        {
            "match_name": "same entity",
            "block_a": "group-a" if index < 60 else f"a-{index}",
            "block_b": "group-b" if index >= 40 else f"b-{index}",
        }
        for index in range(100)
    ])
    config = {
        "threshold": 0.4,
        "exact_row_match": False,
        "rules": [{"column": "match_name", "method": "exact", "weight": 2}],
        "blocking_rules": [
            {"column": "block_a", "method": "exact"},
            {"column": "block_b", "method": "exact"},
        ],
        "cluster_validation": {
            "enabled": True,
            "method": "representative",
            "min_representative_score": 0.4,
            "min_cohesion": 0.4,
        },
    }

    result = resolve_entities(frame, config)

    assert result["clusters"]
    assert all(len(cluster["members"]) <= 20 for cluster in result["clusters"])
    assert all(cluster["cohesion"] >= 0.4 for cluster in result["clusters"])


def test_threshold_calibration_uses_both_human_review_classes():
    insufficient = calibrate_threshold([(0.9, True), (0.8, True)])
    calibrated = calibrate_threshold([
        (0.95, True), (0.86, True), (0.82, True),
        (0.72, False), (0.55, False), (0.30, False),
    ])

    assert insufficient["available"] is False
    assert calibrated == {
        "available": True,
        "positive_pairs": 3,
        "negative_pairs": 3,
        "recommended_threshold": 0.82,
        "balanced_accuracy": 1.0,
        "sensitivity": 1.0,
        "specificity": 1.0,
    }
