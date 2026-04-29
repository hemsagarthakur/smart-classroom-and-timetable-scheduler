import logging
import os

from bson import ObjectId
from flask import Flask, redirect, render_template, url_for
from flask_login import LoginManager, current_user

from config import Config
from database.db import User, mongo
from routes.admin import admin_bp
from routes.auth import auth_bp
from routes.faculty import faculty_bp
from routes.hod import hod_bp
from routes.viewer import viewer_bp


logging.basicConfig(
    filename="scheduler.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)

login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message_category = "warning"


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    app.config["TEMPLATES_AUTO_RELOAD"] = True
    app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0

    os.makedirs(os.path.join(app.root_path, app.config["CHARTS_FOLDER"]), exist_ok=True)
    os.makedirs(os.path.join(app.root_path, app.config["EXPORT_FOLDER"]), exist_ok=True)

    mongo.init_app(app)
    login_manager.init_app(app)
    app.jinja_env.auto_reload = True

    @login_manager.user_loader
    def load_user(user_id):
        try:
            doc = mongo.db.users.find_one({"_id": ObjectId(user_id)})
            if doc:
                return User(doc)
        except Exception:
            return None
        return None

    @app.context_processor
    def inject_globals():
        def asset_version(filename):
            file_path = os.path.join(app.static_folder, filename)
            try:
                return int(os.path.getmtime(file_path))
            except OSError:
                return 1

        return {"current_user": current_user, "asset_version": asset_version}

    @app.route("/")
    def index():
        if current_user.is_authenticated:
            if current_user.role in {"admin", "superadmin"}:
                return redirect(url_for("admin.dashboard"))
            if current_user.role == "hod":
                return redirect(url_for("hod.dashboard"))
            if current_user.role == "faculty":
                return redirect(url_for("faculty_portal.timetable"))
            return redirect(url_for("viewer.timetables"))
        return redirect(url_for("auth.login"))

    @app.errorhandler(404)
    def not_found(_error):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def server_error(_error):
        return render_template("errors/500.html"), 500

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(faculty_bp)
    app.register_blueprint(hod_bp)
    app.register_blueprint(viewer_bp)

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
