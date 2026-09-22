from functools import wraps

from flask import session, redirect, url_for, flash, request

from database import get_connection


# ============================================================
# LOOKUP
# ============================================================

def get_user_by_username(username):
    """Fetch one row from AppUsers by username (case-insensitive)."""

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            SELECT
                UserId AS "UserId",
                Username AS "Username",
                Password AS "Password",
                Role AS "Role",
                EmployeeCode AS "EmployeeCode",
                IsActive AS "IsActive"
            FROM AppUsers
            WHERE LOWER(Username) = LOWER(%s)
        """, (username,))

        return cursor.fetchone()

    finally:
        cursor.close()
        connection.close()


def get_user_by_employee_code(employee_code):
    """Fetch the client login account linked to this employee, if any."""

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            SELECT
                UserId AS "UserId",
                Username AS "Username",
                Password AS "Password",
                Role AS "Role",
                EmployeeCode AS "EmployeeCode",
                IsActive AS "IsActive"
            FROM AppUsers
            WHERE EmployeeCode = %s
        """, (employee_code,))

        return cursor.fetchone()

    finally:
        cursor.close()
        connection.close()


# ============================================================
# EMPLOYEE LOGIN ACCOUNT (optional username/password on Add/Edit Employee)
# ============================================================

def upsert_employee_login(employee_code, username, password):
    """
    Create or update the client login account tied to one employee.

    Both `username` and `password` are optional and independent:
      - Neither given: do nothing (no account created/changed).
      - An account already exists for this employee: update whichever
        of username/password was actually provided, leave the other
        field untouched.
      - No account exists yet: a new one is only created if BOTH
        username and password are given (a login needs both); if only
        one was given, nothing is created and the caller is told why.

    Returns (ok: bool, message: str | None). `message` is set only
    when nothing could be done and the caller should flash a warning.
    """

    username = (username or "").strip()
    password = password or ""

    if not username and not password:
        return True, None

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            SELECT UserId AS "UserId", Username AS "Username", Password AS "Password"
            FROM AppUsers
            WHERE EmployeeCode = %s
        """, (employee_code,))

        existing = cursor.fetchone()

        if not existing and (not username or not password):
            return False, (
                "A username and a password are both needed to create a "
                "login for this employee — nothing was saved since only "
                "one was provided."
            )

        if username:
            cursor.execute("""
                SELECT UserId AS "UserId"
                FROM AppUsers
                WHERE LOWER(Username) = LOWER(%s)
                  AND EmployeeCode IS DISTINCT FROM %s
            """, (username, employee_code))

            if cursor.fetchone():
                return False, (
                    f"The username \u201c{username}\u201d is already taken by "
                    "another account — login details were not saved."
                )

        if existing:
            new_username = username or existing.Username
            new_password = password or existing.Password

            cursor.execute("""
                UPDATE AppUsers
                SET Username = %s,
                    Password = %s,
                    IsActive = 1
                WHERE UserId = %s
            """, (
                new_username,
                new_password,
                existing.UserId,
            ))

        else:
            cursor.execute("""
                INSERT INTO AppUsers
                (Username, Password, Role, EmployeeCode, IsActive)
                VALUES
                (%s, %s, 'client', %s, 1)
            """, (
                username,
                password,
                employee_code,
            ))

        connection.commit()

        return True, None

    except Exception:
        connection.rollback()
        raise

    finally:
        cursor.close()
        connection.close()


def verify_login(username, password):
    """
    Returns the matching AppUsers row if the username/password are
    correct and the account is active, otherwise None.
    """

    user = get_user_by_username(username)

    if not user or not user.IsActive:
        return None

    if user.Password != password:
        return None

    return user


# ============================================================
# ROUTE PROTECTION
# ============================================================

def login_required(view_func):
    """Require any signed-in user (admin or client)."""

    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Please sign in to continue.", "error")
            return redirect(url_for("login", next=request.path))
        return view_func(*args, **kwargs)

    return wrapped


def role_required(*roles):
    """Require a signed-in user whose role is one of `roles`."""

    def decorator(view_func):
        @wraps(view_func)
        def wrapped(*args, **kwargs):
            if "user_id" not in session:
                flash("Please sign in to continue.", "error")
                return redirect(url_for("login", next=request.path))

            if session.get("role") not in roles:
                flash("You don't have permission to do that.", "error")
                return redirect(url_for("index"))

            return view_func(*args, **kwargs)

        return wrapped

    return decorator