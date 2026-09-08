# Security Notes

## Threats directly exercised by tests

- replay after successful effectuation,
- concurrent replay race,
- signed-envelope modification,
- wrong verification key,
- Candidate Act substitution,
- resource widening,
- effect-parameter substitution,
- effect-class substitution,
- sink substitution,
- missing validation evidence,
- missing sink-local activation state,
- stale topology/configuration state,
- stale policy/revocation/authority epochs,
- protected-state substitution,
- expired Candidate Act or authority,
- nonce reuse,
- missing required attestation,
- disallowed/unresolved jurisdiction,
- disallowed purpose.

## Trust assumptions in this reference build

- PED code is trusted.
- Sink code is trusted.
- Signer key material is trusted.
- The Python process and host are trusted.
- `ProtectedNetworkState` is assumed authentic/current.
- In-memory locks and SQLite atomic updates behave correctly.
- The consequence is reachable only through the demo sink.

Those assumptions are intentionally visible because production systems must replace them with real protected boundaries.

## Fail closed

Every missing load-bearing state produces denial. There is no default allow on cache miss, timeout, missing authority, missing evidence, missing activation record, stale epoch, signature failure, or unknown jurisdiction in the configured demo policy.
