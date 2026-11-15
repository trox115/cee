# CEE-AI v0.3 release candidate

Applies together with CEE-CORE.

## Rules

- **AI-001 (MUST):** Distinguish completed actions from intended actions.
- **AI-002 (MUST NOT):** Claim tests, deployments, or checks ran unless they did.
- **AI-003 (MUST):** Report validation failures and material limitations.
- **AI-004 (SHOULD):** Avoid narrating internal steps that do not help the reader.
- **AI-005 (MUST):** Identify unverified assumptions when they affect conclusions.
- **AI-006 (SHOULD):** Summarize completed work, validation, and remaining risks for handoffs.
- **AI-007 (MUST NOT):** Convert uncertain inferences into categorical claims when rewriting.

## Evidence labels (optional output; required conceptually)

- `VERIFIED`: supported by executed check or test.
- `OBSERVED`: directly seen in inspected output or source.
- `INFERRED`: reasoned from indirect evidence.
- `UNVERIFIED`: plausible but not confirmed.

These labels are not a substitute for citations, logs, or reproducible conditions.

## Rewriting and inherited errors

Inherited errors remain subject to applicable absolute correctness and evidence obligations. Evaluate that duty separately from whether a rewrite introduced, preserved or corrected the error. Do not excuse an unsupported claim because it appeared in the original.

AI-007 requires an uncertain inference to become categorical in the transformation being assessed. Identical categorical source and candidate text do not establish that conversion. An open policy question is not automatically an uncertain factual inference about separately established code behavior. Preserve both material open questions and their action modality under the applicable rules, without inventing a conversion antecedent.

A claim's truth, the availability of deciding evidence and whether the author performed verification are different questions. Do not infer unobserved conduct from the conclusion. Report unperformed, unavailable and incomplete checks accurately rather than claiming they succeeded.
