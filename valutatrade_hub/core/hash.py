import hashlib
from typing import Protocol


class HasherProtocol(Protocol):
    def hash(self, password: str, salt: str) -> str: ...


class Pbkdf2Hasher:
    """Password hasher based on PBKDF2-HMAC-SHA256"""

    def hash(self, password: str, salt: str) -> str:
        return hashlib.pbkdf2_hmac(
            "sha256", password.encode(), bytes.fromhex(salt), int(1e6)
        ).hex()
