from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from network_finality.canonical import digest_value
from network_finality.engine import build_reference_system, make_candidate, make_effect

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "examples"
OUT.mkdir(exist_ok=True)


def write(name: str, value) -> None:
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")
    (OUT / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> None:
    fixed = datetime(2026, 8, 26, 17, 50, 0, tzinfo=timezone.utc)
    candidate = make_candidate(now=fixed, ttl_seconds=5)
    effect = make_effect(candidate)
    write("candidate-act.json", candidate)
    write("proposed-effect.json", effect)

    vector = {
        "canonicalization": "UTF-8 JSON, recursively sorted object keys, compact separators",
        "hash": "SHA-256",
        "effect_parameters": effect.parameters,
        "effect_parameters_digest_base64url": digest_value(effect.parameters),
        "candidate_act_digest_base64url": digest_value(candidate),
    }
    write("deterministic-digest-vector.json", vector)

    system = build_reference_system(signing_backend="ed25519")
    # use live time for the runnable allow trace
    live_candidate = make_candidate(candidate_act_id="net-example-live-0001", nonce="LIVEEXAMPLE00000001")
    live_effect = make_effect(live_candidate)
    ped = system.ped.validate_and_issue(live_candidate)
    sink = system.sink.verify_and_effectuate(
        request_id="net-verify-example",
        candidate=live_candidate,
        authority=ped.authority,
        proposed_effect=live_effect,
    )
    trace = {
        "candidate": live_candidate.model_dump(mode="json"),
        "ped_decision": ped.decision.model_dump(mode="json"),
        "authority": ped.authority.model_dump(mode="json") if ped.authority else None,
        "sink_result": sink.model_dump(mode="json"),
        "network_effects": system.network.effects,
    }
    write("allow-trace.json", trace)


if __name__ == "__main__":
    main()
