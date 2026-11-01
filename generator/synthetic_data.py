"""
generator/synthetic_data.py
============================
RecruitFlow – Comprehensive synthetic data generation.

Uses only Python stdlib + numpy + random (no Faker dependency).

Targets:
  - 5 departments
  - 30 employees
  - 200 requisitions
  - 5 000 candidates
  - 8 000 applications  (+  stage history)
  - 2 000 interviews
  - 4 000 interviewer assignments
  - 2 000 scorecards
  - 1 000 offers

Run:
  python generator/synthetic_data.py

Idempotent: running again will not insert duplicates.
Fixed SEED = 42 guarantees reproducibility.
"""

from __future__ import annotations

import random
import string
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import engine
from app.models import (
    Application,
    ApplicationStageHistory,
    Candidate,
    Department,
    Employee,
    Interview,
    Interviewer,
    Offer,
    Requisition,
    Scorecard,
)

# ── Reproducibility ──────────────────────────────────────────────────────────

SEED = 42
random.seed(SEED)
rng = np.random.default_rng(SEED)

# ── Name parts for realistic synthetic names ──────────────────────────────────

FIRST_NAMES = [
    "Aarav", "Aditya", "Akash", "Amelia", "Ananya", "Arjun", "Aryan", "Ayesha",
    "Deepika", "Dev", "Divya", "Emily", "Faisal", "Fatima", "Gaurav", "Harini",
    "Ishaan", "Jaya", "Kabir", "Kavya", "Keerthi", "Kiran", "Lakshmi", "Manish",
    "Meera", "Mohammed", "Nandini", "Nikhil", "Nisha", "Pooja", "Pradeep",
    "Priya", "Rahul", "Rajesh", "Ravi", "Ritika", "Rohan", "Rohini", "Sakshi",
    "Sanjay", "Sarah", "Shivani", "Shreya", "Siddharth", "Sneha", "Suresh",
    "Tanvi", "Usha", "Varun", "Vikram", "Vikas", "Vivek", "Yamini", "Zara",
    "Abhinav", "Abhishek", "Aditi", "Aishwarya", "Amar", "Amrita", "Amit",
    "Ankita", "Aparna", "Archana", "Ashish", "Asma", "Bhavna", "Chetan",
    "Chirag", "Disha", "Geetanjali", "Harsha", "Heena", "Hemant", "Isha",
    "Jyothi", "Kartik", "Komal", "Kritika", "Madhuri", "Mahesh", "Manoj",
    "Megha", "Mihir", "Mitali", "Mohan", "Namrata", "Naveen", "Neha",
    "Pankaj", "Piyush", "Pranav", "Preeti", "Preethi", "Radhika", "Rajiv",
    "Rakesh", "Ram", "Ramesh", "Rashmi", "Rekha", "Renu", "Rishi", "Rohit",
    "Rupal", "Rushali", "Sandhya", "Sangeeta", "Sarika", "Satish", "Sharad",
    "Shilpa", "Shobha", "Shweta", "Smita", "Sonal", "Sonali", "Srikanth",
    "Subhash", "Sumit", "Sunita", "Swati", "Tejas", "Uday", "Urmila",
    "Vandana", "Veena", "Venkat", "Vidya", "Vijay", "Vinay", "Vinita",
    "Yash", "Yashika", "Yogesh",
]

LAST_NAMES = [
    "Agarwal", "Ahuja", "Bhat", "Bhatia", "Bhatt", "Chandra", "Chatterjee",
    "Chauhan", "Chopra", "Das", "Desai", "Deshpande", "Dubey", "Dutta",
    "Garg", "Ghosh", "Goswami", "Goyal", "Gupta", "Iyengar", "Iyer",
    "Jain", "Jha", "Johari", "Joshi", "Kapur", "Kapoor", "Kaur", "Khan",
    "Khanna", "Kulkarni", "Kumar", "Lal", "Malhotra", "Mathur", "Mehta",
    "Menon", "Mishra", "Modi", "Mukherjee", "Nair", "Naidu", "Nayak",
    "Pandey", "Patel", "Pathak", "Patil", "Pillai", "Prasad", "Rao",
    "Rastogi", "Reddy", "Roy", "Saha", "Sahoo", "Saini", "Saxena",
    "Seth", "Sethi", "Shah", "Sharma", "Shastri", "Shukla", "Singh",
    "Singhal", "Sinha", "Srivastava", "Thakur", "Tiwari", "Tripathi",
    "Upadhyay", "Varma", "Verma", "Vyas", "Yadav", "Bose", "Banerjee",
    "Chakraborty", "Chowdhury", "Dey", "Ganguly", "Mandal", "Sarkar",
    "Sen", "Misra", "Aggarwal", "Anand", "Arora", "Bajaj", "Bali",
    "Bhargava", "Bhowmik", "Chaturvedi", "Chawla", "Choudhary", "Dixit",
    "Gandhi", "Hegde", "Hora", "Lamba", "Luthra", "Madan", "Mittal",
    "Narang", "Oberoi", "Ohri", "Puri", "Rathi", "Sachdeva", "Sood",
    "Tandon", "Taneja", "Wadhwa", "Walia",
]

DOMAINS = [
    "gmail.com", "yahoo.com", "outlook.com", "hotmail.com",
    "rediffmail.com", "protonmail.com",
]

CITY_LOCATIONS = [
    "Hyderabad", "Bangalore", "Mumbai", "Pune", "Chennai",
    "Delhi", "Kolkata", "Ahmedabad", "Noida", "Gurgaon",
]

QUALIFICATIONS = [
    "B.Tech", "M.Tech", "MCA", "BCA", "MBA",
    "B.Sc", "M.Sc", "B.Com", "M.Com", "PhD",
]

SOURCES = [
    "LinkedIn", "Naukri", "Indeed", "Company Website",
    "Referral", "Internshala", "Campus Placement", "HeadHunter",
]

EMPLOYMENT_TYPES = ["Full-time", "Part-time", "Contract", "Internship"]

DEPARTMENT_NAMES = [
    "Engineering",
    "Human Resources",
    "Product Management",
    "Sales & Marketing",
    "Finance & Accounting",
]

EMPLOYEE_ROLES = [
    "Hiring Manager", "Recruiter", "Interviewer", "HR Lead", "Director",
]

JOB_TITLES_BY_DEPT: dict[str, list[str]] = {
    "Engineering": [
        "Python Developer", "Backend Engineer", "Data Engineer",
        "DevOps Engineer", "QA Engineer", "Cloud Architect",
        "ML Engineer", "Full Stack Developer", "Android Developer", "iOS Developer",
    ],
    "Human Resources": [
        "HR Generalist", "Talent Acquisition Specialist",
        "HR Business Partner", "Learning & Development Manager", "Compensation Analyst",
    ],
    "Product Management": [
        "Product Manager", "Associate Product Manager",
        "Product Owner", "Business Analyst", "UX Researcher",
    ],
    "Sales & Marketing": [
        "Sales Executive", "Digital Marketing Specialist",
        "Brand Manager", "Inside Sales Manager", "Growth Hacker",
    ],
    "Finance & Accounting": [
        "Financial Analyst", "Accountant",
        "Audit Manager", "Tax Consultant", "Treasury Analyst",
    ],
}

SALARY_RANGES_BY_DEPT: dict[str, tuple[int, int]] = {
    "Engineering": (400_000, 2_500_000),
    "Human Resources": (300_000, 1_200_000),
    "Product Management": (500_000, 2_000_000),
    "Sales & Marketing": (300_000, 1_500_000),
    "Finance & Accounting": (350_000, 1_800_000),
}

APPLICATION_STAGES = [
    "applied", "screening", "interview", "assessment", "offer", "hired", "rejected",
]

INTERVIEW_TYPES = ["technical", "hr", "managerial", "behavioral", "case_study"]

RECOMMENDATIONS = ["strong_hire", "hire", "hold", "no_hire"]
RECOMMENDATION_WEIGHTS = [0.25, 0.35, 0.25, 0.15]

OFFER_STATUSES = [
    "draft", "pending_approval", "approved",
    "released", "accepted", "rejected", "expired",
]
OFFER_STATUS_WEIGHTS = [0.05, 0.10, 0.15, 0.25, 0.30, 0.10, 0.05]

REQUISITION_STATUS_WEIGHTS = [
    ("open", 0.55),
    ("closed", 0.25),
    ("draft", 0.10),
    ("cancelled", 0.10),
]

APP_STAGE_WEIGHTS = [
    ("applied", 0.20),
    ("screening", 0.20),
    ("interview", 0.20),
    ("assessment", 0.10),
    ("offer", 0.10),
    ("hired", 0.10),
    ("rejected", 0.10),
]

# ── Helpers ───────────────────────────────────────────────────────────────────


def weighted_choice(choices: list[tuple[str, float]]) -> str:
    items, weights = zip(*choices)
    return random.choices(list(items), weights=list(weights), k=1)[0]


def random_date_between(start: date, end: date) -> date:
    delta = (end - start).days
    if delta <= 0:
        return start
    return start + timedelta(days=random.randint(0, delta))


def random_datetime_between(start: datetime, end: datetime) -> datetime:
    delta = int((end - start).total_seconds())
    if delta <= 0:
        return start
    return start + timedelta(seconds=random.randint(0, delta))


def make_name() -> str:
    return f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"


def make_email(name: str, suffix: str = "") -> str:
    """Generate an email from a name. suffix is appended before @domain."""
    base = name.lower().replace(" ", ".").replace("'", "")
    # strip non-ascii chars
    base = "".join(c for c in base if c in string.ascii_lowercase + ".")
    return f"{base}{suffix}@{random.choice(DOMAINS)}"


def make_phone() -> str:
    return f"+91 {random.randint(70000, 99999)} {random.randint(10000, 99999)}"


def random_sentence(nb_words: int = 15) -> str:
    words = [
        "excellent", "strong", "candidate", "demonstrated", "technical",
        "communication", "skills", "problem", "solving", "ability",
        "needs", "improvement", "good", "performance", "interview",
        "hire", "recommend", "assessment", "overall", "satisfactory",
        "outstanding", "average", "below", "expectations", "exceeded",
        "thorough", "analytical", "leadership", "potential", "growth",
    ]
    sentence = " ".join(random.choices(words, k=nb_words))
    return sentence.capitalize() + "."


# ── Phase 1: Departments ──────────────────────────────────────────────────────


def seed_departments(session: Session) -> dict[str, Department]:
    dept_map: dict[str, Department] = {}
    for name in DEPARTMENT_NAMES:
        existing = session.scalar(
            select(Department).where(Department.department_name == name)
        )
        if not existing:
            dept = Department(department_name=name)
            session.add(dept)
            session.flush()
            dept_map[name] = dept
        else:
            dept_map[name] = existing
    print(f"  Departments: {len(dept_map)}")
    return dept_map


# ── Phase 2: Employees ────────────────────────────────────────────────────────


def seed_employees(
    session: Session, dept_map: dict[str, Department]
) -> list[Employee]:
    """Generate 30 employees spread across departments."""
    dept_names = list(dept_map.keys())

    # At least 2 per dept (5×2=10), remaining distributed randomly
    assignments: list[str] = []
    for d in dept_names:
        assignments.extend([d, d])
    remaining = 30 - len(assignments)
    assignments.extend(random.choices(dept_names, k=remaining))
    random.shuffle(assignments)

    employees: list[Employee] = []
    used_emails: set[str] = set(session.scalars(select(Employee.email)).all())

    for i, dept_name in enumerate(assignments):
        dept = dept_map[dept_name]
        name = make_name()
        email = make_email(name, suffix=str(i + 1))

        # Ensure uniqueness
        while email in used_emails:
            email = make_email(name, suffix=str(uuid.uuid4().hex[:4]))

        used_emails.add(email)

        existing = session.scalar(
            select(Employee).where(Employee.email == email)
        )
        if existing:
            employees.append(existing)
            continue

        role = random.choice(EMPLOYEE_ROLES)
        emp = Employee(
            department_id=dept.department_id,
            full_name=name,
            email=email,
            role=role,
        )
        session.add(emp)
        session.flush()
        employees.append(emp)

    print(f"  Employees: {len(employees)}")
    return employees


# ── Phase 3: Requisitions ─────────────────────────────────────────────────────


def seed_requisitions(
    session: Session,
    dept_map: dict[str, Department],
    employees: list[Employee],
) -> list[Requisition]:
    """Generate 200 job requisitions."""
    req_start = date(2024, 1, 1)
    req_end = date(2026, 10, 1)
    reqs: list[Requisition] = []

    for _ in range(200):
        dept_name = random.choice(list(dept_map.keys()))
        dept = dept_map[dept_name]
        job_title = random.choice(JOB_TITLES_BY_DEPT[dept_name])

        dept_employees = [
            e for e in employees if e.department_id == dept.department_id
        ]
        if not dept_employees:
            dept_employees = employees
        hiring_manager = random.choice(dept_employees)

        salary_lo, salary_hi = SALARY_RANGES_BY_DEPT[dept_name]
        s_min = random.randint(salary_lo, max(salary_lo, salary_hi - 200_000))
        s_max = min(s_min + random.randint(100_000, 800_000), salary_hi)

        exp_min = random.randint(0, 8)
        exp_max = exp_min + random.randint(1, 6)

        created_dt = random_date_between(req_start, req_end)
        status = weighted_choice(REQUISITION_STATUS_WEIGHTS)
        closed_at: Optional[datetime] = None
        if status in ("closed", "cancelled"):
            closed_dt = created_dt + timedelta(days=random.randint(30, 180))
            if closed_dt <= date.today():
                closed_at = datetime.combine(
                    closed_dt, datetime.min.time()
                ).replace(tzinfo=timezone.utc)

        req = Requisition(
            department_id=dept.department_id,
            hiring_manager_id=hiring_manager.employee_id,
            job_title=job_title,
            employment_type=random.choice(EMPLOYMENT_TYPES),
            location=random.choice(CITY_LOCATIONS),
            openings=random.randint(1, 10),
            experience_min=exp_min,
            experience_max=exp_max,
            salary_min=Decimal(str(s_min)),
            salary_max=Decimal(str(s_max)),
            status=status,
            closed_at=closed_at,
        )
        session.add(req)
        reqs.append(req)

    session.flush()
    print(f"  Requisitions: {len(reqs)}")
    return reqs


# ── Phase 4: Candidates ───────────────────────────────────────────────────────


def seed_candidates(session: Session, target: int = 5000) -> list[Candidate]:
    """Generate unique candidates."""
    existing_emails: set[str] = set(
        session.scalars(select(Candidate.email)).all()
    )
    candidates: list[Candidate] = []
    counter = len(existing_emails)

    while len(candidates) < target:
        name = make_name()
        email = make_email(name, suffix=str(counter))
        while email in existing_emails:
            counter += 1
            email = make_email(name, suffix=str(counter))

        existing_emails.add(email)
        counter += 1

        exp = round(random.uniform(0, 20), 1)
        cand = Candidate(
            full_name=name,
            email=email,
            phone=make_phone(),
            experience_years=Decimal(str(exp)),
            highest_qualification=random.choice(QUALIFICATIONS),
            current_location=random.choice(CITY_LOCATIONS),
        )
        session.add(cand)
        candidates.append(cand)

        if len(candidates) % 500 == 0:
            session.flush()

    session.flush()
    print(f"  Candidates: {len(candidates)}")
    return candidates


# ── Phase 5: Applications ─────────────────────────────────────────────────────


def seed_applications(
    session: Session,
    candidates: list[Candidate],
    requisitions: list[Requisition],
    employees: list[Employee],
    target: int = 8000,
) -> list[Application]:
    """Generate applications with no duplicate candidate-requisition pairs."""
    open_reqs = [r for r in requisitions if r.status == "open"]
    if not open_reqs:
        open_reqs = requisitions
    req_pool = open_reqs * 4 + requisitions  # weight toward open

    existing_pairs: set[tuple[int, int]] = set(
        session.execute(
            select(Application.candidate_id, Application.requisition_id)
        ).all()
    )

    apps: list[Application] = []
    attempts = 0
    base_date = date(2024, 1, 1)
    today = date.today()
    recruiter = employees[0]
    batch: list[Application] = []

    while len(apps) < target and attempts < target * 6:
        attempts += 1
        cand = random.choice(candidates)
        req = random.choice(req_pool)
        pair = (cand.candidate_id, req.requisition_id)

        if pair in existing_pairs:
            continue
        existing_pairs.add(pair)

        app_date = random_date_between(base_date, today)
        current_stage = weighted_choice(APP_STAGE_WEIGHTS)
        status = "active" if current_stage not in ("hired", "rejected") else "closed"

        app = Application(
            candidate_id=cand.candidate_id,
            requisition_id=req.requisition_id,
            application_date=app_date,
            current_stage=current_stage,
            status=status,
            source=random.choice(SOURCES),
        )
        session.add(app)
        apps.append(app)
        batch.append(app)

        if len(batch) >= 500:
            session.flush()
            for a in batch:
                _add_stage_history(session, a, recruiter)
            session.flush()
            batch = []

    if batch:
        session.flush()
        for a in batch:
            _add_stage_history(session, a, recruiter)
        session.flush()

    print(f"  Applications: {len(apps)}")
    return apps


def _add_stage_history(
    session: Session, app: Application, recruiter: Employee
) -> None:
    """Insert stage history records for an application."""
    stages = APPLICATION_STAGES
    if app.current_stage == "rejected":
        current_idx = random.randint(0, 4)
    elif app.current_stage in stages:
        current_idx = stages.index(app.current_stage)
    else:
        current_idx = 0

    stages_to_insert = stages[: current_idx + 1]
    base_dt = datetime.combine(app.application_date, datetime.min.time()).replace(
        tzinfo=timezone.utc
    )

    for idx, stage in enumerate(stages_to_insert):
        dt = base_dt + timedelta(days=idx * random.randint(3, 10))
        hist = ApplicationStageHistory(
            application_id=app.application_id,
            previous_stage=stages[idx - 1] if idx > 0 else None,
            new_stage=stage,
            changed_by=recruiter.employee_id,
            changed_at=dt,
            remarks=f"Moved to {stage}.",
        )
        session.add(hist)


# ── Phase 6: Interviews ───────────────────────────────────────────────────────


def seed_interviews(
    session: Session,
    apps: list[Application],
    target: int = 2000,
) -> list[Interview]:
    """Generate interviews for applications past 'applied' stage."""
    eligible_stages = {"screening", "interview", "assessment", "offer", "hired"}
    eligible_apps = [a for a in apps if a.current_stage in eligible_stages]
    random.shuffle(eligible_apps)

    existing_pairs: set[tuple[int, int]] = set(
        session.execute(
            select(Interview.application_id, Interview.interview_round)
        ).all()
    )

    interviews: list[Interview] = []
    base_start = datetime(2024, 3, 1, 9, 0, tzinfo=timezone.utc)
    base_end = datetime(2026, 10, 15, 18, 0, tzinfo=timezone.utc)
    count = 0

    for app in eligible_apps:
        if count >= target:
            break
        num_rounds = random.choices([1, 2, 3], weights=[0.50, 0.40, 0.10])[0]

        for rnd in range(1, num_rounds + 1):
            if count >= target:
                break
            pair = (app.application_id, rnd)
            if pair in existing_pairs:
                continue
            existing_pairs.add(pair)

            scheduled = random_datetime_between(base_start, base_end)
            status = random.choices(
                ["completed", "scheduled", "cancelled", "rescheduled"],
                weights=[0.55, 0.25, 0.10, 0.10],
            )[0]
            completed_at = None
            if status == "completed":
                completed_at = scheduled + timedelta(hours=random.randint(1, 3))

            iv = Interview(
                application_id=app.application_id,
                interview_round=rnd,
                interview_type=random.choice(INTERVIEW_TYPES),
                scheduled_at=scheduled,
                completed_at=completed_at,
                status=status,
            )
            session.add(iv)
            interviews.append(iv)
            count += 1

        if count % 200 == 0 and interviews:
            session.flush()

    session.flush()
    print(f"  Interviews: {len(interviews)}")
    return interviews


# ── Phase 7: Interviewer Assignments ─────────────────────────────────────────


def seed_interviewer_assignments(
    session: Session,
    interviews: list[Interview],
    employees: list[Employee],
    target: int = 4000,
) -> list[Interviewer]:
    """Assign employees as interviewers."""
    existing_pairs: set[tuple[int, int]] = set(
        session.execute(
            select(Interviewer.interview_id, Interviewer.employee_id)
        ).all()
    )

    assignments: list[Interviewer] = []
    count = 0

    for iv in interviews:
        if count >= target:
            break
        n = random.choices([1, 2, 3], weights=[0.35, 0.50, 0.15])[0]
        chosen = random.sample(employees, min(n, len(employees)))

        for emp in chosen:
            if count >= target:
                break
            pair = (iv.interview_id, emp.employee_id)
            if pair in existing_pairs:
                continue
            existing_pairs.add(pair)

            a = Interviewer(
                interview_id=iv.interview_id,
                employee_id=emp.employee_id,
            )
            session.add(a)
            assignments.append(a)
            count += 1

    session.flush()
    print(f"  Interviewer assignments: {len(assignments)}")
    return assignments


# ── Phase 8: Scorecards ───────────────────────────────────────────────────────


def seed_scorecards(
    session: Session,
    assignments: list[Interviewer],
    target: int = 2000,
) -> list[Scorecard]:
    """Create one scorecard per interviewer assignment for completed interviews."""
    completed_ids: set[int] = set(
        session.scalars(
            select(Interview.interview_id).where(Interview.status == "completed")
        ).all()
    )
    eligible = [a for a in assignments if a.interview_id in completed_ids]
    random.shuffle(eligible)

    existing_pairs: set[tuple[int, int]] = set(
        session.execute(
            select(Scorecard.interview_id, Scorecard.employee_id)
        ).all()
    )

    scorecards: list[Scorecard] = []

    for assignment in eligible:
        if len(scorecards) >= target:
            break
        pair = (assignment.interview_id, assignment.employee_id)
        if pair in existing_pairs:
            continue
        existing_pairs.add(pair)

        t = Decimal(str(round(random.uniform(3.0, 10.0), 2)))
        c = Decimal(str(round(random.uniform(3.0, 10.0), 2)))
        p = Decimal(str(round(random.uniform(3.0, 10.0), 2)))
        overall = ((t + c + p) / Decimal("3")).quantize(Decimal("0.01"))
        recommendation = random.choices(
            RECOMMENDATIONS, weights=RECOMMENDATION_WEIGHTS
        )[0]

        sc = Scorecard(
            interview_id=assignment.interview_id,
            employee_id=assignment.employee_id,
            technical_score=t,
            communication_score=c,
            problem_solving_score=p,
            overall_score=overall,
            recommendation=recommendation,
            feedback=random_sentence(nb_words=15),
        )
        session.add(sc)
        scorecards.append(sc)

    session.flush()
    print(f"  Scorecards: {len(scorecards)}")
    return scorecards


# ── Phase 9: Offers ───────────────────────────────────────────────────────────


def seed_offers(
    session: Session,
    apps: list[Application],
    requisitions: list[Requisition],
    employees: list[Employee],
    target: int = 1000,
) -> list[Offer]:
    """Generate offers for applications at offer/hired stage."""
    offer_eligible = {"offer", "hired"}
    eligible = [a for a in apps if a.current_stage in offer_eligible]
    random.shuffle(eligible)

    req_map: dict[int, Requisition] = {r.requisition_id: r for r in requisitions}
    existing_app_ids: set[int] = set(
        session.scalars(select(Offer.application_id)).all()
    )

    offers: list[Offer] = []

    for app in eligible:
        if len(offers) >= target:
            break
        if app.application_id in existing_app_ids:
            continue
        existing_app_ids.add(app.application_id)

        req = req_map.get(app.requisition_id)
        if req is None:
            continue

        today = date.today()
        min_offer = app.application_date + timedelta(days=20)
        if min_offer >= today:
            offer_date = today
        else:
            offer_date = random_date_between(min_offer, today)

        expiry_date = offer_date + timedelta(days=random.randint(7, 21))
        joining_date = offer_date + timedelta(days=random.randint(30, 90))

        sal_min = float(req.salary_min)
        sal_max = float(req.salary_max)
        offered_salary = Decimal(str(round(random.uniform(sal_min, sal_max), 2)))

        status = random.choices(OFFER_STATUSES, weights=OFFER_STATUS_WEIGHTS)[0]
        approved_by = None
        if status in ("approved", "released", "accepted", "rejected", "expired"):
            approved_by = random.choice(employees).employee_id

        offer = Offer(
            application_id=app.application_id,
            offered_salary=offered_salary,
            offer_date=offer_date,
            expiry_date=expiry_date,
            joining_date=joining_date,
            status=status,
            approved_by=approved_by,
        )
        session.add(offer)
        offers.append(offer)

    session.flush()
    print(f"  Offers: {len(offers)}")
    return offers


# ── Phase 10: Anomalous Records ───────────────────────────────────────────────


def seed_anomalous_records(
    session: Session,
    candidates: list[Candidate],
    requisitions: list[Requisition],
    employees: list[Employee],
    apps: list[Application],
) -> None:
    """
    Insert labelled anomalous records for anomaly-detection testing.
    Identifiable by the 'anomaly_' email prefix.

    Anomaly A01 – Overqualified candidate applied to entry-level role
    Anomaly A02 – Offer salary inflated 3.5× above salary_max
    """
    print("  Inserting anomalous records (labelled)...")

    # A01: Overqualified candidate
    entry_req = next(
        (r for r in requisitions if r.experience_max <= 3 and r.status == "open"),
        None,
    )
    if entry_req:
        existing_anom = session.scalar(
            select(Candidate).where(
                Candidate.email == "anomaly_overqualified@example.com"
            )
        )
        if not existing_anom:
            anom_cand = Candidate(
                full_name="Anomaly Overqualified",
                email="anomaly_overqualified@example.com",
                phone="+91 00000 00001",
                experience_years=Decimal("18.0"),
                highest_qualification="PhD",
                current_location="Hyderabad",
            )
            session.add(anom_cand)
            session.flush()

            existing_app = session.scalar(
                select(Application).where(
                    Application.candidate_id == anom_cand.candidate_id,
                    Application.requisition_id == entry_req.requisition_id,
                )
            )
            if not existing_app:
                anom_app = Application(
                    candidate_id=anom_cand.candidate_id,
                    requisition_id=entry_req.requisition_id,
                    application_date=date.today(),
                    current_stage="applied",
                    status="active",
                    source="LinkedIn",
                )
                session.add(anom_app)
                session.flush()

    # A02: Inflated offer
    offer_app = next(
        (a for a in apps if a.current_stage == "offer"),
        None,
    )
    if offer_app:
        req = session.get(Requisition, offer_app.requisition_id)
        existing_offer = session.scalar(
            select(Offer).where(Offer.application_id == offer_app.application_id)
        )
        if req and not existing_offer:
            inflated = Decimal(str(round(float(req.salary_max) * 3.5, 2)))
            today = date.today()
            anom_offer = Offer(
                application_id=offer_app.application_id,
                offered_salary=inflated,
                offer_date=today,
                expiry_date=today + timedelta(days=10),
                joining_date=today + timedelta(days=45),
                status="released",
                approved_by=employees[0].employee_id,
            )
            session.add(anom_offer)
            session.flush()

    print("  Anomalous records inserted.")


# ── Main orchestrator ─────────────────────────────────────────────────────────


def generate_all(
    *,
    n_candidates: int = 5000,
    n_applications: int = 8000,
    n_interviews: int = 2000,
    n_assignments: int = 4000,
    n_scorecards: int = 2000,
    n_offers: int = 1000,
    include_anomalies: bool = True,
) -> None:
    """
    Full pipeline: runs all phases inside a single session.
    Each phase is committed separately so that the next phase
    can query freshly persisted IDs.
    """
    print("\n========================================")
    print(" RecruitFlow Synthetic Data Generator")
    print("========================================\n")

    with Session(engine) as session:

        print("[1/9] Departments")
        with session.begin_nested():
            dept_map = seed_departments(session)
        session.commit()

        print("[2/9] Employees")
        with session.begin_nested():
            employees = seed_employees(session, dept_map)
        session.commit()
        employees = list(session.scalars(select(Employee)).all())

        print("[3/9] Requisitions")
        with session.begin_nested():
            requisitions = seed_requisitions(session, dept_map, employees)
        session.commit()
        requisitions = list(session.scalars(select(Requisition)).all())

        print("[4/9] Candidates")
        with session.begin_nested():
            candidates = seed_candidates(session, n_candidates)
        session.commit()
        candidates = list(session.scalars(select(Candidate)).all())

        print("[5/9] Applications + Stage History")
        with session.begin_nested():
            apps = seed_applications(
                session, candidates, requisitions, employees, n_applications
            )
        session.commit()
        apps = list(session.scalars(select(Application)).all())

        print("[6/9] Interviews")
        with session.begin_nested():
            interviews = seed_interviews(session, apps, n_interviews)
        session.commit()
        interviews = list(session.scalars(select(Interview)).all())

        print("[7/9] Interviewer Assignments")
        with session.begin_nested():
            assignments = seed_interviewer_assignments(
                session, interviews, employees, n_assignments
            )
        session.commit()
        assignments = list(session.scalars(select(Interviewer)).all())

        print("[8/9] Scorecards")
        with session.begin_nested():
            _sc = seed_scorecards(session, assignments, n_scorecards)
        session.commit()

        print("[9/9] Offers")
        with session.begin_nested():
            _of = seed_offers(session, apps, requisitions, employees, n_offers)
        session.commit()

        if include_anomalies:
            print("[+]   Anomalous Records")
            with session.begin_nested():
                seed_anomalous_records(
                    session, candidates, requisitions, employees, apps
                )
            session.commit()

    print("\n========================================")
    print(" Data generation completed successfully!")
    print("========================================\n")


if __name__ == "__main__":
    generate_all()
