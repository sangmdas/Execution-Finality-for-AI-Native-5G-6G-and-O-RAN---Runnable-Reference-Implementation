from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from .errors import Denial
from .models import NetworkCandidateAct
from .state import ProtectedNetworkState


@dataclass
class PolicyConfig:
    max_candidate_age_seconds: float = 5.0
    max_effect_duration_seconds: int = 300
    authority_ttl_seconds: float = 4.0
    require_attestation: bool = False
    allowed_act_types: set[str] = field(default_factory=set)


class TelecomPolicy:
    def __init__(self, config: PolicyConfig | None = None) -> None:
        self.config = config or PolicyConfig()

    def validate(self, candidate: NetworkCandidateAct, state: ProtectedNetworkState,
                 now: datetime) -> Denial | None:
        now = now.astimezone(timezone.utc)
        if now < candidate.created_at:
            return Denial("MALFORMED_ACT", "candidate created_at is in the future")
        if now >= candidate.expires_at:
            return Denial("STALE_AUTHORITY", "candidate act is expired")
        if (now - candidate.created_at).total_seconds() > self.config.max_candidate_age_seconds:
            return Denial("NONCE_FAILURE", "candidate act freshness window exceeded")
        if candidate.policy_state.policy_epoch != state.policy_epoch:
            return Denial("POLICY_EPOCH_MISMATCH", "policy epoch is not current")
        if candidate.policy_state.authority_epoch != state.authority_epoch:
            return Denial("PROTECTED_STATE_MISMATCH", "authority epoch is not current")
        if candidate.policy_state.revocation_epoch != state.revocation_epoch:
            return Denial("REVOCATION_STATE_MISMATCH", "revocation epoch is not current")
        if candidate.finality_sink.sink_id not in state.allowed_sink_ids:
            return Denial("SINK_MISMATCH", "candidate targets an unauthorized finality sink")
        jurisdiction = candidate.network_context.jurisdiction
        if not jurisdiction:
            return Denial("JURISDICTION_UNRESOLVED", "jurisdiction is required by this demo policy")
        if state.allowed_jurisdictions and jurisdiction not in state.allowed_jurisdictions:
            return Denial("JURISDICTION_MISMATCH", "jurisdiction is outside the permitted set")
        if state.allowed_purposes and candidate.purpose.purpose_id not in state.allowed_purposes:
            return Denial("PURPOSE_MISMATCH", "purpose is outside the permitted set")
        required_attestation = self.config.require_attestation or state.require_attestation
        if required_attestation and not candidate.initiator.runtime_attestation_digest:
            return Denial("ATTESTATION_FAILURE", "runtime attestation is required")
        if self.config.allowed_act_types and candidate.act_type.value not in self.config.allowed_act_types:
            return Denial("CONSEQUENCE_CLASS_MISMATCH", "act type is not enabled by policy")
        duration = candidate.requested_effect.duration_seconds
        if duration is not None and duration > self.config.max_effect_duration_seconds:
            return Denial("SCOPE_MISMATCH", "requested duration exceeds policy envelope")
        if not candidate.resource_scope.resource_ids:
            return Denial("SCOPE_MISMATCH", "resource scope is empty")
        return None
