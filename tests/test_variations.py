from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from network_finality.engine import build_reference_system, make_candidate, make_effect
from network_finality.models import ScopeType


def test_hmac_backend():
    s = build_reference_system(signing_backend="hmac")
    c = make_candidate()
    e = make_effect(c)
    r = s.ped.validate_and_issue(c)
    out = s.sink.verify_and_effectuate(request_id="hmac", candidate=c, authority=r.authority, proposed_effect=e)
    assert out.effectuation_permitted


def test_sqlite_backend(tmp_path: Path):
    s = build_reference_system(persistence="sqlite", state_dir=tmp_path)
    c = make_candidate()
    e = make_effect(c)
    r = s.ped.validate_and_issue(c)
    out = s.sink.verify_and_effectuate(request_id="sqlite", candidate=c, authority=r.authority, proposed_effect=e)
    assert out.effectuation_permitted
    assert (tmp_path / "activation.sqlite3").exists()
    assert (tmp_path / "evidence.sqlite3").exists()


def test_sqlite_replay_survives_new_store_instance(tmp_path: Path):
    s = build_reference_system(persistence="sqlite", state_dir=tmp_path)
    c = make_candidate()
    e = make_effect(c)
    r = s.ped.validate_and_issue(c)
    out = s.sink.verify_and_effectuate(request_id="sqlite1", candidate=c, authority=r.authority, proposed_effect=e)
    assert out.effectuation_permitted
    from network_finality.state import SQLiteActivationStore
    s.sink.activation_store = SQLiteActivationStore(tmp_path / "activation.sqlite3")
    replay = s.sink.verify_and_effectuate(request_id="sqlite2", candidate=c, authority=r.authority, proposed_effect=e)
    assert replay.code == "EF-005"


def test_concurrent_replay_only_one_effectuates(system, candidate, effect, issued):
    def call(i):
        return system.sink.verify_and_effectuate(request_id=f"r-{i}", candidate=candidate, authority=issued.authority, proposed_effect=effect)
    with ThreadPoolExecutor(max_workers=8) as ex:
        results = list(ex.map(call, range(16)))
    allowed = [r for r in results if r.effectuation_permitted]
    denied = [r for r in results if not r.effectuation_permitted]
    assert len(allowed) == 1
    assert len(denied) == 15
    assert len(system.network.effects) == 1


@pytest.mark.parametrize("ttl", [0.05, 0.25, 1.0, 4.0])
def test_authority_ttl_variations(ttl):
    s = build_reference_system(authority_ttl_seconds=ttl)
    c = make_candidate(ttl_seconds=10)
    r = s.ped.validate_and_issue(c)
    lifetime = (r.authority.lifetime.expires_at - r.authority.lifetime.issued_at).total_seconds()
    assert lifetime == pytest.approx(ttl, abs=0.01)


@pytest.mark.parametrize(
    "scope_type,reference",
    [
        (ScopeType.TENANT, "tenant-A"),
        (ScopeType.SLICE, "slice-17"),
        (ScopeType.SINGLE_SUBSCRIBER, "subscriber-123"),
        (ScopeType.SUBSCRIBER_GROUP, "group-7"),
        (ScopeType.CELL_POPULATION, "cell-108"),
    ],
)
def test_subscriber_scope_variations(scope_type, reference):
    s = build_reference_system()
    c = make_candidate(scope_type=scope_type, scope_reference=reference)
    e = make_effect(c)
    r = s.ped.validate_and_issue(c)
    out = s.sink.verify_and_effectuate(request_id="scope", candidate=c, authority=r.authority, proposed_effect=e)
    assert out.effectuation_permitted


def test_effect_is_absent_before_sink_verification(system, candidate):
    r = system.ped.validate_and_issue(candidate)
    assert r.authority is not None
    assert system.network.effects == {}


def test_denied_sink_attempt_does_not_consume_authority(system, candidate, issued):
    bad = make_effect(candidate, {"additional_prb_percent": 99, "duration_seconds": 120})
    r1 = system.sink.verify_and_effectuate(request_id="bad", candidate=candidate, authority=issued.authority, proposed_effect=bad)
    assert not r1.effectuation_permitted
    good = make_effect(candidate)
    r2 = system.sink.verify_and_effectuate(request_id="good", candidate=candidate, authority=issued.authority, proposed_effect=good)
    assert r2.effectuation_permitted


def test_evidence_chain_changes_each_commit():
    s = build_reference_system()
    c1 = make_candidate(candidate_act_id="candidate-evidence-0001", nonce="NONCE000000000001")
    c2 = make_candidate(candidate_act_id="candidate-evidence-0002", nonce="NONCE000000000002")
    r1 = s.ped.validate_and_issue(c1)
    r2 = s.ped.validate_and_issue(c2)
    e1 = s.ped.evidence_store.get(r1.decision.evidence_id)
    e2 = s.ped.evidence_store.get(r2.decision.evidence_id)
    assert e1.digest != e2.digest
    assert e2.previous_digest == e1.digest
