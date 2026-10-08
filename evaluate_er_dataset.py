"""Score entity resolution against the ground truth in the generated dataset.

Reads `true_entity_id` / `use_case` from the CSV produced by
generate_er_dataset.py, runs the backend resolver, and reports pairwise
precision/recall overall plus recall per use case. UC4 rows are the
false-positive trap: any merge inside a `uc4_family_false_positive` group is a
defect, so they are reported separately as a false-merge rate.

Usage:
    python evaluate_er_dataset.py                              # 20k rows, reference config
    python evaluate_er_dataset.py --rows 50000 --threshold 0.85
    python evaluate_er_dataset.py --config my_config.json      # your own dedup config
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from itertools import combinations

import pandas as pd

sys.path.insert(0, "backend")
from app.config import settings  # noqa: E402
from app.services.entity_resolution import resolve_entities  # noqa: E402

GROUND_TRUTH_COLUMNS = ["use_case", "expected_match", "true_entity_id",
                        "pair_group_id", "variant"]

# Reference config for this dataset. `required` on nik means: when both rows
# carry a NIK they must match exactly, but the rule is skipped when either side
# is missing — which is what lets UC2/UC3 still match while UC4 siblings are
# vetoed apart.
#
# cluster_validation is on because without it connected-component closure chains
# unrelated people together through one weak link (measured on this dataset:
# precision 0.42 -> 0.62 at the same threshold).
REFERENCE_CONFIG = {
    "threshold": 0.8,
    "exact_row_match": True,
    "cluster_validation": {"enabled": True, "method": "representative",
                           "min_representative_score": 0.8, "min_cohesion": 0.7},
    "rules": [
        {"column": "nik", "method": "exact", "normalizers": ["identifier"],
         "weight": 6.0, "required": True},
        {"column": "dob", "method": "exact", "normalizers": ["date"],
         "weight": 3.0, "mismatch_penalty": 0.85},
        {"column": "full_name", "method": "token_sort", "normalizers": ["name"],
         "weight": 2.5},
        {"column": "full_name", "method": "phonetic", "normalizers": ["name"],
         "weight": 1.5},
        {"column": "phone_number", "method": "phone", "normalizers": ["phone"],
         "weight": 3.0},
        {"column": "alamat", "method": "token_set", "normalizers": ["address"],
         "weight": 2.0},
    ],
}


def truth_pairs(df: pd.DataFrame) -> set[tuple[int, int]]:
    by_entity: dict[str, list[int]] = defaultdict(list)
    for position, entity in enumerate(df["true_entity_id"]):
        by_entity[entity].append(position)
    return {pair for members in by_entity.values() if len(members) > 1
            for pair in combinations(sorted(members), 2)}


def predicted_pairs(clusters: list[dict]) -> set[tuple[int, int]]:
    return {pair for cluster in clusters
            for pair in combinations(sorted(cluster["members"]), 2)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="samples/er_dataset_10k.csv")
    parser.add_argument("--rows", type=int, default=None,
                        help="score only the first N rows. Slicing a fully "
                             "shuffled file cuts partners out of the slice and "
                             "makes precision look worse than it is — prefer "
                             "scoring a whole (smaller) file")
    parser.add_argument("--threshold", type=float, default=None)
    parser.add_argument("--config", help="JSON file with a dedup_config to test")
    args = parser.parse_args()

    df = pd.read_csv(args.input, dtype=str, keep_default_na=False, nrows=args.rows)
    truth = df[GROUND_TRUTH_COLUMNS].copy()
    # The resolver must not see the answers.
    subject = df.drop(columns=GROUND_TRUTH_COLUMNS)

    config = json.load(open(args.config)) if args.config else dict(REFERENCE_CONFIG)
    if args.threshold is not None:
        config["threshold"] = args.threshold

    print(f"Scoring {len(df):,} rows from {args.input} "
          f"(threshold={config.get('threshold')}, er_max_pairs={settings.er_max_pairs:,})")
    if args.rows:
        orphans = (truth.groupby("pair_group_id").size()
                   != pd.read_csv(args.input, usecols=["pair_group_id"])
                   .pair_group_id.value_counts().reindex(truth.pair_group_id.unique())).sum()
        if orphans:
            print(f"WARNING: {orphans:,} groups are only partly inside this slice; "
                  "their missing partners are excluded from the ground truth")
    result = resolve_entities(subject, config)
    predicted = predicted_pairs(result["clusters"])
    expected = truth_pairs(truth)

    hits = predicted & expected
    precision = len(hits) / len(predicted) if predicted else 0.0
    recall = len(hits) / len(expected) if expected else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0

    print(f"\nclusters found       : {len(result['clusters']):,}")
    print(f"pairs predicted      : {len(predicted):,}")
    print(f"pairs in ground truth: {len(expected):,}")
    print(f"\nprecision {precision:.4f}   recall {recall:.4f}   F1 {f1:.4f}")

    # Recall per use case: which scenarios the algorithm actually solves.
    use_case = truth["use_case"].tolist()
    per_case_total: dict[str, int] = defaultdict(int)
    per_case_hit: dict[str, int] = defaultdict(int)
    for left, right in expected:
        case = use_case[left]
        per_case_total[case] += 1
        per_case_hit[case] += (left, right) in predicted

    print(f"\n{'use_case':<30}{'true pairs':>12}{'matched':>10}{'recall':>9}")
    for case in sorted(per_case_total):
        total, hit = per_case_total[case], per_case_hit[case]
        print(f"{case:<30}{total:>12,}{hit:>10,}{hit / total:>9.2%}")

    # UC4: any predicted pair inside one household group is a wrong merge.
    group = truth["pair_group_id"].tolist()
    uc4_pairs = [p for p in predicted
                 if use_case[p[0]] == "uc4_family_false_positive"
                 and group[p[0]] == group[p[1]]]
    uc4_groups = truth[truth.use_case == "uc4_family_false_positive"].pair_group_id.nunique()
    merged_groups = len({group[p[0]] for p in uc4_pairs})
    print(f"\nUC4 false-merge: {merged_groups:,} of {uc4_groups:,} household groups "
          f"wrongly merged ({merged_groups / uc4_groups:.2%})" if uc4_groups else "")

    # Everything else that was merged but shouldn't be.
    other_fp = len(predicted - expected) - len(uc4_pairs)
    print(f"other false merges (incl. normal_data): {other_fp:,}")

    worst = sorted(
        ((variant, count) for variant, count in
         pd.Series([truth["variant"][l] for l, r in expected - predicted]).value_counts().items()),
        key=lambda item: -item[1])[:10]
    if worst:
        print("\nTop missed variants (recall failures):")
        for variant, count in worst:
            print(f"  {count:>6,}  {variant}")


if __name__ == "__main__":
    main()
