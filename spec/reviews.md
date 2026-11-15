# CEE-REV v0.3 release candidate

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

- **REV-011 (SHOULD):** Address existing explanations and relevant review threads before publishing; omit duplicates. For code proposed for removal, defer the finding or state that it applies only if the approach remains.
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

- **REV-015 (MUST):** Justify severity by impact, not writing intensity or confidence.

Assign defect severity only to defects or risks; blocking status is separate. State material uncertainty about impact in the prose. A supported conditional risk may use conditional severity, for example `[P2 if the queue is shared]`, with the unverified precondition explained. Unknown frequency or impact does not by itself turn an established reachable defect into a conditional risk.

## Applicability and evidence

A review-discussion context does not make every statement a defect finding. Apply finding-specific requirements only to communications functioning as findings, and only when the requirement's own conditions hold. General technical assurances still carry applicable CORE duties and the material-claim obligations of REV-012. In particular, do not apply REV-003's finding-evidence requirement or REV-013's finding classification merely because an assertion appears in a review thread.

For REV-003, a specific assertion is not evidence for itself. A stated failure condition must reproduce the alleged failure, or the finding must supply other specific supporting evidence. A concrete but non-failing invocation does not satisfy that condition.

REV-012 separates checking conduct from observable claim and disclosure requirements. Identify known missing evidence that materially limits a claim. Without a verification trace, a correct or incorrect conclusion alone does not establish whether checking was performed. A timed-out or incomplete search does not prove absence. Inspect relevant consumers, configuration and release state before extending a local result to a wider system; preserve unavailable checks as limitations.

## Supported scope and classification

Identify the assertion, trigger and claimed effect before deciding whether a problem is established. Under REV-007, an unsupported concrete extension of a real defect is still unsupported; this does not imply deliberate fabrication. Under REV-010, a real underlying defect with an incorrect trigger can require revision rather than zero findings. Omit a finding when no supported defect or credible risk remains, rather than inventing one to meet a quota.

A type marker alone does not establish the evidence needed for that type. Under REV-013, presenting absent defective behavior as a confirmed defect is an independently unjustified classification. An incorrect trigger on an otherwise established defect does not automatically prove a separate type-confusion violation. A reachable demonstrated failure remains confirmed when only frequency or impact is unknown. Split an independently actionable defect from a separate design concern under REV-001.

Multiple independently justified rule violations can describe one incident. Conversely, a familiar rule ID attached to a different complaint does not identify that incident. Do not infer incident detection solely from rule presence or infer all overlapping failures from one factual error.

## Fixes and recommendations

REV-005 recommends the smallest safe fix only when one is known. A refuted defect does not create a duty to propose a code change. Distinguish an ineffective suggestion from an established violation of that conditional recommendation. If the implementation or error policy of a suggested validation is unspecified, do not assume that it rejects otherwise safe inputs or that a particular minimal fix is established.

REV-008 is guidance, not a hard word-count gate. Correct the claim and preserve its material conditions before removing repetition. Keep a justified SHOULD exception explicit when it matters to the reader; do not trade evidence or correctness for brevity.
