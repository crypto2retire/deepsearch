import pytest
from app.services.auth import hash_password, verify_password


def test_password_hash_and_verify():
    pw = "testpassword123"
    hashed = hash_password(pw)
    assert hashed != pw
    assert verify_password(pw, hashed)
    assert not verify_password("wrongpassword", hashed)
