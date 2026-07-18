"""
tests/_test_helpers.py - Shared test utilities.

build_test_db() - returns a fresh, seeded in-memory sqlite3 connection.

Usage in a test:
    def setUp(self):
        self.conn = build_test_db()
        import app as flask_app
        flask_app.app.config["TESTING"] = True
        flask_app.app.config["TEST_DB_CONN"] = self.conn
        self.client = flask_app.app.test_client()

    def tearDown(self):
        flask_app.app.config.pop("TEST_DB_CONN", None)
        self.conn.close()
"""

import sqlite3
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "BACKEND"))

from werkzeug.security import generate_password_hash


def build_test_db():
    """Return a fresh, fully-seeded in-memory sqlite3 connection.

    Left open; callers must call conn.close() in tearDown.
    """
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")

    with conn:
        conn.execute("""
            CREATE TABLE customers (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT    NOT NULL UNIQUE,
                password TEXT    NOT NULL,
                name     TEXT    NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE accounts (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER NOT NULL UNIQUE REFERENCES customers(id),
                balance     REAL    NOT NULL DEFAULT 0.0
            )
        """)
        for username, raw_pw, name, balance in [
            ("alice", "password123", "Alice Johnson", 1000.00),
            ("bob",   "secret456",   "Bob Smith",     2500.50),
        ]:
            cur = conn.execute(
                "INSERT INTO customers (username, password, name) VALUES (?, ?, ?)",
                (username, generate_password_hash(raw_pw), name),
            )
            conn.execute(
                "INSERT INTO accounts (customer_id, balance) VALUES (?, ?)",
                (cur.lastrowid, balance),
            )
    return conn
