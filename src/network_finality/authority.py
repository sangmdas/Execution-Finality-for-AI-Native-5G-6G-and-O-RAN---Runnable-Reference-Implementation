from __future__ import annotations

from copy import deepcopy

from .canonical import canonical_json_bytes, digest_value
from .models import NetworkFinalityAuthority


def unsigned_authority_payload(authority: NetworkFinalityAuthority) -> bytes:
    clone = authority.model_copy(deep=True)
    clone.issuer.signature = ""
    return canonical_json_bytes(clone)


def authority_digest(authority: NetworkFinalityAuthority) -> str:
    return digest_value(authority)
