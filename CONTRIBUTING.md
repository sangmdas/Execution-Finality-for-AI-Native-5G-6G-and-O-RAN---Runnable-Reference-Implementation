# Contributing

Contributions should preserve the central execution-finality invariant: protected consequences must not become effective when required finality state is absent, stale, mismatched, replayed, revoked, uncertain, or bound to another sink.

For behavioral changes:

1. add or update tests;
2. include at least one denial-path test when a new load-bearing field is introduced;
3. do not add default-allow fallbacks for timeouts, missing policy, missing evidence, or missing protected state;
4. document whether the change is derived from the Internet-Draft or is an implementation choice;
5. avoid claims of IETF, 3GPP, O-RAN, or IMT-2030 conformance unless a separate formal conformance profile exists.

Run before submitting:

```bash
pytest -q
python scripts/benchmark.py --iterations 100
```
