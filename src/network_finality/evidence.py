from __future__ import annotations

import sqlite3
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol

from .canonical import digest_value


@dataclass(frozen=True)
class EvidenceRecord:
    evidence_id: str
    candidate_act_id: str
    decision_id: str
    decision: str
    committed_at: datetime
    protected_state_reference: str
    monotonic_counter: int
    previous_digest: str
    digest: str


class EvidenceStore(Protocol):
    def commit(self, *, evidence_id: str, candidate_act_id: str, decision_id: str,
               decision: str, protected_state_reference: str,
               monotonic_counter: int, committed_at: datetime) -> EvidenceRecord: ...
    def get(self, evidence_id: str) -> EvidenceRecord | None: ...


class InMemoryEvidenceStore:
    def __init__(self) -> None:
        self._records: dict[str, EvidenceRecord] = {}
        self._tail = "GENESIS"
        self._lock = threading.RLock()

    def commit(self, **kwargs) -> EvidenceRecord:
        with self._lock:
            body = {**kwargs, "previous_digest": self._tail}
            digest = digest_value(body)
            rec = EvidenceRecord(**kwargs, previous_digest=self._tail, digest=digest)
            self._records[rec.evidence_id] = rec
            self._tail = digest
            return rec

    def get(self, evidence_id: str) -> EvidenceRecord | None:
        with self._lock:
            return self._records.get(evidence_id)


class SQLiteEvidenceStore:
    """Append-oriented demo evidence store; not a substitute for TEE/HSM/sealed/monotonic storage."""

    def __init__(self, path: str | Path) -> None:
        self.path = str(path)
        self._lock = threading.RLock()
        with self._connect() as db:
            db.execute(
                """CREATE TABLE IF NOT EXISTS evidence (
                    seq INTEGER PRIMARY KEY AUTOINCREMENT,
                    evidence_id TEXT UNIQUE NOT NULL,
                    candidate_act_id TEXT NOT NULL,
                    decision_id TEXT NOT NULL,
                    decision TEXT NOT NULL,
                    committed_at TEXT NOT NULL,
                    protected_state_reference TEXT NOT NULL,
                    monotonic_counter INTEGER NOT NULL,
                    previous_digest TEXT NOT NULL,
                    digest TEXT NOT NULL
                )"""
            )

    def _connect(self):
        db = sqlite3.connect(self.path, timeout=5, isolation_level=None)
        db.execute("PRAGMA journal_mode=WAL")
        return db

    def commit(self, **kwargs) -> EvidenceRecord:
        with self._lock, self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT digest FROM evidence ORDER BY seq DESC LIMIT 1").fetchone()
            previous = row[0] if row else "GENESIS"
            body = {**kwargs, "previous_digest": previous}
            digest = digest_value(body)
            rec = EvidenceRecord(**kwargs, previous_digest=previous, digest=digest)
            db.execute(
                "INSERT INTO evidence(evidence_id,candidate_act_id,decision_id,decision,committed_at,protected_state_reference,monotonic_counter,previous_digest,digest) VALUES (?,?,?,?,?,?,?,?,?)",
                (rec.evidence_id, rec.candidate_act_id, rec.decision_id, rec.decision,
                 rec.committed_at.astimezone(timezone.utc).isoformat(), rec.protected_state_reference,
                 rec.monotonic_counter, rec.previous_digest, rec.digest),
            )
            db.commit()
            return rec

    def get(self, evidence_id: str) -> EvidenceRecord | None:
        with self._connect() as db:
            row = db.execute(
                "SELECT evidence_id,candidate_act_id,decision_id,decision,committed_at,protected_state_reference,monotonic_counter,previous_digest,digest FROM evidence WHERE evidence_id=?",
                (evidence_id,),
            ).fetchone()
        if not row:
            return None
        return EvidenceRecord(row[0], row[1], row[2], row[3], datetime.fromisoformat(row[4]), row[5], row[6], row[7], row[8])
