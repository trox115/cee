# CEE initial evaluation protocol

## Sample

30-50 anonymized code review cases, including clean diffs and false-positive traps. Do not publish proprietary code or secrets.

## Design

Use identical code context for baseline and CEE variants. Randomize presentation order and blind reviewers to variant identity.

## Measures

- Accuracy: is the finding technically correct?
- Evidence: can the claim be checked from provided context?
- Actionability: can the reader decide what to do?
- Critical omissions: did the rewrite hide a condition or risk?
- Reading time and words per finding.
- False positive rate on known-clean examples.

## Acceptance criteria

Do not accept a version that reduces words while materially reducing accuracy or increasing critical omissions. Record raw results and reviewer disagreements.

## Retrospective and prospective evaluation

Keep findings, author replies and non-finding segments separate. Compare like-for-like word counts (document tokenization and code exclusions); retain negative compression. A retrospective rewrite is not a controlled generation experiment. Record whether each change corrects an error, adds a condition, removes information or merely changes wording. Blind independent readers before claiming measured comprehension gains.

- **BENCH-001 (MUST):** Preserve negative compression results.
- **BENCH-002 (MUST):** Evaluate acceptance, technical validity, reproducibility, severity justification and fix outcome separately.
- **BENCH-003 (MUST):** Evaluate language compliance separately from technical validity.

Record type, severity, confidence, publication decision and reason. Track reviewed revision, context changes and merged revision when available. For merge outcomes distinguish fixed, open, claimed fixed but missing, deferred, not applicable and unknown. A reply accurate when written may become stale; do not infer dishonesty. Report unavailable context and do not count unknowns as verified successes. Keep technical false positives separate from low-value comments. Include clean diffs and rejected findings. Private evidence stays private.
