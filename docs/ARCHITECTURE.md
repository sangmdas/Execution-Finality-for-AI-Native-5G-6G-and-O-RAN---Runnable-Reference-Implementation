# Architecture

## Security boundary model

The reference implementation has two separate decision boundaries.

### Boundary 1 — Protected Enforcement Domain

The PED receives a `NetworkCandidateAct` that is still non-effective. It validates current policy and state, reserves freshness, commits protected validation evidence, constructs a scope-limited authority, signs it, and installs sink-local activation state. PED success alone does not modify `DemoNetwork`.

### Boundary 2 — Network Finality Sink

The sink independently verifies the signed authority, exact Candidate Act, protected evidence, protected activation, current epochs, current network state, scope, nonce, sink identity, and exact effect parameters. It consumes the authority only when the effect can be committed.

## Why two boundaries

A single policy engine can decide that an act is acceptable and still be separated in time, process, topology state, or trust boundary from the component that creates the real consequence. The second check closes that gap for the protected effect path.

## Non-effective state in code

There is no direct call from `ProtectedEnforcementDomain.validate_and_issue()` to `DemoNetwork.apply()`. The network object is only held by `NetworkFinalitySink`. Tests verify that an authority can exist while the network has zero effects.

## Non-bearer representation

The authority envelope is signed and portable, but the sink requires a separately installed activation record. The activation record is bound to the authority digest, Candidate Act digest, nonce, sink, expiration, and consumption state. A copied envelope without the sink-local record therefore fails closed.

## Effect-parameter binding

The Candidate Act commits to the proposed effect parameters by digest. At the sink, the parameters are canonicalized and hashed again. The recomputed digest must match both the effect request and the authority scope.

## Atomicity

The in-memory demo locks consumption and network mutation together. This is pedagogical atomicity, not a substitute for a real transaction/hardware gate at an external side-effect boundary.
