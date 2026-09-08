from __future__ import annotations

from dataclasses import dataclass


FAILURE_CODES = {
    "MALFORMED_ACT": "EF-001",
    "NO_FINALITY_AUTHORITY": "EF-002",
    "INVALID_AUTHORITY": "EF-003",
    "STALE_AUTHORITY": "EF-004",
    "AUTHORITY_ALREADY_USED": "EF-005",
    "REPLAY_DETECTED": "EF-006",
    "NONCE_FAILURE": "EF-007",
    "ACT_MISMATCH": "EF-010",
    "DESCRIPTOR_MISMATCH": "EF-011",
    "SCOPE_MISMATCH": "EF-012",
    "PURPOSE_MISMATCH": "EF-013",
    "CONSEQUENCE_CLASS_MISMATCH": "EF-014",
    "DESTINATION_MISMATCH": "EF-020",
    "JURISDICTION_MISMATCH": "EF-021",
    "DATA_RESIDENCY_MISMATCH": "EF-022",
    "PRECISION_MISMATCH": "EF-023",
    "POLICY_EPOCH_MISMATCH": "EF-030",
    "REVOCATION_STATE_MISMATCH": "EF-031",
    "PROTECTED_STATE_MISMATCH": "EF-032",
    "NETWORK_STATE_MISMATCH": "EF-033",
    "SINK_MISMATCH": "EF-040",
    "EFFECTUATION_BOUNDARY_MISMATCH": "EF-041",
    "ATTESTATION_FAILURE": "EF-050",
    "VALIDATION_TIMEOUT": "EF-060",
    "AUTHORITY_UNCERTAIN": "EF-061",
    "POLICY_UNAVAILABLE": "EF-062",
    "JURISDICTION_UNRESOLVED": "EF-063",
    "ESCALATION_REQUIRED": "EF-070",
    "FAIL_CLOSED": "EF-080",
    "EVIDENCE_MISSING": "EF-080",
    "ACTIVATION_MISSING": "EF-080",
}


def code(name: str) -> str:
    return FAILURE_CODES.get(name, "EF-080")


@dataclass(frozen=True)
class Denial:
    reason: str
    message: str

    @property
    def code(self) -> str:
        return code(self.reason)
