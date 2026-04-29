from datetime import datetime

from pymongo import MongoClient
from werkzeug.security import generate_password_hash


def seed_database():
    client = MongoClient("mongodb://localhost:27017/")
    db = client["smartscheduler"]

    for collection_name in [
        "users",
        "departments",
        "faculty",
        "rooms",
        "subjects",
        "time_slots",
        "timetable_variants",
    ]:
        db.drop_collection(collection_name)

    db.users.create_index("email", unique=True)
    db.departments.create_index("code", unique=True)
    db.rooms.create_index("room_code", unique=True)
    db.subjects.create_index([("department_id", 1), ("semester", 1)])
    db.faculty.create_index("email", unique=True)
    db.time_slots.create_index([("day", 1), ("period_number", 1), ("shift", 1)], unique=True)
    db.timetable_variants.create_index("batch_id")

    departments = [
        {"name": "Computer Science Engineering", "code": "CSE", "shift": "morning", "created_at": datetime.utcnow()},
        {"name": "Electronics & Communication Engineering", "code": "ECE", "shift": "morning", "created_at": datetime.utcnow()},
        {"name": "Mechanical Engineering", "code": "MECH", "shift": "morning", "created_at": datetime.utcnow()},
        {"name": "Master of Business Administration", "code": "MBA", "shift": "evening", "created_at": datetime.utcnow()},
    ]
    db.departments.insert_many(departments)
    dept_map = {item["code"]: db.departments.find_one({"code": item["code"]})["_id"] for item in departments}

    users = [
        {"full_name": "Super Admin", "email": "superadmin@scheduler.com", "password": "Super@1234", "role": "superadmin", "department_id": None},
        {"full_name": "System Admin", "email": "admin@scheduler.com", "password": "Admin@1234", "role": "admin", "department_id": None},
        {"full_name": "HOD - CSE", "email": "hod.cse@scheduler.com", "password": "HodCSE@1234", "role": "hod", "department_id": dept_map["CSE"]},
        {"full_name": "HOD - ECE", "email": "hod.ece@scheduler.com", "password": "HodECE@1234", "role": "hod", "department_id": dept_map["ECE"]},
        {"full_name": "Viewer User", "email": "viewer@scheduler.com", "password": "View@1234", "role": "viewer", "department_id": None},
    ]

    rooms = [
        {"room_code": "CS-101", "capacity": 60, "room_type": "classroom", "has_projector": True, "department_id": dept_map["CSE"]},
        {"room_code": "CS-102", "capacity": 60, "room_type": "classroom", "has_projector": True, "department_id": dept_map["CSE"]},
        {"room_code": "CS-LAB1", "capacity": 30, "room_type": "lab", "has_projector": True, "department_id": dept_map["CSE"]},
        {"room_code": "CS-LAB2", "capacity": 30, "room_type": "lab", "has_projector": False, "department_id": dept_map["CSE"]},
        {"room_code": "EC-101", "capacity": 60, "room_type": "classroom", "has_projector": True, "department_id": dept_map["ECE"]},
        {"room_code": "EC-LAB1", "capacity": 30, "room_type": "lab", "has_projector": True, "department_id": dept_map["ECE"]},
        {"room_code": "HALL-1", "capacity": 120, "room_type": "classroom", "has_projector": True, "department_id": None},
        {"room_code": "CONF-1", "capacity": 20, "room_type": "classroom", "has_projector": True, "department_id": None},
    ]
    db.rooms.insert_many([{**item, "created_at": datetime.utcnow()} for item in rooms])

    subjects = [
        {"name": "Data Structures", "code": "DS101", "department_id": dept_map["CSE"], "semester": 3, "credits": 4, "hours_per_week": 4, "is_lab": False, "requires_projector": False},
        {"name": "Object Oriented Prog", "code": "OOP102", "department_id": dept_map["CSE"], "semester": 3, "credits": 4, "hours_per_week": 4, "is_lab": False, "requires_projector": True},
        {"name": "Database Management", "code": "DBMS103", "department_id": dept_map["CSE"], "semester": 3, "credits": 3, "hours_per_week": 3, "is_lab": False, "requires_projector": False},
        {"name": "DS Lab", "code": "DSL101", "department_id": dept_map["CSE"], "semester": 3, "credits": 2, "hours_per_week": 2, "is_lab": True, "requires_projector": True},
        {"name": "OOP Lab", "code": "OOPL102", "department_id": dept_map["CSE"], "semester": 3, "credits": 2, "hours_per_week": 2, "is_lab": True, "requires_projector": False},
        {"name": "Mathematics III", "code": "MATH103", "department_id": dept_map["CSE"], "semester": 3, "credits": 4, "hours_per_week": 4, "is_lab": False, "requires_projector": False},
    ]
    db.subjects.insert_many([{**item, "created_at": datetime.utcnow()} for item in subjects])
    subject_map = {item["code"]: db.subjects.find_one({"code": item["code"]})["_id"] for item in subjects}

    faculty = [
        {"name": "Dr. Ramesh Kumar", "email": "ramesh@college.edu", "phone": "9876543210", "department_id": dept_map["CSE"], "subject_ids": [subject_map["DS101"]], "available_days": ["Mon", "Tue", "Wed", "Thu", "Fri"], "max_hours_per_week": 20, "avg_leaves_per_month": 2},
        {"name": "Dr. Priya Sharma", "email": "priya@college.edu", "phone": "9876543211", "department_id": dept_map["CSE"], "subject_ids": [subject_map["OOP102"], subject_map["OOPL102"]], "available_days": ["Mon", "Tue", "Wed", "Thu", "Fri"], "max_hours_per_week": 18, "avg_leaves_per_month": 1},
        {"name": "Dr. Anil Verma", "email": "anil@college.edu", "phone": "9876543212", "department_id": dept_map["CSE"], "subject_ids": [subject_map["DBMS103"]], "available_days": ["Mon", "Tue", "Wed", "Thu"], "max_hours_per_week": 16, "avg_leaves_per_month": 3},
        {"name": "Dr. Sunita Rao", "email": "sunita@college.edu", "phone": "9876543213", "department_id": dept_map["CSE"], "subject_ids": [subject_map["DSL101"], subject_map["DS101"]], "available_days": ["Mon", "Tue", "Wed", "Thu", "Fri"], "max_hours_per_week": 20, "avg_leaves_per_month": 2},
        {"name": "Prof. Kiran Patel", "email": "kiran@college.edu", "phone": "9876543214", "department_id": dept_map["CSE"], "subject_ids": [subject_map["MATH103"]], "available_days": ["Tue", "Wed", "Thu", "Fri", "Sat"], "max_hours_per_week": 22, "avg_leaves_per_month": 1},
    ]
    db.faculty.insert_many([{**item, "created_at": datetime.utcnow()} for item in faculty])
    faculty_map = {item["email"]: db.faculty.find_one({"email": item["email"]})["_id"] for item in faculty}

    users.append(
        {
            "full_name": "Faculty User",
            "email": "faculty@scheduler.com",
            "password": "Faculty@1234",
            "role": "faculty",
            "department_id": dept_map["CSE"],
            "faculty_id": faculty_map["ramesh@college.edu"],
        }
    )
    db.users.insert_many(
        [
            {
                "full_name": item["full_name"],
                "email": item["email"],
                "password_hash": generate_password_hash(item["password"]),
                "role": item["role"],
                "department_id": item.get("department_id"),
                "faculty_id": item.get("faculty_id"),
                "is_active": True,
                "created_at": datetime.utcnow(),
            }
            for item in users
        ]
    )

    slot_times = [
        (1, "09:00", "10:00"),
        (2, "10:00", "11:00"),
        (3, "11:00", "12:00"),
        (4, "12:00", "13:00"),
        (5, "14:00", "15:00"),
        (6, "15:00", "16:00"),
        (7, "16:00", "17:00"),
    ]
    time_slots = []
    for day in ["Mon", "Tue", "Wed", "Thu", "Fri"]:
        for period, start_time, end_time in slot_times:
            time_slots.append(
                {
                    "day": day,
                    "period_number": period,
                    "start_time": start_time,
                    "end_time": end_time,
                    "shift": "morning",
                    "is_fixed": False,
                    "fixed_subject_id": None,
                    "created_at": datetime.utcnow(),
                }
            )
    db.time_slots.insert_many(time_slots)
    print("Database seeded successfully!")


if __name__ == "__main__":
    seed_database()
