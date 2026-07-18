"""
tests/test_account.py - Integration tests for dashboard, deposit, and withdraw.

Sets app.config["TEST_DB_CONN"] before each test so db.get_connection()
always returns the shared in-memory connection seeded with alice's account.
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "BACKEND"))

from _test_helpers import build_test_db
import app as flask_app


class _LoggedInBase(unittest.TestCase):
    """Seeded in-memory DB, TEST_DB_CONN set, alice pre-logged-in."""

    def setUp(self):
        self.conn = build_test_db()
        flask_app.app.config["TESTING"] = True
        flask_app.app.config["SECRET_KEY"] = "test-secret"
        flask_app.app.config["TEST_DB_CONN"] = self.conn
        self.client = flask_app.app.test_client()
        # Log in as alice
        self.client.post("/login", data={"username": "alice", "password": "password123"})

    def tearDown(self):
        flask_app.app.config.pop("TEST_DB_CONN", None)
        self.conn.close()

    def _alice_id(self):
        row = self.conn.execute(
            "SELECT id FROM customers WHERE username = 'alice'"
        ).fetchone()
        return row["id"]

    def _alice_balance(self):
        row = self.conn.execute(
            "SELECT balance FROM accounts WHERE customer_id = ?",
            (self._alice_id(),),
        ).fetchone()
        return float(row["balance"])


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

class TestDashboard(_LoggedInBase):

    def test_dashboard_returns_200(self):
        self.assertEqual(self.client.get("/dashboard").status_code, 200)

    def test_dashboard_shows_balance(self):
        self.assertIn(b"1,000.00", self.client.get("/dashboard").data)

    def test_dashboard_shows_customer_name(self):
        self.assertIn(b"Alice", self.client.get("/dashboard").data)

    def test_dashboard_has_deposit_link(self):
        self.assertIn(b"deposit", self.client.get("/dashboard").data.lower())

    def test_dashboard_has_withdraw_link(self):
        self.assertIn(b"withdraw", self.client.get("/dashboard").data.lower())


# ---------------------------------------------------------------------------
# Deposit
# ---------------------------------------------------------------------------

class TestDeposit(_LoggedInBase):

    def test_get_deposit_returns_200(self):
        self.assertEqual(self.client.get("/deposit").status_code, 200)

    def test_valid_deposit_increases_balance(self):
        self.client.post("/deposit", data={"amount": "500"})
        self.assertAlmostEqual(self._alice_balance(), 1500.00, places=2)

    def test_valid_deposit_redirects_to_dashboard(self):
        resp = self.client.post("/deposit", data={"amount": "100"}, follow_redirects=False)
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/dashboard", resp.headers["Location"])

    def test_deposit_small_amount(self):
        self.client.post("/deposit", data={"amount": "0.01"})
        self.assertAlmostEqual(self._alice_balance(), 1000.01, places=2)

    def test_deposit_zero_shows_error(self):
        resp = self.client.post("/deposit", data={"amount": "0"}, follow_redirects=True)
        self.assertIn(b"greater than zero", resp.data)

    def test_deposit_negative_shows_error(self):
        resp = self.client.post("/deposit", data={"amount": "-50"}, follow_redirects=True)
        self.assertIn(b"greater than zero", resp.data)

    def test_deposit_non_numeric_shows_error(self):
        resp = self.client.post("/deposit", data={"amount": "abc"}, follow_redirects=True)
        self.assertIn(b"valid number", resp.data)

    def test_deposit_empty_shows_error(self):
        resp = self.client.post("/deposit", data={"amount": ""}, follow_redirects=True)
        self.assertIn(b"required", resp.data)

    def test_deposit_too_many_decimals_shows_error(self):
        resp = self.client.post("/deposit", data={"amount": "10.001"}, follow_redirects=True)
        self.assertIn(b"two decimal places", resp.data)

    def test_deposit_error_does_not_change_balance(self):
        self.client.post("/deposit", data={"amount": "abc"})
        self.assertAlmostEqual(self._alice_balance(), 1000.00, places=2)


# ---------------------------------------------------------------------------
# Withdraw
# ---------------------------------------------------------------------------

class TestWithdraw(_LoggedInBase):

    def test_get_withdraw_returns_200(self):
        self.assertEqual(self.client.get("/withdraw").status_code, 200)

    def test_withdraw_page_shows_balance(self):
        self.assertIn(b"1,000.00", self.client.get("/withdraw").data)

    def test_valid_withdraw_decreases_balance(self):
        self.client.post("/withdraw", data={"amount": "200"})
        self.assertAlmostEqual(self._alice_balance(), 800.00, places=2)

    def test_valid_withdraw_redirects_to_dashboard(self):
        resp = self.client.post("/withdraw", data={"amount": "100"}, follow_redirects=False)
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/dashboard", resp.headers["Location"])

    def test_withdraw_exact_balance_succeeds(self):
        self.client.post("/withdraw", data={"amount": "1000"})
        self.assertAlmostEqual(self._alice_balance(), 0.00, places=2)

    def test_withdraw_exceeds_balance_shows_error(self):
        resp = self.client.post("/withdraw", data={"amount": "9999"}, follow_redirects=True)
        self.assertIn(b"Insufficient funds", resp.data)

    def test_withdraw_exceeds_balance_does_not_change_balance(self):
        self.client.post("/withdraw", data={"amount": "9999"})
        self.assertAlmostEqual(self._alice_balance(), 1000.00, places=2)

    def test_withdraw_zero_shows_error(self):
        resp = self.client.post("/withdraw", data={"amount": "0"}, follow_redirects=True)
        self.assertIn(b"greater than zero", resp.data)

    def test_withdraw_negative_shows_error(self):
        resp = self.client.post("/withdraw", data={"amount": "-10"}, follow_redirects=True)
        self.assertIn(b"greater than zero", resp.data)

    def test_withdraw_non_numeric_shows_error(self):
        resp = self.client.post("/withdraw", data={"amount": "xyz"}, follow_redirects=True)
        self.assertIn(b"valid number", resp.data)

    def test_withdraw_small_amount(self):
        self.client.post("/withdraw", data={"amount": "0.50"})
        self.assertAlmostEqual(self._alice_balance(), 999.50, places=2)


if __name__ == "__main__":
    unittest.main()
