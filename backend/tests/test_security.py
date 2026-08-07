"""
Unit tests for app.utils.security.

These are pure unit tests — no database, no HTTP client — since the
module under test has no side effects of its own.
"""

from datetime import timedelta

import pytest
from jose import JWTError

from app.utils.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_hash_password_produces_a_different_string_than_the_input():
    hashed = hash_password("correct-horse-battery-staple")

    assert hashed != "correct-horse-battery-staple"
    assert hashed.startswith("$2b$")  # bcrypt hash prefix


def test_verify_password_accepts_the_correct_password():
    hashed = hash_password("correct-horse-battery-staple")

    assert verify_password("correct-horse-battery-staple", hashed) is True


def test_verify_password_rejects_the_wrong_password():
    hashed = hash_password("correct-horse-battery-staple")

    assert verify_password("wrong-password", hashed) is False


def test_hashing_the_same_password_twice_yields_different_hashes():
    # bcrypt salts automatically — two hashes of the same password must
    # never be equal, or a database leak would let an attacker spot
    # users who share a password.
    first = hash_password("same-password")
    second = hash_password("same-password")

    assert first != second
    assert verify_password("same-password", first) is True
    assert verify_password("same-password", second) is True


def test_create_and_decode_access_token_round_trip():
    token = create_access_token(subject="user-id-123")
    payload = decode_access_token(token)

    assert payload["sub"] == "user-id-123"
    assert "exp" in payload
    assert "iat" in payload


def test_decode_access_token_rejects_an_expired_token():
    token = create_access_token(
        subject="user-id-123", expires_delta=timedelta(seconds=-1)
    )

    with pytest.raises(JWTError):
        decode_access_token(token)


def test_decode_access_token_rejects_a_tampered_token():
    token = create_access_token(subject="user-id-123")
    tampered = token[:-1] + ("A" if token[-1] != "A" else "B")

    with pytest.raises(JWTError):
        decode_access_token(tampered)


def test_tokens_for_different_subjects_are_different():
    token_a = create_access_token(subject="user-a")
    token_b = create_access_token(subject="user-b")

    assert token_a != token_b
    assert decode_access_token(token_a)["sub"] == "user-a"
    assert decode_access_token(token_b)["sub"] == "user-b"