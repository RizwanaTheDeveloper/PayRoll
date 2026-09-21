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