import pandas as pd

from app.services.cross_dataset_checks import check_referential_integrity


def test_referential_profile_reports_overlap_and_orphans_and_ignores_blanks():
    child = pd.DataFrame({"customer_id": ["C-1", "C-2", "C-9", "", None]})
    parent = pd.DataFrame({"id": ["C-1", "C-2", "C-3"]})

    result = check_referential_integrity(child, "customer_id", parent, "id")

    assert result == {
        "checked": 3,
        "matched": 2,
        "key_overlap": 0.6667,
        "violations": 1,
        "orphan_rate": 0.3333,
        "samples": ["C-9"],
    }
