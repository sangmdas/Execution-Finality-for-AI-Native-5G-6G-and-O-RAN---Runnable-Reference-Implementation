from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass
from typing import Protocol

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from .canonical import b64url, b64url_decode


class Signer(Protocol):
    key_id: str
    algorithm: str

    def sign(self, payload: bytes) -> str: ...
    def verifier(self) -> "Verifier": ...


class Verifier(Protocol):
    key_id: str
    algorithm: str

    def verify(self, payload: bytes, signature: str) -> bool: ...


@dataclass
class Ed25519Verifier:
    public_key: Ed25519PublicKey
    key_id: str = "ped-ed25519-1"
    algorithm: str = "Ed25519"

    def verify(self, payload: bytes, signature: str) -> bool:
        try:
            self.public_key.verify(b64url_decode(signature), payload)
            return True
        except Exception:
            return False

    def public_key_pem(self) -> str:
        return self.public_key.public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode("ascii")


@dataclass
class Ed25519Signer:
    private_key: Ed25519PrivateKey
    key_id: str = "ped-ed25519-1"
    algorithm: str = "Ed25519"

    @classmethod
    def generate(cls, key_id: str = "ped-ed25519-1") -> "Ed25519Signer":
        return cls(Ed25519PrivateKey.generate(), key_id=key_id)

    def sign(self, payload: bytes) -> str:
        return b64url(self.private_key.sign(payload))

    def verifier(self) -> Ed25519Verifier:
        return Ed25519Verifier(self.private_key.public_key(), self.key_id, self.algorithm)


@dataclass
class HMACVerifier:
    secret: bytes
    key_id: str = "ped-hmac-1"
    algorithm: str = "HMAC-SHA256"

    def verify(self, payload: bytes, signature: str) -> bool:
        try:
            expected = hmac.new(self.secret, payload, hashlib.sha256).digest()
            return hmac.compare_digest(expected, b64url_decode(signature))
        except Exception:
            return False


@dataclass
class HMACSigner:
    secret: bytes
    key_id: str = "ped-hmac-1"
    algorithm: str = "HMAC-SHA256"

    def sign(self, payload: bytes) -> str:
        return b64url(hmac.new(self.secret, payload, hashlib.sha256).digest())

    def verifier(self) -> HMACVerifier:
        return HMACVerifier(self.secret, self.key_id, self.algorithm)
