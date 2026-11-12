"""A small, well-behaved module: the benchmark expects no findings here."""
import hashlib
import hmac
import secrets
import sqlite3
from pathlib import Path

BASE_DIR = Path("/srv/data").resolve()


def get_user(conn: sqlite3.Connection, user_id: int):
    return conn.execute("SELECT id, name FROM users WHERE id = ?", (user_id,)).fetchone()


def new_token() -> str:
    return secrets.token_urlsafe(32)


def hash_password(password: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 200_000)


def verify(password: str, salt: bytes, expected: bytes) -> bool:
    return hmac.compare_digest(hash_password(password, salt), expected)


def read_data(name: str) -> bytes:
    path = (BASE_DIR / name).resolve()
    if not path.is_relative_to(BASE_DIR):
        raise ValueError("path escapes data directory")
    return path.read_bytes()


def unique_sorted(values: list[int]) -> list[int]:
    return sorted(set(values))
