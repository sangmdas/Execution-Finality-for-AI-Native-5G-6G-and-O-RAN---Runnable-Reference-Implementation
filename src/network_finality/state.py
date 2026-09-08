from __future__ import annotations

import json
import sqlite3
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol


@dataclass
class ProtectedNetworkState:
    policy_epoch: int = 42
    authority_epoch: int = 8
    revocation_epoch: int = 7
    topology_epoch: int = 993
    configuration_epoch: int = 771
    protected_state_reference: str = "net-ped-state-7801"
    monotonic_counter: int = 184991
    allowed_sink_ids: set[str] = field(default_factory=lambda: {"ran-finality-sink-04"})
    allowed_jurisdictions: set[str] = field(default_factory=lambda: {"IN"})
    allowed_purposes: set[str] = field(default_factory=lambda: {"latency-optimization", "congestion-optimization"})
    require_attestation: bool = False

    def advance_counter(self) -> int:
        self.monotonic_counter += 1
        return self.monotonic_counter


@dataclass(frozen=True)
class ActivationRecord:
    authority_id: str
    authority_digest: str
    candidate_digest: str
    sink_id: str
    nonce: str
    activation_commitment: str
    expires_at: datetime
    used: bool = False


class ActivationStore(Protocol):
    def put(self, record: ActivationRecord) -> None: ...
    def get(self, authority_id: str) -> ActivationRecord | None: ...
    def consume(self, authority_id: str) -> bool: ...
    def is_used(self, authority_id: str) -> bool: ...


class InMemoryActivationStore:
    def __init__(self) -> None:
        self._records: dict[str, ActivationRecord] = {}
        self._used: set[str] = set()
        self._lock = threading.RLock()

    def put(self, record: ActivationRecord) -> None:
        with self._lock:
            if record.authority_id in self._records:
                raise ValueError("activation already exists")
            self._records[record.authority_id] = record

    def get(self, authority_id: str) -> ActivationRecord | None:
        with self._lock:
            return self._records.get(authority_id)

    def consume(self, authority_id: str) -> bool:
        with self._lock:
            if authority_id not in self._records or authority_id in self._used:
                return False
            self._used.add(authority_id)
            return True

    def unconsume(self, authority_id: str) -> None:
        with self._lock:
            self._used.discard(authority_id)

    def is_used(self, authority_id: str) -> bool:
        with self._lock:
            return authority_id in self._used


class SQLiteActivationStore:
    """Durable demo store. It is not a tamper-resistant protected-state implementation."""

    def __init__(self, path: str | Path) -> None:
        self.path = str(path)
        self._lock = threading.RLock()
        with self._connect() as db:
            db.execute(
                """CREATE TABLE IF NOT EXISTS activations (
                    authority_id TEXT PRIMARY KEY,
                    authority_digest TEXT NOT NULL,
                    candidate_digest TEXT NOT NULL,
                    sink_id TEXT NOT NULL,
                    nonce TEXT NOT NULL,
                    activation_commitment TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    used INTEGER NOT NULL DEFAULT 0
                )"""
            )

    def _connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.path, timeout=5, isolation_level=None)
        db.execute("PRAGMA journal_mode=WAL")
        return db

    def put(self, record: ActivationRecord) -> None:
        with self._lock, self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute(
                "INSERT INTO activations VALUES (?, ?, ?, ?, ?, ?, ?, 0)",
                (
                    record.authority_id,
                    record.authority_digest,
                    record.candidate_digest,
                    record.sink_id,
                    record.nonce,
                    record.activation_commitment,
                    record.expires_at.astimezone(timezone.utc).isoformat(),
                ),
            )
            db.commit()

    def get(self, authority_id: str) -> ActivationRecord | None:
        with self._connect() as db:
            row = db.execute(
                "SELECT authority_id, authority_digest, candidate_digest, sink_id, nonce, activation_commitment, expires_at, used FROM activations WHERE authority_id=?",
                (authority_id,),
            ).fetchone()
        if not row:
            return None
        return ActivationRecord(
            authority_id=row[0], authority_digest=row[1], candidate_digest=row[2],
            sink_id=row[3], nonce=row[4], activation_commitment=row[5],
            expires_at=datetime.fromisoformat(row[6]), used=bool(row[7])
        )

    def consume(self, authority_id: str) -> bool:
        with self._lock, self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            cur = db.execute(
                "UPDATE activations SET used=1 WHERE authority_id=? AND used=0",
                (authority_id,),
            )
            db.commit()
            return cur.rowcount == 1

    def unconsume(self, authority_id: str) -> None:
        with self._lock, self._connect() as db:
            db.execute("UPDATE activations SET used=0 WHERE authority_id=?", (authority_id,))

    def is_used(self, authority_id: str) -> bool:
        r = self.get(authority_id)
        return bool(r and r.used)


class NonceRegistry:
    def __init__(self) -> None:
        self._seen: set[str] = set()
        self._lock = threading.RLock()

    def reserve(self, nonce: str) -> bool:
        with self._lock:
            if nonce in self._seen:
                return False
            self._seen.add(nonce)
            return True

    def contains(self, nonce: str) -> bool:
        with self._lock:
            return nonce in self._seen
