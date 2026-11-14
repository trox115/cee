# CEE review taxonomy v0.2

Applies to CEE-REV. Type, impact, confidence and publication decision are independent.

| Type | Meaning |
|---|---|
| `confirmed_defect` | Evidence establishes a violation or failure under stated conditions. |
| `conditional_risk` | Failure depends on a material unverified precondition. |
| `clarification_request` | Missing information requires an answer. |
| `suggestion` | Optional improvement, including style. |
| `design_concern` | Structural concern, possibly outside the PR scope. |

Documentation and test defects can be confirmed defects. A pre-existing defect is not necessarily a regression. State scope when relevant.

Severity P0–P3 applies to defects and risks. Confidence describes evidence quality (high, medium, low); state material uncertainty in prose. Blocking status is independent of severity. Labels need not all appear in published text if their meaning is clear.

Publication decisions: `publish` (useful and supported), `revise` (repair evidence or wording), `omit` (duplicate, unsupported or irrelevant), `defer` (track elsewhere or revisit if the approach remains). These decisions are evaluation metadata, not required comment decorations.
