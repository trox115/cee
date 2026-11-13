---
name: cee-review
description: Produce concise, evidence-based code review findings following experimental CEE v0.1 CORE+REV+AI.
---

# CEE Review Skill — v0.1

Review the supplied diff and relevant surrounding code. Use these rules for your **published review comments**, not as a substitute for technical analysis.

## Priority

Technical correctness > evidence > clarity > brevity > style.

## Mandatory requirements

1. Report one independently actionable problem per finding. Do not invent findings.
2. Begin each finding with `[P0]`, `[P1]`, `[P2]`, or `[P3]` and a concrete defect statement.
3. Include a specific failure condition and evidence grounded in the diff or supplied context. Explain non-obvious impact.
4. Preserve relevant conditions, identifiers, and uncertainty. Do not present a hypothesis as a confirmed bug.
5. Do not present style preferences as functional defects.
6. Suggest the smallest safe correction when sufficiently supported.
7. Avoid filler, generic praise, repeated code, and decorative summaries.
8. Target 60 words or fewer per finding, but never remove critical information to meet the target.
9. Consolidate duplicate findings. If none qualify, output exactly `No actionable findings.`
10. Never claim to have run tests or checked files unless you actually did. State material validation limits when relevant.

## Severity

- **P0**: Critical immediate impact, such as severe exploitation or widespread outage.
- **P1**: High-impact defect normally requiring correction before merge.
- **P2**: Material functional defect or credible risk.
- **P3**: Low-impact defect or optional improvement, clearly labeled as such.

## Output format

```text
[P2] Guard against a missing user

When `user` is null, `user.name` throws before the handler can return a response.
Check `user` before reading `name`.
```

No preamble. One finding per block. Do not disclose secrets from the codebase.

## Source of truth

This skill is a portable summary. When available, the repository's `spec/core.md`, `spec/reviews.md`, and `spec/agents.md` define normative requirements. If there is a conflict, follow those files.
