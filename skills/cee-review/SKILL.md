---
name: cee-review
description: Produce precise, evidence-based engineering reviews under experimental CEE v0.3 release candidate CORE+REV+AI.
---

# CEE Review Skill — v0.3 release candidate

Technical correctness > evidence > clarity > brevity > style.

Inspect the diff, relevant source, consumers, requirements, configuration, release state and existing explanations. Before a universal or system-wide claim, establish its scope and the relevant paths. Distinguish completed, incomplete and unavailable checks; a timeout does not prove absence. Do not infer verification conduct solely from a conclusion or claim checks ran unless they did.

Preserve materially relevant behavior, triggers, identifiers, literal values and expressions. Keep identifiers needed to locate, interpret or reproduce the concern, without mechanically repeating every name. Correct disproved source assertions rather than preserving their errors. An unchanged inherited error still has absolute correctness and evidence duties, but it does not alone prove a new preservation loss or uncertainty-to-certainty conversion.

Apply finding-specific rules only to actual findings and preserve each rule's antecedents. Keep factual truth, deciding evidence, uncertainty and policy questions separate. An open policy question is not automatically an uncertain factual inference. Preserve action modality: an option stays optional, and an unresolved question stays open unless evidence resolves it.

Publish only supported useful observations. A specific but non-failing invocation is not evidence for its alleged failure. Correct a false extension of a real defect rather than automatically deleting the supported issue; omit a finding when none remains supported. Several rules may concern one incident, but independently justify every rule instead of treating one factual error as all overlapping violations.

Use [P0] critical immediate impact, [P1] high impact, [P2] material impact, [P3] low impact for defects or credible risks. Under REV-015 severity follows impact, not confidence. An established reachable defect remains confirmed if only frequency or impact is unknown; state the uncertainty. Use [question], [blocking question], [suggestion] or [design] for non-defect items. Split independent defect and design subjects. A label cannot substitute for evidence.

Each finding leads with the issue, supplies specific evidence or a valid reproducer, preserves triggers and explains non-obvious impact. Suggest the smallest safe fix only when known. Do not invent a fix for a refuted defect or infer an unspecified validation's behavior. Address existing explanations and omit duplicates. For proposed-for-removal code, defer or explicitly condition the finding on the approach remaining.

Correct material assertions before optimizing wording. Remove title/body repetition only when it adds no information, then recheck correctness, evidence, triggers and modality. Aim for 60 words unless necessary detail requires more; never make that a hard gate. Conditional SHOULD requirements remain conditional. For approach reviews, put decisive questions before dependent items and keep an alternative optional unless established. Describe image evidence and source without exposing secrets.

If no actionable findings or material questions qualify, output `No actionable findings.` Report material validation limits. This release candidate has not demonstrated quality improvements and independent human validation remains incomplete.

Example:

```text
[P2] Reject expired credentials before writing

When the credential has expired, `authorize()` denies access but the write runs first. Check authorization before writing.
```

The repository's spec/core.md, spec/reviews.md, spec/taxonomy.md and spec/agents.md are normative. This portable summary does not guarantee technical correctness.
