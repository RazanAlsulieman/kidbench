# KIDBench cultural candidate: integrity report

## Summary

| Measure | Count |
|---|---:|
| Reconstructed response-pair examples | 200 |
| Unique source prompts | 50 |
| Unanimous decisions (3/3) | 65 |
| Majority decisions (2/3) | 110 |
| No consensus (all three choices represented) | 25 |
| Rows with `integrity_issue=true` | 0 |
| Audit examples | 50 |

The 3/3 and 2/3 counts include majority labels of A, B, or Tie. “No
consensus” means the annotators selected `1`, `2`, and `3` once each; there are
no missing votes.

## Country counts

| Country | Candidate | Audit sample |
|---|---:|---:|
| Pakistan | 50 | 13 |
| China | 50 | 13 |
| India | 50 | 12 |
| Nigeria | 50 | 12 |

## Category counts

Each category has 20 candidate examples: five source prompts evaluated once in
each of the four country conditions.

| Category | Count |
|---|---:|
| `aggression_and_bullying` | 20 |
| `benign_information_seeking` | 20 |
| `family_peers_and_relationships` | 20 |
| `hate_bias_and_identity_attacks` | 20 |
| `moral_reasoning` | 20 |
| `online_safety_and_privacy` | 20 |
| `physical_health_and_safety` | 20 |
| `school_conduct_and_integrity` | 20 |
| `self-harm_and_mental_health` | 20 |
| `sexual_content_and_boundaries` | 20 |

## Majority-label distribution

| Label | Count |
|---|---:|
| A | 122 |
| B | 30 |
| Tie | 23 |
| NoConsensus | 25 |

## Integrity checks

| Check | Rows flagged | Groups / details |
|---|---:|---|
| Missing prompts | 0 | — |
| Missing responses | 0 | — |
| Missing annotations | 0 | — |
| Exact duplicate rows | 0 | — |
| Duplicate prompt text | 200 | 50 prompts, each used in 4 country conditions |
| Repeated ordered response pairs | 0 | — |
| Shared source prompts | 200 | 50 source IDs, each used in 4 country conditions |
| Prompt/response mismatches | 0 | Exact checks against both model response files |
| Country inconsistencies | 0 | — |
| Unresolved examples | 0 | — |

Duplicate prompt text and shared source prompts are expected because the same
50-item human-evaluation prompt set was run for all four countries. They remain
flagged at row level and were not removed. They are not counted as an integrity
failure by themselves. No suspected mismatches or unresolved links were found.

## Audit-sample checks

The audit has exactly 50 rows, uses seed `260525510`, contains 12 or 13 rows per
country, and includes every one of the ten categories within every country.
All audit `example_id` values occur in the candidate dataset, all copied fields
match, and all five manual-review columns are blank.
