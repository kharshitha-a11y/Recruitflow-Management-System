"""
app/api/routes/analytics.py
===========================
REST API endpoints providing recruitment analytics and KPI metrics.
"""

from typing import Annotated, Any
from fastapi import APIRouter, Depends
from sqlalchemy import String, case, func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    Application,
    Candidate,
    Department,
    Interview,
    Offer,
    Requisition,
    Scorecard,
)
from app.schemas.analytics import (
    AnalyticsOverviewResponse,
    DepartmentRequisitions,
    MonthlyTrend,
)

router = APIRouter(prefix="/analytics", tags=["Analytics & KPIs"])
DBSession = Annotated[Session, Depends(get_db)]


@router.get(
    "/overview",
    response_model=AnalyticsOverviewResponse,
    summary="Recruitment analytics and dashboard overview",
    description=(
        "Returns executive-level recruitment metrics: candidate and requisition counts, "
        "pipeline stages, recruitment channels, interview outcomes, offer acceptance rates, "
        "and hiring conversion benchmarks."
    ),
)
def get_analytics_overview(db: DBSession) -> AnalyticsOverviewResponse:
    # 1. High-level counts
    total_candidates = db.scalar(select(func.count(Candidate.candidate_id))) or 0
    total_requisitions = db.scalar(select(func.count(Requisition.requisition_id))) or 0
    open_positions = (
        db.scalar(
            select(func.count(Requisition.requisition_id)).where(
                Requisition.status == "open"
            )
        )
        or 0
    )
    total_applications = db.scalar(select(func.count(Application.application_id))) or 0
    interviews_scheduled = (
        db.scalar(
            select(func.count(Interview.interview_id)).where(
                Interview.status.in_(["scheduled", "completed"])
            )
        )
        or 0
    )
    offers_released = (
        db.scalar(
            select(func.count(Offer.offer_id)).where(
                Offer.status.in_(["released", "accepted", "declined"])
            )
        )
        or 0
    )
    hired_count = (
        db.scalar(
            select(func.count(Application.application_id)).where(
                Application.current_stage == "hired"
            )
        )
        or 0
    )
    accepted_offers = (
        db.scalar(
            select(func.count(Offer.offer_id)).where(Offer.status == "accepted")
        )
        or 0
    )

    # 2. Conversion and Time-to-Hire
    conversion_rate = (
        round((hired_count / total_applications) * 100.0, 2)
        if total_applications > 0
        else 0.0
    )

    # Time to hire: calculate average days between offer_date and application created_at for accepted offers
    # Cross-database fallback calculation
    avg_days = 0.0
    accepted_offer_rows = db.execute(
        select(Offer.offer_date, Application.created_at)
        .join(Application, Offer.application_id == Application.application_id)
        .where(Offer.status == "accepted")
    ).all()

    if accepted_offer_rows:
        diffs: list[float] = []
        for o_date, a_created in accepted_offer_rows:
            if o_date and a_created:
                c_date = (
                    a_created.date() if hasattr(a_created, "date") else a_created
                )
                diff_days = abs((o_date - c_date).days)
                diffs.append(float(diff_days))
        if diffs:
            avg_days = round(sum(diffs) / len(diffs), 1)

    # 3. Applications by Stage
    stage_rows = db.execute(
        select(
            Application.current_stage, func.count(Application.application_id)
        ).group_by(Application.current_stage)
    ).all()
    apps_by_stage = {str(stage or "unspecified"): count for stage, count in stage_rows}

    # 4. Applications by Recruitment Source
    source_rows = db.execute(
        select(Application.source, func.count(Application.application_id)).group_by(
            Application.source
        )
    ).all()
    apps_by_source = {str(source or "Direct / Unspecified"): count for source, count in source_rows}

    # 5. Monthly Trends
    month_col = func.substr(func.cast(Application.created_at, String), 1, 7)
    trend_rows = db.execute(
        select(
            month_col.label("month"),
            func.count(Application.application_id),
            func.coalesce(
                func.sum(case((Application.current_stage == "hired", 1), else_=0)), 0
            ),
        )
        .group_by(month_col)
        .order_by(month_col.asc())
        .limit(12)
    ).all()
    hiring_trends = [
        MonthlyTrend(month=str(m), applications=int(app_cnt), hires=int(hire_cnt))
        for m, app_cnt, hire_cnt in trend_rows
    ]

    # 6. Requisitions by Department
    dept_stmt = (
        select(
            Department.department_name,
            func.count(Requisition.requisition_id),
            func.coalesce(
                func.sum(case((Requisition.status == "open", 1), else_=0)), 0
            ),
        )
        .outerjoin(Requisition, Department.department_id == Requisition.department_id)
        .group_by(Department.department_name)
    )
    dept_rows = db.execute(dept_stmt).all()
    reqs_by_dept = [
        DepartmentRequisitions(
            department_name=d_name,
            total_requisitions=int(tot),
            open_requisitions=int(op),
        )
        for d_name, tot, op in dept_rows
    ]

    # 7. Interview Outcomes (Scorecard recommendations)
    outcome_rows = db.execute(
        select(Scorecard.recommendation, func.count(Scorecard.scorecard_id)).group_by(
            Scorecard.recommendation
        )
    ).all()
    interview_outcomes = {rec: count for rec, count in outcome_rows if rec}

    # 8. Offer Status Breakdown and Acceptance Rate
    offer_status_rows = db.execute(
        select(Offer.status, func.count(Offer.offer_id)).group_by(Offer.status)
    ).all()
    offer_status_breakdown = {status: count for status, count in offer_status_rows}

    decisioned_offers = (
        offer_status_breakdown.get("accepted", 0)
        + offer_status_breakdown.get("rejected", 0)
        + offer_status_breakdown.get("expired", 0)
        + offer_status_breakdown.get("released", 0)
    )
    offer_acceptance_rate = (
        round((accepted_offers / decisioned_offers) * 100.0, 2)
        if decisioned_offers > 0
        else 0.0
    )

    return AnalyticsOverviewResponse(
        total_candidates=total_candidates,
        total_requisitions=total_requisitions,
        open_positions=open_positions,
        total_applications=total_applications,
        interviews_scheduled=interviews_scheduled,
        offers_released=offers_released,
        hiring_conversion_rate=conversion_rate,
        avg_time_to_hire_days=avg_days,
        applications_by_stage=apps_by_stage,
        applications_by_source=apps_by_source,
        hiring_trends=hiring_trends,
        requisitions_by_department=reqs_by_dept,
        interview_outcomes=interview_outcomes,
        offer_status_breakdown=offer_status_breakdown,
        offer_acceptance_rate=offer_acceptance_rate,
    )
