# CEE-CORE v0.3 release candidate

## Normative language

MUST and MUST NOT indicate requirements. SHOULD and SHOULD NOT indicate recommendations; deviations require a reason. MAY indicates an option.

## Priority

Technical correctness > evidence > clarity > brevity > style.

## Rules

- **CORE-001 (MUST):** Put the main technical point before supporting explanation.
- **CORE-002 (MUST):** Do not state a hypothesis as a verified fact.
- **CORE-003 (MUST):** Preserve relevant conditions, constraints, identifiers, and failure modes.
- **CORE-004 (MUST NOT):** Add introductory filler, praise, or a conclusion that conveys no new information.
- **CORE-005 (SHOULD):** Use direct verbs and concrete nouns.
- **CORE-006 (SHOULD):** Address one independent subject per paragraph.
- **CORE-007 (MUST):** Preserve uncertainty where evidence is incomplete.
- **CORE-008 (SHOULD):** Remove redundant phrases and repeated information.
- **CORE-009 (MUST):** Preserve literal code identifiers, logs, and quoted source material when relevant.
- **CORE-010 (MUST):** Never omit critical information solely to meet a length target.

- **CORE-011 (SHOULD):** Place information that can invalidate subsequent items before those items.
- **CORE-012 (SHOULD):** Identify the source and relevant content of image evidence in text, without exposing sensitive information.

## Notes

Word counts are guidance, not hard conformance criteria. Quoted code and user-supplied text are exempt from lexical replacements.

## Applying the rules

Apply each rule only when its own conditions are met. Several rules can concern one problem, but each violation needs a separate justification. A false conclusion alone does not establish every nearby rule violation.

CORE-003 covers materially relevant behavior as well as conditions and names: return values, side effects, exceptions, defaults and the circumstances selecting them. Reversing a failure mode changes preserved meaning even when a function name remains unchanged. Correcting a disproved source assertion is not a preservation failure. An unchanged assertion does not by itself establish a new loss during rewriting; its absolute correctness and evidence obligations still apply.

Under CORE-009, relevance depends on what the reader needs to locate, interpret or reproduce the concern. Preserve material literal values and expressions, not only identifier spelling. Omitting a name is not automatically a violation when the review location or remaining context identifies the same subject without ambiguity. Do not remove a materially necessary identifier merely to shorten the text.

Assess factual correctness, deciding evidence and the expressed certainty separately. Sufficient evidence can establish either truth or falsity. A refuted claim is not an evidence gap; a missing contract does not establish a false claim. CORE-002 requires a hypothesis presented as verified, not merely any incorrect reading. CORE-007 applies to material uncertainty from incomplete evidence, including inherited categorical claims; it does not require the original to have expressed a hedge.

When rewriting, retain material uncertainty, technical conditions and action modality. Making an implied action explicit does not justify turning an option into a requirement or an unresolved question into a decision. Report an unresolved policy question separately from established code behavior; one does not decide the other.

Correct material assertions and restore conditions before shortening. Remove redundant wording only when it adds no information, then recheck correctness, evidence, triggers and modality. Necessary qualification takes priority over a length target. The conditional scope of a SHOULD recommendation remains conditional; an absent prerequisite is not a deviation requiring a fabricated remedy.
