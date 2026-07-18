"""
tests/test_db.py - Unit tests for the database helper layer (db.py).

Verifies schema, seeding, and query helpers against a fresh in-memory DB
built by build_test_db().  Query helpers are called directly using a plain
sqlite3 connection (no Flask context needed).
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "BACKEND"))

from _test_helpers import build_test_db


class _Base(unittest.TestCase):
    def setUp(self):
        self.conn = build_test_db()

    def tearDown(self):
        self.conn.close()


class TestInitSchema(_Base):

    def test_customers_table_exists(self):
        tables = {
            r[0] for r in
            self.conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        self.assertIn("customers", tables)

    def test_accounts_table_exists(self):
        tables = {
            r[0] for r in
            self.conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        self.assertIn("accounts", tables)

    def test_seed_creates_two_customers(self):
        count = self.conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
        self.assertEqual(count, 2)

    def test_seed_creates_two_accounts(self):
        count = self.conn.execute("SELECT COUNT(*) FROM accounts").fetchone()[0]
        self.assertEqual(count, 2)


class TestQueryHelpers(_Base):
    """Test the db helper functions by calling them via a patched g-less path.

    Because db.get_connection() tries Flask g first and falls back to a plain
    connection outside of a request context, we test the helpers in an
    app-context so g is available and we can prime it.
    """

    def setUp(self):
        super().setUp()
        import app as flask_app
        flask_app.app.config["TESTING"] = True
        flask_app.app.config["TEST_DB_CONN"] = self.conn
        self._app = flask_app.app
        self._ctx = flask_app.app.app_context()
        self._ctx.push()

    def tearDown(self):
        self._ctx.pop()
        self._app.config.pop("TEST_DB_CONN", None)
        super().tearDown()

    def test_get_customer_by_username_returns_alice(self):
        import db
        row = db.get_customer_by_username("alice")
        self.assertIsNotNone(row)
        self.assertEqual(row["username"], "alice")

    def test_get_customer_by_username_unknown_returns_none(self):
        import db
        self.assertIsNone(db.get_customer_by_username("ghost"))

    def test_get_balance_returns_1000_for_alice(self):
        import db
        alice_id = db.get_customer_by_username("alice")["id"]
        self.assertAlmostEqual(db.get_balance(alice_id), 1000.00, places=2)

    def test_get_balance_returns_2500_50_for_bob(self):
        import db
        bob_id = db.get_customer_by_username("bob")["id"]
        self.assertAlmostEqual(db.get_balance(bob_id), 2500.50, places=2)

    def test_update_balance_persists_new_value(self):
        import db
        alice_id = db.get_customer_by_username("alice")["id"]
        db.update_balance(alice_id, 1500.00)
        self.assertAlmostEqual(db.get_balance(alice_id), 1500.00, places=2)

    def test_update_balance_rounds_to_two_decimal_places(self):
        import db
        alice_id = db.get_customer_by_username("alice")["id"]
        db.update_balance(alice_id, 123.456789)
        self.assertAlmostEqual(db.get_balance(alice_id), 123.46, places=2)

    def test_update_balance_allows_zero(self):
        import db
        alice_id = db.get_customer_by_username("alice")["id"]
        db.update_balance(alice_id, 0.0)
        self.assertAlmostEqual(db.get_balance(alice_id), 0.0, places=2)


if __name__ == "__main__":
    unittest.main()
