import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from types import SimpleNamespace

from app.routers import rules as rules_router
from app.routers.rules import DedupConfigUpdate


def test_dedup_v2_config_accepts_advanced_algorithms():
    config = DedupConfigUpdate.model_validate({
        "threshold": 0.82,
        "rules": [{
            "columns": ["first_name", "last_name"],
            "method": "composite_exact",
            "weight": 2,
        }],
        "blocking_rules": [{
            "column": "first_name", "method": "ngram", "length": 3,
        }],
        "exact_match_rules": [{
            "columns": ["customer_id"], "normalizers": ["identifier"],
        }],
    })

    assert config.version == 2
    assert config.cluster_validation.method == "representative"


@pytest.mark.parametrize("payload", [
    {"rules": [{"column": "name", "method": "unknown"}]},
    {"rules": [{"column": "name", "method": "composite_exact"}]},
    {"blocking_rules": [{
        "column": "name", "method": "ngram", "normalizers": ["unknown"],
    }]},
    {"exact_match_rules": [{"columns": ["id"], "normalizers": ["unknown"]}]},
])
def test_dedup_v2_config_rejects_unsafe_or_unknown_options(payload):
    with pytest.raises(ValidationError):
        DedupConfigUpdate.model_validate(payload)


class _FakeDb:
    def __init__(self, dataset):
        self.dataset = dataset
        self.commits = 0

    def get(self, _model, _identifier):
        return self.dataset

    def commit(self):
        self.commits += 1


def test_update_rejects_unknown_columns_before_saving(monkeypatch):
    dataset = SimpleNamespace(id=7, org_id=1, dedup_config=None)
    db = _FakeDb(dataset)
    user = SimpleNamespace(org_id=1)
    body = DedupConfigUpdate.model_validate({
        "rules": [{"column": "unknown", "method": "exact"}],
    })
    monkeypatch.setattr(rules_router, "_column_info", lambda _db, _id: [SimpleNamespace(name="name")])

    with pytest.raises(HTTPException) as error:
        rules_router.update_dedup_config(7, body, db, user)

    assert error.value.status_code == 400
    assert db.commits == 0


def test_update_rolls_back_config_when_recalculation_cannot_be_queued(monkeypatch):
    previous = {"threshold": 0.7, "rules": []}
    dataset = SimpleNamespace(id=7, org_id=1, dedup_config=previous)
    db = _FakeDb(dataset)
    user = SimpleNamespace(org_id=1)
    body = DedupConfigUpdate.model_validate({
        "rules": [{"column": "name", "method": "jaro_winkler"}],
    })
    monkeypatch.setattr(rules_router, "_column_info", lambda _db, _id: [SimpleNamespace(name="name")])
    monkeypatch.setattr(
        rules_router, "enqueue_refresh_dataset",
        lambda _id: (_ for _ in ()).throw(RuntimeError("queue offline")),
    )

    with pytest.raises(HTTPException) as error:
        rules_router.update_dedup_config(7, body, db, user)

    assert error.value.status_code == 503
    assert dataset.dedup_config == previous
    assert db.commits == 2
