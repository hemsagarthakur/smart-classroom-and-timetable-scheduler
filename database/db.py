from flask_pymongo import PyMongo
from flask_login import UserMixin


mongo = PyMongo()


class User(UserMixin):
    def __init__(self, user_doc):
        self.id = str(user_doc["_id"])
        self.email = user_doc["email"]
        self.full_name = user_doc["full_name"]
        self.role = user_doc["role"]
        self.department_id = str(user_doc.get("department_id", ""))
        self.faculty_id = str(user_doc.get("faculty_id", ""))
        self.is_active_user = user_doc.get("is_active", True)

    def get_id(self):
        return self.id

    @property
    def is_active(self):
        return self.is_active_user


def get_db():
    return mongo.db


def get_users_col():
    return mongo.db.users


def get_faculty_col():
    return mongo.db.faculty


def get_rooms_col():
    return mongo.db.rooms


def get_subjects_col():
    return mongo.db.subjects


def get_departments_col():
    return mongo.db.departments


def get_slots_col():
    return mongo.db.time_slots


def get_variants_col():
    return mongo.db.timetable_variants
