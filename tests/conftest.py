from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone

import pytest

from network_finality.engine import build_reference_system, make_candidate, make_effect


@pytest.fixture
def system():
    return build_reference_system()


@pytest.fixture
def candidate():
    return make_candidate()


@pytest.fixture
def effect(candidate):
    return make_effect(candidate)


@pytest.fixture
def issued(system, candidate):
    result = system.ped.validate_and_issue(candidate)
    assert result.authority is not None
    return result
