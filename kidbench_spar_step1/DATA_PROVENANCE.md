# KIDBench cultural candidate: data provenance

## Repository snapshot

- Repository: <https://github.com/RazanAlsulieman/kidbench.git>
- Paper: <https://arxiv.org/abs/2605.25510>
- Source commit: `8789d50ec2b44cb7e6ffc983621d6d9bfe6be96c`
- Extraction script: `kidbench_spar_step1/build_kidbench_candidate.py`
- This is extraction and verification only. No judge was run, no response was
  generated, no model score was used as ground truth, and no human annotation
  was changed.

## Source inventory

### Prompt and metadata source

- `dataset/kidbench/kidbench_single.json` supplies the child prompt, benchmark
  category, and stable position within the category. Only the English
  `with_cues` prompts are linked here.

### Response sources

Model 1 / Response A is copied from `llamaplushie-3-8b-sft-3`; Model 2 /
Response B is copied from `qwen-3.6-27b`. The eight files are:

- `responses/single_turn/llamaplushie-3-8b-sft-3/with_cues/english_true_pakistan.json`
- `responses/single_turn/llamaplushie-3-8b-sft-3/with_cues/english_true_china.json`
- `responses/single_turn/llamaplushie-3-8b-sft-3/with_cues/english_true_india.json`
- `responses/single_turn/llamaplushie-3-8b-sft-3/with_cues/english_true_nigeria.json`
- `responses/single_turn/qwen-3.6-27b/with_cues/english_true_pakistan.json`
- `responses/single_turn/qwen-3.6-27b/with_cues/english_true_china.json`
- `responses/single_turn/qwen-3.6-27b/with_cues/english_true_india.json`
- `responses/single_turn/qwen-3.6-27b/with_cues/english_true_nigeria.json`

### Human-evaluation sources

For each country, `{country}.csv` is the unfilled response-pair template and
`annotator_1.csv`, `annotator_2.csv`, and `annotator_3.csv` contain the three
original votes. The 16 files used are:

- `evaluations/human_eval/cultural/pakistan/pakistan.csv`
- `evaluations/human_eval/cultural/pakistan/annotator_1.csv`
- `evaluations/human_eval/cultural/pakistan/annotator_2.csv`
- `evaluations/human_eval/cultural/pakistan/annotator_3.csv`
- `evaluations/human_eval/cultural/china/china.csv`
- `evaluations/human_eval/cultural/china/annotator_1.csv`
- `evaluations/human_eval/cultural/china/annotator_2.csv`
- `evaluations/human_eval/cultural/china/annotator_3.csv`
- `evaluations/human_eval/cultural/india/india.csv`
- `evaluations/human_eval/cultural/india/annotator_1.csv`
- `evaluations/human_eval/cultural/india/annotator_2.csv`
- `evaluations/human_eval/cultural/india/annotator_3.csv`
- `evaluations/human_eval/cultural/nigeria/nigeria.csv`
- `evaluations/human_eval/cultural/nigeria/annotator_1.csv`
- `evaluations/human_eval/cultural/nigeria/annotator_2.csv`
- `evaluations/human_eval/cultural/nigeria/annotator_3.csv`

`evaluations/human_eval/cultural/instructions.pdf` is the annotation-protocol
metadata used to interpret `Pick`. The repository's per-country response JSON
filenames provide the country condition. No DeepSeek evaluation file,
KIDGuard response, or generated gold response is an input.

## Reconstruction logic

1. Read each country's 50-row unfilled template in its original row order.
2. Join each annotator file by country and row position, but require `Prompt`,
   `Model 1`, and `Model 2` to match the template on that row. Any disagreement
   is retained and flagged rather than repaired.
3. Match `Prompt` exactly to the English `with_cues` text in
   `kidbench_single.json`. `source_prompt_id` is
   `{category}_{zero_based_index}`; the zero-based index is the prompt's stable
   position within that category in the source JSON. This produces a unique
   benchmark prompt match for every row.
4. Match Model 1 and Model 2 text exactly against the corresponding country,
   prompt, and response-model JSON. Every response has exactly one expected
   match. Both response paths are retained, in A/B order, separated by `;`.
5. Preserve the original `Pick` strings (`1`, `2`, or `3`) in the annotator
   columns. Source file paths and the one-based physical CSV row number
   (including the header as row 1) are recorded on every result row.

## Annotation and majority mapping

The human-evaluation instructions define:

- `1` = Model 1 is preferred, mapped to `A`;
- `2` = Model 2 is preferred, mapped to `B`;
- `3` = both are equally good or equally bad, mapped to `Tie`.

`majority_label` is `A`, `B`, or `Tie` when at least two of the three mapped
votes agree. It is `NoConsensus` when all three mapped votes differ or when a
vote is missing/unrecognised. The raw annotator columns are never rewritten.

## Integrity and duplicate detection

Comparisons are exact Unicode string comparisons; no trimming, case folding,
or semantic/fuzzy matching is used.

- `exact_duplicate`: another row has the same country, prompt, both responses,
  and all three raw votes.
- `duplicate_prompt`: the exact prompt string occurs on another row.
- `repeated_response_pair`: the exact ordered `(response_a, response_b)` pair
  occurs on another row.
- `shared_source_prompt`: another example has the same `source_prompt_id`.
- `prompt_response_mismatch`: annotator/template cells differ, a source
  response is absent, or an exact response-text check fails.
- `country_inconsistency`: an expected response source filename does not match
  the row's country.
- `unresolved_linkage`: the prompt cannot be linked exactly to the benchmark.

All 50 source prompts were intentionally evaluated in all four country
conditions. Consequently, all 200 rows have `duplicate_prompt=true` and
`shared_source_prompt=true`; these are expected design properties and are not
alone counted as `integrity_issue`. A row is an integrity issue for an exact
duplicate, repeated response pair, missing required value, mismatch, country
inconsistency, or unresolved linkage. Nothing is deleted.

## Audit sample

The fixed Python PRNG seed is **`260525510`**. Sampling first chooses one row
from every category in every country, then fills the remaining slots from that
country without replacement. Country targets are Pakistan 13, China 13, India
12, and Nigeria 12. The combined 50 rows are deterministically shuffled. This
ensures all ten categories appear in every country's audit stratum.

The generated audit CSV SHA-256 is
`cc1dc7109dce7f89031ff39a1543c83bff1fd2024f6084fd4aa61ba4912d4189`.
The five manual-review columns are created blank.

## Unresolved linkage issues

None. All 200 prompts, 400 responses, and 600 human votes linked exactly.
The cross-country reuse of 50 source prompts is explicitly flagged for an
auditor's awareness, but is not an unresolved linkage.
