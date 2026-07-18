# Banking Web Application - Step-by-Step Implementation Guide

> **Instructions only.** This guide describes *what to do* and *why*, in plain English.
> It does not contain complete source code, SQL scripts, or API contracts.
> Cross-reference [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md) for architecture decisions and scope.

---

## Table of Contents

1. [Environment Setup](#1-environment-setup)
2. [Backend Implementation](#2-backend-implementation)
3. [Frontend Implementation](#3-frontend-implementation)
4. [Integration Steps](#4-integration-steps)
5. [Validation Rules](#5-validation-rules)
6. [Testing](#6-testing)
7. [Deployment](#7-deployment)

---

## 1. Environment Setup

### 1.1 Prerequisites

Before writing any code, confirm the following are available on your machine:

- **Python 3.10 or later** - the backend runtime. Verify by running `python --version` in a terminal.
- **pip** - Python's package manager, bundled with Python 3.10+.
- **A modern browser** - Chrome, Firefox, or Edge for manual testing.
- **A code editor** - VS Code or any editor with Python and HTML support.

---

### 1.2 Create the Project Directory Structure

Create the top-level project folder (e.g., `banking-app/`) and inside it create two sub-folders:

- `FRONTEND/` - will hold all HTML templates and static assets.
- `BACKEND/` - will hold all Python source files and the database.

Inside `FRONTEND/`, create two further sub-folders:
- `templates/` - for Jinja2 HTML page files.
- `static/css/` and `static/js/` - for stylesheets and optional JavaScript.

This structure keeps browser concerns and server concerns cleanly separated from the start.

---

### 1.3 Create and Activate a Python Virtual Environment

A virtual environment isolates this project's Python packages from any other projects on your machine. Inside the `BACKEND/` folder:

1. Run the command to create a virtual environment (conventionally named `venv`).
2. Activate it - the activation command differs between Windows (`venv\Scripts\activate`) and macOS/Linux (`source venv/bin/activate`).
3. Once activated, your terminal prompt will show the environment name. All `pip install` commands from this point forward only affect this project.

Never commit the `venv/` folder to version control - add it to `.gitignore`.

---

### 1.4 Install Python Dependencies

With the virtual environment active, install the required packages using `pip`. The project needs:

- **Flask** - the web framework that handles routing, templating, and the development server.
- **Werkzeug** - ships with Flask and provides the password hashing utilities you will use in `auth.py`.

After installing, create a `requirements.txt` file in `BACKEND/` by running `pip freeze > requirements.txt`. This file lets any developer reproduce the exact same environment later.

---

### 1.5 Verify Flask is Working

Create a minimal `app.py` in `BACKEND/` that:

1. Imports Flask and creates an application instance.
2. Defines a single test route (e.g., `GET /`) that returns the text "Flask is running".
3. Starts the development server when run directly.

Run `python app.py` and open `http://127.0.0.1:5000` in a browser. Seeing the test text confirms Flask is wired up correctly. Delete or replace the test route before moving to the next step.

---

## 2. Backend Implementation

### 2.1 Database Helper - `db.py`

`db.py` is the only file in the project that is allowed to talk directly to SQLite. Every other module calls functions from `db.py` instead of opening database connections themselves. This keeps SQL contained in one place and makes future changes easier.

**What to implement in `db.py`:**

- A function that opens a connection to `bank.db` (creating the file if it does not exist) and returns that connection object. Use Python's built-in `sqlite3` module.
- A function that initialises the database tables on first run. Call this once when the app starts. It should use `CREATE TABLE IF NOT EXISTS` so it is safe to run every time.
- A function that seeds at least one test customer with a hashed password and a starting balance. This lets you log in immediately for testing without building a registration flow.
- Helper query functions used by other modules: look up a customer by username, get balance by customer ID, update balance by customer ID.

**Key principle:** All queries must use parameterised statements (placeholders like `?`) rather than string formatting. This prevents SQL injection.

---

### 2.2 Flask App Entry Point - `app.py`

`app.py` is the application's entry point. Its responsibilities are narrow: create the Flask app object, register all routes, and start the server. Business logic does not belong here.

**What to implement in `app.py`:**

- Create the Flask app instance and point it at the correct template and static folders (`FRONTEND/templates/` and `FRONTEND/static/`).
- Set a strong, random `SECRET_KEY` on the app. Flask uses this to sign session cookies - without it, sessions cannot be trusted. For local development a hardcoded string is acceptable; for production use an environment variable.
- Call the `db.py` initialisation function so tables exist before any request is served.
- Register a route for each page and action: `GET /login`, `POST /login`, `GET /dashboard`, `GET /deposit`, `POST /deposit`, `GET /withdraw`, `POST /withdraw`, `GET /logout`.
- Each route delegates immediately to a function in `auth.py` or `account.py`. Routes themselves contain no logic.

---

### 2.3 Authentication Controller - `auth.py`

`auth.py` owns everything related to proving who the user is and maintaining their session.

**Login logic (called by `POST /login`):**

1. Read the `username` and `password` fields from the submitted form data.
2. Look up the customer record in the database using the username. If no record is found, return the login page with a generic error message ("Invalid credentials"). Do not say specifically whether the username or password was wrong - that leaks information.
3. Use Werkzeug's `check_password_hash` function to compare the submitted password against the stored hash. If they do not match, return the same generic error.
4. On success, store the customer's ID (not their username or password) in the Flask `session` dictionary. The session is a server-side dictionary tied to a signed cookie; storing the ID is enough to identify the user on subsequent requests.
5. Redirect the user to `GET /dashboard`.

**Session guard (a reusable check):**

Write a small helper function (or decorator) that inspects `session` for the customer ID. If it is absent, redirect to `GET /login`. Call this at the top of every protected route handler. This is the single mechanism that prevents unauthenticated access to any page other than login.

**Logout logic (called by `GET /logout`):**

1. Call Flask's `session.clear()` to remove all session data.
2. Redirect to `GET /login`.

There is nothing else to do for logout - clearing the session is sufficient.

---

### 2.4 Account Controller - `account.py`

`account.py` owns everything related to reading and modifying account balances.

**Get balance:**

1. Read the customer ID from the session.
2. Call the `db.py` helper that fetches the balance for that customer ID.
3. Return the balance value to the caller (the route handler, which passes it to the template).

**Deposit logic (called by `POST /deposit`):**

1. Run the session guard - redirect to login if not authenticated.
2. Read the `amount` field from the form.
3. Apply validation rules (see Section 5).
4. If validation passes, fetch the current balance, add the deposit amount to it, and persist the new value using the `db.py` update helper - wrapped in a database transaction so the read and write are atomic.
5. Redirect back to the dashboard with a success flash message.
6. If validation fails, re-render the deposit form with an error message.

**Withdraw logic (called by `POST /withdraw`):**

1. Run the session guard.
2. Read the `amount` field from the form.
3. Apply validation rules (see Section 5), including the check that the balance is sufficient.
4. If validation passes, fetch the current balance, subtract the withdrawal amount, and persist using `db.py` - inside a transaction.
5. Redirect to the dashboard with a success flash message.
6. If the balance is insufficient or another validation fails, re-render the withdraw form with a descriptive error message.

**Why transactions matter:** Between reading the balance and writing the updated value, another request could theoretically modify the same row. Wrapping the read-update-write in a single SQLite transaction prevents that race condition.

---

### 2.5 Session Management

Flask sessions work via a signed cookie stored in the browser. The cookie contains an encrypted reference tied to `SECRET_KEY`. Because the key signs the cookie, tampering with the cookie makes it invalid.

**Key practices to follow:**

- Store only the customer's database ID in the session, never sensitive fields like password or full account details.
- Set the `SESSION_COOKIE_HTTPONLY` flag to `True` (Flask default) so JavaScript cannot read the cookie.
- For any non-localhost deployment, set `SESSION_COOKIE_SECURE` to `True` so the cookie is only sent over HTTPS.
- Always call `session.clear()` on logout - do not just delete individual keys.

---

### 2.6 Error Handling

Flask provides a mechanism to register custom handlers for HTTP error codes using the `@app.errorhandler` decorator.

**What to implement:**

- A handler for **404 Not Found** - render a simple "Page not found" template rather than Flask's default HTML error page.
- A handler for **500 Internal Server Error** - render a generic "Something went wrong" page. Log the actual exception internally but never display it to the user.
- For user-facing validation errors (wrong password, bad amount), do not use HTTP error codes. Instead re-render the relevant form with an inline error message passed as a template variable. This gives the user an opportunity to correct their input without losing context.

---

## 3. Frontend Implementation

All pages live in `FRONTEND/templates/` and are rendered by Flask using the Jinja2 template engine, which is built into Flask. Jinja2 lets you embed Python expressions inside `{{ }}` and control structures inside `{% %}` directly in HTML.

### 3.1 Base Layout (`base.html`)

Before building individual pages, create a shared base template that all other pages extend. This avoids repeating the Bootstrap CDN link, the `<head>` block, and the navigation bar on every page.

**What the base template should include:**

- A standard HTML5 `<!DOCTYPE html>` document structure.
- A `<meta name="viewport">` tag so Bootstrap's responsive grid works on mobile.
- A `<link>` tag pulling in Bootstrap CSS from its CDN (no local install needed).
- A `{% block content %}{% endblock %}` placeholder - child templates fill this in.
- A navigation bar showing the app name and, when the user is logged in, a "Logout" link.
- A section for displaying flash messages (success/error notifications from Flask's `flash()` function). Loop over `get_flashed_messages()` and render each as a Bootstrap alert.

---

### 3.2 Login Page (`login.html`)

This is the only page accessible without authentication.

**Layout intent:**

- Center a compact card on the screen using Bootstrap's grid (`d-flex justify-content-center align-items-center` on a full-height container).
- Inside the card: the bank name/logo, a username text input, a password input, and a "Login" submit button.
- If the server sends back an error message (via a template variable), display it above the form as a Bootstrap danger alert.
- The form's `action` should point to `POST /login` and the `method` must be `POST` so credentials are sent in the request body, not the URL.

---

### 3.3 Dashboard (`dashboard.html`)

The dashboard is the first page a user sees after login and the hub for all navigation.

**Layout intent:**

- Display a personalised greeting using the customer name passed from the server (e.g., "Welcome, Alice").
- Show the current balance in a prominent Bootstrap card or "jumbotron-style" hero section. Format the number as currency.
- Provide two clear call-to-action buttons: "Deposit" (links to `GET /deposit`) and "Withdraw" (links to `GET /withdraw`).
- Display any flash messages (success/error from a completed transaction) at the top of the page.

---

### 3.4 Deposit Form (`deposit.html`)

**Layout intent:**

- A single-field form asking for the deposit amount.
- Use `type="number"` with a `min="0.01"` and `step="0.01"` attribute for basic browser-side enforcement of positive decimals. This is a UX convenience only - server-side validation (Section 5) is the real guard.
- A "Deposit" submit button and a "Back to Dashboard" link.
- Display server-side validation errors inline above the form field using a Bootstrap danger alert.

---

### 3.5 Withdraw Form (`withdraw.html`)

**Layout intent:**

- Identical structure to the deposit form but labelled "Withdraw".
- Optionally display the current balance near the form so the user knows their limit before submitting. Pass the balance from the server as a template variable.
- Same `type="number"` input constraints and back-link as deposit.
- Display a specific error if the server returns an insufficient-funds result.

---

### 3.6 Bootstrap Layout Principles

Apply these Bootstrap conventions consistently across all pages:

- Use the **12-column grid** (`col-md-6 offset-md-3` etc.) to centre form cards on larger screens while letting them go full-width on mobile.
- Use **Bootstrap utility classes** (`mt-4`, `mb-3`, `p-4`, `shadow`) for spacing and depth rather than writing custom CSS.
- Use **semantic button colours**: `btn-primary` for the main action, `btn-secondary` for back/cancel actions, `btn-danger` for logout.
- Use **Bootstrap form classes** (`form-control`, `form-label`, `mb-3`) for consistent input styling.
- Reserve `static/css/` for any overrides (brand colour, font) that Bootstrap does not provide - keep this file small.

---

## 4. Integration Steps

### 4.1 Connect Flask to the Templates Folder

When creating the Flask app instance in `app.py`, explicitly specify:

- `template_folder` - point this to `FRONTEND/templates/` (relative to `app.py`).
- `static_folder` - point this to `FRONTEND/static/`.

Without these, Flask defaults to looking for templates in a `templates/` sub-folder right next to `app.py`. Since the project separates frontend and backend into different directories, you must override the defaults.

---

### 4.2 Render Templates from Route Handlers

In each route handler, call Flask's `render_template()` function with the template filename and any variables the template needs. For example, the dashboard handler must pass the customer's name and balance as keyword arguments to `render_template()`. Jinja2 then makes those values available inside `{{ }}` expressions in the HTML.

---

### 4.3 Handle Form Submissions

Every form page needs two route handlers with the same URL path but different HTTP methods:

- `GET /deposit` - renders the empty form.
- `POST /deposit` - reads form data, runs business logic, redirects or re-renders with errors.

In Flask, you declare both methods on a single route by passing `methods=["GET", "POST"]`. Inside the handler, check `request.method` to decide which branch of logic to run.

**Always redirect after a successful POST** (the Post-Redirect-Get pattern). If you render a template directly after a POST and the user refreshes the page, the browser re-submits the form. Redirecting to `GET /dashboard` after a successful deposit prevents this.

---

### 4.4 Connect Flask to SQLite via `db.py`

The integration point between Flask and SQLite is the `db.py` module. The connection flow works as follows:

1. When `app.py` starts, it calls `db.init_db()` to ensure tables exist.
2. Each request that needs database access calls a `db.py` helper function, which opens a connection, runs the query, and closes the connection. SQLite connections are lightweight, so opening one per request is acceptable.
3. Alternatively, use Flask's `g` object (request-scoped global) to open one connection per request and close it in a teardown function - this is slightly more efficient and is the pattern Flask's official documentation recommends for SQLite.

---

### 4.5 Flash Messages

Flask's `flash()` function stores a one-time message in the session that is displayed on the next page render and then discarded. Use it to communicate the outcome of form submissions:

- After a successful deposit, call `flash("Deposit successful.", "success")` before redirecting.
- After a failed withdrawal, call `flash("Insufficient funds.", "danger")` before re-rendering the form.
- In the base template, retrieve messages with `get_flashed_messages(with_categories=True)` and render each using the corresponding Bootstrap alert class (`alert-success`, `alert-danger`, etc.).

---

## 5. Validation Rules

All validation runs on the **server side** in `auth.py` and `account.py`. Client-side HTML attributes (`required`, `min`, `type="number"`) are a convenience only and must not be relied upon for security.

### 5.1 Login Validation

| Field | Rule | Error message |
|---|---|---|
| Username | Must not be empty | "Username is required." |
| Password | Must not be empty | "Password is required." |
| Credentials | Username must exist in DB and password must match the stored hash | "Invalid username or password." |

Use the same generic message for both "user not found" and "wrong password". Distinguishing them tells an attacker which usernames are valid.

---

### 5.2 Deposit Validation

| Field | Rule | Error message |
|---|---|---|
| Amount (presence) | Must not be empty or blank | "Amount is required." |
| Amount (type) | Must be convertible to a decimal number | "Amount must be a valid number." |
| Amount (range) | Must be greater than zero | "Deposit amount must be greater than zero." |
| Amount (precision) | Allow up to two decimal places; reject more | "Amount cannot have more than two decimal places." |

After passing all checks, convert the amount to a Python `float` or `Decimal` before using it in arithmetic. Never use the raw string in a calculation.

---

### 5.3 Withdraw Validation

Apply the same rules as deposit validation first, then add one additional check:

| Rule | Error message |
|---|---|
| Current balance ? withdrawal amount | "Insufficient funds. Your current balance is $X.XX." |

Fetch the balance from the database *inside the same transaction* as the update. This ensures the balance you check is the same balance you deduct from, protecting against theoretical concurrent modifications.

---

### 5.4 General Principles

- **Reject early** - check the simplest conditions (empty, non-numeric) before running the database query.
- **Never trust form data** - treat everything from `request.form` as untrusted user input.
- **Return to the form on failure** - do not redirect to an error page; re-render the form with the error message so the user can fix and resubmit without re-entering everything.

---

## 6. Testing

### 6.1 Unit Tests

Unit tests verify individual functions in isolation, without a running server or real database.

**What to test in `auth.py`:**
- The login function returns a failure result when the username does not exist.
- The login function returns a failure result when the password is wrong.
- The login function returns a success result and stores the correct customer ID in the session when credentials are valid.

**What to test in `account.py`:**
- The get-balance function returns the correct value for a known customer.
- The deposit function correctly increases the balance by the specified amount.
- The withdraw function correctly decreases the balance.
- The withdraw function returns an error when the amount exceeds the balance.

**Testing approach:** Use Python's built-in `unittest` module or `pytest`. For database-dependent tests, use an **in-memory SQLite database** (`sqlite3.connect(":memory:")`) seeded with known test data at the start of each test. This keeps tests fast and isolated from the real `bank.db` file.

---

### 6.2 Integration Tests

Integration tests exercise the full HTTP request/response cycle through Flask without a real browser.

Flask ships with a **test client** (`app.test_client()`) that lets you send GET and POST requests in code and inspect the response status code, headers, and body.

**What to test:**
- `GET /login` returns HTTP 200.
- `POST /login` with valid credentials returns HTTP 302 redirecting to `/dashboard`.
- `POST /login` with invalid credentials returns HTTP 200 with an error message in the body.
- `GET /dashboard` without a session returns HTTP 302 redirecting to `/login`.
- `GET /dashboard` with a valid session returns HTTP 200 containing the word "balance".
- `POST /deposit` with a valid amount returns HTTP 302 and the balance increases.
- `POST /withdraw` with an amount exceeding the balance returns HTTP 200 with an insufficient-funds message.
- `GET /logout` clears the session and redirects to `/login`.

---

### 6.3 Manual Testing Checklist

Run through every step in this checklist in a real browser before considering the application ready:

**Login flow:**
- [ ] Visiting any protected page while logged out redirects to the login page.
- [ ] Submitting the login form with a blank username shows a validation error.
- [ ] Submitting with a wrong password shows a generic error (does not reveal which field was wrong).
- [ ] Submitting with correct credentials lands on the dashboard.

**Dashboard:**
- [ ] The dashboard displays the correct customer name.
- [ ] The dashboard displays the correct starting balance.
- [ ] The Deposit and Withdraw buttons are visible and link to the correct pages.

**Deposit:**
- [ ] Submitting a blank amount shows an error.
- [ ] Submitting a negative amount shows an error.
- [ ] Submitting a valid amount redirects to the dashboard with a success message.
- [ ] The balance on the dashboard reflects the deposit.

**Withdraw:**
- [ ] Submitting an amount greater than the balance shows an insufficient-funds error.
- [ ] Submitting a valid amount redirects to the dashboard with a success message.
- [ ] The balance on the dashboard reflects the withdrawal.

**Logout:**
- [ ] Clicking Logout redirects to the login page.
- [ ] After logout, pressing the browser's Back button to `/dashboard` redirects to login.

---

## 7. Deployment

### 7.1 Run Locally

To start the application for local development:

1. Activate the virtual environment in the `BACKEND/` folder.
2. Set `FLASK_DEBUG=1` (or `FLASK_ENV=development`) as an environment variable. This enables the interactive debugger and auto-reloader, which restarts the server whenever you save a Python file.
3. Run `python app.py`. Flask's built-in development server starts on `http://127.0.0.1:5000`.
4. Open that address in a browser. The application is fully functional locally.

**Important:** Flask's development server is single-threaded and not hardened against attacks. It is only for local development. Never expose it directly on a public network.

---

### 7.2 Production Considerations

When moving beyond local development, the following changes are required:

**Use a production WSGI server:**
Flask's built-in server is not suitable for production. Replace it with **Gunicorn** (Linux/macOS) or **Waitress** (Windows-compatible). These servers are multi-threaded, handle concurrent requests, and can be placed behind a reverse proxy.

**Put a reverse proxy in front:**
Place **Nginx** or **Apache** in front of Gunicorn. The reverse proxy handles TLS termination, static file serving (removing that burden from Flask), and connection limiting.

**Enable HTTPS:**
Obtain a TLS certificate (Let's Encrypt provides free certificates). All HTTP traffic should redirect to HTTPS. Once HTTPS is active, set `SESSION_COOKIE_SECURE = True` in the Flask config so session cookies are never sent over plain HTTP.

**Move secrets out of source code:**
The `SECRET_KEY` and any other sensitive config values must be stored as environment variables or in a secrets manager - never hardcoded in `app.py` or committed to version control.

**Database location:**
SQLite is suitable for a low-traffic single-server deployment. Ensure `bank.db` is stored outside the web root and that the application's OS user has read/write permission to that path only (not execute or directory-listing permission). Take regular file-system backups of `bank.db`.

**Logging:**
Replace `print()` statements with Python's `logging` module. Configure log level, format, and output destination (file or a log aggregation service) before going live. Never log sensitive data such as passwords or full session tokens.

**Checklist before going live:**
- [ ] `DEBUG = False` in Flask config.
- [ ] `SECRET_KEY` loaded from environment variable, not hardcoded.
- [ ] `SESSION_COOKIE_SECURE = True` and `SESSION_COOKIE_HTTPONLY = True`.
- [ ] WSGI server (Gunicorn or Waitress) used instead of Flask dev server.
- [ ] HTTPS enabled via reverse proxy.
- [ ] `bank.db` backed up and stored outside the web root.
- [ ] Error pages show no internal stack traces to the user.

---

*End of Step-by-Step Implementation Guide.*
