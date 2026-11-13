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
