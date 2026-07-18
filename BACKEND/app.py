"""
app.py - Flask application entry point.

Responsibilities:
  . Create the Flask app instance
  . Configure template/static folder paths
  . Register all routes (delegates logic to auth.py and account.py)
  . Register error handlers
  . Initialise the database on startup
  . Start the development server when run directly
"""

import os
import sys

from flask import Flask, render_template

# Allow imports from this same BACKEND/ directory
sys.path.insert(0, os.path.dirname(__file__))

import db
from auth import handle_login, handle_logout
from account import handle_dashboard, handle_deposit, handle_withdraw

# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

# Resolve paths relative to this file so the app works regardless of the
# directory from which it is launched.
_backend_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.dirname(_backend_dir)

app = Flask(
    __name__,
    template_folder=os.path.join(_project_root, "FRONTEND", "templates"),
    static_folder=os.path.join(_project_root, "FRONTEND", "static"),
)

# SECRET_KEY signs session cookies.
# For production: load from an environment variable, never hardcode.
app.config["SECRET_KEY"] = os.environ.get(
    "FLASK_SECRET_KEY", "dev-only-change-in-production-a3f9c2d1"
)
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

# ---------------------------------------------------------------------------
# Initialise database (creates tables + seeds demo data on first run)
# ---------------------------------------------------------------------------

db.init_app(app)

with app.app_context():
    db.init_db()

# ---------------------------------------------------------------------------
# Routes - each handler is defined in auth.py or account.py
# ---------------------------------------------------------------------------

@app.route("/", methods=["GET"])
def index():
    """Root redirect: send visitors straight to /login."""
    from flask import redirect, url_for
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    return handle_login()


@app.route("/logout")
def logout():
    return handle_logout()


@app.route("/dashboard")
def dashboard():
    return handle_dashboard()


@app.route("/deposit", methods=["GET", "POST"])
def deposit():
    return handle_deposit()


@app.route("/withdraw", methods=["GET", "POST"])
def withdraw():
    return handle_withdraw()


# ---------------------------------------------------------------------------
# Error handlers
# ---------------------------------------------------------------------------

@app.errorhandler(404)
def page_not_found(e):
    return render_template("404.html"), 404


@app.errorhandler(500)
def internal_error(e):
    app.logger.error("500 error: %s", e)
    return render_template("500.html"), 500


# ---------------------------------------------------------------------------
# Dev server entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
