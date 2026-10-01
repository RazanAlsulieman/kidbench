#!/usr/bin/env python3
"""Verify the reconstructed KIDBench cultural candidate and audit CSVs."""

from __future__ import annotations

import csv
import sys
from collections import Counter
from pathlib import Path


OUT = Path(__file__).resolve().parent
ROOT = OUT.parent
COUNTRIES = {"Pakistan", "China", "India", "Nigeria"}
VALID_LABELS = {"A", "B", "Tie", "NoConsensus"}
VOTE_MAP = {"1": "A", "2": "B", "3": "Tie"}
REQUIRED_COLUMNS = {
    "example_id", "source_prompt_id", "country", "category", "prompt",
    "response_a", "response_b", "annotator_1", "annotator_2",
    "annotator_3", "majority_label", "source_prompt_file",
    "source_response_file", "source_annotation_file", "exact_duplicate",
    "shared_source_prompt", "integrity_issue", "integrity_notes",
}
REQUIRED_VALUES = {
    "example_id", "source_prompt_id", "country", "category", "prompt",
    "response_a", "response_b", "annotator_1", "annotator_2",
    "annotator_3", "majority_label", "source_prompt_file",
    "source_response_file", "source_annotation_file",
}
MANUAL_COLUMNS = {
    "my_label", "gt_correct", "ambiguous", "exclude_recommendation",
    "audit_notes",
}


def load(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return reader.fieldnames or [], list(reader)


def expected_majority(row: dict[str, str]) -> str:
    votes = [VOTE_MAP.get(row[f"annotator_{number}"]) for number in range(1, 4)]
    if any(vote is None for vote in votes):
        return "NoConsensus"
    counts = Counter(votes)
    label, count = counts.most_common(1)[0]
    return label if count >= 2 else "NoConsensus"


def main() -> int:
    errors: list[str] = []
    candidate_columns, candidate = load(OUT / "kidbench_cultural_candidate.csv")
    audit_columns, audit = load(OUT / "kidbench_cultural_audit50.csv")

    for name, columns in (("candidate", candidate_columns), ("audit", audit_columns)):
        missing = REQUIRED_COLUMNS - set(columns)
        if missing:
            errors.append(f"{name} missing required columns: {sorted(missing)}")
    missing_manual = MANUAL_COLUMNS - set(audit_columns)
    if missing_manual:
        errors.append(f"audit missing manual-review columns: {sorted(missing_manual)}")
    if len(audit) != 50:
        errors.append(f"audit has {len(audit)} rows, expected 50")

    candidate_by_id = {row["example_id"]: row for row in candidate}
    if len(candidate_by_id) != len(candidate):
        errors.append("candidate example_id values are not unique")
    for row in audit:
        source = candidate_by_id.get(row.get("example_id", ""))
        if source is None:
            errors.append(f"audit example not in candidate: {row.get('example_id')!r}")
            continue
        for column in candidate_columns:
            if row.get(column) != source.get(column):
                errors.append(f"audit row {row['example_id']} changed candidate field {column}")
        if any(row.get(column, "") != "" for column in MANUAL_COLUMNS):
            errors.append(f"audit manual columns are not blank for {row['example_id']}")

    country_counts = Counter(row.get("country") for row in audit)
    if set(country_counts) != COUNTRIES or sorted(country_counts.values()) != [12, 12, 13, 13]:
        errors.append(f"invalid audit country stratification: {dict(country_counts)}")

    for row in candidate:
        missing_values = sorted(column for column in REQUIRED_VALUES if not row.get(column, ""))
        if missing_values:
            errors.append(f"candidate {row.get('example_id')} silently dropped required values: {missing_values}")
        if row.get("country") not in COUNTRIES:
            errors.append(f"candidate {row.get('example_id')} has invalid country {row.get('country')!r}")
        if row.get("majority_label") not in VALID_LABELS:
            errors.append(f"candidate {row.get('example_id')} has invalid label {row.get('majority_label')!r}")
        reproduced = expected_majority(row)
        if row.get("majority_label") != reproduced:
            errors.append(f"candidate {row.get('example_id')} majority is {row.get('majority_label')}, expected {reproduced}")

    # Verify that each annotation was copied exactly from its named source row.
    source_cache: dict[str, list[dict[str, str]]] = {}
    for row in candidate:
        source_row = int(row["source_row_number"]) - 2
        paths = row["source_annotation_file"].split(";")
        if len(paths) != 3:
            errors.append(f"candidate {row['example_id']} does not name three annotation files")
            continue
        for number, relative in enumerate(paths, 1):
            if relative not in source_cache:
                with (ROOT / relative).open(encoding="utf-8-sig", newline="") as handle:
                    source_cache[relative] = list(csv.DictReader(handle))
            source_rows = source_cache[relative]
            if source_row >= len(source_rows) or source_rows[source_row].get("Pick", "") != row[f"annotator_{number}"]:
                errors.append(f"candidate {row['example_id']} annotator_{number} differs from source")

    if errors:
        print("VERIFICATION FAILED")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"VERIFICATION PASSED: {len(candidate)} candidates; 50 audit rows; countries={dict(country_counts)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
