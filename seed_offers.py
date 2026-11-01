
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import engine

from app.models import (
    Candidate,
    Requisition,
    Application,
    Employee,
    Offer,
    Scorecard,
    Interview
)


def seed_offers():

    with Session(engine) as session:

        with session.begin():

            print("Starting offer data generation...")

            offer_data = [
                {
                    "candidate_email": "sai@example.com",
                    "job_title": "Python Developer",
                    "salary": Decimal("550000.00"),
                    "status": "released",
                    "joining_days": 45
                },
                {
                    "candidate_email": "ananya@example.com",
                    "job_title": "Python Developer",
                    "salary": Decimal("500000.00"),
                    "status": "approved",
                    "joining_days": 45
                },
                {
                    "candidate_email": "vikram@example.com",
                    "job_title": "Data Analyst",
                    "salary": Decimal("450000.00"),
                    "status": "pending_approval",
                    "joining_days": 60
                }
            ]

            inserted_count = 0
            existing_count = 0

            manager = session.scalar(
                select(Employee).where(
                    Employee.email == "rahul@recruitflow.com"
                )
            )

            if manager is None:
                raise ValueError("Hiring manager not found.")

            for data in offer_data:

                candidate = session.scalar(
                    select(Candidate).where(
                        Candidate.email == data["candidate_email"]
                    )
                )

                requisition = session.scalar(
                    select(Requisition).where(
                        Requisition.job_title == data["job_title"]
                    )
                )

                if candidate is None or requisition is None:
                    raise ValueError("Candidate or job not found.")

                application = session.scalar(
                    select(Application).where(
                        Application.candidate_id == candidate.candidate_id,
                        Application.requisition_id == requisition.requisition_id
                    )
                )

                if application is None:
                    raise ValueError("Application not found.")

                # Verify that the candidate has an interview scorecard
                interview = session.scalar(
                    select(Interview).where(
                        Interview.application_id == application.application_id
                    )
                )

                if interview is None:
                    raise ValueError("Interview not found.")

                scorecard = session.scalar(
                    select(Scorecard).where(
                        Scorecard.interview_id == interview.interview_id
                    )
                )

                if scorecard is None:
                    raise ValueError("Scorecard not found.")

                # Check for an existing offer
                existing = session.scalar(
                    select(Offer).where(
                        Offer.application_id == application.application_id
                    )
                )

                if existing:
                    existing_count += 1
                    print(f"Offer already exists: {candidate.full_name}")
                    continue

                today = date.today()

                approved_by = (
                    manager.employee_id
                    if data["status"] in ("approved", "released")
                    else None
                )

                offer = Offer(
                    application_id=application.application_id,
                    offered_salary=data["salary"],
                    offer_date=today,
                    expiry_date=today + timedelta(days=10),
                    joining_date=today + timedelta(
                        days=data["joining_days"]
                    ),
                    status=data["status"],
                    approved_by=approved_by
                )

                session.add(offer)

                inserted_count += 1

                print(f"Created offer: {candidate.full_name}")

            print("\nOffer generation summary:")
            print(f"New offers: {inserted_count}")
            print(f"Existing offers: {existing_count}")

    print("\nOffer generation completed!")


if __name__ == "__main__":
    seed_offers()
