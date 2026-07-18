# SecureBank - Banking Web Application

A lightweight full-stack banking app built with **Python Flask**, **SQLite**, and **Bootstrap 5**.

---

## Quick Start

### 1. Prerequisites
- Python 3.10+
- pip

### 2. Install dependencies

```bash
cd banking-app
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate

pip install -r BACKEND/requirements.txt
```

### 3. Run the application

```bash
# From the banking-app/ root, with venv active:
python BACKEND/app.py
```

Open **http://127.0.0.1:5000** in your browser.

### 4. Demo credentials

| Username | Password    | Starting Balance |
|----------|-------------|-----------------|
| alice    | password123 | $1,000.00       |
| bob      | secret456   | $2,500.50       |

---

## Run Tests

```bash
# From the banking-app/ root, with venv active:
python -m pytest TESTS/ -v
```

---

## Project Structure

```
banking-app/
??? FRONTEND/
?   ??? templates/          # Jinja2 HTML pages
?   ?   ??? base.html
?   ?   ??? login.html
?   ?   ??? dashboard.html
?   ?   ??? deposit.html
?   ?   ??? withdraw.html
?   ?   ??? 404.html
?   ?   ??? 500.html
?   ??? static/
?       ??? css/style.css
??? BACKEND/
?   ??? app.py              # Flask entry point & routes
?   ??? auth.py             # Login / logout / session guard
?   ??? account.py          # Balance, deposit, withdraw logic
?   ??? db.py               # SQLite helpers (only file touching DB)
?   ??? bank.db             # Auto-created on first run
?   ??? requirements.txt
??? TESTS/
?   ??? test_auth.py
?   ??? test_account.py
?   ??? test_db.py
??? IMPLEMENTATION_PLAN.md
??? STEP_BY_STEP_IMPLEMENTATION_GUIDE.md
```

---

## Features

- **Login / Logout** with session-cookie authentication
- **Dashboard** showing personalised greeting and current balance
- **Deposit** - validated, atomic balance update
- **Withdraw** - validated, insufficient-funds protection
- Server-side validation on all inputs
- Bootstrap 5 responsive layout
- Custom 404 / 500 error pages
