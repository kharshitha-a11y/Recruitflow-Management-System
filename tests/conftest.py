"""
tests/conftest.py
=================
Shared pytest fixtures for the RecruitFlow API test suite.

Strategy
--------
* Uses an in-memory SQLite database with StaticPool so all connections share
  the same in-memory database and never touch PostgreSQL.
* Registers a SQLAlchemy DDL compiler override so that BigInteger columns
  are treated as INTEGER by SQLite for primary key autoincrement.
* Provides a lightweight ASGI test client that drives the FastAPI app
  without requiring httpx / httpx2.
* Session-scoped seed fixtures build a minimal dataset reused across tests.
"""

from __future__ import annotations

import asyncio
import json as json_module
import urllib.parse
from datetime import date, timedelta
from decimal import Decimal
from typing import Any, Optional

import pytest
from sqlalchemy import BigInteger, Integer, create_engine, event
from sqlalchemy.dialects.sqlite.base import SQLiteTypeCompiler
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

# ---------------------------------------------------------------------------
# SQLite DDL Type Overrides
# ---------------------------------------------------------------------------
# SQLite does NOT support BigInteger auto-increment; it needs INTEGER.
def _visit_big_integer(self, type_, **kw):
    return "INTEGER"

SQLiteTypeCompiler.visit_big_integer = _visit_big_integer


# ---------------------------------------------------------------------------
# SQLite-compatible test engine with StaticPool
# ---------------------------------------------------------------------------
TEST_ENGINE = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


@event.listens_for(TEST_ENGINE, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=TEST_ENGINE)


from app.database import get_db
from app.main import app as fastapi_app
from app.models.base import Base
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


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """Create all tables once per test session; drop them at the end."""
    Base.metadata.create_all(bind=TEST_ENGINE)
    yield
    Base.metadata.drop_all(bind=TEST_ENGINE)


@pytest.fixture()
def db_session(setup_test_database):
    """
    Per-test transactional session with rollback.
    """
    connection = TEST_ENGINE.connect()
    transaction = connection.begin()
    session = Session(bind=connection)
    yield session
    session.close()
    transaction.rollback()
    connection.close()


# ---------------------------------------------------------------------------
# Override the FastAPI DB dependency -> test DB
# ---------------------------------------------------------------------------

def override_get_db():
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


fastapi_app.dependency_overrides[get_db] = override_get_db


# ---------------------------------------------------------------------------
# Lightweight in-process ASGI test client (no httpx required)
# ---------------------------------------------------------------------------

class _Response:
    def __init__(self, status_code: int, headers: dict, body: bytes):
        self.status_code = status_code
        self.headers = headers
        self._body = body

    def json(self) -> Any:
        return json_module.loads(self._body.decode("utf-8"))

    @property
    def text(self) -> str:
        return self._body.decode("utf-8")


class ASGIClient:
    """Synchronous wrapper around an ASGI app for testing (no httpx needed)."""

    def __init__(self, asgi_app):
        self._app = asgi_app

    def _call(
        self,
        method: str,
        path: str,
        *,
        json: Optional[Any] = None,
        params: Optional[dict] = None,
    ) -> _Response:
        query_string = b""
        if params:
            cleaned = {k: str(v) for k, v in params.items() if v is not None}
            query_string = urllib.parse.urlencode(cleaned).encode("ascii")

        body = b""
        raw_headers: list[tuple[bytes, bytes]] = [(b"host", b"testserver")]
        if json is not None:
            body = json_module.dumps(json).encode("utf-8")
            raw_headers += [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode("ascii")),
            ]

        scope: dict = {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": method.upper(),
            "path": path,
            "raw_path": path.encode("ascii"),
            "query_string": query_string,
            "headers": raw_headers,
            "client": ("127.0.0.1", 9999),
            "server": ("testserver", 80),
        }

        messages: list[dict] = []
        request_sent = False

        async def _receive():
            nonlocal request_sent
            if not request_sent:
                request_sent = True
                return {"type": "http.request", "body": body, "more_body": False}
            return {"type": "http.disconnect"}

        async def _send(message: dict):
            messages.append(message)

        asyncio.run(self._app(scope, _receive, _send))

        status_code = 500
        resp_headers: dict = {}
        resp_body = b""
        for msg in messages:
            if msg["type"] == "http.response.start":
                status_code = msg["status"]
                resp_headers = {
                    k.decode("latin1"): v.decode("latin1")
                    for k, v in msg.get("headers", [])
                }
            elif msg["type"] == "http.response.body":
                resp_body += msg.get("body", b"")

        return _Response(status_code, resp_headers, resp_body)

    def get(self, path: str, *, params: Optional[dict] = None) -> _Response:
        return self._call("GET", path, params=params)

    def post(self, path: str, *, json: Optional[Any] = None) -> _Response:
        return self._call("POST", path, json=json)

    def patch(self, path: str, *, json: Optional[Any] = None) -> _Response:
        return self._call("PATCH", path, json=json)

    def put(self, path: str, *, json: Optional[Any] = None) -> _Response:
        return self._call("PUT", path, json=json)

    def delete(self, path: str) -> _Response:
        return self._call("DELETE", path)


@pytest.fixture(scope="session")
def client() -> ASGIClient:
    return ASGIClient(fastapi_app)


# ---------------------------------------------------------------------------
# Session-scoped seed fixtures (built directly via DB, not via API)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def seed_dept(setup_test_database) -> dict:
    db = TestSessionLocal()
    try:
        dept = Department(department_name="Test Engineering")
        db.add(dept)
        db.commit()
        db.refresh(dept)
        return {"department_id": dept.department_id, "department_name": dept.department_name}
    finally:
        db.close()


@pytest.fixture(scope="session")
def seed_manager(seed_dept) -> dict:
    db = TestSessionLocal()
    try:
        emp = Employee(
            department_id=seed_dept["department_id"],
            full_name="Test Manager",
            email="test.manager@recruitflow.test",
            role="Hiring Manager",
        )
        db.add(emp)
        db.commit()
        db.refresh(emp)
        return {"employee_id": emp.employee_id, "full_name": emp.full_name, "role": emp.role}
    finally:
        db.close()


@pytest.fixture(scope="session")
def seed_interviewer(seed_dept) -> dict:
    db = TestSessionLocal()
    try:
        emp = Employee(
            department_id=seed_dept["department_id"],
            full_name="Test Interviewer",
            email="test.interviewer@recruitflow.test",
            role="Interviewer",
        )
        db.add(emp)
        db.commit()
        db.refresh(emp)
        return {"employee_id": emp.employee_id}
    finally:
        db.close()


@pytest.fixture(scope="session")
def seed_requisition(seed_dept, seed_manager) -> dict:
    db = TestSessionLocal()
    try:
        req = Requisition(
            department_id=seed_dept["department_id"],
            hiring_manager_id=seed_manager["employee_id"],
            job_title="Test Software Engineer",
            employment_type="Full-time",
            location="Test City",
            openings=5,
            experience_min=1,
            experience_max=5,
            salary_min=Decimal("500000"),
            salary_max=Decimal("1000000"),
            status="open",
        )
        db.add(req)
        db.commit()
        db.refresh(req)
        return {"requisition_id": req.requisition_id}
    finally:
        db.close()


@pytest.fixture(scope="session")
def seed_candidate(setup_test_database) -> dict:
    db = TestSessionLocal()
    try:
        cand = Candidate(
            full_name="Test Candidate",
            email="test.candidate@example.test",
            phone="9000000001",
            experience_years=Decimal("3.0"),
            highest_qualification="B.Tech",
            current_location="Test City",
        )
        db.add(cand)
        db.commit()
        db.refresh(cand)
        return {"candidate_id": cand.candidate_id}
    finally:
        db.close()


@pytest.fixture(scope="session")
def seed_application(seed_candidate, seed_requisition) -> dict:
    db = TestSessionLocal()
    try:
        app_obj = Application(
            candidate_id=seed_candidate["candidate_id"],
            requisition_id=seed_requisition["requisition_id"],
            current_stage="applied",
            status="active",
            source="Test",
        )
        db.add(app_obj)
        db.flush()
        history = ApplicationStageHistory(
            application_id=app_obj.application_id,
            previous_stage=None,
            new_stage="applied",
            remarks="Test application.",
        )
        db.add(history)
        db.commit()
        db.refresh(app_obj)
        return {"application_id": app_obj.application_id}
    finally:
        db.close()


@pytest.fixture(scope="session")
def seed_interview(seed_application, seed_interviewer) -> dict:
    db = TestSessionLocal()
    try:
        from datetime import datetime, timezone
        iv = Interview(
            application_id=seed_application["application_id"],
            interview_round=1,
            interview_type="Technical Round",
            scheduled_at=datetime(2026, 12, 1, 10, 0, 0, tzinfo=timezone.utc),
            status="scheduled",
        )
        db.add(iv)
        db.flush()
        assignment = Interviewer(
            interview_id=iv.interview_id,
            employee_id=seed_interviewer["employee_id"],
        )
        db.add(assignment)
        db.commit()
        db.refresh(iv)
        return {
            "interview_id": iv.interview_id,
            "interviewer_employee_id": seed_interviewer["employee_id"],
        }
    finally:
        db.close()


@pytest.fixture(scope="session")
def seed_offer(seed_application, seed_manager) -> dict:
    db = TestSessionLocal()
    try:
        today = date.today()
        offer = Offer(
            application_id=seed_application["application_id"],
            offered_salary=Decimal("800000"),
            offer_date=today,
            expiry_date=today + timedelta(days=14),
            joining_date=today + timedelta(days=45),
            status="draft",
            approved_by=None,
        )
        db.add(offer)
        db.commit()
        db.refresh(offer)
        return {
            "offer_id": offer.offer_id,
            "manager_employee_id": seed_manager["employee_id"],
        }
    finally:
        db.close()
