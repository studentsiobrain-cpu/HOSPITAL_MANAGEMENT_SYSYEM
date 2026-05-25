import hashlib
import hmac
import os
from dataclasses import dataclass

from .config import ROLE_PERMISSIONS


PBKDF2_ITERATIONS = 180_000


@dataclass(frozen=True)
class CurrentUser:
    id: int
    username: str
    role: str
    full_name: str

    def can(self, permission: str) -> bool:
        role_permissions = ROLE_PERMISSIONS.get(self.role, set())
        return "*" in role_permissions or permission in role_permissions


def hash_password(password: str, salt: bytes | None = None) -> str:
    if salt is None:
        salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return f"{salt.hex()}${digest.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        salt_hex, digest_hex = stored_hash.split("$", 1)
        candidate = hash_password(password, bytes.fromhex(salt_hex)).split("$", 1)[1]
        return hmac.compare_digest(candidate, digest_hex)
    except ValueError:
        return False
