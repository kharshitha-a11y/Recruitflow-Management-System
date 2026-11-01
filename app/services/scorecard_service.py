"""
app/services/scorecard_service.py
=================================
Service layer for Interview Scorecard evaluation and calculation.
"""

from decimal import Decimal
from typing import Optional
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.business_rules import (
    BusinessRuleError,
    ConflictError,
    ResourceNotFoundError,
    calculate_overall_score,
    validate_scorecard_scores,
)
from app.models import Interview, Interviewer, Scorecard


def get_by_id(db: Session, scorecard_id: int) -> Optional[Scorecard]:
    """Return a single scorecard by primary key, or None."""
    return db.get(Scorecard, scorecard_id)


def get_by_interview(db: Session, interview_id: int) -> list[Scorecard]:
    """Return all scorecards submitted for a given interview."""
    return list(
        db.scalars(
            select(Scorecard).where(Scorecard.interview_id == interview_id)
        ).all()
    )


def get_all(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    interview_id: Optional[int] = None,
    employee_id: Optional[int] = None,
) -> list[Scorecard]:
    """Return a paginated list of scorecards with optional filters."""
    stmt = select(Scorecard).offset(skip).limit(limit)
    if interview_id is not None:
        stmt = stmt.where(Scorecard.interview_id == interview_id)
    if employee_id is not None:
        stmt = stmt.where(Scorecard.employee_id == employee_id)
    return list(db.scalars(stmt).all())


def create(
    db: Session,
    interview_id: int,
    employee_id: int,
    technical_score: Decimal,
    communication_score: Decimal,
    problem_solving_score: Decimal,
    overall_score: Optional[Decimal] = None,
    recommendation: str = "hire",
    feedback: Optional[str] = None,
) -> Scorecard:
    """
    Submit an interview evaluation scorecard.

    Enforces business rules:
      - Interview must exist (ResourceNotFoundError)
      - Employee must be assigned to this interview panel (BusinessRuleError)
      - Each assigned interviewer can submit at most one scorecard per interview (ConflictError)
      - Scorecard values must be strictly between 0 and 10 (BusinessRuleError)
      - If overall_score is omitted, it is calculated as the mean of component scores.
    """
    if not db.get(Interview, interview_id):
        raise ResourceNotFoundError(f"Interview ID {interview_id} not found.")

    # Business rule: Employee must be assigned as interviewer
    assignment = db.get(
        Interviewer,
        {"interview_id": interview_id, "employee_id": employee_id},
    )
    if not assignment:
        raise BusinessRuleError(
            f"Employee {employee_id} is not assigned to Interview {interview_id} and cannot submit a scorecard."
        )

    # Business rule: Duplicate scorecard prevention
    existing = db.scalar(
        select(Scorecard).where(
            Scorecard.interview_id == interview_id,
            Scorecard.employee_id == employee_id,
        )
    )
    if existing:
        raise ConflictError(
            f"Scorecard already submitted by Employee {employee_id} for Interview {interview_id}."
        )

    # Automatic calculation of overall score if omitted
    if overall_score is None:
        overall_score = calculate_overall_score(
            technical_score, communication_score, problem_solving_score
        )

    # Validate score values between 0 and 10
    score_errors = validate_scorecard_scores(
        technical_score, communication_score, problem_solving_score, overall_score
    )
    if score_errors:
        raise BusinessRuleError("; ".join(score_errors))

    scorecard = Scorecard(
        interview_id=interview_id,
        employee_id=employee_id,
        technical_score=technical_score,
        communication_score=communication_score,
        problem_solving_score=problem_solving_score,
        overall_score=overall_score,
        recommendation=recommendation.strip(),
        feedback=feedback.strip() if feedback else None,
    )
    db.add(scorecard)
    db.commit()
    db.refresh(scorecard)
    return scorecard


def get_interview_summary(db: Session, interview_id: int) -> dict:
    """
    Calculate overall evaluation scores across all interviewers for an interview.
    Returns averages and recommendation tallies.
    """
    if not db.get(Interview, interview_id):
        raise ResourceNotFoundError(f"Interview ID {interview_id} not found.")

    scorecards = get_by_interview(db, interview_id)
    if not scorecards:
        return {
            "interview_id": interview_id,
            "total_scorecards": 0,
            "average_technical_score": Decimal("0.0"),
            "average_communication_score": Decimal("0.0"),
            "average_problem_solving_score": Decimal("0.0"),
            "average_overall_score": Decimal("0.0"),
            "recommendations_summary": {},
        }

    total = len(scorecards)
    avg_tech = sum(Decimal(str(s.technical_score)) for s in scorecards) / Decimal(str(total))
    avg_comm = sum(Decimal(str(s.communication_score)) for s in scorecards) / Decimal(str(total))
    avg_prob = sum(Decimal(str(s.problem_solving_score)) for s in scorecards) / Decimal(str(total))
    avg_over = sum(Decimal(str(s.overall_score)) for s in scorecards) / Decimal(str(total))

    rec_counts: dict[str, int] = {}
    for s in scorecards:
        rec_counts[s.recommendation] = rec_counts.get(s.recommendation, 0) + 1

    return {
        "interview_id": interview_id,
        "total_scorecards": total,
        "average_technical_score": round(avg_tech, 2),
        "average_communication_score": round(avg_comm, 2),
        "average_problem_solving_score": round(avg_prob, 2),
        "average_overall_score": round(avg_over, 2),
        "recommendations_summary": rec_counts,
    }
