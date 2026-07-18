"""
db.py - Database access layer.

This is the ONLY module that opens SQLite connections.
All other modules call the helper functions defined here.

Connection strategy
-------------------
During a live Flask request, one connection is opened per request and stored
on Flask's ``g`` object.  It is automatically closed by the teardown handler
registered in ``init_app()``.

Outside a request context (e.g. ``init_db`` called at startup, or tests),
the helpers fall back to opening and closing a short-lived connection.
"""

import sqlite3
import os
from werkzeug.security import generate_password_hash

DB_PATH = os.path.join(os.path.dirname(__file__), "bank.db")

_flask_app = None   # set by init_app()


def init_app(app):
    """Register the per-request connection lifecycle with *app*."""
    global _flask_app
    _flask_app = app

    @app.teardown_appcontext
    def _close_db(exc):
        import flask
        conn = flask.g.pop("db_conn", None)
        if conn is not None:
            conn.close()


def _open_connection():
    """Open a new raw connection to DB_PATH."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def get_connection():
    """Return the connection for the current context.

    Inside a Flask request:
      - If app.config["TEST_DB_CONN"] is set, return that connection
        (used by tests to inject an in-memory database).
      - Otherwise open and cache one connection per request on g.
    Outside a request context (startup): returns a plain connection that
    the caller must close.
    """
    try:
        from flask import g, current_app
        # Allow tests to inject a specific connection via app config.
        test_conn = current_app.config.get("TEST_DB_CONN")
        if test_conn is not None:
            return test_conn
        if "db_conn" not in g:
            g.db_conn = _open_connection()
        return g.db_conn
    except RuntimeError:
        # No application context (e.g. called from init_db at startup).
        return _open_connection()


# ---------------------------------------------------------------------------
# Schema initialisation
# ---------------------------------------------------------------------------

def init_db():
    """Create tables and seed demo data.  Safe to call multiple times."""
    conn = _open_connection()
    try:
        with conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS customers (
                    id       INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT    NOT NULL UNIQUE,
                    password TEXT    NOT NULL,
                    name     TEXT    NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS accounts (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_id INTEGER NOT NULL UNIQUE
                                    REFERENCES customers(id),
                    balance     REAL    NOT NULL DEFAULT 0.0
                )
            """)
            _seed_demo_data(conn)
    finally:
        conn.close()


def _seed_demo_data(conn):
    """Insert demo users if the customers table is empty."""
    existing = conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
    if existing == 0:
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


# ---------------------------------------------------------------------------
# Query helpers
# ---------------------------------------------------------------------------

def get_customer_by_username(username: str):
    """Return the customers row for *username*, or None."""
    conn = get_connection()
    return conn.execute(
        "SELECT id, username, password, name FROM customers WHERE username = ?",
        (username,),
    ).fetchone()


def get_balance(customer_id: int) -> float:
    """Return the current balance for *customer_id* as a float."""
    conn = get_connection()
    row = conn.execute(
        "SELECT balance FROM accounts WHERE customer_id = ?",
        (customer_id,),
    ).fetchone()
    return float(row["balance"]) if row else 0.0


def update_balance(customer_id: int, new_balance: float) -> None:
    """Persist *new_balance* (rounded to 2 d.p.) for *customer_id*."""
    conn = get_connection()
    conn.execute(
        "UPDATE accounts SET balance = ? WHERE customer_id = ?",
        (round(new_balance, 2), customer_id),
    )
    conn.commit()
