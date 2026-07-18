"""
tests/test_auth.py - Tests for login, logout, and session guard routes.

Sets app.config["TEST_DB_CONN"] to an in-memory connection before each
test.  db.get_connection() returns that connection for every request,
so all queries go to the seeded in-memory database.
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "BACKEND"))

from _test_helpers import build_test_db
import app as flask_app


class _AppBase(unittest.TestCase):

    def setUp(self):
        self.conn = build_test_db()
        flask_app.app.config["TESTING"] = True
        flask_app.app.config["SECRET_KEY"] = "test-secret"
        flask_app.app.config["TEST_DB_CONN"] = self.conn
        self.client = flask_app.app.test_client()

    def tearDown(self):
        flask_app.app.config.pop("TEST_DB_CONN", None)
        self.conn.close()


# ---------------------------------------------------------------------------
# GET /login
# ---------------------------------------------------------------------------

class TestLoginPage(_AppBase):

    def test_get_login_returns_200(self):
        self.assertEqual(self.client.get("/login").status_code, 200)

    def test_login_page_contains_form(self):
        resp = self.client.get("/login")
        self.assertIn(b"username", resp.data)
        self.assertIn(b"password", resp.data)

    def test_root_redirects_to_login(self):
        resp = self.client.get("/", follow_redirects=False)
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/login", resp.headers["Location"])

    def test_already_logged_in_skips_login(self):
        self.client.post("/login", data={"username": "alice", "password": "password123"})
        resp = self.client.get("/login", follow_redirects=False)
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/dashboard", resp.headers["Location"])


# ---------------------------------------------------------------------------
# POST /login
# ---------------------------------------------------------------------------

class TestLoginPost(_AppBase):

    def test_valid_credentials_redirect_to_dashboard(self):
        resp = self.client.post(
            "/login",
            data={"username": "alice", "password": "password123"},
            follow_redirects=False,
        )
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/dashboard", resp.headers["Location"])

    def test_wrong_password_shows_generic_error(self):
        resp = self.client.post(
            "/login",
            data={"username": "alice", "password": "wrong"},
            follow_redirects=True,
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Invalid username or password", resp.data)

    def test_unknown_username_shows_generic_error(self):
        resp = self.client.post(
            "/login",
            data={"username": "ghost", "password": "password123"},
            follow_redirects=True,
        )
        self.assertIn(b"Invalid username or password", resp.data)

    def test_empty_username_shows_error(self):
        resp = self.client.post(
            "/login",
            data={"username": "", "password": "password123"},
            follow_redirects=True,
        )
        self.assertIn(b"Username is required", resp.data)

    def test_empty_password_shows_error(self):
        resp = self.client.post(
            "/login",
            data={"username": "alice", "password": ""},
            follow_redirects=True,
        )
        self.assertIn(b"Password is required", resp.data)

    def test_second_user_can_log_in(self):
        resp = self.client.post(
            "/login",
            data={"username": "bob", "password": "secret456"},
            follow_redirects=False,
        )
        self.assertEqual(resp.status_code, 302)


# ---------------------------------------------------------------------------
# Session guard
# ---------------------------------------------------------------------------

class TestSessionGuard(_AppBase):

    def test_dashboard_redirects_unauthenticated(self):
        resp = self.client.get("/dashboard", follow_redirects=False)
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/login", resp.headers["Location"])

    def test_deposit_redirects_unauthenticated(self):
        resp = self.client.get("/deposit", follow_redirects=False)
        self.assertEqual(resp.status_code, 302)

    def test_withdraw_redirects_unauthenticated(self):
        resp = self.client.get("/withdraw", follow_redirects=False)
        self.assertEqual(resp.status_code, 302)


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------

class TestLogout(_AppBase):

    def _login(self):
        self.client.post("/login", data={"username": "alice", "password": "password123"})

    def test_logout_redirects_to_login(self):
        self._login()
        resp = self.client.get("/logout", follow_redirects=False)
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/login", resp.headers["Location"])

    def test_dashboard_inaccessible_after_logout(self):
        self._login()
        self.client.get("/logout")
        resp = self.client.get("/dashboard", follow_redirects=False)
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/login", resp.headers["Location"])


if __name__ == "__main__":
    unittest.main()
