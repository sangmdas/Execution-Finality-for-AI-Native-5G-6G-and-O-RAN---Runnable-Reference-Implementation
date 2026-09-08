# Test Matrix

Current packaged result: **79 passed**.

Run with:

```bash
pytest -q
```

Major groups:

- happy path and binding assertions,
- telecom act/sink variations,
- sink fail-closed checks,
- PED denial checks,
- replay and concurrency,
- Ed25519/HMAC cryptography,
- memory/SQLite persistence,
- scope and TTL variations,
- evidence ordering/chain behavior,
- canonical serialization,
- strict model validation.

The tests are designed to make failures observable as **absence of network effect**, not merely log messages.
