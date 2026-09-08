from __future__ import annotations

import threading
import uuid
from datetime import datetime, timezone
from typing import Callable

from .authority import authority_digest, unsigned_authority_payload
from .canonical import digest_value
from .crypto import Verifier
from .evidence import EvidenceStore
from .errors import code
from .models import (
    Decision,
    NetworkCandidateAct,
    NetworkFinalityAuthority,
    NetworkStateSnapshot,
    ProposedEffect,
    SinkVerifyResponse,
)
from .network import DemoNetwork
from .state import ActivationStore, ProtectedNetworkState


class NetworkFinalitySink:
    def __init__(
        self,
        *,
        sink_id: str,
        sink_type: str = "RAN_CONTROL",
        state: ProtectedNetworkState,
        verifier: Verifier,
        evidence_store: EvidenceStore,
        activation_store: ActivationStore,
        network: DemoNetwork,
        clock=lambda: datetime.now(timezone.utc),
    ) -> None:
        self.sink_id = sink_id
        self.sink_type = sink_type.value if hasattr(sink_type, "value") else str(sink_type)
        self.state = state
        self.verifier = verifier
        self.evidence_store = evidence_store
        self.activation_store = activation_store
        self.network = network
        self.clock = clock
        self._lock = threading.RLock()

    def _deny(self, request_id: str, reason: str, message: str, checks: dict[str, str] | None = None,
              authority_id: str | None = None) -> SinkVerifyResponse:
        return SinkVerifyResponse(
            request_id=request_id,
            decision=Decision.DENY,
            code=code(reason),
            verification=checks or {},
            authority_id=authority_id,
            consumed=False,
            effectuation_permitted=False,
            message=message,
        )

    def verify_and_effectuate(
        self,
        *,
        request_id: str,
        candidate: NetworkCandidateAct,
        authority: NetworkFinalityAuthority | None,
        proposed_effect: ProposedEffect,
    ) -> SinkVerifyResponse:
        now = self.clock().astimezone(timezone.utc)
        checks: dict[str, str] = {}

        if authority is None:
            return self._deny(request_id, "NO_FINALITY_AUTHORITY", "no finality authority supplied")
        if authority.issuer.key_id != self.verifier.key_id or authority.issuer.algorithm != self.verifier.algorithm:
            return self._deny(request_id, "INVALID_AUTHORITY", "unrecognized signing key or algorithm", authority_id=authority.authority_id)
        if not self.verifier.verify(unsigned_authority_payload(authority), authority.issuer.signature):
            return self._deny(request_id, "INVALID_AUTHORITY", "authority signature verification failed", authority_id=authority.authority_id)
        checks["authority_signature"] = "VALID"

        if now >= authority.lifetime.expires_at:
            return self._deny(request_id, "STALE_AUTHORITY", "authority is expired", checks, authority.authority_id)

        candidate_digest = digest_value(candidate)
        if candidate_digest != authority.binding.candidate_act_digest.value or candidate.candidate_act_id != authority.candidate_act_id:
            return self._deny(request_id, "ACT_MISMATCH", "candidate act does not match authority binding", checks, authority.authority_id)
        checks["candidate_act_binding"] = "MATCH"

        evidence = self.evidence_store.get(authority.binding.evidence_id)
        if (evidence is None or evidence.digest != authority.binding.evidence_digest.value or evidence.decision != "ALLOW"
                or evidence.candidate_act_id != candidate.candidate_act_id or evidence.decision_id != authority.decision_id):
            return self._deny(request_id, "EVIDENCE_MISSING", "protected validation evidence missing or mismatched", checks, authority.authority_id)
        checks["evidence_binding"] = "MATCH"

        activation = self.activation_store.get(authority.authority_id)
        if activation is None:
            return self._deny(request_id, "ACTIVATION_MISSING", "sink-local activation state is absent", checks, authority.authority_id)
        if now >= activation.expires_at:
            return self._deny(request_id, "STALE_AUTHORITY", "sink-local activation state is expired", checks, authority.authority_id)
        if activation.sink_id != self.sink_id:
            return self._deny(request_id, "SINK_MISMATCH", "activation state is bound to a different sink", checks, authority.authority_id)
        if activation.authority_digest != authority_digest(authority) or activation.candidate_digest != candidate_digest:
            return self._deny(request_id, "PROTECTED_STATE_MISMATCH", "sink-local activation state does not match authority", checks, authority.authority_id)
        if activation.activation_commitment != authority.binding.activation_commitment:
            return self._deny(request_id, "PROTECTED_STATE_MISMATCH", "activation commitment mismatch", checks, authority.authority_id)
        checks["activation_binding"] = "MATCH"

        if self.activation_store.is_used(authority.authority_id):
            return self._deny(request_id, "AUTHORITY_ALREADY_USED", "single-use authority has already been consumed", checks, authority.authority_id)
        checks["consumption_state"] = "UNUSED"

        if authority.binding.finality_sink_id != self.sink_id or candidate.finality_sink.sink_id != self.sink_id:
            return self._deny(request_id, "SINK_MISMATCH", "authority is bound to a different finality sink", checks, authority.authority_id)
        expected_boundary = f"boundary:{self.sink_type}:{self.sink_id}"
        if authority.binding.effectuation_boundary_id != expected_boundary or candidate.finality_sink.sink_type.value != self.sink_type:
            return self._deny(request_id, "EFFECTUATION_BOUNDARY_MISMATCH", "effectuation boundary or sink type mismatch", checks, authority.authority_id)
        checks["sink_binding"] = "MATCH"

        if authority.binding.protected_state_reference != self.state.protected_state_reference:
            return self._deny(request_id, "PROTECTED_STATE_MISMATCH", "protected state reference mismatch", checks, authority.authority_id)
        if authority.binding.topology_epoch != self.state.topology_epoch:
            return self._deny(request_id, "NETWORK_STATE_MISMATCH", "topology epoch changed after validation", checks, authority.authority_id)
        checks["topology_epoch"] = "CURRENT"
        if authority.binding.configuration_epoch != self.state.configuration_epoch:
            return self._deny(request_id, "NETWORK_STATE_MISMATCH", "configuration epoch changed after validation", checks, authority.authority_id)
        checks["configuration_epoch"] = "CURRENT"
        if authority.binding.policy_epoch != self.state.policy_epoch:
            return self._deny(request_id, "POLICY_EPOCH_MISMATCH", "policy epoch changed after validation", checks, authority.authority_id)
        checks["policy_epoch"] = "CURRENT"
        if authority.binding.authority_epoch != self.state.authority_epoch:
            return self._deny(request_id, "PROTECTED_STATE_MISMATCH", "authority epoch changed after validation", checks, authority.authority_id)
        checks["authority_epoch"] = "CURRENT"
        if authority.binding.revocation_epoch != self.state.revocation_epoch:
            return self._deny(request_id, "REVOCATION_STATE_MISMATCH", "revocation epoch changed after validation", checks, authority.authority_id)
        checks["revocation_epoch"] = "CURRENT"

        if authority.binding.nonce != candidate.freshness.nonce or activation.nonce != candidate.freshness.nonce:
            return self._deny(request_id, "NONCE_FAILURE", "nonce mismatch", checks, authority.authority_id)
        checks["nonce"] = "FRESH"
        if authority.binding.sequence != candidate.freshness.sequence:
            return self._deny(request_id, "NONCE_FAILURE", "sequence mismatch", checks, authority.authority_id)
        checks["sequence"] = "MATCH"

        if authority.scope.act_type != candidate.act_type:
            return self._deny(request_id, "CONSEQUENCE_CLASS_MISMATCH", "act type exceeds issued authority", checks, authority.authority_id)
        if authority.scope.resource_type != proposed_effect.resource_type:
            return self._deny(request_id, "SCOPE_MISMATCH", "resource type mismatch", checks, authority.authority_id)
        if set(proposed_effect.resource_ids) != set(authority.scope.resource_ids):
            return self._deny(request_id, "SCOPE_MISMATCH", "resource IDs do not match issued scope", checks, authority.authority_id)
        checks["resource_scope"] = "MATCH"
        if authority.scope.subscriber_scope != candidate.resource_scope.subscriber_scope:
            return self._deny(request_id, "SCOPE_MISMATCH", "subscriber scope changed", checks, authority.authority_id)
        checks["subscriber_scope"] = "MATCH"
        if authority.scope.purpose_id != candidate.purpose.purpose_id:
            return self._deny(request_id, "PURPOSE_MISMATCH", "purpose changed", checks, authority.authority_id)
        checks["purpose"] = "MATCH"
        if authority.scope.jurisdiction != candidate.network_context.jurisdiction:
            return self._deny(request_id, "JURISDICTION_MISMATCH", "jurisdiction changed", checks, authority.authority_id)
        if proposed_effect.effect_type != authority.scope.permitted_effect_type:
            return self._deny(request_id, "CONSEQUENCE_CLASS_MISMATCH", "effect type differs from authority", checks, authority.authority_id)

        actual_parameters_digest = digest_value(proposed_effect.parameters, proposed_effect.parameters_digest.algorithm)
        if actual_parameters_digest != proposed_effect.parameters_digest.value:
            return self._deny(request_id, "DESCRIPTOR_MISMATCH", "proposed effect parameters_digest is internally inconsistent", checks, authority.authority_id)
        if proposed_effect.parameters_digest.value != authority.scope.parameters_digest:
            return self._deny(request_id, "ACT_MISMATCH", "effect parameters differ from Candidate Act", checks, authority.authority_id)
        checks["effect_parameters"] = "MATCH"

        max_duration = authority.scope.duration_seconds_max
        if max_duration is not None and proposed_effect.duration_seconds is not None and proposed_effect.duration_seconds > max_duration:
            return self._deny(request_id, "SCOPE_MISMATCH", "effect duration exceeds authority", checks, authority.authority_id)

        # Demonstration of atomicity: the replay/consumption update and the in-memory
        # consequence mutation happen under one lock. Production systems must couple
        # consumption to the real protected effect boundary transactionally or in hardware.
        with self._lock, self.network.lock:
            if self.activation_store.is_used(authority.authority_id):
                return self._deny(request_id, "AUTHORITY_ALREADY_USED", "authority was consumed concurrently", checks, authority.authority_id)
            if not self.activation_store.consume(authority.authority_id):
                return self._deny(request_id, "AUTHORITY_ALREADY_USED", "authority could not be consumed", checks, authority.authority_id)
            try:
                effect_id = self.network.apply({
                    "candidate_act_id": candidate.candidate_act_id,
                    "authority_id": authority.authority_id,
                    "effect_type": proposed_effect.effect_type,
                    "resource_type": proposed_effect.resource_type.value,
                    "resource_ids": list(proposed_effect.resource_ids),
                    "parameters": dict(proposed_effect.parameters),
                    "duration_seconds": proposed_effect.duration_seconds,
                })
            except Exception:
                unconsume = getattr(self.activation_store, "unconsume", None)
                if unconsume:
                    unconsume(authority.authority_id)
                raise

        checks["consumption_state"] = "CONSUMED"
        return SinkVerifyResponse(
            request_id=request_id,
            decision=Decision.ALLOW,
            code="OK",
            verification=checks,
            authority_id=authority.authority_id,
            consumed=True,
            effectuation_permitted=True,
            network_effect_id=effect_id,
        )
