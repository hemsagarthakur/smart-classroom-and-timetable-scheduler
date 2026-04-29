from functools import wraps

from flask import flash, redirect, url_for
from flask_login import current_user


def role_required(*roles):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated or current_user.role not in roles:
                flash("You are not authorized to access this page.", "danger")
                return redirect(url_for("auth.login"))
            return func(*args, **kwargs)

        return wrapper

    return decorator
