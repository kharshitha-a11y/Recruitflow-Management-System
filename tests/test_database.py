"""
tests/test_database.py
========================
Part 1 test suite for RecruitFlow.

Tests:
  - Database connectivity
  - All 10 tables exist
  - Model relationships
  - Primary key and foreign key structure (via SQLAlchemy inspect)
  - Unique constraints
  - Data generation (generator module)
  - Data integrity (no orphan FKs, no duplicate pairs)

Run:
  pytest tests/test_database.py -v
"""

from __future__ import annotations

import random
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest
from sqlalchemy import inspect, select, text
from sqlalchemy.orm import Session

from app.database import engine, get_db
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
from app.business_rules import (
    validate_application,
    validate_interview_assignment,
    validate_offer,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture(scope="session")
def db():
    """Provide a real database session for the entire test session."""
    with Session(engine) as session:
        yield session


# ── 1. Database connectivity ──────────────────────────────────────────────────


class TestDatabaseConnectivity:

    def test_engine_connects(self):
        """Engine can connect and execute a simple query."""
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            assert result.scalar() == 1

    def test_get_db_yields_session(self):
        """get_db() dependency yields a working Session."""
        gen = get_db()
        session = next(gen)
        try:
            result = session.execute(text("SELECT 1")).scalar()
            assert result == 1
        finally:
            try:
                next(gen)
            except StopIteration:
                pass


# ── 2. Schema verification ────────────────────────────────────────────────────


EXPECTED_TABLES = {
    "departments",
    "employees",
    "requisitions",
    "candidates",
    "applications",
    "application_stage_history",
    "interviews",
    "interviewers",
    "scorecards",
    "offers",
}


class TestSchema:

    def test_all_expected_tables_exist(self):
        """All 10 required tables must exist in the public schema."""
        inspector = inspect(engine)
        existing = set(inspector.get_table_names(schema="public"))
        missing = EXPECTED_TABLES - existing
        assert missing == set(), f"Missing tables: {missing}"

    def test_departments_primary_key(self):
        inspector = inspect(engine)
        pk = inspector.get_pk_constraint("departments")
        assert "department_id" in pk["constrained_columns"]

    def test_employees_primary_key(self):
        inspector = inspect(engine)
        pk = inspector.get_pk_constraint("employees")
        assert "employee_id" in pk["constrained_columns"]

    def test_employees_fk_to_departments(self):
        inspector = inspect(engine)
        fks = inspector.get_foreign_keys("employees")
        referred = [fk["referred_table"] for fk in fks]
        assert "departments" in referred

    def test_requisitions_fk_to_departments(self):
        inspector = inspect(engine)
        fks = inspector.get_foreign_keys("requisitions")
        referred = [fk["referred_table"] for fk in fks]
        assert "departments" in referred

    def test_requisitions_fk_to_employees(self):
        inspector = inspect(engine)
        fks = inspector.get_foreign_keys("requisitions")
        referred = [fk["referred_table"] for fk in fks]
        assert "employees" in referred

    def test_applications_unique_constraint_exists(self):
        inspector = inspect(engine)
        uqs = inspector.get_unique_constraints("applications")
        uq_cols = [set(u["column_names"]) for u in uqs]
        assert {"candidate_id", "requisition_id"} in uq_cols

    def test_interviews_unique_constraint_exists(self):
        inspector = inspect(engine)
        uqs = inspector.get_unique_constraints("interviews")
        uq_cols = [set(u["column_names"]) for u in uqs]
        assert {"application_id", "interview_round"} in uq_cols

    def test_scorecards_fk_to_interviewers(self):
        inspector = inspect(engine)
        fks = inspector.get_foreign_keys("scorecards")
        referred = [fk["referred_table"] for fk in fks]
        assert "interviewers" in referred

    def test_offers_fk_to_applications(self):
        inspector = inspect(engine)
        fks = inspector.get_foreign_keys("offers")
        referred = [fk["referred_table"] for fk in fks]
        assert "applications" in referred


# ── 3. Model relationships ────────────────────────────────────────────────────


class TestModelRelationships:

    def test_department_has_employees_relationship(self, db):
        dept = db.scalar(select(Department).limit(1))
        if dept is None:
            pytest.skip("No departments in database")
        assert hasattr(dept, "employees")

    def test_department_has_requisitions_relationship(self, db):
        dept = db.scalar(select(Department).limit(1))
        if dept is None:
            pytest.skip("No departments in database")
        assert hasattr(dept, "requisitions")

    def test_employee_has_department_relationship(self, db):
        emp = db.scalar(select(Employee).limit(1))
        if emp is None:
            pytest.skip("No employees in database")
        assert hasattr(emp, "department")

    def test_application_has_candidate_relationship(self, db):
        app = db.scalar(select(Application).limit(1))
        if app is None:
            pytest.skip("No applications in database")
        assert hasattr(app, "candidate")

    def test_application_has_requisition_relationship(self, db):
        app = db.scalar(select(Application).limit(1))
        if app is None:
            pytest.skip("No applications in database")
        assert hasattr(app, "requisition")

    def test_application_has_stage_history_relationship(self, db):
        app = db.scalar(select(Application).limit(1))
        if app is None:
            pytest.skip("No applications in database")
        assert hasattr(app, "stage_history")

    def test_interview_has_application_relationship(self, db):
        iv = db.scalar(select(Interview).limit(1))
        if iv is None:
            pytest.skip("No interviews in database")
        assert hasattr(iv, "application")

    def test_interviewer_has_interview_relationship(self, db):
        assignment = db.scalar(select(Interviewer).limit(1))
        if assignment is None:
            pytest.skip("No interviewer assignments in database")
        assert hasattr(assignment, "interview")

    def test_scorecard_has_interviewer_record_relationship(self, db):
        sc = db.scalar(select(Scorecard).limit(1))
        if sc is None:
            pytest.skip("No scorecards in database")
        assert hasattr(sc, "interviewer_record")

    def test_offer_has_application_relationship(self, db):
        offer = db.scalar(select(Offer).limit(1))
        if offer is None:
            pytest.skip("No offers in database")
        assert hasattr(offer, "application")


# ── 4. Data counts (post-generation) ─────────────────────────────────────────


class TestDataCounts:

    def test_department_count(self, db):
        from sqlalchemy import func
        count = db.scalar(select(func.count()).select_from(Department))
        assert count >= 5, f"Expected >= 5 departments, got {count}"

    def test_employee_count(self, db):
        from sqlalchemy import func
        count = db.scalar(select(func.count()).select_from(Employee))
        assert count >= 30, f"Expected >= 30 employees, got {count}"

    def test_requisition_count(self, db):
        from sqlalchemy import func
        count = db.scalar(select(func.count()).select_from(Requisition))
        assert count >= 200, f"Expected >= 200 requisitions, got {count}"

    def test_candidate_count(self, db):
        from sqlalchemy import func
        count = db.scalar(select(func.count()).select_from(Candidate))
        assert count >= 5000, f"Expected >= 5000 candidates, got {count}"

    def test_application_count(self, db):
        from sqlalchemy import func
        count = db.scalar(select(func.count()).select_from(Application))
        assert count >= 8000, f"Expected >= 8000 applications, got {count}"

    def test_stage_history_count(self, db):
        from sqlalchemy import func
        count = db.scalar(select(func.count()).select_from(ApplicationStageHistory))
        assert count > 0, "Expected stage history records"

    def test_interview_count(self, db):
        from sqlalchemy import func
        count = db.scalar(select(func.count()).select_from(Interview))
        assert count >= 1000, f"Expected >= 1000 interviews, got {count}"

    def test_interviewer_assignment_count(self, db):
        from sqlalchemy import func
        count = db.scalar(select(func.count()).select_from(Interviewer))
        assert count >= 1000, f"Expected >= 1000 assignments, got {count}"

    def test_scorecard_count(self, db):
        from sqlalchemy import func
        count = db.scalar(select(func.count()).select_from(Scorecard))
        assert count > 0, "Expected scorecard records"

    def test_offer_count(self, db):
        from sqlalchemy import func
        count = db.scalar(select(func.count()).select_from(Offer))
        assert count > 0, "Expected offer records"


# ── 5. Data integrity ─────────────────────────────────────────────────────────


class TestDataIntegrity:

    def test_no_orphan_employees(self, db):
        """Every employee must belong to an existing department."""
        orphans = db.scalars(
            select(Employee).where(
                ~select(Department)
                .where(Department.department_id == Employee.department_id)
                .correlate(Employee)
                .exists()
            )
        ).all()
        assert len(orphans) == 0, f"Found {len(orphans)} orphan employees"

    def test_no_orphan_applications(self, db):
        """Every application must link to an existing candidate and requisition."""
        orphan_cands = db.scalars(
            select(Application).where(
                ~select(Candidate)
                .where(Candidate.candidate_id == Application.candidate_id)
                .correlate(Application)
                .exists()
            )
        ).all()
        assert len(orphan_cands) == 0

        orphan_reqs = db.scalars(
            select(Application).where(
                ~select(Requisition)
                .where(Requisition.requisition_id == Application.requisition_id)
                .correlate(Application)
                .exists()
            )
        ).all()
        assert len(orphan_reqs) == 0

    def test_no_duplicate_candidate_requisition_pairs(self, db):
        """No two applications should share the same (candidate_id, requisition_id)."""
        result = db.execute(
            text("""
                SELECT candidate_id, requisition_id, COUNT(*) as cnt
                FROM applications
                GROUP BY candidate_id, requisition_id
                HAVING COUNT(*) > 1
                LIMIT 5
            """)
        ).all()
        assert len(result) == 0, f"Found {len(result)} duplicate pairs"

    def test_no_duplicate_interview_rounds(self, db):
        """No two interviews should share (application_id, interview_round)."""
        result = db.execute(
            text("""
                SELECT application_id, interview_round, COUNT(*) as cnt
                FROM interviews
                GROUP BY application_id, interview_round
                HAVING COUNT(*) > 1
                LIMIT 5
            """)
        ).all()
        assert len(result) == 0, f"Found {len(result)} duplicate interview rounds"

    def test_interview_rounds_are_positive(self, db):
        """Interview rounds must be > 0."""
        bad = db.scalars(
            select(Interview).where(Interview.interview_round <= 0)
        ).all()
        assert len(bad) == 0

    def test_scorecards_belong_to_assigned_interviewers(self, db):
        """Every scorecard (interview_id, employee_id) must have an interviewers row."""
        result = db.execute(
            text("""
                SELECT s.scorecard_id
                FROM scorecards s
                LEFT JOIN interviewers i
                  ON s.interview_id = i.interview_id
                 AND s.employee_id  = i.employee_id
                WHERE i.interview_id IS NULL
                LIMIT 5
            """)
        ).all()
        assert len(result) == 0, f"Found {len(result)} scorecards without assignments"

    def test_offer_dates_are_valid(self, db):
        """expiry_date >= offer_date and joining_date >= offer_date."""
        bad_expiry = db.execute(
            text("SELECT offer_id FROM offers WHERE expiry_date < offer_date LIMIT 5")
        ).all()
        assert len(bad_expiry) == 0

        bad_joining = db.execute(
            text("""
                SELECT offer_id FROM offers
                WHERE joining_date IS NOT NULL AND joining_date < offer_date
                LIMIT 5
            """)
        ).all()
        assert len(bad_joining) == 0

    def test_salary_ranges_are_consistent(self, db):
        """salary_max >= salary_min for all requisitions."""
        bad = db.execute(
            text("SELECT requisition_id FROM requisitions WHERE salary_max < salary_min LIMIT 5")
        ).all()
        assert len(bad) == 0

    def test_candidate_emails_unique(self, db):
        """No two candidates share an email."""
        result = db.execute(
            text("""
                SELECT email, COUNT(*) FROM candidates
                GROUP BY email HAVING COUNT(*) > 1
                LIMIT 5
            """)
        ).all()
        assert len(result) == 0

    def test_employee_emails_unique(self, db):
        """No two employees share an email."""
        result = db.execute(
            text("""
                SELECT email, COUNT(*) FROM employees
                GROUP BY email HAVING COUNT(*) > 1
                LIMIT 5
            """)
        ).all()
        assert len(result) == 0

    def test_offers_one_per_application(self, db):
        """Each application has at most one offer."""
        result = db.execute(
            text("""
                SELECT application_id, COUNT(*) FROM offers
                GROUP BY application_id HAVING COUNT(*) > 1
                LIMIT 5
            """)
        ).all()
        assert len(result) == 0

    def test_scorecards_unique_per_interviewer_per_interview(self, db):
        """Each (interview_id, employee_id) has at most one scorecard."""
        result = db.execute(
            text("""
                SELECT interview_id, employee_id, COUNT(*)
                FROM scorecards
                GROUP BY interview_id, employee_id
                HAVING COUNT(*) > 1
                LIMIT 5
            """)
        ).all()
        assert len(result) == 0


# ── 6. Data generation module ─────────────────────────────────────────────────


class TestDataGenerationModule:

    def test_generator_module_importable(self):
        """The generator package must be importable."""
        from generator import synthetic_data  # noqa: F401

    def test_make_name_returns_string(self):
        from generator.synthetic_data import make_name
        name = make_name()
        assert isinstance(name, str)
        assert len(name) > 3
        assert " " in name

    def test_make_email_returns_valid_format(self):
        from generator.synthetic_data import make_email
        email = make_email("Rahul Sharma", "1")
        assert "@" in email
        assert "." in email.split("@")[1]

    def test_weighted_choice_returns_valid_item(self):
        from generator.synthetic_data import weighted_choice
        choices = [("a", 0.5), ("b", 0.3), ("c", 0.2)]
        for _ in range(20):
            result = weighted_choice(choices)
            assert result in ("a", "b", "c")

    def test_random_date_between(self):
        from generator.synthetic_data import random_date_between
        start = date(2024, 1, 1)
        end = date(2024, 12, 31)
        for _ in range(10):
            d = random_date_between(start, end)
            assert start <= d <= end

    def test_random_sentence_returns_string(self):
        from generator.synthetic_data import random_sentence
        s = random_sentence(10)
        assert isinstance(s, str)
        assert len(s) > 5
