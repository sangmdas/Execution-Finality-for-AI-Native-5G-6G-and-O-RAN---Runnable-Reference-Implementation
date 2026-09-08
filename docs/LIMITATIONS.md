# Limitations and Non-Claims

1. **Reference implementation, not a standard.** The code accompanies an Internet-Draft and makes its concepts executable. It is not IETF/3GPP/O-RAN conformance certification.
2. **No hardware-protected PED.** Python process memory is not a TEE, enclave, HSM, protected OS service, DPU, or secure network function.
3. **No hardware Finality Sink.** The demo consequence is an in-memory mutation, not a UPF/RAN/RF hardware state transition.
4. **No proof of alternate-path closure.** A production deployment must identify every route capable of producing the same protected consequence.
5. **SQLite is not protected monotonic state.** A privileged attacker able to rewrite or roll back the database can defeat assumptions unless storage is separately protected.
6. **No real attestation verification.** The code can require/bind an attestation digest but does not verify EAT/TPM/TEE/vendor evidence.
7. **No live 3GPP/O-RAN bindings.** No N4, SBA, CAPIF, NEF, A1, E2, or carrier orchestration adapter is included.
8. **No distributed state protocol.** The example does not solve replication, quorum, split-brain, inter-operator federation, or Byzantine faults.
9. **No trusted time service.** Runtime system time is used for example freshness and TTL decisions.
10. **No full policy language.** The included telecom policy is a minimal allowlist/epoch policy sufficient for execution-finality demonstrations.
11. **No emergency/preemption semantics.** Production telecom systems need explicit handling for emergency, lawful, safety, and operator override classes rather than ad hoc bypasses.
12. **No formal verification.** Passing tests do not prove security under all implementations or threat models.
13. **No carrier throughput claim.** Python benchmark numbers are local software measurements only.
14. **No external ledger requirement or implementation.** The local evidence chain demonstrates ordering; it is not a blockchain.
15. **No new IANA assignments.** `EF-xxx` codes are illustrative.
16. **No implied patent license.** See the source draft's IPR note and repository `NOTICE.md`.

## Most important deployment limitation

A Finality Sink only provides the intended property if the protected consequence is technically non-completable through another route. Wrapping one API call while leaving a privileged alternate path unguarded does not establish execution finality for the consequence.
