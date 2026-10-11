#!/usr/bin/env python3
"""Verify Step 2 blinding, coverage, and deterministic response randomization."""

from __future__ import annotations

import csv
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent
SEED = 260525511
EXPECTED_COUNTRIES = {"Pakistan": 13, "China": 13, "India": 12, "Nigeria": 12}
EXPECTED_MANUAL_FIELDS = {
    "my_label", "confidence", "ambiguous", "gt_correct",
    "exclude_recommendation", "error_type", "audit_notes",
}
FORBIDDEN_EXACT = {
    "annotator_1", "annotator_2", "annotator_3", "majority_label",
    "response_a_model", "response_b_model", "displayed_a_source",
    "displayed_b_source", "original_response_a_position",
    "original_response_b_position",
}
FORBIDDEN_FRAGMENTS = (
    "deepseek", "kidguard", "evaluation_label", "judge_label", "model_score",
)


def load(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return reader.fieldnames or [], list(reader)


def main() -> int:
    errors: list[str] = []
    step1_fields, step1 = load(ROOT / "kidbench_spar_step1/kidbench_cultural_audit50.csv")
    blinded_fields, blinded = load(OUT / "kidbench_cultural_audit50_blinded.csv")
    review_fields, review = load(OUT / "kidbench_cultural_audit50_review.csv")
    mapping_fields, mapping = load(OUT / "audit_ab_mapping.csv")

    if len(blinded) != 50:
        errors.append(f"blinded file has {len(blinded)} rows, expected 50")
    if len(review) != 50:
        errors.append(f"review file has {len(review)} rows, expected 50")
    if len(mapping) != 50:
        errors.append(f"mapping file has {len(mapping)} rows, expected 50")

    step1_ids = [row["example_id"] for row in step1]
    blinded_ids = [row.get("example_id", "") for row in blinded]
    if Counter(blinded_ids) != Counter(step1_ids):
        errors.append("blinded examples do not represent every Step 1 example exactly once")
    if any(count != 1 for count in Counter(blinded_ids).values()):
        errors.append("blinded example_id values are not unique")

    normalized_fields = {field.lower() for field in blinded_fields}
    leaked_fields = FORBIDDEN_EXACT & normalized_fields
    leaked_fragments = sorted(
        field for field in normalized_fields if any(fragment in field for fragment in FORBIDDEN_FRAGMENTS)
    )
    if leaked_fields:
        errors.append(f"ground-truth/model-identity fields leaked: {sorted(leaked_fields)}")
    if leaked_fragments:
        errors.append(f"automated-evaluation fields leaked: {leaked_fragments}")
    if not EXPECTED_MANUAL_FIELDS <= set(blinded_fields):
        errors.append("blinded file is missing manual-review fields")

    for file_name, rows in (("blinded", blinded), ("review", review)):
        for row in rows:
            nonblank = [field for field in EXPECTED_MANUAL_FIELDS if row.get(field, "") != ""]
            if nonblank:
                errors.append(f"{file_name} row {row.get('example_id')} has nonblank manual fields: {nonblank}")

    country_counts = Counter(row.get("country") for row in blinded)
    if dict(country_counts) != EXPECTED_COUNTRIES:
        errors.append(f"country distribution is {dict(country_counts)}, expected {EXPECTED_COUNTRIES}")
    categories_by_country: dict[str, set[str]] = defaultdict(set)
    for row in blinded:
        categories_by_country[row.get("country", "")].add(row.get("category", ""))
    for country in EXPECTED_COUNTRIES:
        if len(categories_by_country[country]) != 10:
            errors.append(f"{country} has {len(categories_by_country[country])} categories, expected 10")

    # Reproduce the balanced swap assignment from Step 1 order and the seed.
    rng = random.Random(SEED)
    swap_assignments = [False] * (len(step1) // 2) + [True] * (len(step1) // 2)
    rng.shuffle(swap_assignments)
    blinded_by_id = {row["example_id"]: row for row in blinded}
    mapping_by_id = {row["example_id"]: row for row in mapping}
    swaps = 0
    for source, swap in zip(step1, swap_assignments, strict=True):
        swaps += int(swap)
        example_id = source["example_id"]
        displayed = blinded_by_id.get(example_id)
        internal = mapping_by_id.get(example_id)
        if displayed is None or internal is None:
            continue
        expected_a = source["response_b"] if swap else source["response_a"]
        expected_b = source["response_a"] if swap else source["response_b"]
        if displayed["response_a"] != expected_a or displayed["response_b"] != expected_b:
            errors.append(f"response randomization is not reproducible for {example_id}")
        expected_mapping = {
            "original_response_a_position": "B" if swap else "A",
            "original_response_b_position": "A" if swap else "B",
            "displayed_a_source": "original_response_b" if swap else "original_response_a",
            "displayed_b_source": "original_response_a" if swap else "original_response_b",
        }
        for field, value in expected_mapping.items():
            if internal.get(field) != value:
                errors.append(f"mapping field {field} is incorrect for {example_id}")

    if swaps != 25:
        errors.append(f"randomization produced {swaps} swaps, expected a balanced 25")

    # The review worksheet must contain exactly the same blinded data, only sorted.
    if blinded_fields != review_fields:
        errors.append("review and blinded schemas differ")
    if {row["example_id"]: row for row in review} != blinded_by_id:
        errors.append("review content differs from blinded content")
    expected_review_ids = [
        row["example_id"]
        for row in sorted(blinded, key=lambda row: (row["country"], row["category"], row["example_id"]))
    ]
    if [row["example_id"] for row in review] != expected_review_ids:
        errors.append("review worksheet is not sorted by country/category/example_id")

    if errors:
        print("VERIFICATION FAILED")
        for error in errors:
            print(f"- {error}")
        return 1
    print(
        "VERIFICATION PASSED: "
        f"50 blinded examples; countries={dict(country_counts)}; "
        f"randomization={swaps} swapped/{50 - swaps} unchanged; "
        "ground_truth_leak=false; manual_fields_empty=true"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
