import base64
import hashlib
import os

from app.wechat.crypto import (
    check_signature,
    decrypt_message,
    encrypt_message,
)


def test_check_signature() -> None:
    token = "test_token"
    timestamp = "1720000000"
    nonce = "abcdef"
    expected = hashlib.sha1("".join(sorted([token, timestamp, nonce])).encode()).hexdigest()
    assert check_signature(token, timestamp, nonce, expected) is True
    assert check_signature(token, timestamp, nonce, "bad") is False


def test_encrypt_decrypt_roundtrip() -> None:
    key = base64.b64encode(os.urandom(32)).decode().rstrip("=")
    app_id = "wx-test-app"
    plain = "<xml><Content>你好</Content></xml>"
    encrypted = encrypt_message(plain, key, app_id)
    assert decrypt_message(encrypted, key, app_id) == plain
