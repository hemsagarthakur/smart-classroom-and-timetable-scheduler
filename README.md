# Smart Classroom & Timetable Scheduler
## SIH 2028 — Problem Statement Solution

## 📸 Project Preview

### 🔐 Login Page
![Login Page](assets/login_dashboard.png)

## Problem Statement
Higher Education institutions often face challenges in efficient class scheduling due to limited infrastructure, faculty constraints, elective courses, and overlapping departmental requirements. Manual timetable preparation leads to frequent clashes in classes, underutilized classrooms, uneven workload distribution, and dissatisfied students and faculty members. With the increasing adoption of multidisciplinary curricula and flexible learning under NEP 2020, the class scheduling process has become more complex and dynamic, requiring intelligent and adaptive solutions.

## About This Project
Smart Classroom & Timetable Scheduler is a Flask-based academic scheduling platform that helps institutions digitize timetable preparation, automate conflict detection, and streamline approval workflows. The system is designed for administrators who manage master data, Heads of Department who review and approve generated timetables, and viewers who need read-only access to approved schedules.

The project uses MongoDB Community Edition locally for storage, DEAP-based Genetic Algorithms for timetable optimization, and Matplotlib analytics for workload and utilization insights. The application reduces manual scheduling effort, improves resource allocation, and provides multiple timetable options for informed decision-making.

## Features
- Role-based login for `superadmin`, `admin`, `hod`, and `viewer`
- Flask-Login session handling with email-based authentication
- MongoDB local database with PyMongo direct collection access
- Admin dashboard with quick stats and recent timetable activity
- Department management with shift configuration
- Faculty management with availability, subject mapping, leave profile, and weekly load limits
- Room management with lab/classroom type, projector availability, and shared-room support
- Subject management with semester, credits, hours per week, and lab/projector flags
- Time slot management with shift filtering and optional fixed-slot subject binding
- Genetic Algorithm timetable generation using DEAP
- Five timetable variants per generation batch with batch-level grouping
- Fitness scoring and violation counting for each generated timetable
- Embedded timetable entries inside `timetable_variants` for single-query retrieval
- Variant comparison screen with tabbed preview cards
- Clash analysis and human-readable improvement suggestions
- Admin selection workflow to forward one timetable to HOD
- HOD review dashboard with approve and reject actions
- Rejection reason capture and decision history
- Viewer portal for approved timetables
- Full timetable grid with print-friendly layout
- Excel export with timetable, faculty workload, and room utilization sheets
- Analytics charts for workload, room utilization, and subject distribution
- Seed script for one-command local setup with sample SIH data
- Ready migration path to MongoDB Atlas by changing only `MONGO_URI`

## Tech Stack
| Technology | Purpose | Version |
|------------|---------|---------|
| Python | Backend language | 3.11 |
| Flask | Web framework | 3.0.3 |
| Flask-Login | Authentication/session management | 0.6.3 |
| Flask-PyMongo | Flask Mongo integration | 2.3.0 |
| PyMongo | Direct MongoDB operations | 4.6.1 |
| dnspython | MongoDB connection support | 2.6.1 |
| Werkzeug | Password hashing/utilities | 3.0.3 |
| DEAP | Genetic Algorithm engine | 1.4.1 |
| Pandas | Chart data shaping | 2.2.2 |
| NumPy | Numeric support | 1.26.4 |
| Matplotlib | Analytics chart rendering | 3.9.0 |
| OpenPyXL | Excel export | 3.1.2 | 
| Bootstrap 5 | UI styling | CDN |
| HTML5/CSS3/Vanilla JS | Frontend | Native |

## Project Structure
```text
SmartScheduler/
├── app.py
├── config.py
├── requirements.txt
├── README.md
├── seed_db.py
├── database/
│   └── db.py
├── core/
│   ├── __init__.py
│   ├── models.py
│   ├── constraints.py
│   ├── scheduler.py
│   └── suggestions.py
├── routes/
│   ├── __init__.py
│   ├── auth.py
│   ├── admin.py
│   ├── hod.py
│   └── viewer.py
├── templates/
│   ├── base.html
│   ├── errors/
│   │   ├── 404.html
│   │   └── 500.html
│   ├── auth/
│   │   └── login.html
│   ├── admin/
│   │   ├── dashboard.html
│   │   ├── departments.html
│   │   ├── faculty.html
│   │   ├── rooms.html
│   │   ├── subjects.html
│   │   ├── timeslots.html
│   │   ├── generate.html
│   │   ├── variants.html
│   │   ├── timetable_view.html
│   │   └── analytics.html
│   ├── hod/
│   │   ├── dashboard.html
│   │   ├── review.html
│   │   └── rejected.html
│   └── viewer/
│       ├── timetables.html
│       └── timetable_view.html
├── static/
│   ├── css/
│   │   └── style.css
│   ├── js/
│   │   └── main.js
│   ├── charts/
│   │   └── .gitkeep
│   └── exports/
├── analytics/
│   ├── __init__.py
│   └── charts.py
└── utils/
    ├── __init__.py
    ├── decorators.py
    └── export.py
```

## Prerequisites
- Python 3.11.x  →  Download from python.org/downloads
- MongoDB Community Edition  →  Download from mongodb.com/try/download/community
- pip (comes with Python)
- Git (optional)

## Installation & Setup

### Step 1 — Install MongoDB Community Edition
Windows: Download installer from mongodb.com, run installer, MongoDB runs as Windows Service automatically

Verify: Open Command Prompt → type: `mongosh`
You should see MongoDB shell. Type `exit` to close.

### Step 2 — Clone / Download the project
Download ZIP and extract, OR:

```bash
git clone <repo-url>
cd SmartScheduler
```

### Step 3 — Create Virtual Environment
```bash
python -m venv venv
```

Activate:
Windows: `venv\Scripts\activate`
Mac/Linux: `source venv/bin/activate`

You should see `(venv)` in your terminal.

### Step 4 — Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 5 — Seed the Database (run once)
```bash
python seed_db.py
```

This will:
- Connect to MongoDB at `localhost:27017`
- Create `smartscheduler` database
- Create all collections with indexes
- Insert all default users, departments, rooms, subjects, faculty, time slots
- Print: `Database seeded successfully!`

### Step 6 — Run the Application
```bash
python app.py
```

Open browser: [http://127.0.0.1:5000](http://127.0.0.1:5000)

## Default Login Credentials
| Role | Email | Password | Access |
|------|-------|----------|--------|
| Super Admin | superadmin@scheduler.com | Super@1234 | Full access + user management |
| Admin | admin@scheduler.com | Admin@1234 | Data input + generate TT |
| HOD (CSE) | hod.cse@scheduler.com | HodCSE@1234 | Review + approve CSE TT |
| HOD (ECE) | hod.ece@scheduler.com | HodECE@1234 | Review + approve ECE TT |
| Viewer | viewer@scheduler.com | View@1234 | View approved timetables only |

## How to Use — Step by Step Workflow

### As Admin:
1. Login with `admin@scheduler.com / Admin@1234`
2. Go to Departments and verify seeded departments
3. Go to Rooms and verify rooms
4. Go to Subjects and verify CSE Semester 3 subjects
5. Go to Faculty and verify faculty assignments
6. Go to Time Slots and verify morning shift slots
7. Open Generate Timetable
8. Select Department: `CSE`, Semester: `3`
9. Click `Generate Timetable`
10. Review the 5 generated timetable options
11. Select the best timetable
12. The selected variant moves to HOD review

### As HOD:
1. Login with `hod.cse@scheduler.com / HodCSE@1234`
2. Open the HOD dashboard
3. Review the pending selected timetable
4. Approve it or reject it with a reason
5. Approved timetables become visible to viewers

### As Viewer:
1. Login with `viewer@scheduler.com / View@1234`
2. Open `Approved Timetables`
3. View the final timetable in read-only mode
4. Print if needed

## Key Parameters Handled
- Faculty availability is stored as day-level constraints and checked during fitness evaluation
- Maximum faculty teaching load is enforced through weekly limits and leave-adjusted capacity penalties
- Average leaves per month are converted into a load buffer during timetable scoring
- Room type compatibility ensures labs are assigned to lab rooms only
- Projector-based subject requirements are validated against room infrastructure
- Department and semester filtering keeps scheduling context-specific
- Shift-based time slots support both morning and evening programs
- Shared rooms allow cross-department infrastructure usage
- Multiple timetable variants provide alternatives rather than a single rigid output
- HOD approval workflow adds human oversight before publication

## Algorithm — Genetic Algorithm Explained Simply
The application converts timetable generation into an optimization problem. Each candidate timetable is represented as a list of class assignments, where every assignment picks a slot, faculty member, subject, and room. A starting population of candidate schedules is created randomly from valid department data.

For each candidate, the system computes a fitness score out of 1000. The score drops when clashes occur, when a lab is assigned to a classroom, when faculty are unavailable, or when subject hours exceed limits. It also rewards correctly honored fixed slots. DEAP then evolves better schedules over many generations using selection, crossover, and mutation. The best individual from each run becomes one timetable variant.

The process runs five times with different random seeds, producing five unique timetable options. These are sorted by fitness and stored for admin review.

## Constraints Enforced
Hard constraints (zero tolerance — heavy penalties):
- Faculty double-booked in the same slot
- Room double-booked in the same slot
- Faculty assigned on unavailable days
- Lab subject placed in non-lab room
- Subject weekly hours exceeded

Soft constraints (optimized — lighter penalties):
- Faculty exceeding max weekly hours
- Faculty exceeding leave-adjusted capacity
- Projector-required subject in non-projector room
- Fixed slot preference handling
- Balanced distribution through repeated GA evolution

## Migrating to MongoDB Atlas (when ready)
Only ONE change needed:
1. Create free account at mongodb.com/atlas
2. Create M0 free cluster
3. Get connection string
4. Open `config.py`
5. Change `MONGO_URI` from:
   ```python
   'mongodb://localhost:27017/smartscheduler'
   ```
   To:
   ```python
   'mongodb+srv://username:password@cluster.xxxxx.mongodb.net/smartscheduler'
   ```
6. Run `seed_db.py` once with the Atlas URI
7. Deploy Flask app to any hosting like Render, Railway, or PythonAnywhere

That is it. No other application code changes are required.

## Troubleshooting
- MongoDB not running:
  Start the MongoDB service, then retry `mongosh` and `python seed_db.py`.
- DEAP install error:
  Upgrade `pip` first using `python -m pip install --upgrade pip`, then reinstall requirements.
- Charts folder missing:
  The app auto-creates `static/charts` and `static/exports` on startup.
- Port already in use:
  Stop the process using port `5000` or change the `app.run()` port temporarily.
- `seed_db.py` fails:
  Confirm MongoDB is running locally at `mongodb://localhost:27017/`.
- Login fails after seeding:
  Re-run `python seed_db.py` and ensure you are using the seeded email addresses, not usernames.

## Future Enhancements
- Mobile app for timetable access
- Email notifications on approval and rejection
- Leave management integration
- AI-based conflict prediction
- Multi-campus scheduling support
- SMS alerts for timetable updates

## License
MIT License — free to use, modify, and distribute
