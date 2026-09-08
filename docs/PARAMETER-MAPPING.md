# Parameter Mapping

This document distinguishes values copied/adapted from the draft's JSON examples from values selected only to make the reference implementation runnable.

## Candidate Act fields

| Field | Example | Origin / rationale |
|---|---|---|
| `version` | `1.0` | Draft JSON profile |
| `object_type` | `network_candidate_act` | Draft JSON profile |
| `candidate_act_id` | `net-39f8820b-reference` | Draft pattern, expanded to satisfy minimum length |
| `act_type` | `SLICE_RESOURCE_ALLOCATION` | Draft enum/example |
| `created_at`, `expires_at` | runtime UTC timestamps | Required by draft schema; runtime-generated |
| `network_function_id` | `ai-ran-controller-7` | Draft complete example |
| `function_type` | `AI_RAN_CONTROLLER` | Draft enum/example |
| `agent_id` | `ran-agent-7` | Draft complete example |
| `model_id` | `traffic-optimizer-v5` | Draft complete example |
| `runtime_attestation_digest` | optional | Draft schema field; not validated cryptographically here |
| `plmn_id` | `00101` | Draft complete example |
| `network_domain` | `ran-domain-2` | Draft example |
| `slice_id` | `slice-17` | Draft example |
| `cell_ids` | `cell-108` | Draft scenario |
| `jurisdiction` | `IN` | Draft example |
| `resource_type` | `SLICE` | Draft example |
| `resource_ids` | `slice-17` | Draft example |
| subscriber scope | `TENANT / tenant-A` | Draft example |
| purpose | `latency-optimization` | Draft example |
| effect | `ALLOCATE_CAPACITY` | Draft example |
| duration | 120 s | Draft example |
| policy epoch | 42 | Draft example |
| authority epoch | 8 | Draft example |
| revocation epoch | 7 | Draft example |
| nonce | `C3929177AA801C55` | Draft example |
| sequence | 8821 | Draft complete example |
| sink | `ran-finality-sink-04` | Draft example |
| sink type | `RAN_CONTROL` | Draft example |

## Protected/network state fields

| Field | Default | Origin / rationale |
|---|---:|---|
| topology epoch | 993 | Draft example |
| configuration epoch | 771 | Draft example |
| protected state reference | `net-ped-state-7801` | Draft example |
| monotonic counter | 184991 | Draft example start value |
| authority TTL | 4 s | Mirrors draft authority lifetime example |

## Pure implementation choices

- Ed25519 signer/verifier classes.
- HMAC backend variation.
- Pydantic validation.
- Canonical JSON serialization details.
- Hash-chain evidence implementation.
- SQLite schema and WAL mode.
- Python locks for atomic demo state.
- Exact demo policy allowlists.
- CLI flags and environment-variable names.
