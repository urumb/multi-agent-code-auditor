# Author: urumb
"""Login, sessions and rate limiting for deployments.

Off by default (AUTH_ENABLED=false): on your own machine the backend only
listens on localhost. Turn it on before exposing the app to a network.
Everything here uses the Python standard library (no paid services, no new
dependencies):

- Passwords are stored as scrypt hashes, never in plain text.
- Sessions are HMAC-signed tokens in an HttpOnly, SameSite=Strict cookie
  (Secure when served over HTTPS), so page scripts can't read them and
  other sites can't use them.
- Login attempts and audit starts are rate-limited per client address.
"""
import base64
import hashlib
import hmac
import secrets
import threading
import time
from collections import defaultdict, deque
from typing import Deque, Dict, Optional

SESSION_COOKIE = "auditor_session"

# scrypt cost parameters (~16 MB memory per hash): slow for attackers,
# instant for a single login.
_SCRYPT_N, _SCRYPT_R, _SCRYPT_P = 2**14, 8, 1


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def hash_password(password: str) -> str:
    """scrypt hash in the form ``scrypt:n:r:p:salt:hash``.

    ``:`` separators (not ``$``) so the value can be pasted into a Docker
    Compose ``.env`` file, where ``$`` would start a variable."""
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=_SCRYPT_N, r=_SCRYPT_R, p=_SCRYPT_P, dklen=32)
    return f"scrypt:{_SCRYPT_N}:{_SCRYPT_R}:{_SCRYPT_P}:{_b64(salt)}:{_b64(digest)}"


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, n, r, p, salt, expected = stored.split(":")
        if scheme != "scrypt":
            return False
        digest = hashlib.scrypt(
            password.encode(), salt=_unb64(salt), n=int(n), r=int(r), p=int(p), dklen=len(_unb64(expected))
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(digest, _unb64(expected))


def _sign(payload: str, secret: str) -> str:
    return _b64(hmac.new(secret.encode(), payload.encode(), hashlib.sha256).digest())


def make_session(username: str, secret: str, ttl_seconds: int, now: Optional[float] = None) -> str:
    expires = int((now or time.time()) + ttl_seconds)
    payload = f"{_b64(username.encode())}.{expires}.{secrets.token_hex(8)}"
    return f"{payload}.{_sign(payload, secret)}"


def read_session(token: Optional[str], secret: str, now: Optional[float] = None) -> Optional[str]:
    """The username in a valid, unexpired session token, else None."""
    if not token or not secret:
        return None
    try:
        user_b64, expires, nonce, signature = token.split(".")
    except ValueError:
        return None
    payload = f"{user_b64}.{expires}.{nonce}"
    if not hmac.compare_digest(signature, _sign(payload, secret)):
        return None
    try:
        if int(expires) < (now or time.time()):
            return None
        return _unb64(user_b64).decode()
    except (ValueError, UnicodeDecodeError):
        return None


class RateLimiter:
    """At most ``limit`` events per ``window`` seconds for each key (e.g. IP)."""

    def __init__(self, limit: int, window: float = 60.0):
        self.limit = limit
        self.window = window
        self._events: Dict[str, Deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str, now: Optional[float] = None) -> bool:
        now = time.monotonic() if now is None else now
        with self._lock:
            events = self._events[key]
            while events and now - events[0] > self.window:
                events.popleft()
            if len(events) >= self.limit:
                return False
            events.append(now)
            # Keep memory bounded when many different clients show up.
            if len(self._events) > 10_000:
                for k in [k for k, v in self._events.items() if not v]:
                    del self._events[k]
            return True

    def reset(self) -> None:
        with self._lock:
            self._events.clear()
