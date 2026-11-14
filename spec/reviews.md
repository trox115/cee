# CEE-REV v0.2

Applies together with CEE-CORE.

## Finding format

`[P1] Short statement of the defect or risk`

Use `[question]`, `[blocking question]`, `[suggestion]` or `[design]` for non-defect items. See [taxonomy](taxonomy.md).

`<Evidence, condition, and impact.>`

`<Suggested fix when sufficiently supported.>`

Do not print placeholder labels unless needed for comprehension.

## Rules

- **REV-001 (MUST):** Each finding addresses one independently actionable problem.
- **REV-002 (MUST):** State the concern, defect or question in the title or first sentence.
- **REV-003 (MUST):** Include specific evidence or a reproducible failure condition. Attribute material production-data claims to their source; identify unavailable evidence.
- **REV-004 (MUST):** Explain non-obvious impact.
- **REV-005 (SHOULD):** Suggest the smallest safe fix when known.
- **REV-006 (MUST NOT):** Report style preferences as functional defects.
- **REV-007 (MUST NOT):** Invent findings or imply that unverified issues are confirmed.
- **REV-008 (SHOULD):** Aim for 60 words or fewer, unless details are necessary.
- **REV-009 (SHOULD):** Consolidate duplicate findings within a pull request.
- **REV-010 (MUST):** Return zero findings when none meet the evidence threshold.

- **REV-011 (SHOULD):** Address existing explanations and relevant review threads before publishing; omit duplicates and defer findings on code proposed for removal unless they matter if the approach stays.
- **REV-012 (MUST):** Verify material claims against accessible source, consumer, configuration and release state as applicable; identify evidence that is unavailable.
- **REV-013 (MUST):** Findings MUST distinguish confirmed defects, conditional risks and clarification requests.
- **REV-014 (MUST):** Review comments MUST preserve the conditions required to reproduce or trigger the reported problem.

## Approach reviews

A top-level review MAY group independently actionable findings when they support an approach-level decision. REV-001 applies to each finding, not the entire review. Present the verdict, blocking questions, findings with actions, proposed alternative, and out-of-scope design notes, as applicable. Follow CORE-011. Do not force a speculative alternative.

Before publication decide whether to publish, revise, omit or defer. Ask a clarification question when missing evidence matters and cannot be resolved from available context. Do not use questions to disguise established defects.

## Severity

- **P0:** Critical immediate impact; severe exploitation or widespread outage.
- **P1:** High-impact defect normally requiring correction before merge.
- **P2:** Material functional defect or credible risk.
- **P3:** Low-impact defect or credible low-impact risk. Label optional improvements separately.

Severity must be justified by impact, not writing intensity or confidence. Assign defect severity only to defects or risks; blocking status is separate.
