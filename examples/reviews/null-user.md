# Example: null user access

## Code context

A request handler receives an optional `user` and reads `user.name` without a guard.

## Non-compliant

It is important to note that there may potentially be a situation in which the user is null, and this could perhaps cause unexpected behavior. It might be beneficial to consider adding some checks to improve robustness.

## CEE-compliant

[P2] Guard against a missing user

When `user` is null, `user.name` throws before the handler can return a response. Check `user` before reading `name`.

## Why

The compliant finding states the condition, exact failure, and corrective action without speculative filler.
