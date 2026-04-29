from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Faculty:
    id: str
    name: str
    email: str
    phone: str
    department_id: str
    subject_ids: List[str]
    available_days: List[str]
    max_hours_per_week: int = 20
    avg_leaves_per_month: int = 2

    @classmethod
    def from_mongo(cls, doc):
        return cls(
            id=str(doc["_id"]),
            name=doc["name"],
            email=doc["email"],
            phone=doc.get("phone", ""),
            department_id=str(doc["department_id"]),
            subject_ids=[str(item) for item in doc.get("subject_ids", [])],
            available_days=doc.get("available_days", []),
            max_hours_per_week=doc.get("max_hours_per_week", 20),
            avg_leaves_per_month=doc.get("avg_leaves_per_month", 2),
        )


@dataclass
class Room:
    id: str
    room_code: str
    capacity: int
    room_type: str
    has_projector: bool
    department_id: Optional[str] = None

    @classmethod
    def from_mongo(cls, doc):
        department_id = doc.get("department_id")
        return cls(
            id=str(doc["_id"]),
            room_code=doc["room_code"],
            capacity=doc["capacity"],
            room_type=doc["room_type"],
            has_projector=doc.get("has_projector", False),
            department_id=str(department_id) if department_id else None,
        )


@dataclass
class Subject:
    id: str
    name: str
    code: str
    department_id: str
    semester: int
    credits: int
    hours_per_week: int
    is_lab: bool
    requires_projector: bool

    @classmethod
    def from_mongo(cls, doc):
        return cls(
            id=str(doc["_id"]),
            name=doc["name"],
            code=doc["code"],
            department_id=str(doc["department_id"]),
            semester=doc["semester"],
            credits=doc["credits"],
            hours_per_week=doc["hours_per_week"],
            is_lab=doc.get("is_lab", False),
            requires_projector=doc.get("requires_projector", False),
        )


@dataclass
class TimeSlot:
    id: str
    day: str
    period_number: int
    start_time: str
    end_time: str
    shift: str
    is_fixed: bool = False
    fixed_subject_id: Optional[str] = None

    @classmethod
    def from_mongo(cls, doc):
        fixed_subject_id = doc.get("fixed_subject_id")
        return cls(
            id=str(doc["_id"]),
            day=doc["day"],
            period_number=doc["period_number"],
            start_time=doc["start_time"],
            end_time=doc["end_time"],
            shift=doc["shift"],
            is_fixed=doc.get("is_fixed", False),
            fixed_subject_id=str(fixed_subject_id) if fixed_subject_id else None,
        )


@dataclass
class TimetableEntry:
    slot_id: str
    day: str
    period_number: int
    start_time: str
    end_time: str
    subject_id: str
    subject_name: str
    subject_code: str
    faculty_id: str
    faculty_name: str
    room_id: str
    room_code: str
    is_fixed: bool = False
    department_code: str = ""

    @classmethod
    def from_mongo(cls, doc):
        return cls(
            slot_id=str(doc["slot_id"]),
            day=doc["day"],
            period_number=doc["period_number"],
            start_time=doc["start_time"],
            end_time=doc["end_time"],
            subject_id=str(doc["subject_id"]),
            subject_name=doc["subject_name"],
            subject_code=doc["subject_code"],
            faculty_id=str(doc["faculty_id"]),
            faculty_name=doc["faculty_name"],
            room_id=str(doc["room_id"]),
            room_code=doc["room_code"],
            is_fixed=doc.get("is_fixed", False),
            department_code=doc.get("department_code", ""),
        )


@dataclass
class TimetableVariant:
    department_id: str
    semester: int
    fitness_score: float
    clash_count: int
    violations: List[dict] = field(default_factory=list)
    entries: List[TimetableEntry] = field(default_factory=list)
    seed_used: int = 0

    @classmethod
    def from_mongo(cls, doc):
        return cls(
            department_id=str(doc["department_id"]),
            semester=doc["semester"],
            fitness_score=doc["fitness_score"],
            clash_count=doc["clash_count"],
            violations=doc.get("violations", []),
            entries=[TimetableEntry.from_mongo(item) for item in doc.get("entries", [])],
            seed_used=doc.get("seed_used", 0),
        )
