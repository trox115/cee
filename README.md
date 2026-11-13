# CEE — Controlled Engineering English

[![License: Apache-2.0](https://img.shields.io/badge/License-Apache--2.0-blue.svg)](LICENSE) [![Status: Experimental](https://img.shields.io/badge/status-experimental-orange.svg)](CHANGELOG.md)

**CEE v0.1 is an experimental, model-agnostic controlled-language specification for software engineering communication.** It aims to reduce reading effort without sacrificing technical correctness, evidence, or useful detail.

> **Not an official standard.** CEE is an independent proposal inspired by controlled-language principles. It is not affiliated with ASD-STE100.

## Start here

- [CORE rules](spec/core.md): mandatory writing and evidence requirements.
- [REV rules](spec/reviews.md): actionable code review findings.
- [AI rules](spec/agents.md): honest reporting of actions and uncertainty.
- [CEE review agent skill](skills/cee-review/SKILL.md): copy into a supported agent's skill directory or adapt as agent instructions.
- [Review examples](examples/reviews/): compliant and non-compliant outputs.
- [Evaluation protocol](benchmarks/protocol.md): how to test whether CEE actually helps.

`ISS` (issues) and `DOC` (documentation) are **planned**. They are not normative in v0.1.

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
3. Ask for actionable findings only, following `CEE/0.1 CORE+REV+AI`.
4. Verify each finding against the code. This skill is **not** a technical correctness guarantee.

The skill is self-contained for portability. Repository `spec/` files remain the normative source if there is a conflict.

## Conformance

A self-declared `CEE/0.1 CORE+REV+AI` output follows all applicable MUST / MUST NOT rules. SHOULD deviations are allowed with justification. No certification, automated validator, or verified compliance badge exists in v0.1.

## Roadmap

- **v0.1**: CORE + REV + AI draft, examples, agent skill, benchmark protocol.
- **v0.2 (proposed)**: testable fixtures and a deterministic linter for mechanical rules.
- **Later**: ISS + DOC modules, semantic evaluation, integrations.

## Contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md) and [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md). Please do not submit employer-owned source code, private diffs, secrets, or personal information.

## License

Apache License 2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE). Contributions are submitted under the same license unless explicitly agreed otherwise.
