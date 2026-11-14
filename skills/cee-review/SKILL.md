---
name: cee-review
description: Produce precise, evidence-based engineering reviews under experimental CEE v0.2 CORE+REV+AI.
---

# CEE Review Skill — v0.2

Technical correctness > evidence > clarity > brevity > style.

Inspect the diff, relevant code, consumers, requirements, configuration and existing review threads when available. Do not claim unavailable checks. Verify reachability and preserve all material triggers; distinguish regression from existing issues. Attribute production data claims. Address existing explanations.

Publish only useful supported observations. Consolidate duplicates; defer out-of-scope items or items on code proposed for removal when appropriate. Ask genuine questions only when material context cannot be resolved. Do not invent findings.

Use [P0] critical immediate impact, [P1] high impact, [P2] material impact, [P3] low impact for defects or credible risks. Distinguish confirmed defects from conditional risks in wording. Use [question], [blocking question], [suggestion] or [design] for other types. Severity reflects impact, not confidence. State evidence gaps and unknown impact explicitly.

Each finding: lead with the issue or question, state evidence and triggers, explain non-obvious impact, suggest the smallest safe action when known. Aim for 60 words unless more are needed. Preserve identifiers, literals and uncertainty. Avoid filler, repetition and unsupported claims. For approach reviews use verdict, blocking questions, independent findings, alternative, out-of-scope notes as applicable. Put decisive items first. Describe image evidence and source in text without exposing secrets.

If no actionable findings or material questions qualify, output `No actionable findings.` Do not claim tests ran unless they did. Report material validation limits.

Example:

```text
[P2] Guard against a missing user

When `user` is null, `user.name` throws before the handler returns. Check `user` before reading `name`.
```

The repository's spec/core.md, spec/reviews.md, spec/taxonomy.md and spec/agents.md are normative. This portable summary does not guarantee technical correctness.
