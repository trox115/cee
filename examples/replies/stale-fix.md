# Synthetic example: stale fix after rebase

The author implemented two corrections, but only one remains in the merged revision.

Non-compliant at merge: Both issues fixed.

Compliant: The retry guard is merged. The logging fix was dropped during the rebase and remains open.

A correct reply at the time of writing can become inaccurate later. Verify the merged state.
