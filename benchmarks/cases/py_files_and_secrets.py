import hashlib
import os
import random

UPLOAD_ROOT = "/srv/uploads"
DB_PASSWORD = "Sup3rS3cret!2024"  # EXPECT: security


def read_upload(filename: str) -> bytes:
    with open(os.path.join(UPLOAD_ROOT, filename), "rb") as fh:  # EXPECT: security
        return fh.read()


def hash_password(password: str) -> str:
    return hashlib.md5(password.encode()).hexdigest()  # EXPECT: security


def reset_token() -> str:
    return "".join(random.choice("abcdef0123456789") for _ in range(32))  # EXPECT: security


def fetch(url: str):
    import requests
    return requests.get(url, verify=False, timeout=10)  # EXPECT: security
