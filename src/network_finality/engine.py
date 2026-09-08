from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .canonical import digest_value
from .crypto import Ed25519Signer, HMACSigner
from .evidence import InMemoryEvidenceStore, SQLiteEvidenceStore
from .models import (
    ActType,
    Digest,
    FinalitySinkDescriptor,
    Freshness,
    FunctionType,
    Initiator,
    NetworkCandidateAct,
    NetworkContext,
    PolicyState,
    ProposedEffect,
    Purpose,
    RequestedEffect,
    ResourceScope,
    ResourceType,
    Reversibility,
    ScopeType,
    SinkType,
    SubscriberScope,
)
from .network import DemoNetwork
from .ped import ProtectedEnforcementDomain
from .policy import PolicyConfig, TelecomPolicy
from .sink import NetworkFinalitySink
from .state import InMemoryActivationStore, ProtectedNetworkState, SQLiteActivationStore


@dataclass
class ReferenceSystem:
    state: ProtectedNetworkState
    ped: ProtectedEnforcementDomain
    sink: NetworkFinalitySink
    network: DemoNetwork


def build_reference_system(
    *,
    signing_backend: str = "ed25519",
    persistence: str = "memory",
    state_dir: str | Path | None = None,
    authority_ttl_seconds: float = 4.0,
    require_attestation: bool = False,
    sink_id: str = "ran-finality-sink-04",
    sink_type: SinkType = SinkType.RAN_CONTROL,
) -> ReferenceSystem:
    state = ProtectedNetworkState(allowed_sink_ids={sink_id}, require_attestation=require_attestation)
    policy = TelecomPolicy(PolicyConfig(authority_ttl_seconds=authority_ttl_seconds, require_attestation=require_attestation))

    if signing_backend == "ed25519":
        signer = Ed25519Signer.generate()
    elif signing_backend == "hmac":
        secret = os.environ.get("EF_HMAC_SECRET", "demo-only-change-me-32-byte-secret!!").encode()
        signer = HMACSigner(secret)
    else:
        raise ValueError("signing_backend must be 'ed25519' or 'hmac'")

    if persistence == "memory":
        evidence = InMemoryEvidenceStore()
        activations = InMemoryActivationStore()
    elif persistence == "sqlite":
        directory = Path(state_dir or ".ef-state")
        directory.mkdir(parents=True, exist_ok=True)
        evidence = SQLiteEvidenceStore(directory / "evidence.sqlite3")
        activations = SQLiteActivationStore(directory / "activation.sqlite3")
    else:
        raise ValueError("persistence must be 'memory' or 'sqlite'")

    network = DemoNetwork()
    sink = NetworkFinalitySink(
        sink_id=sink_id,
        sink_type=sink_type,
        state=state,
        verifier=signer.verifier(),
        evidence_store=evidence,
        activation_store=activations,
        network=network,
    )
    ped = ProtectedEnforcementDomain(
        ped_id="operator-ped-1",
        state=state,
        policy=policy,
        signer=signer,
        evidence_store=evidence,
        activation_store=activations,
    )
    return ReferenceSystem(state=state, ped=ped, sink=sink, network=network)


def make_candidate(
    *,
    parameters: dict[str, Any] | None = None,
    candidate_act_id: str = "net-39f8820b-reference",
    nonce: str = "C3929177AA801C55",
    sequence: int = 8821,
    act_type: ActType = ActType.SLICE_RESOURCE_ALLOCATION,
    function_type: FunctionType = FunctionType.AI_RAN_CONTROLLER,
    resource_type: ResourceType = ResourceType.SLICE,
    resource_ids: list[str] | None = None,
    scope_type: ScopeType = ScopeType.TENANT,
    scope_reference: str = "tenant-A",
    purpose_id: str = "latency-optimization",
    effect_type: str = "ALLOCATE_CAPACITY",
    duration_seconds: int = 120,
    jurisdiction: str = "IN",
    sink_id: str = "ran-finality-sink-04",
    sink_type: SinkType = SinkType.RAN_CONTROL,
    attestation_digest: str | None = None,
    now: datetime | None = None,
    ttl_seconds: float = 5.0,
    policy_epoch: int = 42,
    authority_epoch: int = 8,
    revocation_epoch: int = 7,
) -> NetworkCandidateAct:
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    parameters = parameters or {"additional_prb_percent": 12, "duration_seconds": duration_seconds}
    return NetworkCandidateAct(
        candidate_act_id=candidate_act_id,
        act_type=act_type,
        created_at=now,
        expires_at=now + timedelta(seconds=ttl_seconds),
        initiator=Initiator(
            network_function_id="ai-ran-controller-7",
            function_type=function_type,
            agent_id="ran-agent-7",
            model_id="traffic-optimizer-v5",
            runtime_attestation_digest=attestation_digest,
        ),
        network_context=NetworkContext(
            plmn_id="00101",
            network_domain="ran-domain-2",
            slice_id="slice-17",
            cell_ids=["cell-108"],
            jurisdiction=jurisdiction,
        ),
        resource_scope=ResourceScope(
            resource_type=resource_type,
            resource_ids=resource_ids or ["slice-17"],
            subscriber_scope=SubscriberScope(scope_type=scope_type, scope_reference=scope_reference),
        ),
        purpose=Purpose(purpose_id=purpose_id, declared_purpose="Maintain bounded network objective"),
        requested_effect=RequestedEffect(
            effect_type=effect_type,
            parameters_digest=Digest(value=digest_value(parameters)),
            duration_seconds=duration_seconds,
            reversibility=Reversibility.REVERSIBLE,
        ),
        policy_state=PolicyState(
            policy_epoch=policy_epoch,
            authority_epoch=authority_epoch,
            revocation_epoch=revocation_epoch,
            operator_policy_profile="ran-autonomy-v3",
        ),
        freshness=Freshness(nonce=nonce, sequence=sequence),
        finality_sink=FinalitySinkDescriptor(sink_id=sink_id, sink_type=sink_type),
    )


def make_effect(candidate: NetworkCandidateAct, parameters: dict[str, Any] | None = None,
                *, resource_ids: list[str] | None = None, effect_type: str | None = None,
                duration_seconds: int | None = None) -> ProposedEffect:
    parameters = parameters or {"additional_prb_percent": 12, "duration_seconds": candidate.requested_effect.duration_seconds}
    return ProposedEffect(
        effect_type=effect_type or candidate.requested_effect.effect_type,
        resource_type=candidate.resource_scope.resource_type,
        resource_ids=resource_ids or list(candidate.resource_scope.resource_ids),
        parameters=parameters,
        parameters_digest=Digest(value=digest_value(parameters)),
        duration_seconds=duration_seconds if duration_seconds is not None else candidate.requested_effect.duration_seconds,
    )
