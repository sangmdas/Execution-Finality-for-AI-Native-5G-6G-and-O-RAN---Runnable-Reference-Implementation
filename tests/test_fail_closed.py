from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone

import pytest

from network_finality.canonical import digest_value
from network_finality.engine import build_reference_system, make_candidate, make_effect
from network_finality.models import Digest


def deny(system, candidate, authority, effect):
    return system.sink.verify_and_effectuate(request_id="deny", candidate=candidate, authority=authority, proposed_effect=effect)


def test_no_authority_no_effect(system, candidate, effect):
    r = deny(system, candidate, None, effect)
    assert not r.effectuation_permitted and r.code == "EF-002"
    assert not system.network.effects


def test_replay_denied(system, candidate, effect, issued):
    first = deny(system, candidate, issued.authority, effect)
    second = deny(system, candidate, issued.authority, effect)
    assert first.effectuation_permitted
    assert not second.effectuation_permitted and second.code == "EF-005"
    assert len(system.network.effects) == 1


def test_topology_epoch_change_denied(system, candidate, effect, issued):
    system.state.topology_epoch += 1
    r = deny(system, candidate, issued.authority, effect)
    assert not r.effectuation_permitted and r.code == "EF-033"


def test_configuration_epoch_change_denied(system, candidate, effect, issued):
    system.state.configuration_epoch += 1
    r = deny(system, candidate, issued.authority, effect)
    assert not r.effectuation_permitted and r.code == "EF-033"


def test_policy_epoch_change_denied(system, candidate, effect, issued):
    system.state.policy_epoch += 1
    r = deny(system, candidate, issued.authority, effect)
    assert not r.effectuation_permitted and r.code == "EF-030"


def test_authority_epoch_change_denied(system, candidate, effect, issued):
    system.state.authority_epoch += 1
    r = deny(system, candidate, issued.authority, effect)
    assert not r.effectuation_permitted and r.code == "EF-032"


def test_revocation_epoch_change_denied(system, candidate, effect, issued):
    system.state.revocation_epoch += 1
    r = deny(system, candidate, issued.authority, effect)
    assert not r.effectuation_permitted and r.code == "EF-031"


def test_protected_state_reference_change_denied(system, candidate, effect, issued):
    system.state.protected_state_reference = "rolled-back-or-substituted-state"
    r = deny(system, candidate, issued.authority, effect)
    assert not r.effectuation_permitted and r.code == "EF-032"


def test_candidate_substitution_denied(system, candidate, effect, issued):
    mutated = candidate.model_copy(deep=True)
    mutated.purpose.purpose_id = "different-purpose"
    r = deny(system, mutated, issued.authority, effect)
    assert not r.effectuation_permitted and r.code == "EF-010"


def test_resource_substitution_denied(system, candidate, issued):
    effect = make_effect(candidate, resource_ids=["slice-999"])
    r = deny(system, candidate, issued.authority, effect)
    assert not r.effectuation_permitted and r.code == "EF-012"


def test_effect_type_substitution_denied(system, candidate, issued):
    effect = make_effect(candidate, effect_type="DELETE_SLICE")
    r = deny(system, candidate, issued.authority, effect)
    assert not r.effectuation_permitted and r.code == "EF-014"


def test_parameter_substitution_denied(system, candidate, issued):
    effect = make_effect(candidate, {"additional_prb_percent": 99, "duration_seconds": 120})
    r = deny(system, candidate, issued.authority, effect)
    assert not r.effectuation_permitted and r.code == "EF-010"


def test_forged_parameter_digest_denied(system, candidate, issued):
    effect = make_effect(candidate)
    effect.parameters["additional_prb_percent"] = 99
    r = deny(system, candidate, issued.authority, effect)
    assert not r.effectuation_permitted and r.code == "EF-011"


def test_duration_escalation_denied(system, candidate, issued):
    effect = make_effect(candidate, duration_seconds=121)
    r = deny(system, candidate, issued.authority, effect)
    assert not r.effectuation_permitted and r.code == "EF-012"


def test_sink_substitution_denied(system, candidate, effect, issued):
    system.sink.sink_id = "other-sink"
    r = deny(system, candidate, issued.authority, effect)
    assert not r.effectuation_permitted and r.code == "EF-040"


def test_signature_tamper_denied(system, candidate, effect, issued):
    issued.authority.scope.purpose_id = "tampered"
    r = deny(system, candidate, issued.authority, effect)
    assert not r.effectuation_permitted and r.code == "EF-003"


def test_signature_bytes_tamper_denied(system, candidate, effect, issued):
    issued.authority.issuer.signature = "AAAA"
    r = deny(system, candidate, issued.authority, effect)
    assert not r.effectuation_permitted and r.code == "EF-003"


def test_missing_evidence_denied(system, candidate, effect, issued):
    system.ped.evidence_store._records.pop(issued.authority.binding.evidence_id)
    r = deny(system, candidate, issued.authority, effect)
    assert not r.effectuation_permitted and r.code == "EF-080"


def test_missing_activation_denied(system, candidate, effect, issued):
    system.ped.activation_store._records.pop(issued.authority.authority_id)
    r = deny(system, candidate, issued.authority, effect)
    assert not r.effectuation_permitted and r.code == "EF-080"


def test_activation_commitment_tamper_denied_via_signature(system, candidate, effect, issued):
    issued.authority.binding.activation_commitment = "x" * 32
    r = deny(system, candidate, issued.authority, effect)
    assert not r.effectuation_permitted and r.code == "EF-003"


def test_wrong_signing_key_denied(candidate, effect):
    a = build_reference_system()
    b = build_reference_system()
    issued = a.ped.validate_and_issue(candidate)
    # copy protected stores so failure is specifically verifier/key related
    b.sink.evidence_store = a.ped.evidence_store
    b.sink.activation_store = a.ped.activation_store
    r = b.sink.verify_and_effectuate(request_id="wrong-key", candidate=candidate, authority=issued.authority, proposed_effect=effect)
    assert not r.effectuation_permitted and r.code == "EF-003"


def test_expired_authority_denied(candidate, effect):
    clock_now = datetime.now(timezone.utc)
    s = build_reference_system(authority_ttl_seconds=0.01)
    c = make_candidate(now=clock_now)
    e = make_effect(c)
    result = s.ped.validate_and_issue(c)
    assert result.authority is not None
    s.sink.clock = lambda: clock_now + timedelta(seconds=1)
    r = deny(s, c, result.authority, e)
    assert not r.effectuation_permitted and r.code == "EF-004"


def test_ped_denies_expired_candidate():
    now = datetime.now(timezone.utc)
    s = build_reference_system()
    c = make_candidate(now=now - timedelta(seconds=10), ttl_seconds=1)
    s.ped.clock = lambda: now
    r = s.ped.validate_and_issue(c)
    assert r.authority is None
    assert r.decision.decision.value == "DENY"


def test_ped_denies_stale_policy_epoch():
    s = build_reference_system()
    c = make_candidate(policy_epoch=41)
    r = s.ped.validate_and_issue(c)
    assert r.authority is None and r.decision.denial_code == "EF-030"


def test_ped_denies_stale_revocation_epoch():
    s = build_reference_system()
    c = make_candidate(revocation_epoch=6)
    r = s.ped.validate_and_issue(c)
    assert r.authority is None and r.decision.denial_code == "EF-031"


def test_ped_denies_wrong_authority_epoch():
    s = build_reference_system()
    c = make_candidate(authority_epoch=7)
    r = s.ped.validate_and_issue(c)
    assert r.authority is None and r.decision.denial_code == "EF-032"


def test_ped_denies_unauthorized_sink():
    s = build_reference_system()
    c = make_candidate(sink_id="unknown-sink")
    r = s.ped.validate_and_issue(c)
    assert r.authority is None and r.decision.denial_code == "EF-040"


def test_ped_denies_disallowed_jurisdiction():
    s = build_reference_system()
    c = make_candidate(jurisdiction="ZZ")
    r = s.ped.validate_and_issue(c)
    assert r.authority is None and r.decision.denial_code == "EF-021"


def test_ped_denies_unknown_jurisdiction():
    s = build_reference_system()
    c = make_candidate()
    c.network_context.jurisdiction = None
    r = s.ped.validate_and_issue(c)
    assert r.authority is None and r.decision.denial_code == "EF-063"


def test_ped_denies_disallowed_purpose():
    s = build_reference_system()
    c = make_candidate(purpose_id="unapproved-purpose")
    r = s.ped.validate_and_issue(c)
    assert r.authority is None and r.decision.denial_code == "EF-013"


def test_ped_denies_missing_required_attestation():
    s = build_reference_system(require_attestation=True)
    c = make_candidate()
    r = s.ped.validate_and_issue(c)
    assert r.authority is None and r.decision.denial_code == "EF-050"


def test_ped_allows_required_attestation_when_present():
    s = build_reference_system(require_attestation=True)
    c = make_candidate(attestation_digest="sha256:attested-runtime")
    r = s.ped.validate_and_issue(c)
    assert r.authority is not None


def test_ped_detects_nonce_reuse():
    s = build_reference_system()
    c1 = make_candidate(candidate_act_id="net-candidate-first-0001")
    c2 = make_candidate(candidate_act_id="net-candidate-second-0002")
    r1 = s.ped.validate_and_issue(c1)
    r2 = s.ped.validate_and_issue(c2)
    assert r1.authority is not None
    assert r2.authority is None and r2.decision.denial_code == "EF-006"


def test_denial_still_commits_evidence():
    s = build_reference_system()
    c = make_candidate(jurisdiction="ZZ")
    r = s.ped.validate_and_issue(c)
    assert r.authority is None
    evidence = s.ped.evidence_store.get(r.decision.evidence_id)
    assert evidence is not None and evidence.decision == "DENY"
