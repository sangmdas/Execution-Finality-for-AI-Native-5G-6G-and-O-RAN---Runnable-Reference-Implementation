from __future__ import annotations

import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from .authority import authority_digest, unsigned_authority_payload
from .canonical import b64url, digest_value, hash_bytes
from .crypto import Signer
from .evidence import EvidenceStore
from .errors import Denial
from .models import (
    AuthorityBinding,
    AuthorityIssuer,
    AuthorityLifetime,
    AuthorityScope,
    Decision,
    Digest,
    NetworkCandidateAct,
    NetworkFinalityAuthority,
    NetworkStateSnapshot,
    NetworkValidationDecision,
    ProtectedStateSnapshot,
    ValidatedPredicates,
)
from .policy import TelecomPolicy
from .state import ActivationRecord, ActivationStore, NonceRegistry, ProtectedNetworkState


@dataclass
class PEDResult:
    decision: NetworkValidationDecision
    authority: NetworkFinalityAuthority | None


class ProtectedEnforcementDomain:
    def __init__(
        self,
        *,
        ped_id: str,
        state: ProtectedNetworkState,
        policy: TelecomPolicy,
        signer: Signer,
        evidence_store: EvidenceStore,
        activation_store: ActivationStore,
        nonce_registry: NonceRegistry | None = None,
        clock=lambda: datetime.now(timezone.utc),
    ) -> None:
        self.ped_id = ped_id
        self.state = state
        self.policy = policy
        self.signer = signer
        self.evidence_store = evidence_store
        self.activation_store = activation_store
        self.nonce_registry = nonce_registry or NonceRegistry()
        self.clock = clock

    def _decision(self, candidate: NetworkCandidateAct, denial: Denial | None, decision_id: str) -> NetworkValidationDecision:
        ok = denial is None
        preds = ValidatedPredicates(
            initiator_attested=ok or not (self.policy.config.require_attestation or self.state.require_attestation),
            resource_scope_valid=ok,
            subscriber_scope_valid=ok,
            purpose_valid=ok,
            requested_effect_valid=ok,
            operator_policy_valid=ok,
            regulatory_policy_valid=ok,
            network_state_valid=ok,
            policy_epoch_valid=ok,
            revocation_state_valid=ok,
            freshness_valid=ok,
            sink_binding_valid=ok,
        )
        return NetworkValidationDecision(
            decision_id=decision_id,
            candidate_act_id=candidate.candidate_act_id,
            decision=Decision.ALLOW if ok else Decision.DENY,
            validated_predicates=preds,
            network_state=NetworkStateSnapshot(
                topology_epoch=self.state.topology_epoch,
                configuration_epoch=self.state.configuration_epoch,
            ),
            protected_state=ProtectedStateSnapshot(
                state_reference=self.state.protected_state_reference,
                monotonic_counter=self.state.monotonic_counter,
            ),
            denial_code=denial.code if denial else None,
        )

    def validate_and_issue(self, candidate: NetworkCandidateAct) -> PEDResult:
        now = self.clock().astimezone(timezone.utc)
        decision_id = f"nvd-{uuid.uuid4().hex[:12]}"

        denial = self.policy.validate(candidate, self.state, now)
        if denial is None and not self.nonce_registry.reserve(candidate.freshness.nonce):
            denial = Denial("REPLAY_DETECTED", "candidate nonce has already been presented to the PED")

        decision = self._decision(candidate, denial, decision_id)
        counter = self.state.advance_counter()
        evidence_id = f"evidence-{uuid.uuid4().hex[:12]}"
        evidence = self.evidence_store.commit(
            evidence_id=evidence_id,
            candidate_act_id=candidate.candidate_act_id,
            decision_id=decision_id,
            decision=decision.decision.value,
            protected_state_reference=self.state.protected_state_reference,
            monotonic_counter=counter,
            committed_at=now,
        )
        decision.evidence_id = evidence.evidence_id
        decision.protected_state.monotonic_counter = counter

        if denial is not None:
            return PEDResult(decision=decision, authority=None)

        candidate_digest = digest_value(candidate)
        activation_commitment = b64url(hash_bytes(secrets.token_bytes(32)))
        ttl = min(
            self.policy.config.authority_ttl_seconds,
            max(0.0, (candidate.expires_at - now).total_seconds()),
        )
        expires_at = now + timedelta(seconds=ttl)
        authority_id = f"nfa-{uuid.uuid4().hex[:12]}"
        authority = NetworkFinalityAuthority(
            authority_id=authority_id,
            candidate_act_id=candidate.candidate_act_id,
            decision_id=decision_id,
            scope=AuthorityScope(
                act_type=candidate.act_type,
                resource_type=candidate.resource_scope.resource_type,
                resource_ids=list(candidate.resource_scope.resource_ids),
                subscriber_scope=candidate.resource_scope.subscriber_scope,
                permitted_effect_type=candidate.requested_effect.effect_type,
                parameters_digest=candidate.requested_effect.parameters_digest.value,
                duration_seconds_max=candidate.requested_effect.duration_seconds,
                network_domain=candidate.network_context.network_domain,
                jurisdiction=candidate.network_context.jurisdiction,
                purpose_id=candidate.purpose.purpose_id,
            ),
            binding=AuthorityBinding(
                candidate_act_digest=Digest(value=candidate_digest),
                evidence_id=evidence.evidence_id,
                evidence_digest=Digest(value=evidence.digest),
                protected_state_reference=self.state.protected_state_reference,
                topology_epoch=self.state.topology_epoch,
                configuration_epoch=self.state.configuration_epoch,
                policy_epoch=self.state.policy_epoch,
                authority_epoch=self.state.authority_epoch,
                revocation_epoch=self.state.revocation_epoch,
                nonce=candidate.freshness.nonce,
                sequence=candidate.freshness.sequence,
                finality_sink_id=candidate.finality_sink.sink_id,
                effectuation_boundary_id=f"boundary:{candidate.finality_sink.sink_type.value}:{candidate.finality_sink.sink_id}",
                activation_commitment=activation_commitment,
            ),
            lifetime=AuthorityLifetime(issued_at=now, expires_at=expires_at, single_use=True),
            issuer=AuthorityIssuer(
                ped_id=self.ped_id,
                key_id=self.signer.key_id,
                algorithm=self.signer.algorithm,
                signature="",
            ),
        )
        authority.issuer.signature = self.signer.sign(unsigned_authority_payload(authority))

        # The non-bearer demonstration uses sink-local protected activation state.
        # The caller receives only the signed authority envelope; the sink also has
        # to possess this independently registered record before effectuation.
        self.activation_store.put(
            ActivationRecord(
                authority_id=authority.authority_id,
                authority_digest=authority_digest(authority),
                candidate_digest=candidate_digest,
                sink_id=candidate.finality_sink.sink_id,
                nonce=candidate.freshness.nonce,
                activation_commitment=activation_commitment,
                expires_at=expires_at,
            )
        )
        return PEDResult(decision=decision, authority=authority)
