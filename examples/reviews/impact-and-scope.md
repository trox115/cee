# Synthetic examples: impact, scope and overlap

## Conditional risk and impact

A job writes to a shared path, but queue ownership is not supplied.

Appropriate: `[P2 if the queue is shared] Two workers can overwrite the same export when they consume this path concurrently. Is the queue shared? Its ownership configuration is not available.`

Do not claim the concurrent path is established without that configuration. If a complete call trace instead establishes the race, it is a confirmed defect even when its frequency is unknown. State unknown impact separately; severity is not a confidence label.

## Real defect with an incorrect trigger

Suppose an established fault requires both an open session and an expired credential. A report claiming either condition alone triggers it needs factual revision. The false extension can violate REV-007; the removed conjunction can independently violate CORE-003 and REV-014. The genuine defect does not disappear, so REV-010 does not automatically require zero findings. Each rule needs its own basis.

## Verification conduct

A review concludes incorrectly about a supplied branch. That establishes a conclusion error, not whether the author skipped a check or misread it. A timed-out search is incomplete, not proof that a symbol is absent. If the material external configuration is unavailable, identify that gap without inventing a check history.

## Proposed removal

A handler is proposed for removal but remains in the current approach.

Appropriate: `If this handler remains, validate the request before writing. Otherwise defer this finding with the removal.`

Address the existing explanation and keep the condition explicit rather than silently exempting a supported concern.
