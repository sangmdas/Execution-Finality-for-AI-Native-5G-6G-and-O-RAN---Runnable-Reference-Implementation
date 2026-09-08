from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from network_finality.canonical import canonical_json_bytes, digest_value
from network_finality.engine import make_candidate
from network_finality.models import SubscriberScope, ScopeType


def test_canonical_digest_stable_across_dict_order():
    assert digest_value({"a": 1, "b": 2}) == digest_value({"b": 2, "a": 1})


def test_canonical_digest_changes_with_value():
    assert digest_value({"a": 1}) != digest_value({"a": 2})


def test_candidate_rejects_extra_fields():
    c = make_candidate().model_dump(mode="python")
    c["unexpected"] = True
    from network_finality.models import NetworkCandidateAct
    with pytest.raises(ValidationError):
        NetworkCandidateAct.model_validate(c)


def test_candidate_id_minimum_length():
    c = make_candidate().model_dump(mode="python")
    c["candidate_act_id"] = "short"
    from network_finality.models import NetworkCandidateAct
    with pytest.raises(ValidationError):
        NetworkCandidateAct.model_validate(c)


def test_nonce_minimum_length():
    c = make_candidate().model_dump(mode="python")
    c["freshness"]["nonce"] = "tiny"
    from network_finality.models import NetworkCandidateAct
    with pytest.raises(ValidationError):
        NetworkCandidateAct.model_validate(c)


def test_expiry_must_follow_creation():
    now = datetime.now(timezone.utc)
    c = make_candidate(now=now).model_dump(mode="python")
    c["expires_at"] = now
    from network_finality.models import NetworkCandidateAct
    with pytest.raises(ValidationError):
        NetworkCandidateAct.model_validate(c)


def test_non_none_scope_requires_reference():
    with pytest.raises(ValidationError):
        SubscriberScope(scope_type=ScopeType.TENANT, scope_reference=None)


def test_timezone_required():
    c = make_candidate().model_dump(mode="python")
    c["created_at"] = datetime.now()
    from network_finality.models import NetworkCandidateAct
    with pytest.raises(ValidationError):
        NetworkCandidateAct.model_validate(c)
