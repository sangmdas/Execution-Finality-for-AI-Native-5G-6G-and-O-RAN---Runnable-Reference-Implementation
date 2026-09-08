# Execution-Finality for AI-Native 5G/6G and O-RAN
## Runnable Reference Implementation

This repository is a **runnable, vendor-neutral reference implementation** of the execution-finality architecture described in `draft-das-ai-native-6g-execution-finality-01`, **Execution-Finality for AI-Native 5G/6G and O-RAN**.

The implementation demonstrates the draft's central invariant:

> A network operation may be generated, computed, scheduled, routed, or approved upstream, but it remains **non-effective** until protected validation evidence exists, scoped finality authority has been issued, and the actual Finality Sink independently verifies current authority immediately before the protected network consequence.

The code is deliberately structured as a two-boundary system rather than a single authorization call:

```text
AI / RIC / Orchestrator / Network Function
                 |
                 v
          Network Candidate Act
                 |
                 v
          NON-EFFECTIVE STATE
                 |
                 v
     Protected Enforcement Domain (PED)
       - validate act-specific predicates
       - verify policy / revocation / state
       - commit protected validation evidence
       - issue scoped finality authority
                 |
                 v
       signed authority envelope
                 +---- sink-local protected activation state
                 |
                 v
          Network Finality Sink
       - independently verify signature
       - re-hash exact Candidate Act
       - verify evidence binding
       - verify protected activation state
       - verify topology/configuration epochs
       - verify policy/authority/revocation epochs
       - verify nonce / sequence / scope / sink
       - recompute actual effect-parameter digest
       - atomically consume single-use authority
                 |
          FAILURE | SUCCESS
        no effect | permitted network effect
```

The reference implementation is intentionally **not** a simulation in which `ALLOW=True` directly mutates network state. The demo network consequence can only be reached through `NetworkFinalitySink.verify_and_effectuate()` after all load-bearing checks complete.

---

## 1. What this repository contains

- Python package implementing the Candidate Act, PED, protected evidence, scoped non-bearer authority, Finality Sink, replay state, and effectuation boundary.
- Pydantic models corresponding to the JSON interoperability objects and telecom fields in the draft.
- Canonical JSON hashing for act and effect binding.
- **Ed25519** signing as the default asymmetric implementation variation.
- **HMAC-SHA256** as a constrained/shared-secret demonstration variation.
- Sink-local activation state so the transported authority envelope is not treated as sufficient merely by possession.
- In-memory state for simple runs.
- SQLite-backed activation and validation-evidence stores for restart/persistence demonstrations.
- Single-use consumption and concurrent replay protection.
- Policy, authority, revocation, topology, and configuration epoch checks at the sink.
- AI-RAN, O-RAN, UPF, session, network-API, sensing, RF, beam, and slice-oriented variations.
- CLI examples for successful effectuation, replay, stale topology, revocation, parameter substitution, sink substitution, and signature tampering.
- Benchmark harness.
- **79 automated tests**, all passing in the packaged reference build.
- GitHub Actions workflow for Python 3.11, 3.12, and 3.13.
- Dockerfile.
- Original Internet-Draft XML under `draft/` for traceability.

---

## 2. Quick start

### Requirements

- Python **3.11+**
- `pydantic >= 2.7, < 3`
- `cryptography >= 42, < 47`
- `pytest >= 8, < 10` for tests

The packaged build was exercised in this environment with Python 3.13.5, Pydantic 2.13.4, cryptography 46.0.4, and pytest 9.0.2.

### Install

```bash
git clone <repository-url>
cd ai-native-6g-execution-finality-reference
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -e '.[dev]'
```

### Run the normal allow path

```bash
network-finality-demo
```

or:

```bash
python -m network_finality.cli
```

Expected result:

1. PED returns `ALLOW` and commits validation evidence.
2. A scoped finality authority is issued.
3. The Finality Sink independently verifies it.
4. The authority is consumed.
5. Exactly one demo network effect is created.

### Demonstrate replay protection

```bash
network-finality-demo --replay
```

The first invocation becomes effective. The second invocation using the same authority is denied with `EF-005 AUTHORITY_ALREADY_USED` semantics.

### Demonstrate stale topology

```bash
network-finality-demo --simulate topology-change
```

The PED can validly approve the act, but the sink rejects it because the topology epoch changed before effectuation.

### Other built-in failure demonstrations

```bash
network-finality-demo --simulate revocation
network-finality-demo --simulate parameter-substitution
network-finality-demo --simulate sink-substitution
network-finality-demo --simulate signature-tamper
```

### Persistent demo state

```bash
network-finality-demo --persistence sqlite --state-dir .ef-state --replay
```

This stores validation evidence and activation/consumption state in SQLite. SQLite persistence demonstrates restart-safe replay state; it is **not** claimed to be protected monotonic hardware state.

### Run all tests

```bash
pytest -q
```

Packaged reference result:

```text
79 passed
```

### Run in Docker

```bash
docker build -t network-finality-reference .
docker run --rm network-finality-reference
```

---

## 3. Source-to-code traceability

The implementation separates **draft-derived protocol concepts** from **implementation choices**. This distinction is important: the Internet-Draft defines architectural and semantic requirements; it does not prescribe one Python library, signing algorithm, database, transport, or hardware product.

| Repository element | Source in the draft | Implementation choice here |
|---|---|---|
| `NetworkCandidateAct` | JSON Interoperability Profile / NetworkCandidateAct object | Pydantic v2 strict model |
| Non-Effective State | Core Invariant / Non-Effective State | No `DemoNetwork.apply()` path is exposed before sink verification |
| PED | First Boundary: PED Validation | Python `ProtectedEnforcementDomain` class |
| Protected validation evidence | Validation Success / Evidence-Gated Progression | Hash-chained evidence record in memory or SQLite |
| Scoped non-bearer finality authority | Scoped Non-Bearer Finality Authority | Signed envelope + independently installed sink-local activation record |
| Act binding | Candidate Act Descriptor / Finality Sink Verification | Canonical JSON + SHA-256 digest |
| Sink binding | Authority and Finality Sink sections | `finality_sink_id` plus boundary ID plus sink-local activation state |
| Freshness | Candidate Act / authority / failure handling | Nonce, optional sequence, candidate expiry, authority expiry |
| Policy/revocation state | Authority Consumption, Replay, and Revocation | Exact integer epoch comparison at PED and sink |
| Topology/configuration state | JSON authority and state mismatch example | Exact topology and configuration epochs verified at sink |
| Replay prevention | Replay / Authority Consumption | Single-use activation store with atomic consume operation |
| Final consequence | Effectuation / Network Finality Sink | In-memory `DemoNetwork` mutation accessible only after finality checks |
| Hot/cold-path concept | Hot Path and Cold Path | Configurable policy/TTL hooks; no remote ledger is required for local demo |
| Transport neutrality | JSON Interoperability Profile | In-process call in demo; serialization is JSON-compatible |

### Important strictness variation

The draft's top-level Candidate Act schema uses `additionalProperties: false`. This implementation applies strict extra-field rejection to **all Pydantic objects**, including nested structures. That is an intentional defensive implementation choice and should not be misrepresented as a normative requirement added by the draft.

---

## 4. How the parameters were selected

The values in the default runnable example are not arbitrary protocol claims. They come from either the draft's JSON examples or explicit reference-implementation decisions.

### Draft-derived example values

The default example mirrors the draft's AI-RAN resource-allocation example:

| Parameter | Default | Why it appears |
|---|---:|---|
| `candidate_act_id` | `net-39f8820b-reference` | Follows draft Candidate Act identifier pattern; length expanded for schema validation |
| `act_type` | `SLICE_RESOURCE_ALLOCATION` | Listed in the draft Candidate Act enum/example |
| network function | `ai-ran-controller-7` | Draft example initiator |
| function type | `AI_RAN_CONTROLLER` | Draft enum/example |
| agent | `ran-agent-7` | Draft complete example |
| model | `traffic-optimizer-v5` | Draft complete example |
| PLMN | `00101` | Draft complete example |
| network domain | `ran-domain-2` | Draft example |
| slice | `slice-17` | Draft example |
| cell | `cell-108` | Draft AI-RAN scenario |
| jurisdiction | `IN` | Draft example |
| subscriber scope | `TENANT / tenant-A` | Draft example |
| purpose | `latency-optimization` | Draft example |
| effect type | `ALLOCATE_CAPACITY` | Draft authority/effect example |
| added capacity | `12%` | Draft proposed effect example |
| duration | `120 s` | Draft example |
| policy epoch | `42` | Draft example |
| authority epoch | `8` | Draft example |
| revocation epoch | `7` | Draft example |
| topology epoch | `993` | Draft validation/authority example |
| configuration epoch | `771` | Draft validation/authority example |
| nonce | `C3929177AA801C55` | Draft example |
| sequence | `8821` | Draft complete example |
| sink | `ran-finality-sink-04` | Draft example |
| sink type | `RAN_CONTROL` | Draft sink-verification example |
| protected-state ref | `net-ped-state-7801` | Draft example |
| starting monotonic counter | `184991` | Draft example |
| authority TTL | `4 seconds` | Mirrors the draft authority example's 4-second lifetime |

### Reference-implementation choices

These are engineering choices used to make the architecture runnable; they are **not normative protocol requirements**:

- Python 3.11+.
- Pydantic for strict runtime models.
- SHA-256 as the default canonical object digest.
- Ed25519 as the default authority signature.
- In-memory lock for the demonstration effect boundary.
- Hash-chained evidence records.
- SQLite as an optional persistence backend.
- Five-second default Candidate Act lifetime for the CLI demo.
- Four-second default finality-authority lifetime.
- Exact set equality for demo resource IDs.
- Default allowlist containing the single demonstration jurisdiction and sink.

Production profiles can replace these choices while preserving the protocol invariant.

---

## 5. Candidate Act binding

A Candidate Act is fully serializable and contains the load-bearing inputs required by the network profile:

```json
{
  "candidate_act_id": "...",
  "act_type": "SLICE_RESOURCE_ALLOCATION",
  "initiator": { "network_function_id": "...", "function_type": "AI_RAN_CONTROLLER" },
  "network_context": { "plmn_id": "00101", "jurisdiction": "IN" },
  "resource_scope": { "resource_type": "SLICE", "resource_ids": ["slice-17"] },
  "purpose": { "purpose_id": "latency-optimization" },
  "requested_effect": {
    "effect_type": "ALLOCATE_CAPACITY",
    "parameters_digest": { "algorithm": "SHA-256", "value": "..." }
  },
  "policy_state": { "policy_epoch": 42, "authority_epoch": 8, "revocation_epoch": 7 },
  "freshness": { "nonce": "C3929177AA801C55", "sequence": 8821 },
  "finality_sink": { "sink_id": "ran-finality-sink-04", "sink_type": "RAN_CONTROL" }
}
```

The whole Candidate Act is canonicalized and hashed. If a load-bearing field is changed after authority issuance, the sink obtains a different digest and denies the act.

The actual proposed effect parameters are separately canonicalized at the sink. This prevents an implementation from presenting a legitimate Candidate Act while substituting broader parameters at the effectuation boundary.

---

## 6. Evidence before authority

The PED does not return a usable authority immediately after a Boolean policy result.

The sequence is:

```text
validate candidate
      |
      +-- DENY --> commit denial evidence --> no authority
      |
      `-- ALLOW
           |
           v
     advance protected counter
           |
           v
     commit validation evidence
           |
           v
     construct bounded authority
           |
           v
     sign authority
           |
           v
     install sink-local activation state
           |
           v
     release authority to caller
```

The in-memory and SQLite evidence stores form a simple previous-digest chain to make ordering visible in the reference code. This is a **demonstration of evidence-gated progression**, not a claim that a normal SQLite database is equivalent to an HSM, TEE, sealed monotonic store, or external ledger.

---

## 7. How “non-bearer” is demonstrated

A signed token can easily become bearer-style if possession of the token alone is treated as sufficient authority. This implementation therefore deliberately requires two different pieces of state:

1. **Transported signed authority envelope** — contains the act/scope/evidence/epoch/sink bindings.
2. **Sink-local activation record** — independently installed in the sink's protected state before the authority is released to the caller.

At effectuation time the sink verifies both. The activation record is bound to:

- authority ID,
- full authority digest,
- Candidate Act digest,
- sink ID,
- nonce,
- activation commitment,
- expiration,
- consumption state.

Copying the authority envelope to another sink therefore fails. Removing the sink-local record also fails. Replaying a consumed authority fails.

This is still a software reference pattern. A production non-bearer implementation could use an HSM object, enclave-resident state, SmartNIC/DPU capability state, protected kernel object, confidential-computing state, secure counter, channel-bound key, or another protected representation.

---

## 8. Independent Finality Sink checks

The Finality Sink does not trust the prior PED decision as sufficient. It re-checks the following immediately before the demo consequence:

- signing key identifier and algorithm,
- authority signature,
- authority expiration,
- exact Candidate Act digest,
- Candidate Act ID,
- protected evidence presence and digest,
- evidence decision state,
- sink-local activation record,
- activation commitment,
- prior consumption state,
- sink identity,
- protected-state reference,
- topology epoch,
- configuration epoch,
- policy epoch,
- authority epoch,
- revocation epoch,
- nonce,
- sequence,
- act type,
- resource type and resource IDs,
- subscriber scope,
- purpose,
- jurisdiction,
- permitted effect type,
- recomputed effect-parameter digest,
- maximum duration.

Only after those checks pass does the sink atomically consume the single-use activation state and mutate `DemoNetwork`.

---

## 9. Telecom variations included

The test suite exercises multiple Candidate Act / sink combinations to show that the architecture is not hard-coded only to one slice-allocation example.

Examples include:

| Candidate Act | Initiator | Resource | Example sink |
|---|---|---|---|
| `SLICE_RESOURCE_ALLOCATION` | AI-RAN controller | Slice | `RAN_CONTROL` |
| `RAN_PARAMETER_CHANGE` | RIC xApp | Cell | `O_RAN_E2` |
| `NETWORK_API_INVOCATION` | Network API client | Network API | `NETWORK_API_GATEWAY` |
| `UPF_RULE_CHANGE` | UPF controller | UPF rule | `UPF` |
| `SESSION_MODIFICATION` | SMF | Session | `SESSION_CONTROLLER` |
| `BEAM_CHANGE` | AI-RAN controller | Beam | `RAN_CONTROL` |
| `SENSING_OPERATION` | Edge agent | Sensing resource | `CONTROL_PLANE_GATEWAY` |
| `RF_ENABLE` | Orchestrator | Spectrum resource | `RF_ENABLE` |

The draft also permits carrier gateways, control-plane functions, signaling gateways, edge network functions, and future 6G enforcement nodes as possible Finality Sink locations. The code models the sink as a replaceable boundary rather than binding the architecture to a particular vendor or network function.

---

## 10. Signing variations

### Ed25519 — default

```bash
network-finality-demo --signing-backend ed25519
```

Properties demonstrated:

- PED retains private signing authority.
- Sink verifies with public key.
- Tampering with the signed envelope fails.
- Appropriate architectural direction where verifier components should not possess the signing key.

### HMAC-SHA256 — demonstration variation

```bash
export EF_HMAC_SECRET='replace-with-a-high-entropy-secret'
network-finality-demo --signing-backend hmac
```

HMAC is useful for demonstrating constrained deployments or symmetric protected channels, but it gives every verifier with the shared secret the ability to generate valid MACs. It should not be interpreted as equivalent to asymmetric key separation.

---

## 11. Persistence variations

### In-memory

Best for unit testing and explanation.

```bash
network-finality-demo --persistence memory
```

Limit: process restart loses replay/evidence state.

### SQLite

Useful for restart and atomic-consumption demonstrations.

```bash
network-finality-demo --persistence sqlite --state-dir .ef-state
```

Limit: ordinary SQLite is not a trusted execution environment, secure monotonic counter, HSM, or tamper-proof ledger. An administrator able to roll back or rewrite the database can violate the protected-state assumptions unless the storage is itself protected.

---

## 12. Hot-path / cold-path interpretation

The draft allows latency-sensitive classes to use local protected state, fresh nonce state, cached policy, short-lived authority, current revocation state, and a pre-bound sink while still requiring sink verification.

This repository implements the building blocks needed for such a local hot path:

- local policy state,
- local epoch state,
- short-lived finality authority,
- local evidence store,
- local activation/consumption store,
- no mandatory external ledger round trip,
- local cryptographic verification.

It does **not** pretend that all telecom consequences should use the same path. A production deployment should escalate high-risk or uncertain operations—such as cross-jurisdiction export, RF emission, high-consequence infrastructure changes, unknown tools, uncertain policy, or unavailable revocation state—to a stronger/cold path.

The fail-closed invariant remains the same: hot-path uncertainty does not become default permission.

---

## 13. Failure behavior demonstrated

The CLI and tests cover failure classes corresponding to the draft's suggested `EF-xxx` identifiers, including:

- `EF-002` no finality authority,
- `EF-003` invalid/tampered authority,
- `EF-004` stale authority,
- `EF-005` already-used authority,
- `EF-006` replay detected,
- `EF-007` nonce/freshness failure,
- `EF-010` act mismatch,
- `EF-011` descriptor/parameter-digest mismatch,
- `EF-012` scope mismatch,
- `EF-013` purpose mismatch,
- `EF-014` consequence/effect class mismatch,
- `EF-021` jurisdiction mismatch,
- `EF-030` policy epoch mismatch,
- `EF-031` revocation mismatch,
- `EF-032` protected-state/authority-epoch mismatch,
- `EF-033` topology/configuration mismatch,
- `EF-040` sink mismatch,
- `EF-050` attestation failure,
- `EF-063` unresolved jurisdiction,
- `EF-080` fail-closed fallback / missing required protected state.

These symbolic identifiers are implementation-facing examples and are not IANA assignments.

---

## 14. Test coverage

The packaged test suite contains **79 tests**.

Coverage includes:

- successful end-to-end effectuation,
- evidence-before-authority ordering,
- act/sink/nonce/epoch/network-state binding,
- single-use authority,
- eight telecom act/sink variations,
- missing authority,
- replay after success,
- concurrent replay race (only one effect is permitted),
- topology change,
- configuration change,
- policy change,
- authority-epoch change,
- revocation change,
- protected-state substitution,
- Candidate Act substitution,
- resource substitution,
- effect-type substitution,
- parameter substitution,
- forged parameter digest,
- duration escalation,
- sink substitution,
- signature-envelope tampering,
- signature bytes tampering,
- wrong verification key,
- missing validation evidence,
- missing sink activation state,
- expired authority,
- expired Candidate Act,
- stale policy/revocation/authority epochs at PED,
- unauthorized sink,
- disallowed and unresolved jurisdiction,
- disallowed purpose,
- mandatory attestation failure/success,
- duplicate Candidate Act nonce,
- denial evidence,
- Ed25519 backend,
- HMAC backend,
- SQLite evidence/activation state,
- replay state surviving store re-open,
- multiple TTL values,
- multiple subscriber-scope types,
- proof that PED approval alone creates no network effect,
- proof that a failed sink attempt does not consume a still-valid authority,
- evidence hash-chain progression,
- canonical JSON order stability,
- schema strictness and timestamp validation.

Run:

```bash
pytest -q
```

---

## 15. Benchmark harness

Run:

```bash
python scripts/benchmark.py --iterations 1000
```

The script measures local Python reference-path latency for:

- Candidate Act creation and hashing,
- PED validation/evidence/authority issuance,
- Finality Sink verification and demo effectuation,
- total end-to-end reference path.

The benchmark is intentionally local and synthetic. It is useful for detecting regressions in the reference code. It is **not** a carrier-grade throughput result and must not be quoted as 5G/6G line-rate performance.

---

## 16. Environment configuration

A sample file is included as `.env.example`.

| Environment variable | Default | Meaning |
|---|---|---|
| `EF_SIGNING_BACKEND` | `ed25519` | `ed25519` or `hmac` |
| `EF_PERSISTENCE` | `memory` | `memory` or `sqlite` |
| `EF_STATE_DIR` | `.ef-state` | SQLite storage directory |
| `EF_AUTHORITY_TTL_SECONDS` | `4` | maximum demo authority lifetime |
| `EF_REQUIRE_ATTESTATION` | `false` | require runtime attestation field in Candidate Act |
| `EF_HMAC_SECRET` | demo fallback | shared secret only when HMAC backend is selected |

No environment option bypasses Finality Sink verification.

---

## 17. Repository layout

```text
.
├── README.md
├── NOTICE.md
├── pyproject.toml
├── requirements.txt
├── requirements-dev.txt
├── Dockerfile
├── Makefile
├── .env.example
├── .github/workflows/test.yml
├── draft/
│   └── draft-das-ai-native-6g-execution-finality-01.xml
├── schemas/
│   ├── draft-network-candidate-act.schema.json
│   └── implementation-network-candidate-act.schema.json
├── examples/
│   ├── candidate-act.json
│   ├── proposed-effect.json
│   ├── allow-trace.json
│   └── deterministic-digest-vector.json
├── docs/
│   ├── ARCHITECTURE.md
│   ├── PARAMETER-MAPPING.md
│   ├── VARIATIONS.md
│   ├── LIMITATIONS.md
│   ├── SECURITY.md
│   ├── TEST-MATRIX.md
│   └── DEPLOYMENT.md
├── scripts/
│   ├── benchmark.py
│   └── generate_examples.py
├── src/network_finality/
│   ├── models.py
│   ├── canonical.py
│   ├── crypto.py
│   ├── evidence.py
│   ├── state.py
│   ├── policy.py
│   ├── authority.py
│   ├── ped.py
│   ├── sink.py
│   ├── network.py
│   ├── engine.py
│   └── cli.py
└── tests/
```

---

## 18. What this implementation does **not** claim

This section is deliberately explicit.

### No standards conformance claim

This code is inspired by and intended to make the accompanying Internet-Draft mechanically understandable. It is not an IETF standard, not a 3GPP release artifact, and not an O-RAN conformance profile.

### No replacement for 3GPP / O-RAN security

The architecture is an additional pre-effectuation control. It can consume identity, SBA authorization, policy, CAPIF/NEF, A1/E2, attestation, RBAC, OAuth, risk, or human-approval decisions as inputs. It does not replace those systems.

### No real TEE/HSM/PED hardware

The Python PED is a logical protected-domain reference. Process memory is not a TEE. SQLite is not sealed monotonic storage. Production implementations need an actual trust boundary appropriate to the consequence class.

### No real carrier Finality Sink

`DemoNetwork` is an in-memory consequence surface. A real Finality Sink must be positioned so the protected network consequence is technically non-completable through another path.

### No alternate-path proof

The repository demonstrates one controlled consequence path. It cannot prove that a real deployment has no bypass through another API, plugin, network function, debug path, privileged operator interface, or hardware path. Deployment architecture must close every path capable of producing the same protected consequence.

### No remote-attestation verifier

The Candidate Act can require and bind a runtime-attestation digest, but this repository does not validate a real TPM/TEE/GPU/CCA/SEV-SNP/TDX attestation evidence chain.

### No full 3GPP/O-RAN interface binding

There is no live N2/N3/N4/SBI/E2/A1/CAPIF/NEF integration. The draft states that the semantic objects can be carried over different protected transports; this implementation focuses on the semantic/finality layer.

### No distributed consensus

The reference stores are local. Multi-site replication, quorum state, split-brain handling, Byzantine fault tolerance, and inter-operator federation are outside the implementation.

### No external ledger requirement

The reference does not require blockchain or remote ledger round trips. The evidence chain is local. A production profile may externally anchor evidence if desired, but later anchoring must not be confused with prior authorization.

### No formal verification

The tests exercise many failure paths but do not constitute a mathematical proof of non-bypassability or protocol correctness.

### No carrier-grade performance claim

The benchmark measures Python on one host. It does not model RAN scheduler timing, DPU/SmartNIC pipelines, UPF packet rate, distributed control-plane RTT, enclave transitions, HSM latency, or inter-operator links.

### No universal policy model

The included policy is intentionally narrow. Real deployments need operator/regulatory policy compilers, jurisdiction resolution, subscriber controls, resource envelopes, risk classes, and possibly emergency overrides.

### No patent-license statement

The draft includes an IPR note concerning pending applications in the DAS Protocols family. This repository does not define additional patent licensing terms. See `NOTICE.md`.

---

## 19. Production adaptation points

The architecture is designed so major demo components can be replaced independently:

| Reference component | Possible production replacement |
|---|---|
| `Ed25519Signer` | HSM/KMS/TEE signing key, operator PKI |
| `InMemoryEvidenceStore` | enclave-sealed log, HSM state, append-only transparency system |
| `SQLiteEvidenceStore` | protected replicated database, hardware-backed monotonic log |
| `InMemoryActivationStore` | kernel object, DPU/SmartNIC state, HSM object, secure enclave state |
| `TelecomPolicy` | PCF/operator policy engine, regulatory policy, risk engine |
| `ProtectedNetworkState` | protected topology/configuration/revocation state feed |
| `DemoNetwork.apply()` | UPF mutation, E2 actuation, session state change, RF gate, API consequence |
| in-process call | mTLS/HTTPS, local IPC, SBA transport, O-RAN control integration |

The critical requirement is not the class name. It is preservation of the ordering and non-completability invariant.

---

## 20. Security review questions for implementers

Before treating a deployment as an execution-finality boundary, answer at least these questions:

1. Can the same protected consequence be triggered through a path that does not call the Finality Sink?
2. Can a privileged process directly mutate the protected resource after the sink denies it?
3. Can consumed-state or epoch state be rolled back?
4. Can a copied authority be used at another sink?
5. Can an authority be reused after revocation or topology change?
6. Is the exact effect parameter set recomputed at the last boundary?
7. Is the signer separated from verifiers?
8. Can a timeout, policy outage, cache miss, or revocation outage accidentally turn into allow?
9. Is authority consumption atomic with the real consequence?
10. If effectuation fails halfway, are replay and recovery semantics defined?
11. Is the Candidate Act digest canonical across languages/implementations?
12. Are time, nonce, sequence, and epoch sources trustworthy?
13. Is attestation fresh and bound to the relevant runtime when attestation is required?
14. Are cross-jurisdiction and subscriber-scope transitions represented before effectuation?
15. Does a hot-path cache preserve current revocation and sink binding?

If the answer to the first question is “yes,” then the deployment does not yet have a complete Finality Sink for that consequence.

---

## 21. Relationship to the accompanying Internet-Draft

The draft explains why authentication of an AI controller or network function is different from authority for one exact live-network consequence. The repository turns that semantic distinction into executable code.

The implementation intentionally preserves these draft principles:

- **network authentication is not network finality**;
- **computation is not authority**;
- Candidate Acts can be fully computed while remaining non-effective;
- validation success alone does not create external consequence;
- protected evidence precedes or is atomic with authority release;
- authority is scoped and non-bearer rather than universal bearer permission;
- the sink re-verifies independently at the consequence boundary;
- replay/revocation/current-state checks occur at the sink;
- failure leaves the protected consequence non-effective;
- existing 3GPP/O-RAN/access-control systems remain useful inputs rather than being replaced.

For the full protocol text, see:

```text
draft/draft-das-ai-native-6g-execution-finality-01.xml
```

---

## 22. Suggested GitHub short description

**Runnable vendor-neutral reference implementation of act-bound, sink-verified execution finality for AI-native 5G/6G, AI-RAN and O-RAN, with protected evidence, non-bearer authority, replay/epoch controls, telecom variations, 79 tests and benchmark tooling.**
