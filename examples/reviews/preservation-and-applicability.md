# Synthetic examples: preservation and applicability

## Material literals and irrelevant names

Suppose the complete function returns `"east"` only when `code == "E"` and returns `"west"` otherwise. Rewriting `code == "E"` as `code == "W"` changes a material expression even though `code` keeps its spelling. CORE-003 concerns the changed condition; CORE-009 independently concerns the material literal.

In a review attached to that single function, an explanation may say "the enclosing function" instead of repeating its name when the location remains unambiguous. Identifier omission is not automatically a violation. It becomes material if the reader can no longer locate, interpret or reproduce the concern.

## Inherited assurance versus conversion

Original and candidate both say: "The queue survives a machine failure." The durability configuration is absent. Unchanged wording does not establish an AI-007 conversion. The categorical assurance still needs qualification under the applicable absolute evidence and uncertainty duties. A general assurance is not automatically a defect finding.

An appropriate rewrite is: "Queue durability across a machine failure is unverified; the persistence configuration is not supplied."

## Separate policy from behavior

The complete `trim_label()` implementation removes outer whitespace. "Should leading spaces be allowed?" is a policy question. Replacing it with "The function removes interior characters" invents different behavior; the open question alone is not proof of an uncertain factual inference converted under AI-007. Preserve the material question and its action modality.

## Refuted finding and unknown fix

The complete `copy_rows()` implementation returns a new list and does not mutate its argument. A mutation finding should be withdrawn, not supplied with an invented defensive patch to satisfy REV-005. If a validation policy is unspecified, do not assert that it rejects valid requests without seeing that policy.

## Correct, shorten, recheck

A title and body can repeat a claim without adding evidence. Remove the repetition, but retain the triggering condition, relevant expression, impact and known safe action. Necessary evidence may exceed 60 words. Brevity never takes precedence over correctness or evidence.
