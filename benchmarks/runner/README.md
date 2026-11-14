# ceebench: CEE benchmark runner (MVP)

`ceebench` prepares and checks retrospective CEE benchmarks. It validates evidence packets, exports a time-bounded generator view per item, counts words with fixed rules, freezes outputs with SHA-256, and writes structured metrics. It does not call a model and does not score quality.

Requirements: Python 3.10+, standard library only. Datasets live outside this repository. Pass their path on the command line.

```sh
cd benchmarks/runner
python3 -m ceebench validate /path/to/dataset
python3 -m ceebench view /path/to/dataset --case CASE --all --out /tmp/views
python3 -m ceebench freeze /path/to/run/generation.json --schema generation
python3 -m ceebench metrics /path/to/dataset --case all --generation /path/to/run/generation.json \
  --require-frozen --spec-root ../.. --out /path/to/run/metrics
python3 -m unittest discover -s tests
```

## Evidence packet format (`ceebench/case/1`)

A dataset is a directory with `dataset.json` (`ceebench/dataset/1`) and one directory per case. Each case directory holds one review discussion:

```
case.json            items, files, snapshots, retrieval log
checksums.sha256     SHA-256 of every file in the case except itself
generator/           tier generator_input: original comments, PR description versions
evidence/            tier review_time: diffs, ticket versions, CI results, other evidence
reference/           tier evaluator_only: sample definition, prior variants, prior assessments
outcomes/            tier outcome: later pushes, merges, replies, raw API dumps
```

Rules that `validate` enforces:

- Every file in the case is declared in `case.json` with a `tier`, and the tier matches its top directory.
- `generator_input` and `review_time` files declare `available_at` (RFC 3339). Use the time the information became available to the original writer, for example push time, status completion time or edit time.
- Each item's `original` text is `generator_input` and is available no later than the item's `posted_at`.
- Parents exist and are not posted after their replies.
- `reference/sample.json` (`ceebench/sample/1`) and `reference/variants/*/variant.json` (`ceebench/variant/1`) validate. Prior variant texts are `evaluator_only`.
- Case manifests and the dataset manifest match the files on disk.

Sample groups, classifications and prior variants are evaluator material. Mark them `reported_judgment` unless they were independently verified.

### Evidence selection and provenance

A `review_time` file can carry a `selection` record:

| Field | Meaning |
|---|---|
| `basis` | `primary`: selected from original comments, anchors, diffs or code dependencies. `secondary`: selected from candidate rewrites or previous evaluations. |
| `method` | How it was selected, for example `changed_file`, `path_reference`, `symbol_definition` or `directory_reference` |
| `repository`, `revision`, `source_path`, `git_blob` | Exact origin of the snapshot |
| `referenced_by` | Item ids, `candidate:<item>` or `prior:<document>` |
| `same_content_at` | Later revisions with identical content (stored once) |

`validate` requires provenance (`referenced_by`) for secondary evidence and allows `selection` only on `review_time` files. Record missing files, unresolved references and unavailable revisions in `retrieval_log` (`unresolved`, `ambiguous`, `omitted_size`, `not_located`, ...).

## Generator isolation

For new case/2 experiments, use `context` to export one focused context per item:

```sh
python3 -m ceebench context /path/to/dataset --case CASE --audience generator --out /tmp/contexts
python3 -m ceebench context /path/to/dataset --case CASE --audience evaluator \
  --candidate-variant VARIANT --budget 100000 --out /tmp/evaluator-contexts
```

The budget counts evidence-content characters. Prompt builders must report total
prompt size separately, including instructions, specification and metadata.
Required evidence exceeding the budget fails the export. Context metadata records
selection decisions, omission reasons and known gaps. Gaps mean insufficient
evidence; selection does not establish semantic completeness.

Groups require an explicit `--unit` with the same posting timestamp and reviewed
revision. The default is separate contexts. Availability is `verified`,
`reconstructed`, or `unknown`; unknown evidence is excluded and reported as a gap.
Commit timestamps used in reconstruction do not prove remote availability.

The older `view` export below remains available for legacy packet compatibility.

`view` builds one directory per target item. It contains:

- every item posted at or before the target's `posted_at`;
- `generator_input` and `review_time` files with `available_at` at or before that time;
- snapshots (repository pointers) available at that time;
- `view.json` (`ceebench/view/1`) and its own `checksums.sha256`.

`evaluator_only` and `outcome` files are never copied. Give the generator the view directory only, never the dataset path. Record the `view_digest` of each view in the generation file (`views`).

`--audience generator` (default) also excludes `secondary` evidence, because its selection depends on later analysis. `--audience evaluator` includes it. Neither view exposes selection basis or provenance.

Limits:

- Isolation is only as good as the `available_at` values in the packet.
- Items posted at the same instant see each other.
- `view` copies files; it does not sandbox the process. A generator with file system access to the dataset can still read it.
- Snapshots are pointers. Resolving them to a full checkout is the operator's job, and that checkout can contain later history unless it is pinned to the revision.

## Word counting (`ceebench-wc/1`)

1. Normalize CRLF and CR to LF.
2. Remove fenced code blocks (``` or ~~~, 3+ characters, up to 3 leading spaces), fence lines included. An unclosed fence runs to the end of the text.
3. Remove Markdown images `![alt](url)` with an optional `{attributes}` block.
4. Count tokens with Python `str.split()`.

Inline code, labels, titles, emphasis markers and URLs count as written. Steps 2 and 3 can be switched off with `--fenced-code include` and `--images include`. Metrics record the ruleset and options, and report fenced and image tokens separately.

## Outputs

Dataset sealing is write-once. `seal` refuses an existing dataset or case manifest.
Create a new dataset version in a new directory when evidence changes. Local
checksums detect changes relative to a recorded manifest. They do not provide
cryptographic protection against an actor who can rewrite both files and manifests.

- `freeze FILE` writes `FILE.sha256` (`shasum -a 256` format, relative name), then makes both files read-only. It refuses to overwrite an existing `.sha256`.
- `metrics` (`ceebench/metrics/1`) records:
  - runner version, Python version, and CEE `VERSION` plus git commit of `--spec-root`;
  - the dataset manifest digest and the input digests;
  - word counts per item and variant;
  - totals per sample and group;
  - deltas against the original;
  - a reproduction check against `reported_words`.

  It refuses to overwrite an existing file. Metrics are `publishable` only when the dataset, the case and every generation input are publishable.

## Schemas

`schemas/` holds JSON Schema (draft 2020-12) files for `dataset`, `case`, `sample`, `variant`, `generation` and `metrics`. The built-in validator implements the subset these schemas use.

New generations use `ceebench/generation/2` with dataset/manifest, case, item-context
digests, specification version/commit, and runner fingerprint bindings. Metrics
require `--contexts-root` and `--spec-root` to verify them. Conflicting specification
metadata is rejected. `--allow-legacy` explicitly imports generation/1 with incomplete
provenance; it does not fabricate historical bindings.

`ceebench/evaluation/1` adds claim origins, corrected errors, absolute violations,
rule results and dimension scores. Validate it with:

```sh
python3 -m ceebench check-evaluation /path/to/dataset evaluation.json \
  --spec-root /path/to/spec --contexts-root /tmp/evaluator-contexts
```

Expected coverage defaults to the prepared context directories; use repeated
`--item` arguments for an explicit subset. Validation checks structure, identities,
coverage and declared consistency. It does not judge the truth of claims. Keyword
contradiction heuristics produce warnings only. Private prompt builders must also
record and verify their exact implementation and instruction fingerprints.

## Not included

Model invocation, semantic scoring and independent evaluation are out of scope.
The runner remains standard-library-only.
