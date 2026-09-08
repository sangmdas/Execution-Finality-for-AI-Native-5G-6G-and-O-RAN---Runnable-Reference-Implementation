from __future__ import annotations

import pytest

from network_finality.engine import build_reference_system, make_candidate, make_effect
from network_finality.models import ActType, FunctionType, ResourceType, ScopeType, SinkType


def test_allow_path(system, candidate, effect, issued):
    response = system.sink.verify_and_effectuate(request_id="r1", candidate=candidate, authority=issued.authority, proposed_effect=effect)
    assert response.effectuation_permitted is True
    assert response.consumed is True
    assert response.code == "OK"
    assert len(system.network.effects) == 1


def test_ped_commits_evidence_before_authority(system, candidate):
    result = system.ped.validate_and_issue(candidate)
    assert result.authority is not None
    evidence = system.ped.evidence_store.get(result.authority.binding.evidence_id)
    assert evidence is not None
    assert evidence.decision == "ALLOW"


def test_authority_is_bound_to_candidate_digest(issued):
    assert issued.authority.binding.candidate_act_digest.value


def test_authority_is_sink_bound(candidate, issued):
    assert issued.authority.binding.finality_sink_id == candidate.finality_sink.sink_id


def test_authority_is_nonce_bound(candidate, issued):
    assert issued.authority.binding.nonce == candidate.freshness.nonce


def test_authority_is_epoch_bound(system, issued):
    b = issued.authority.binding
    assert (b.policy_epoch, b.authority_epoch, b.revocation_epoch) == (system.state.policy_epoch, system.state.authority_epoch, system.state.revocation_epoch)


def test_authority_is_network_state_bound(system, issued):
    b = issued.authority.binding
    assert (b.topology_epoch, b.configuration_epoch) == (system.state.topology_epoch, system.state.configuration_epoch)


def test_authority_is_single_use(issued):
    assert issued.authority.lifetime.single_use is True


def test_effect_parameters_are_bound(candidate, effect):
    assert effect.parameters_digest.value == candidate.requested_effect.parameters_digest.value


@pytest.mark.parametrize(
    "act_type,function_type,resource_type,sink_type",
    [
        (ActType.SLICE_RESOURCE_ALLOCATION, FunctionType.AI_RAN_CONTROLLER, ResourceType.SLICE, SinkType.RAN_CONTROL),
        (ActType.RAN_PARAMETER_CHANGE, FunctionType.RIC_XAPP, ResourceType.CELL, SinkType.O_RAN_E2),
        (ActType.NETWORK_API_INVOCATION, FunctionType.NETWORK_API_CLIENT, ResourceType.NETWORK_API, SinkType.NETWORK_API_GATEWAY),
        (ActType.UPF_RULE_CHANGE, FunctionType.UPF_CONTROLLER, ResourceType.UPF_RULE, SinkType.UPF),
        (ActType.SESSION_MODIFICATION, FunctionType.SMF, ResourceType.SESSION, SinkType.SESSION_CONTROLLER),
        (ActType.BEAM_CHANGE, FunctionType.AI_RAN_CONTROLLER, ResourceType.BEAM, SinkType.RAN_CONTROL),
        (ActType.SENSING_OPERATION, FunctionType.EDGE_AGENT, ResourceType.SENSING_RESOURCE, SinkType.CONTROL_PLANE_GATEWAY),
        (ActType.RF_ENABLE, FunctionType.ORCHESTRATOR, ResourceType.SPECTRUM_RESOURCE, SinkType.RF_ENABLE),
    ],
)
def test_telecom_variations(act_type, function_type, resource_type, sink_type):
    sink_id = f"sink-{sink_type.value.lower()}"
    s = build_reference_system(sink_id=sink_id, sink_type=sink_type)
    c = make_candidate(
        act_type=act_type,
        function_type=function_type,
        resource_type=resource_type,
        resource_ids=["resource-1"],
        scope_type=ScopeType.TENANT,
        scope_reference="tenant-A",
        effect_type=f"EFFECT_{act_type.value}",
        sink_id=sink_id,
        sink_type=sink_type,
    )
    e = make_effect(c)
    r = s.ped.validate_and_issue(c)
    assert r.authority is not None
    out = s.sink.verify_and_effectuate(request_id="variation", candidate=c, authority=r.authority, proposed_effect=e)
    assert out.effectuation_permitted
