"""
account.py - Account management controller.

Handles:
  . Dashboard : read balance and render summary
  . Deposit   : validate amount, add to balance
  . Withdraw  : validate amount, check sufficiency, subtract from balance

All monetary arithmetic uses Python's decimal.Decimal to avoid
floating-point rounding surprises before storing as REAL in SQLite.
"""

from decimal import Decimal, InvalidOperation, ROUND_DOWN
from flask import session, redirect, url_for, render_template, request, flash
from auth import login_required
import db


# ---------------------------------------------------------------------------
# Shared validation helper
# ---------------------------------------------------------------------------

def _parse_amount(raw: str):
    """Parse and validate a monetary amount string.

    Returns (Decimal, None) on success or (None, error_message) on failure.
    Accepts up to two decimal places and requires a value > 0.
    """
    if not raw or not raw.strip():
        return None, "Amount is required."

    try:
        amount = Decimal(raw.strip())
    except InvalidOperation:
        return None, "Amount must be a valid number."

    if amount <= 0:
        return None, "Amount must be greater than zero."

    # Reject more than 2 decimal places (e.g. 1.001)
    # ROUND_DOWN truncates; if the result differs from original, reject.
    if amount != amount.quantize(Decimal("0.01"), rounding=ROUND_DOWN):
        return None, "Amount cannot have more than two decimal places."

    return amount, None


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@login_required
def handle_dashboard():
    """Render the dashboard with the current balance."""
    customer_id = session["customer_id"]
    balance = db.get_balance(customer_id)
    return render_template(
        "dashboard.html",
        customer_name=session["customer_name"],
        balance=f"{balance:,.2f}",
    )


# ---------------------------------------------------------------------------
# Deposit
# ---------------------------------------------------------------------------

@login_required
def handle_deposit():
    """Process GET and POST for /deposit.

    GET  ? render the deposit form.
    POST ? validate amount, add to balance, redirect to dashboard.
    """
    if request.method == "GET":
        return render_template("deposit.html")

    # --- POST ---
    raw_amount = request.form.get("amount", "")
    amount, error = _parse_amount(raw_amount)

    if error:
        return render_template("deposit.html", error=error, amount=raw_amount)

    customer_id = session["customer_id"]
    current_balance = Decimal(str(db.get_balance(customer_id)))
    new_balance = current_balance + amount

    db.update_balance(customer_id, float(new_balance))
    flash(f"Deposit of ${amount:,.2f} was successful. New balance: ${new_balance:,.2f}", "success")
    return redirect(url_for("dashboard"))


# ---------------------------------------------------------------------------
# Withdraw
# ---------------------------------------------------------------------------

@login_required
def handle_withdraw():
    """Process GET and POST for /withdraw.

    GET  ? render the withdraw form with current balance.
    POST ? validate amount, check sufficiency, subtract from balance, redirect.
    """
    customer_id = session["customer_id"]

    if request.method == "GET":
        balance = db.get_balance(customer_id)
        return render_template("withdraw.html", balance=f"{balance:,.2f}")

    # --- POST ---
    raw_amount = request.form.get("amount", "")
    amount, error = _parse_amount(raw_amount)

    if error:
        balance = db.get_balance(customer_id)
        return render_template(
            "withdraw.html",
            error=error,
            amount=raw_amount,
            balance=f"{balance:,.2f}",
        )

    # Fetch balance inside the same logical operation before updating
    current_balance = Decimal(str(db.get_balance(customer_id)))

    if amount > current_balance:
        return render_template(
            "withdraw.html",
            error=f"Insufficient funds. Your current balance is ${current_balance:,.2f}.",
            amount=raw_amount,
            balance=f"{current_balance:,.2f}",
        )

    new_balance = current_balance - amount
    db.update_balance(customer_id, float(new_balance))
    flash(f"Withdrawal of ${amount:,.2f} was successful. New balance: ${new_balance:,.2f}", "success")
    return redirect(url_for("dashboard"))
