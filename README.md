# CEE — Controlled Engineering English

[![License: Apache-2.0](https://img.shields.io/badge/License-Apache--2.0-blue.svg)](LICENSE) [![Status: Experimental](https://img.shields.io/badge/status-experimental-orange.svg)](CHANGELOG.md)

**CEE v0.3 release candidate is an experimental, model-agnostic controlled-language specification for software engineering communication.** It aims to reduce reading effort without sacrificing technical correctness, evidence, or useful detail.

> **Not an official standard.** CEE is an independent proposal inspired by controlled-language principles. It is not affiliated with ASD-STE100.

## Start here

- [CORE rules](spec/core.md): mandatory writing and evidence requirements.
- [REV rules](spec/reviews.md): actionable code review findings.
- [Reply rules](spec/replies.md): accurate author replies and approvals.
- [Review taxonomy](spec/taxonomy.md): type, severity and confidence.
- [Reply agent skill](skills/cee-reply/SKILL.md): portable reply instructions.
- [AI rules](spec/agents.md): honest reporting of actions and uncertainty.
- [CEE review agent skill](skills/cee-review/SKILL.md): copy into a supported agent's skill directory or adapt as agent instructions.
- [Review examples](examples/reviews/): compliant and non-compliant outputs.
- [v0.3 decisions](docs/v0.3-decisions.md): scope and rationale for the release candidate.
- [v0.3 validation plan](docs/v0.3-validation-plan.md): proposed checks and evidence still needed.
- [Evaluation protocol](benchmarks/protocol.md): how to test whether CEE actually helps.

`ISS` (issues) and `DOC` (documentation) are **planned**. They are not normative in this release candidate.

## Review output example

```text
[P2] Guard against a missing user

When `user` is null, `user.name` throws before the handler can return a response.
Check `user` before reading `name`.
```

No findings? Return `No actionable findings.` **Do not fabricate a finding.**

## Try it in an agent

1. Copy [`skills/cee-review/SKILL.md`](skills/cee-review/SKILL.md) to the location supported by your agent, or paste its instructions into your reviewer configuration.
2. Provide the diff, surrounding code, and relevant requirements or tests.
3. Ask for actionable findings only, following `CEE/0.3 CORE+REV+AI`.
4. Verify each finding against the code. This skill is **not** a technical correctness guarantee.

The skill is self-contained for portability. Repository `spec/` files remain the normative source if there is a conflict.

## Conformance

A self-declared `CEE/0.3 CORE+REV+AI` output follows all applicable MUST / MUST NOT rules. SHOULD deviations are allowed with justification. No certification, automated validator, or verified compliance badge exists in this release candidate.

## Roadmap

- **v0.1**: initial CORE + REV + AI draft.
- **v0.2**: review taxonomy, reply rules, approach reviews and expanded evaluation protocol.
- **v0.3 release candidate**: applicability, preservation, uncertainty, verification and conditional recommendation clarifications.
- **Later**: ISS + DOC modules, semantic evaluation, integrations.

## Contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md) and [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md). Please do not submit employer-owned source code, private diffs, secrets, or personal information.

## License

Apache License 2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE). Contributions are submitted under the same license unless explicitly agreed otherwise.

## Release-candidate status

`VERSION` is `0.3.0-rc.1`. This is an experimental release candidate, not a published or validated release. Comparative effectiveness against 0.2.0 has not been validated. Independent human incident validation remains incomplete. No improvement in technical quality, reading time or evaluator reliability has been demonstrated for this candidate.

Existing rule identifiers and normative levels are retained. REV-015 gives an identifier to the existing severity-by-impact obligation; it is not a new severity policy. The current runner discovers it from the specification without an infrastructure change. Its review-discussion profile therefore contains 28 entries instead of 27. Historical evaluations remain bound to their original specification and profile; never rebind them to this working tree or claim their scores validate this candidate.

The lexical dictionary has its own unchanged version. The benchmark runner's implementation/version is separate from the CEE specification version. Deterministic link/profile checks can detect mechanical inconsistencies; they do not certify semantic conformance.
