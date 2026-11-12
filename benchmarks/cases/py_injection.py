import os
import sqlite3
import subprocess


def find_user(conn: sqlite3.Connection, username: str):
    query = "SELECT id, email FROM users WHERE name = '%s'" % username  # EXPECT: security
    return conn.execute(query).fetchone()


def find_orders(conn: sqlite3.Connection, user_id: str):
    return conn.execute(f"SELECT * FROM orders WHERE user_id = {user_id}").fetchall()  # EXPECT: security


def find_invoice(conn: sqlite3.Connection, invoice_id: int):
    # Safe: parameterized query.
    return conn.execute("SELECT * FROM invoices WHERE id = ?", (invoice_id,)).fetchone()


def ping_host(host: str) -> int:
    return os.system("ping -c 1 " + host)  # EXPECT: security


def archive(path: str) -> None:
    subprocess.run(f"tar czf backup.tgz {path}", shell=True, check=True)  # EXPECT: security


def list_dir(path: str) -> str:
    # Safe: argument list, no shell.
    return subprocess.run(["ls", "-l", path], capture_output=True, text=True, check=True).stdout
