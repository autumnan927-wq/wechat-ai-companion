import base64
import hashlib
import os
import secrets

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad


class WeChatCryptoError(ValueError):
    """Raised when a WeChat signature or encrypted payload is invalid."""


def _signature(token: str, timestamp: str, nonce: str, encrypted: str = "") -> str:
    items = sorted([token, timestamp, nonce, encrypted])
    joined = "".join(items)
    return hashlib.sha1(joined.encode("utf-8")).hexdigest()


def check_signature(token: str, timestamp: str, nonce: str, signature: str) -> bool:
    if not token or not signature:
        return False
    expected = _signature(token, timestamp, nonce)
    return secrets.compare_digest(expected, signature)


def check_encrypted_signature(
    token: str,
    timestamp: str,
    nonce: str,
    msg_signature: str,
    encrypted: str,
) -> bool:
    if not token or not msg_signature:
        return False
    expected = _signature(token, timestamp, nonce, encrypted)
    return secrets.compare_digest(expected, msg_signature)


def _aes_key(encoding_aes_key: str) -> bytes:
    normalized_key = encoding_aes_key.rstrip("=") + "="
    key = base64.b64decode(normalized_key)
    if len(key) != 32:
        raise WeChatCryptoError("WECHAT_ENCODING_AES_KEY 必须是 43 位字符串")
    return key


def decrypt_message(encrypted: str, encoding_aes_key: str, app_id: str | None = None) -> str:
    key = _aes_key(encoding_aes_key)
    raw = base64.b64decode(encrypted)
    cipher = AES.new(key, AES.MODE_CBC, key[:16])
    try:
        plain = unpad(cipher.decrypt(raw), AES.block_size)
    except ValueError as exc:
        raise WeChatCryptoError("微信消息解密失败") from exc

    message_length = int.from_bytes(plain[16:20], "big")
    message = plain[20 : 20 + message_length].decode("utf-8")
    received_app_id = plain[20 + message_length :].decode("utf-8")
    if app_id and not secrets.compare_digest(received_app_id, app_id):
        raise WeChatCryptoError("微信消息 AppID 不匹配")
    return message


def encrypt_message(message: str, encoding_aes_key: str, app_id: str) -> str:
    key = _aes_key(encoding_aes_key)
    random_prefix = os.urandom(16)
    content = message.encode("utf-8")
    length_prefix = len(content).to_bytes(4, "big")
    payload = pad(random_prefix + length_prefix + content + app_id.encode("utf-8"), AES.block_size)
    cipher = AES.new(key, AES.MODE_CBC, key[:16])
    return base64.b64encode(cipher.encrypt(payload)).decode("ascii")

