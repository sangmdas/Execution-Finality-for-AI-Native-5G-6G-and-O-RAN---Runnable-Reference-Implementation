from __future__ import annotations

from network_finality.crypto import Ed25519Signer, HMACSigner


def test_ed25519_sign_verify():
    signer = Ed25519Signer.generate()
    payload = b"execution-finality"
    sig = signer.sign(payload)
    assert signer.verifier().verify(payload, sig)


def test_ed25519_rejects_changed_payload():
    signer = Ed25519Signer.generate()
    sig = signer.sign(b"a")
    assert not signer.verifier().verify(b"b", sig)


def test_hmac_sign_verify():
    signer = HMACSigner(b"0123456789abcdef0123456789abcdef")
    sig = signer.sign(b"execution-finality")
    assert signer.verifier().verify(b"execution-finality", sig)


def test_hmac_rejects_changed_payload():
    signer = HMACSigner(b"0123456789abcdef0123456789abcdef")
    sig = signer.sign(b"a")
    assert not signer.verifier().verify(b"b", sig)
