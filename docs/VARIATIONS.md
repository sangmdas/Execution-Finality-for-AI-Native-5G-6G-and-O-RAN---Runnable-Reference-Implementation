# Implementation Variations

The protocol pattern is intentionally independent of one hardware vendor or transport. This repository exposes variations without changing the core ordering invariant.

## Cryptographic authority

- **Ed25519**: default; separates PED signing key from sink verification key.
- **HMAC-SHA256**: shared-secret demonstration for constrained environments. Not equivalent to asymmetric key separation.

## Protected-state persistence

- **In-memory**: deterministic and fast for tests; loses state at process restart.
- **SQLite**: demonstrates durable replay/consumption and evidence state; not tamper resistant.

## Candidate Act classes exercised

- slice allocation,
- RAN parameter change,
- network API invocation,
- UPF rule change,
- session modification,
- beam change,
- sensing operation,
- RF enable.

## Sink placements modeled

- RAN control,
- O-RAN E2,
- network API gateway,
- UPF,
- session controller,
- control-plane gateway,
- RF enable boundary.

## Subscriber scopes exercised

- tenant,
- slice,
- single subscriber,
- subscriber group,
- cell population.

## Attestation mode

`--require-attestation` requires a runtime attestation digest to be present in the Candidate Act. The repository intentionally does not pretend that checking presence equals validating real attestation evidence.

## Authority lifetime

Authority TTL is configurable. Shorter values reduce stale-authority exposure but increase sensitivity to clock and control-path latency. Production values must be selected from actual network timing and consequence class.

## Hot/cold path

The current code demonstrates local state suitable for a bounded hot path. A production policy adapter can route higher-risk acts to remote validators, multi-party approval, human authorization, or additional attestation before authority issuance.
