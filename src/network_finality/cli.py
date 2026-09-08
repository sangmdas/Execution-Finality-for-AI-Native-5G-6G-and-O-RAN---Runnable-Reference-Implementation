from __future__ import annotations

import argparse
import json
import os
from copy import deepcopy

from .engine import build_reference_system, make_candidate, make_effect


def _dump(obj) -> str:
    return json.dumps(obj.model_dump(mode="json"), indent=2, sort_keys=True)


def run_demo(args: argparse.Namespace) -> int:
    system = build_reference_system(
        signing_backend=args.signing_backend,
        persistence=args.persistence,
        state_dir=args.state_dir,
        authority_ttl_seconds=args.authority_ttl,
        require_attestation=args.require_attestation,
    )
    candidate = make_candidate(attestation_digest="sha256:demo-attestation" if args.require_attestation else None)
    effect = make_effect(candidate)

    ped_result = system.ped.validate_and_issue(candidate)
    print("=== PED DECISION ===")
    print(_dump(ped_result.decision))
    if ped_result.authority is None:
        print("No authority issued; Candidate Act remains NON-EFFECTIVE.")
        return 2

    print("\n=== FINALITY AUTHORITY ===")
    print(_dump(ped_result.authority))

    if args.simulate == "topology-change":
        system.state.topology_epoch += 1
    elif args.simulate == "revocation":
        system.state.revocation_epoch += 1
    elif args.simulate == "parameter-substitution":
        effect = make_effect(candidate, {"additional_prb_percent": 99, "duration_seconds": 120})
    elif args.simulate == "sink-substitution":
        system.sink.sink_id = "other-sink"
    elif args.simulate == "signature-tamper":
        ped_result.authority.scope.purpose_id = "tampered-purpose"

    response = system.sink.verify_and_effectuate(
        request_id="net-verify-reference",
        candidate=candidate,
        authority=ped_result.authority,
        proposed_effect=effect,
    )
    print("\n=== SINK RESULT ===")
    print(_dump(response))
    print("\n=== NETWORK EFFECT COUNT ===")
    print(len(system.network.effects))

    if args.replay and response.effectuation_permitted:
        replay = system.sink.verify_and_effectuate(
            request_id="net-verify-replay",
            candidate=candidate,
            authority=ped_result.authority,
            proposed_effect=effect,
        )
        print("\n=== REPLAY ATTEMPT ===")
        print(_dump(replay))

    return 0 if response.effectuation_permitted else 3


def main() -> int:
    parser = argparse.ArgumentParser(description="Execution-finality reference implementation demo")
    parser.add_argument("--signing-backend", choices=["ed25519", "hmac"], default=os.getenv("EF_SIGNING_BACKEND", "ed25519"))
    parser.add_argument("--persistence", choices=["memory", "sqlite"], default=os.getenv("EF_PERSISTENCE", "memory"))
    parser.add_argument("--state-dir", default=os.getenv("EF_STATE_DIR", ".ef-state"))
    parser.add_argument("--authority-ttl", type=float, default=float(os.getenv("EF_AUTHORITY_TTL_SECONDS", "4")))
    parser.add_argument("--require-attestation", action="store_true", default=os.getenv("EF_REQUIRE_ATTESTATION", "false").lower() == "true")
    parser.add_argument("--replay", action="store_true", help="attempt a second effectuation with the consumed authority")
    parser.add_argument("--simulate", choices=["none", "topology-change", "revocation", "parameter-substitution", "sink-substitution", "signature-tamper"], default="none")
    args = parser.parse_args()
    return run_demo(args)


if __name__ == "__main__":
    raise SystemExit(main())
