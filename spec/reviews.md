# CEE-REV v0.1

Applies together with CEE-CORE.

## Finding format

`[P1] Short statement of the defect`

`<Evidence, condition, and impact.>`

`<Suggested fix when sufficiently supported.>`

Do not print placeholder labels unless needed for comprehension.

## Rules

- **REV-001 (MUST):** Each finding addresses one independently actionable problem.
- **REV-002 (MUST):** State the defect in the title or first sentence.
- **REV-003 (MUST):** Include specific evidence or a reproducible failure condition.
- **REV-004 (MUST):** Explain non-obvious impact.
- **REV-005 (SHOULD):** Suggest the smallest safe fix when known.
- **REV-006 (MUST NOT):** Report style preferences as functional defects.
- **REV-007 (MUST NOT):** Invent findings or imply that unverified issues are confirmed.
- **REV-008 (SHOULD):** Aim for 60 words or fewer, unless details are necessary.
- **REV-009 (SHOULD):** Consolidate duplicate findings within a pull request.
- **REV-010 (MUST):** Return zero findings when none meet the evidence threshold.

## Severity

- **P0:** Critical immediate impact; severe exploitation or widespread outage.
- **P1:** High-impact defect normally requiring correction before merge.
- **P2:** Material functional defect or credible risk.
- **P3:** Low-impact defect or optional improvement. Do not misrepresent an improvement as a defect.

Severity must be justified by context, not writing intensity.
