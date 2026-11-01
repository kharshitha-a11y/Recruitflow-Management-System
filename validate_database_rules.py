from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import engine
from app.models import (
    Application,
    Candidate,
    Requisition,
    Interview,
    Interviewer,
    Offer,
)

from app.business_rules import (
    validate_application,
    validate_interview_assignment,
    validate_offer,
)


def validate_database_records():
    total_checks = 0
    total_errors = 0

    with Session(engine) as session:

        # 1. Validate applications
        print("\n========== APPLICATION VALIDATION ==========")

        application_records = session.execute(
            select(Application, Candidate, Requisition)
            .join(Candidate, Application.candidate_id == Candidate.candidate_id)
            .join(Requisition, Application.requisition_id == Requisition.requisition_id)
        ).all()

        for application, candidate, requisition in application_records:
            errors = validate_application(candidate, requisition)
            total_checks += 1

            if errors:
                total_errors += len(errors)
                print(f"[FAIL] Application ID: {application.application_id}")
                for error in errors:
                    print("  -", error)
            else:
                print(f"[PASS] Application ID: {application.application_id}")

        # 2. Validate interviewer assignments
        print("\n========== INTERVIEW VALIDATION ==========")

        interview_records = session.execute(
            select(Interview, Interviewer)
            .join(
                Interviewer,
                Interview.interview_id == Interviewer.interview_id
            )
        ).all()

        for interview, interviewer in interview_records:
            errors = validate_interview_assignment(interview, interviewer)
            total_checks += 1

            if errors:
                total_errors += len(errors)
                print(f"[FAIL] Interview ID: {interview.interview_id}")
                for error in errors:
                    print("  -", error)
            else:
                print(f"[PASS] Interview ID: {interview.interview_id}")

        # 3. Validate offers
        print("\n========== OFFER VALIDATION ==========")

        offers = session.scalars(select(Offer)).all()

        for offer in offers:
            errors = validate_offer(offer)
            total_checks += 1

            if errors:
                total_errors += len(errors)
                print(f"[FAIL] Offer ID: {offer.offer_id}")
                for error in errors:
                    print("  -", error)
            else:
                print(f"[PASS] Offer ID: {offer.offer_id}")

    print("\n========== VALIDATION SUMMARY ==========")
    print("Total records checked:", total_checks)
    print("Total validation errors:", total_errors)

    if total_errors == 0:
        print("All business rules passed!")
    else:
        print("Some business rule violations were found.")

        
if __name__ == "__main__":
    validate_database_records()