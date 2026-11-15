# CEE-REPLY v0.3 release candidate

Applies with CEE-CORE. For AI-generated replies also apply CEE-AI.

- **REPLY-001 (MUST):** A fix claim identifies the verified code state. Recheck claims after rebase, squash or other changes that may invalidate them; update stale references. Do not claim a fix is merged until verified in the merged state.
- **REPLY-002 (MUST):** Answer each material question or explicitly identify it as open.
- **REPLY-003 (SHOULD):** Link a follow-up task when deferring work; state if no task exists.
- **REPLY-004 (SHOULD):** State useful evidence when approving or agreeing; omit redundant agreement comments.

Distinguish proposed, implemented, tested and merged. A commit reference alone does not demonstrate correction. At merge, unresolved items may be explicitly accepted or deferred; do not silently describe them as fixed. This specification does not mandate a merge policy.

## Applying the reply rules

Keep technical facts, policy questions and author commitments separate. Preserve an option as an option and an unresolved question as open unless evidence resolves it. A rewrite cannot supply an unseen image fact, an unknown task or an unmade commitment.

REPLY-003 remains a conditional recommendation about deferred work. When a task link or its existence cannot be verified, state that limit; not finding a task does not establish that none exists. Do not invent a task to fill a placeholder. State useful evidence without repeating the entire review.

Inherited factual or evidence errors still need correction or an explicit limitation. Their presence does not establish a new AI-007 conversion without the corresponding source-to-reply change. Recheck the material obligations after shortening a reply, especially unresolved questions, uncertainty and the verified code state. These duties do not create a repository merge policy.
