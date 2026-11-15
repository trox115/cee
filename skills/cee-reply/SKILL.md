---
name: cee-reply
description: Write evidence-based author replies and approvals under experimental CEE v0.3 release candidate.
---

# CEE Reply Skill — v0.3 release candidate

Technical correctness > evidence > clarity > brevity > style.

Answer each material question or mark it open. Keep technical facts, policy questions and commitments separate. Preserve material uncertainty, technical conditions, relevant identifiers and action modality. Do not turn an option into a requirement or an unresolved question into a decision without evidence.

Distinguish proposed, implemented, tested and merged work. Verify fix claims against the relevant code state and recheck after rebase or other history changes. A commit reference alone does not establish a fix or its merge outcome. Do not infer checks from a conclusion or claim unperformed checks ran.

Inherited errors remain subject to absolute correctness and evidence duties. Identical categorical text does not alone establish a new uncertainty-to-certainty conversion. State a material evidence gap rather than inventing an author-only image fact, task or commitment. Link deferred work when possible; when a task or link is unverified, state the limitation. A failed search is not proof that no task exists. Keep conditional SHOULD recommendations conditional.

State useful evidence for an approval and omit redundant agreement. Correct material content before shortening, then recheck open questions, uncertainty, commitments and code-state claims. Never sacrifice correctness or evidence for brevity. Avoid filler, secrets and mechanical repetition of irrelevant identifiers.

Example:

```text
The permission check is implemented in the current branch. Tests have not run. Open: whether to backport the change. The follow-up task link is not available.
```

Repository spec/core.md, spec/replies.md and spec/agents.md are normative. This release candidate does not guarantee technical correctness; quality improvements are unproven and independent human validation remains incomplete.
