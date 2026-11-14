# Synthetic example: missing context

A worker retries failed writes. The transaction boundary is not visible.

Non-compliant: [P1] Retries always duplicate records.

Compliant: [question] Does the write commit before the retry is scheduled? If it commits and no idempotency guard exists, retrying can duplicate records. The transaction boundary is not available in the supplied code.

Do not assert reachability without evidence.
