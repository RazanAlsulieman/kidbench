#!/usr/bin/env python3
"""Reconstruct the human-rated KIDBench cultural preference subset.

This script only joins repository artifacts and derives deterministic integrity
flags and a stratified audit sample. It does not score or alter responses.
"""

from __future__ import annotations

import csv
import hashlib
import json
import random
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent
COUNTRIES = ("Pakistan", "China", "India", "Nigeria")
AUDIT_COUNTS = {"Pakistan": 13, "China": 13, "India": 12, "Nigeria": 12}
SEED = 260525510
MODEL_A = "llamaplushie-3-8b-sft-3"
MODEL_B = "qwen-3.6-27b"
VOTE_MAP = {"1": "A", "2": "B", "3": "Tie"}

COLUMNS = [
    "example_id", "source_prompt_id", "country", "category", "prompt",
    "response_a", "response_b", "annotator_1", "annotator_2",
    "annotator_3", "majority_label", "response_a_model",
    "response_b_model", "source_prompt_file", "source_response_file",
    "source_annotation_file", "source_template_file", "source_row_number",
    "exact_duplicate", "duplicate_prompt", "repeated_response_pair",
    "shared_source_prompt", "prompt_response_mismatch",
    "country_inconsistency", "unresolved_linkage", "integrity_issue",
    "integrity_notes",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def flatten_response_file(path: Path) -> dict[str, tuple[str, str, int]]:
    """Return prompt -> (response, category, zero-based category index)."""
    data = json.loads(path.read_text(encoding="utf-8"))
    result = {}
    for category, items in data.items():
        for index, item in enumerate(items):
            result[item["prompt"]] = (item["response"], category, index)
    return result


def majority(votes: list[str]) -> str:
    mapped = [VOTE_MAP[v] for v in votes if v in VOTE_MAP]
    if len(mapped) != 3:
        return "NoConsensus"
    label, count = Counter(mapped).most_common(1)[0]
    return label if count >= 2 else "NoConsensus"


def bool_text(value: bool) -> str:
    return "true" if value else "false"


def build_rows() -> list[dict[str, str]]:
    benchmark_path = ROOT / "dataset/kidbench/kidbench_single.json"
    benchmark = json.loads(benchmark_path.read_text(encoding="utf-8"))["english"]
    prompt_metadata = {
        item["with_cues"]: (category, index)
        for category, items in benchmark.items()
        for index, item in enumerate(items)
    }
    rows: list[dict[str, str]] = []

    for country in COUNTRIES:
        slug = country.lower()
        human_dir = ROOT / "evaluations/human_eval/cultural" / slug
        template_path = human_dir / f"{slug}.csv"
        template = read_csv(template_path)
        annotation_paths = [human_dir / f"annotator_{n}.csv" for n in range(1, 4)]
        annotations = [read_csv(path) for path in annotation_paths]
        response_paths = [
            ROOT / f"responses/single_turn/{MODEL_A}/with_cues/english_true_{slug}.json",
            ROOT / f"responses/single_turn/{MODEL_B}/with_cues/english_true_{slug}.json",
        ]
        response_maps = [flatten_response_file(path) for path in response_paths]

        for index, source in enumerate(template):
            prompt = source.get("Prompt", "")
            response_a = source.get("Model 1", "")
            response_b = source.get("Model 2", "")
            votes = [items[index].get("Pick", "") if index < len(items) else "" for items in annotations]
            notes = []

            metadata = prompt_metadata.get(prompt)
            unresolved = metadata is None
            category, prompt_index = metadata if metadata else ("", -1)
            source_prompt_id = f"{category}_{prompt_index}" if metadata else ""

            mismatch = False
            country_inconsistency = False
            for response_path, response_map, expected in zip(
                response_paths, response_maps, (response_a, response_b)
            ):
                linked = response_map.get(prompt)
                if linked is None or linked[0] != expected:
                    mismatch = True
                if f"english_true_{slug}.json" != response_path.name:
                    country_inconsistency = True

            for annotator_number, items in enumerate(annotations, 1):
                if index >= len(items):
                    notes.append(f"missing annotator {annotator_number} row")
                    continue
                compared = items[index]
                if any(compared.get(key, "") != source.get(key, "") for key in ("Prompt", "Model 1", "Model 2")):
                    mismatch = True
                    notes.append(f"annotator {annotator_number} row content differs from template")
                if votes[annotator_number - 1] not in VOTE_MAP:
                    notes.append(f"missing or unknown annotator {annotator_number} vote")

            if not prompt:
                notes.append("missing prompt")
            if not response_a:
                notes.append("missing response A")
            if not response_b:
                notes.append("missing response B")
            if mismatch:
                notes.append("prompt/response source linkage mismatch")
            if country_inconsistency:
                notes.append("country filename mismatch")
            if unresolved:
                notes.append("source prompt linkage unresolved")

            rows.append({
                "example_id": f"cultural_{slug}_{index + 1:03d}",
                "source_prompt_id": source_prompt_id,
                "country": country,
                "category": category,
                "prompt": prompt,
                "response_a": response_a,
                "response_b": response_b,
                "annotator_1": votes[0],
                "annotator_2": votes[1],
                "annotator_3": votes[2],
                "majority_label": majority(votes),
                "response_a_model": MODEL_A,
                "response_b_model": MODEL_B,
                "source_prompt_file": benchmark_path.relative_to(ROOT).as_posix(),
                "source_response_file": ";".join(path.relative_to(ROOT).as_posix() for path in response_paths),
                "source_annotation_file": ";".join(path.relative_to(ROOT).as_posix() for path in annotation_paths),
                "source_template_file": template_path.relative_to(ROOT).as_posix(),
                "source_row_number": str(index + 2),
                "prompt_response_mismatch": bool_text(mismatch),
                "country_inconsistency": bool_text(country_inconsistency),
                "unresolved_linkage": bool_text(unresolved),
                "integrity_notes": "; ".join(notes),
            })

    exact_counts = Counter(
        (r["country"], r["prompt"], r["response_a"], r["response_b"],
         r["annotator_1"], r["annotator_2"], r["annotator_3"])
        for r in rows
    )
    prompt_counts = Counter(r["prompt"] for r in rows)
    source_counts = Counter(r["source_prompt_id"] for r in rows if r["source_prompt_id"])
    pair_counts = Counter((r["response_a"], r["response_b"]) for r in rows)
    for row in rows:
        exact = exact_counts[(row["country"], row["prompt"], row["response_a"], row["response_b"],
                              row["annotator_1"], row["annotator_2"], row["annotator_3"])] > 1
        duplicate_prompt = prompt_counts[row["prompt"]] > 1
        shared_source = bool(row["source_prompt_id"] and source_counts[row["source_prompt_id"]] > 1)
        repeated_pair = pair_counts[(row["response_a"], row["response_b"])] > 1
        row["exact_duplicate"] = bool_text(exact)
        row["duplicate_prompt"] = bool_text(duplicate_prompt)
        row["repeated_response_pair"] = bool_text(repeated_pair)
        row["shared_source_prompt"] = bool_text(shared_source)
        severe = exact or repeated_pair or row["prompt_response_mismatch"] == "true" or row["country_inconsistency"] == "true" or row["unresolved_linkage"] == "true" or not all(row[k] for k in ("prompt", "response_a", "response_b", "annotator_1", "annotator_2", "annotator_3"))
        row["integrity_issue"] = bool_text(severe)
        descriptive = []
        if duplicate_prompt:
            descriptive.append("prompt intentionally recurs across country conditions")
        if shared_source:
            descriptive.append("source prompt shared across country conditions")
        if repeated_pair:
            descriptive.append("response pair repeated")
        if exact:
            descriptive.append("exact duplicate row")
        row["integrity_notes"] = "; ".join(filter(None, [row["integrity_notes"], *descriptive]))
    return rows


def write_csv(path: Path, rows: list[dict[str, str]], columns: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        writer.writerows({column: row.get(column, "") for column in columns} for row in rows)


def audit_sample(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    rng = random.Random(SEED)
    selected = []
    for country in COUNTRIES:
        country_rows = [row for row in rows if row["country"] == country]
        by_category = defaultdict(list)
        for row in country_rows:
            by_category[row["category"]].append(row)
        first_pass = []
        for category in sorted(by_category):
            choices = sorted(by_category[category], key=lambda row: row["example_id"])
            first_pass.append(rng.choice(choices))
        chosen_ids = {row["example_id"] for row in first_pass}
        remaining = [row for row in country_rows if row["example_id"] not in chosen_ids]
        rng.shuffle(remaining)
        selected.extend(first_pass + remaining[: AUDIT_COUNTS[country] - len(first_pass)])
    rng.shuffle(selected)
    for row in selected:
        row.update({key: "" for key in ("my_label", "gt_correct", "ambiguous", "exclude_recommendation", "audit_notes")})
    return selected


def main() -> None:
    rows = build_rows()
    write_csv(OUT / "kidbench_cultural_candidate.csv", rows, COLUMNS)
    audit_columns = COLUMNS + ["my_label", "gt_correct", "ambiguous", "exclude_recommendation", "audit_notes"]
    write_csv(OUT / "kidbench_cultural_audit50.csv", audit_sample(rows), audit_columns)
    digest = hashlib.sha256((OUT / "kidbench_cultural_audit50.csv").read_bytes()).hexdigest()
    print(f"Wrote {len(rows)} candidates and 50 audit rows (seed={SEED}, audit sha256={digest})")


if __name__ == "__main__":
    main()
