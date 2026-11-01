"""
app/schemas/__init__.py
=======================
Central export of all Pydantic request and response schemas.
"""

from app.schemas.common import OrmBase, MessageResponse
from app.schemas.department import DepartmentCreate, DepartmentResponse
from app.schemas.employee import EmployeeCreate, EmployeeResponse
from app.schemas.requisition import (
    RequisitionCreate,
    RequisitionUpdate,
    RequisitionStatusUpdate,
    RequisitionResponse,
    VALID_REQUISITION_STATUSES,
)
from app.schemas.candidate import (
    CandidateCreate,
    CandidateUpdate,
    CandidateResponse,
)
from app.schemas.application import (
    ApplicationCreate,
    ApplicationStageAdvance,
    ApplicationResponse,
    StageHistoryResponse,
    VALID_APPLICATION_STAGES,
)
from app.schemas.interview import (
    InterviewCreate,
    InterviewScheduleUpdate,
    InterviewStatusUpdate,
    InterviewReschedule,
    InterviewCompletion,
    InterviewerAssignCreate,
    InterviewerResponse,
    InterviewResponse,
    VALID_INTERVIEW_STATUSES,
)
from app.schemas.scorecard import (
    ScorecardCreate,
    ScorecardResponse,
    ScorecardSummaryResponse,
    VALID_RECOMMENDATIONS,
)
from app.schemas.offer import (
    OfferCreate,
    OfferUpdate,
    OfferStatusUpdate,
    OfferApprovalAction,
    OfferCandidateDecision,
    OfferResponse,
    OfferExpiryCheckResponse,
    VALID_OFFER_STATUSES,
)
from app.schemas.anomaly import (
    AnomalyResponse,
    AnomalyStatusUpdate,
    DataQualityReportResponse,
    AnomalyDetectionRunResponse,
    VALID_ANOMALY_STATUSES,
    VALID_SEVERITIES,
)
from app.schemas.analytics import (
    AnalyticsOverviewResponse,
    DepartmentRequisitions,
    MonthlyTrend,
)

__all__ = [
    "OrmBase",
    "MessageResponse",
    "DepartmentCreate",
    "DepartmentResponse",
    "EmployeeCreate",
    "EmployeeResponse",
    "RequisitionCreate",
    "RequisitionUpdate",
    "RequisitionStatusUpdate",
    "RequisitionResponse",
    "VALID_REQUISITION_STATUSES",
    "CandidateCreate",
    "CandidateUpdate",
    "CandidateResponse",
    "ApplicationCreate",
    "ApplicationStageAdvance",
    "ApplicationResponse",
    "StageHistoryResponse",
    "VALID_APPLICATION_STAGES",
    "InterviewCreate",
    "InterviewScheduleUpdate",
    "InterviewStatusUpdate",
    "InterviewReschedule",
    "InterviewCompletion",
    "InterviewerAssignCreate",
    "InterviewerResponse",
    "InterviewResponse",
    "VALID_INTERVIEW_STATUSES",
    "ScorecardCreate",
    "ScorecardResponse",
    "ScorecardSummaryResponse",
    "VALID_RECOMMENDATIONS",
    "OfferCreate",
    "OfferUpdate",
    "OfferStatusUpdate",
    "OfferApprovalAction",
    "OfferCandidateDecision",
    "OfferResponse",
    "OfferExpiryCheckResponse",
    "VALID_OFFER_STATUSES",
    "AnomalyResponse",
    "AnomalyStatusUpdate",
    "DataQualityReportResponse",
    "AnomalyDetectionRunResponse",
    "VALID_ANOMALY_STATUSES",
    "VALID_SEVERITIES",
    "AnalyticsOverviewResponse",
    "DepartmentRequisitions",
    "MonthlyTrend",
]
