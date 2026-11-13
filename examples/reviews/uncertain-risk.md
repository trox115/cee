# Example: unverified risk

## Context

A request handler calls `lookupAccount(id)`, but the function's implementation and contract are not available.

## Non-compliant

[P1] Account lookup crashes when the account does not exist.

## CEE-compliant

No actionable findings.

## Why

The available context does not establish whether `lookupAccount` throws, returns null, or handles missing accounts. Request more context before asserting a defect.
