# CEE review taxonomy v0.3 release candidate

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

## Classification boundaries

A demonstrated reachable violation under stated conditions is a confirmed defect even if its frequency or impact is unknown. State that uncertainty separately. A conditional risk depends on a material unverified precondition, not merely uncertainty about severity. A policy question does not establish a code defect.

A general assertion in a review discussion is not automatically a defect finding. A type label identifies the intended type but cannot supply missing evidence. A disproved alleged defect is not made valid by changing its label; an established underlying defect with a misreported trigger may need factual revision while retaining its type. Justify any additional classification violation independently.

When a comment mixes independent subjects, such as a demonstrated defect and an optional design change, separate them under REV-001. Publication, type, severity and confidence remain independent; no metadata field is required to decorate every published sentence. REV-015 indexes the existing severity-by-impact obligation without changing it.
