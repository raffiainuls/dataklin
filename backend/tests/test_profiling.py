import re

import pandas as pd

from app.services.profiling import profile_dataframe


def _by_name(profiles: list[dict], name: str) -> dict:
    return next(profile for profile in profiles if profile["name"] == name)


def test_profile_covers_structure_content_and_key_discovery():
    frame = pd.DataFrame({
        "id": [1, 2, 3, 4],
        "amount": [10, 20, 30, 100],
        "phone": ["0812-1111", "0813-2222", "021 3333", "   "],
        "status": ["active", "active", "inactive", None],
    })

    profiles = profile_dataframe(frame)
    identifier = _by_name(profiles, "id")
    amount = _by_name(profiles, "amount")
    phone = _by_name(profiles, "phone")
    status = _by_name(profiles, "status")

    assert identifier["stats"]["is_candidate_key"] is True
    assert identifier["inferred_type"] == "numeric"
    assert {key: amount["stats"][key] for key in ("min", "max", "mean", "median")} == {
        "min": 10.0, "max": 100.0, "mean": 40.0, "median": 25.0,
    }
    assert amount["stats"]["q1"] == 17.5
    assert amount["stats"]["q3"] == 47.5

    assert phone["completeness"] == 0.75
    assert phone["null_count"] == 1
    assert phone["stats"]["null_count"] == 0
    assert phone["stats"]["blank_count"] == 1
    assert phone["stats"]["length"] == {
        "min": 8, "max": 9, "mean": 8.67, "median": 9.0,
    }
    assert sum(item["count"] for item in phone["stats"]["patterns"]) == 3
    assert all(re.fullmatch(item["regex"], item["example"])
               for item in phone["stats"]["patterns"])

    assert status["top_values"][0] == {
        "value": "active", "count": 2, "percentage": 0.6667,
    }
    assert status["stats"]["duplicate_count"] == 1


def test_empty_and_boolean_columns_have_json_safe_profiles():
    frame = pd.DataFrame({
        "empty": [None, "", "  "],
        "flag": ["yes", "no", "yes"],
        "single_number": [5, None, None],
    })

    profiles = profile_dataframe(frame)
    empty = _by_name(profiles, "empty")
    flag = _by_name(profiles, "flag")
    number = _by_name(profiles, "single_number")

    assert empty["completeness"] == 0.0
    assert empty["uniqueness"] is None
    assert empty["top_values"] == []
    assert empty["stats"]["length"] == {
        "min": None, "max": None, "mean": None, "median": None,
    }
    assert flag["inferred_type"] == "boolean"
    assert number["stats"]["std"] == 0.0
