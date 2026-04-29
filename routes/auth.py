import re

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required, login_user, logout_user
from werkzeug.security import check_password_hash

from database.db import User, get_users_col


auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        if not email:
            flash("Email is required.", "danger")
            return redirect(request.url)
        if not password:
            flash("Password is required.", "danger")
            return redirect(request.url)

        try:
            user_doc = get_users_col().find_one({"email": {"$regex": f"^{re.escape(email)}$", "$options": "i"}})
        except Exception as exc:
            flash(f"Database error: {str(exc)}", "danger")
            return redirect(request.url)

        if user_doc and check_password_hash(user_doc["password_hash"], password):
            user = User(user_doc)
            login_user(user)
            flash("Login successful.", "success")
            if user.role in {"admin", "superadmin"}:
                return redirect(url_for("admin.dashboard"))
            if user.role == "hod":
                return redirect(url_for("hod.dashboard"))
            if user.role == "faculty":
                return redirect(url_for("faculty_portal.timetable"))
            return redirect(url_for("viewer.timetables"))

        flash("Invalid email or password", "danger")
        return redirect(request.url)

    return render_template("auth/login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))
