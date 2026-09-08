# Local Synthetic Benchmark

This file records one local execution of the reference benchmark after the packaged test suite passed.

Environment used for this run:

- Python: 3.13.5
- Pydantic: 2.13.4
- cryptography: 46.0.4
- pytest: 9.0.2
- signing backend: Ed25519
- persistence backend: in-memory
- benchmark iterations: 500

Observed local results:

```text
PED          mean=311.3us p50=292.8us p95=419.5us p99=568.6us
Sink         mean=339.7us p50=323.6us p95=426.5us p99=563.2us
End-to-end   mean=651.4us p50=620.4us p95=804.4us p99=989.7us
```

These figures are **not protocol requirements and not carrier-grade performance claims**. They measure a local Python process with in-memory state. They do not include network transport, TEE/HSM transitions, live O-RAN/3GPP interfaces, distributed state, SmartNIC/DPU pipelines, RAN scheduling, external attestation, or remote policy services.

Re-run locally with:

```bash
python scripts/benchmark.py --iterations 1000
```
