# Reference Implementation v0.1.0

Initial runnable release accompanying `draft-das-ai-native-6g-execution-finality-01`.

Included:

- two-boundary PED + Network Finality Sink implementation;
- Candidate Act JSON model and schema traceability;
- protected validation evidence before authority issuance;
- signed, scope-limited, sink-bound finality authority;
- sink-local activation state to demonstrate non-bearer semantics;
- exact Candidate Act and effect-parameter hashing;
- topology/configuration/policy/authority/revocation epoch checks;
- nonce/sequence freshness and single-use consumption;
- Ed25519 and HMAC signing variations;
- in-memory and SQLite persistence variations;
- AI-RAN/O-RAN/UPF/session/network-API/RF/sensing/beam test variations;
- 79 automated tests;
- local benchmark harness;
- Dockerfile and GitHub Actions matrix.
