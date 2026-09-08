from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=False)


class ActType(str, Enum):
    ROUTE_CHANGE = "ROUTE_CHANGE"
    SESSION_MODIFICATION = "SESSION_MODIFICATION"
    QOS_CHANGE = "QOS_CHANGE"
    SLICE_RESOURCE_ALLOCATION = "SLICE_RESOURCE_ALLOCATION"
    RAN_PARAMETER_CHANGE = "RAN_PARAMETER_CHANGE"
    POLICY_UPDATE = "POLICY_UPDATE"
    NETWORK_API_INVOCATION = "NETWORK_API_INVOCATION"
    UPF_RULE_CHANGE = "UPF_RULE_CHANGE"
    BEAM_CHANGE = "BEAM_CHANGE"
    SENSING_OPERATION = "SENSING_OPERATION"
    RF_ENABLE = "RF_ENABLE"
    SERVICE_ACTIVATION = "SERVICE_ACTIVATION"
    OTHER = "OTHER"


class FunctionType(str, Enum):
    AI_RAN_CONTROLLER = "AI_RAN_CONTROLLER"
    RIC_XAPP = "RIC_XAPP"
    RIC_RAPP = "RIC_RAPP"
    SMF = "SMF"
    AMF = "AMF"
    PCF = "PCF"
    UPF_CONTROLLER = "UPF_CONTROLLER"
    ORCHESTRATOR = "ORCHESTRATOR"
    NETWORK_API_CLIENT = "NETWORK_API_CLIENT"
    EDGE_AGENT = "EDGE_AGENT"
    OTHER = "OTHER"


class ResourceType(str, Enum):
    SLICE = "SLICE"
    CELL = "CELL"
    QOS_FLOW = "QOS_FLOW"
    SESSION = "SESSION"
    UPF_RULE = "UPF_RULE"
    ROUTE = "ROUTE"
    SPECTRUM_RESOURCE = "SPECTRUM_RESOURCE"
    BEAM = "BEAM"
    NETWORK_API = "NETWORK_API"
    SENSING_RESOURCE = "SENSING_RESOURCE"
    OTHER = "OTHER"


class ScopeType(str, Enum):
    NONE = "NONE"
    SINGLE_SUBSCRIBER = "SINGLE_SUBSCRIBER"
    SUBSCRIBER_GROUP = "SUBSCRIBER_GROUP"
    TENANT = "TENANT"
    SLICE = "SLICE"
    CELL_POPULATION = "CELL_POPULATION"


class SinkType(str, Enum):
    UPF = "UPF"
    CONTROL_PLANE_GATEWAY = "CONTROL_PLANE_GATEWAY"
    RAN_CONTROL = "RAN_CONTROL"
    O_RAN_E2 = "O_RAN_E2"
    O_RAN_A1 = "O_RAN_A1"
    NETWORK_API_GATEWAY = "NETWORK_API_GATEWAY"
    RF_ENABLE = "RF_ENABLE"
    SESSION_CONTROLLER = "SESSION_CONTROLLER"
    OTHER = "OTHER"


class Reversibility(str, Enum):
    REVERSIBLE = "REVERSIBLE"
    PARTIALLY_REVERSIBLE = "PARTIALLY_REVERSIBLE"
    IRREVERSIBLE = "IRREVERSIBLE"


class Decision(str, Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"


class Digest(StrictModel):
    algorithm: Literal["SHA-256", "SHA-384", "SHA-512"] = "SHA-256"
    value: str = Field(min_length=8)


class Initiator(StrictModel):
    network_function_id: str = Field(min_length=1)
    function_type: FunctionType
    agent_id: str | None = None
    model_id: str | None = None
    runtime_attestation_digest: str | None = None


class NetworkContext(StrictModel):
    plmn_id: str | None = None
    network_domain: str | None = None
    slice_id: str | None = None
    cell_ids: list[str] = Field(default_factory=list)
    edge_region: str | None = None
    jurisdiction: str | None = None


class SubscriberScope(StrictModel):
    scope_type: ScopeType = ScopeType.NONE
    scope_reference: str | None = None

    @model_validator(mode="after")
    def reference_when_scoped(self) -> "SubscriberScope":
        if self.scope_type != ScopeType.NONE and not self.scope_reference:
            raise ValueError("scope_reference is required when subscriber scope is not NONE")
        return self


class ResourceScope(StrictModel):
    resource_type: ResourceType
    resource_ids: list[str] = Field(min_length=1)
    subscriber_scope: SubscriberScope = Field(default_factory=SubscriberScope)


class Purpose(StrictModel):
    purpose_id: str = Field(min_length=1)
    declared_purpose: str = Field(min_length=1)
    service_intent_reference: str | None = None
    purpose_epoch: int | None = Field(default=None, ge=0)


class RequestedEffect(StrictModel):
    effect_type: str = Field(min_length=1)
    parameters_digest: Digest
    duration_seconds: int | None = Field(default=None, ge=0)
    reversibility: Reversibility | None = None


class PolicyState(StrictModel):
    policy_epoch: int = Field(ge=0)
    authority_epoch: int = Field(ge=0)
    revocation_epoch: int = Field(ge=0)
    operator_policy_profile: str | None = None
    regulatory_profile: str | None = None


class Freshness(StrictModel):
    nonce: str = Field(min_length=16)
    sequence: int | None = Field(default=None, ge=0)
    session_id: str | None = None


class FinalitySinkDescriptor(StrictModel):
    sink_id: str = Field(min_length=1)
    sink_type: SinkType


class NetworkCandidateAct(StrictModel):
    version: Literal["1.0"] = "1.0"
    object_type: Literal["network_candidate_act"] = "network_candidate_act"
    candidate_act_id: str = Field(min_length=16)
    act_type: ActType
    created_at: datetime
    expires_at: datetime
    initiator: Initiator
    network_context: NetworkContext
    resource_scope: ResourceScope
    purpose: Purpose
    requested_effect: RequestedEffect
    policy_state: PolicyState
    freshness: Freshness
    finality_sink: FinalitySinkDescriptor

    @field_validator("created_at", "expires_at")
    @classmethod
    def tz_aware(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError("timestamps must be timezone-aware")
        return v.astimezone(timezone.utc)

    @model_validator(mode="after")
    def expiry_after_creation(self) -> "NetworkCandidateAct":
        if self.expires_at <= self.created_at:
            raise ValueError("expires_at must be after created_at")
        return self


class ValidatedPredicates(StrictModel):
    initiator_attested: bool
    resource_scope_valid: bool
    subscriber_scope_valid: bool
    purpose_valid: bool
    requested_effect_valid: bool
    operator_policy_valid: bool
    regulatory_policy_valid: bool
    network_state_valid: bool
    policy_epoch_valid: bool
    revocation_state_valid: bool
    freshness_valid: bool
    sink_binding_valid: bool

    def all_true(self) -> bool:
        return all(self.model_dump().values())


class NetworkStateSnapshot(StrictModel):
    topology_epoch: int = Field(ge=0)
    configuration_epoch: int = Field(ge=0)
    slice_state: str = "ACTIVE"
    congestion_state: str = "NORMAL"


class ProtectedStateSnapshot(StrictModel):
    state_reference: str = Field(min_length=1)
    monotonic_counter: int = Field(ge=0)


class NetworkValidationDecision(StrictModel):
    version: Literal["1.0"] = "1.0"
    object_type: Literal["network_validation_decision"] = "network_validation_decision"
    decision_id: str = Field(min_length=1)
    candidate_act_id: str = Field(min_length=1)
    decision: Decision
    validated_predicates: ValidatedPredicates
    network_state: NetworkStateSnapshot
    protected_state: ProtectedStateSnapshot
    evidence_id: str | None = None
    denial_code: str | None = None


class AuthorityScope(StrictModel):
    act_type: ActType
    resource_type: ResourceType
    resource_ids: list[str] = Field(min_length=1)
    subscriber_scope: SubscriberScope
    permitted_effect_type: str
    parameters_digest: str
    duration_seconds_max: int | None = Field(default=None, ge=0)
    network_domain: str | None = None
    jurisdiction: str | None = None
    purpose_id: str


class AuthorityBinding(StrictModel):
    candidate_act_digest: Digest
    evidence_id: str
    evidence_digest: Digest
    protected_state_reference: str
    topology_epoch: int = Field(ge=0)
    configuration_epoch: int = Field(ge=0)
    policy_epoch: int = Field(ge=0)
    authority_epoch: int = Field(ge=0)
    revocation_epoch: int = Field(ge=0)
    nonce: str = Field(min_length=16)
    sequence: int | None = Field(default=None, ge=0)
    finality_sink_id: str
    effectuation_boundary_id: str
    activation_commitment: str = Field(min_length=16)


class AuthorityLifetime(StrictModel):
    issued_at: datetime
    expires_at: datetime
    single_use: bool = True

    @field_validator("issued_at", "expires_at")
    @classmethod
    def tz_aware(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError("timestamps must be timezone-aware")
        return v.astimezone(timezone.utc)


class AuthorityIssuer(StrictModel):
    ped_id: str
    key_id: str
    algorithm: str
    signature: str = ""


class NetworkFinalityAuthority(StrictModel):
    version: Literal["1.0"] = "1.0"
    object_type: Literal["network_finality_authority"] = "network_finality_authority"
    authority_id: str
    candidate_act_id: str
    decision_id: str
    scope: AuthorityScope
    binding: AuthorityBinding
    lifetime: AuthorityLifetime
    issuer: AuthorityIssuer


class ProposedEffect(StrictModel):
    effect_type: str
    resource_type: ResourceType
    resource_ids: list[str] = Field(min_length=1)
    parameters: dict[str, Any]
    parameters_digest: Digest
    duration_seconds: int | None = Field(default=None, ge=0)


class SinkVerifyRequest(StrictModel):
    operation: Literal["NetworkSinkVerify"] = "NetworkSinkVerify"
    request_id: str
    candidate_act_id: str
    authority_id: str
    sink: FinalitySinkDescriptor
    proposed_effect: ProposedEffect
    current_network_state: NetworkStateSnapshot
    freshness: Freshness


class VerificationStatus(StrictModel):
    authority_signature: str
    candidate_act_binding: str
    evidence_binding: str
    activation_binding: str
    resource_scope: str
    subscriber_scope: str
    purpose: str
    effect_parameters: str
    topology_epoch: str
    configuration_epoch: str
    policy_epoch: str
    authority_epoch: str
    revocation_epoch: str
    nonce: str
    sequence: str
    consumption_state: str
    sink_binding: str


class SinkVerifyResponse(StrictModel):
    operation: Literal["NetworkSinkVerify"] = "NetworkSinkVerify"
    request_id: str
    decision: Decision
    code: str
    verification: dict[str, str] = Field(default_factory=dict)
    authority_id: str | None = None
    consumed: bool = False
    effectuation_permitted: bool = False
    network_effect_id: str | None = None
    message: str | None = None
