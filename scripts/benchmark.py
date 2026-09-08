from __future__ import annotations

import argparse
import statistics
import time
from datetime import datetime, timezone

from network_finality.engine import build_reference_system, make_candidate, make_effect


def pct(values, p):
    if not values:
        return 0.0
    s = sorted(values)
    idx = min(len(s) - 1, max(0, int(round((p / 100) * (len(s) - 1)))))
    return s[idx]


def us(seconds):
    return seconds * 1_000_000


def main() -> int:
    parser = argparse.ArgumentParser(description="Local synthetic benchmark for the reference implementation")
    parser.add_argument("--iterations", type=int, default=1000)
    parser.add_argument("--signing-backend", choices=["ed25519", "hmac"], default="ed25519")
    args = parser.parse_args()

    system = build_reference_system(signing_backend=args.signing_backend)
    ped_times = []
    sink_times = []
    total_times = []

    for i in range(args.iterations):
        candidate = make_candidate(
            candidate_act_id=f"bench-candidate-{i:08d}",
            nonce=f"BENCHNONCE{i:010d}",
            sequence=i,
            now=datetime.now(timezone.utc),
        )
        effect = make_effect(candidate)
        t0 = time.perf_counter()
        p0 = time.perf_counter()
        issued = system.ped.validate_and_issue(candidate)
        p1 = time.perf_counter()
        if issued.authority is None:
            raise RuntimeError("benchmark Candidate Act was unexpectedly denied")
        s0 = time.perf_counter()
        result = system.sink.verify_and_effectuate(
            request_id=f"bench-{i}", candidate=candidate, authority=issued.authority, proposed_effect=effect
        )
        s1 = time.perf_counter()
        if not result.effectuation_permitted:
            raise RuntimeError(f"benchmark sink denied: {result.code} {result.message}")
        t1 = time.perf_counter()
        ped_times.append(p1 - p0)
        sink_times.append(s1 - s0)
        total_times.append(t1 - t0)

    def row(name, vals):
        return {
            "name": name,
            "mean_us": us(statistics.mean(vals)),
            "p50_us": us(pct(vals, 50)),
            "p95_us": us(pct(vals, 95)),
            "p99_us": us(pct(vals, 99)),
        }

    print(f"iterations={args.iterations} backend={args.signing_backend}")
    for r in [row("PED", ped_times), row("Sink", sink_times), row("End-to-end", total_times)]:
        print(f"{r['name']:12s} mean={r['mean_us']:.1f}us p50={r['p50_us']:.1f}us p95={r['p95_us']:.1f}us p99={r['p99_us']:.1f}us")
    print("NOTE: local Python synthetic benchmark only; not a carrier line-rate or standards performance claim.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
