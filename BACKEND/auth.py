"""
auth.py - Authentication controller.

Handles:
  . Login  : verify credentials, write session
  . Logout : clear session
  . Session guard : decorator for protected routes
"""

import functools
from flask import session, redirect, url_for, render_template, request, flash
from werkzeug.security import check_password_hash
from db import get_customer_by_username


# ---------------------------------------------------------------------------
# Session guard decorator
# ---------------------------------------------------------------------------

def login_required(view_func):
    """Decorator that redirects unauthenticated visitors to /login.

    Usage:
        @app.route("/dashboard")
        @login_required
        def dashboard():
            ...
    """
    @functools.wraps(view_func)
    def wrapped(*args, **kwargs):
        if "customer_id" not in session:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login"))
        return view_func(*args, **kwargs)
    return wrapped


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------

def handle_login():
    """Process GET and POST for /login.

    GET  ? render the login form.
    POST ? validate credentials; on success set session and redirect to
           /dashboard; on failure re-render the form with an error.
    """
    if request.method == "GET":
        # If already authenticated, skip straight to dashboard.
        if "customer_id" in session:
            return redirect(url_for("dashboard"))
        return render_template("login.html")

    # --- POST ---
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")

    # Field-presence validation
    if not username:
        return render_template("login.html", error="Username is required.")
    if not password:
        return render_template("login.html", error="Password is required.")

    # Credential check - same generic message for both "not found" and "wrong password"
    customer = get_customer_by_username(username)
    if customer is None or not check_password_hash(customer["password"], password):
        return render_template("login.html", error="Invalid username or password.")

    # Success - store only the customer's ID in the session (never the password)
    session.clear()                            # prevent session fixation
    session["customer_id"] = customer["id"]
    session["customer_name"] = customer["name"]

    return redirect(url_for("dashboard"))


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------

def handle_logout():
    """Clear the session and redirect to /login."""
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))
