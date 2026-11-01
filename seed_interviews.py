
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import engine

from app.models import (
    Candidate,
    Requisition,
    Application,
    Employee,
    Interview,
    Interviewer
)


def seed_interviews():

    with Session(engine) as session:

        with session.begin():

            print("Starting interview data generation...")

            # 1. Fetch employees who will conduct interviews
            interviewer_emails = [
                "arjun@recruitflow.com",
                "priya@recruitflow.com"
            ]

            employees = {}

            for email in interviewer_emails:

                employee = session.scalar(
                    select(Employee).where(
                        Employee.email == email
                    )
                )

                if employee is None:
                    raise ValueError(
                        f"Interviewer not found: {email}"
                    )

                employees[email] = employee

            # 2. Define interview records
            interview_data = [
                {
                    "candidate_email": "sai@example.com",
                    "job_title": "Python Developer",
                    "interview_type": "technical",
                    "interview_round": 1,
                    "interviewer_emails": [
                        "arjun@recruitflow.com"
                    ]
                },
                {
                    "candidate_email": "ananya@example.com",
                    "job_title": "Python Developer",
                    "interview_type": "technical",
                    "interview_round": 1,
                    "interviewer_emails": [
                        "arjun@recruitflow.com",
                        "priya@recruitflow.com"
                    ]
                },
                {
                    "candidate_email": "vikram@example.com",
                    "job_title": "Data Analyst",
                    "interview_type": "technical",
                    "interview_round": 1,
                    "interviewer_emails": [
                        "arjun@recruitflow.com"
                    ]
                }
            ]

            inserted_count = 0
            existing_count = 0
            assignments_created = 0

            # 3. Process interviews
            for data in interview_data:

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
                    raise ValueError(
                        "Candidate or requisition not found."
                    )

                application = session.scalar(
                    select(Application).where(
                        Application.candidate_id == candidate.candidate_id,
                        Application.requisition_id == requisition.requisition_id
                    )
                )

                if application is None:
                    raise ValueError(
                        f"Application not found for {candidate.full_name}"
                    )

                # 4. Check for existing interview
                interview = session.scalar(
                    select(Interview).where(
                        Interview.application_id == application.application_id,
                        Interview.interview_round == data["interview_round"]
                    )
                )

                if interview is None:

                    interview = Interview(
                        application_id=application.application_id,
                        interview_round=data["interview_round"],
                        interview_type=data["interview_type"],
                        scheduled_at=(
                            datetime.now(timezone.utc)
                            + timedelta(days=2)
                        ),
                        status="scheduled"
                    )

                    session.add(interview)
                    session.flush()

                    inserted_count += 1

                    print(
                        f"Created interview: {candidate.full_name} - "
                        f"{requisition.job_title}"
                    )

                else:
                    existing_count += 1

                    print(
                        f"Interview already exists: "
                        f"{candidate.full_name}"
                    )

                # 5. Assign interviewers
                for email in data["interviewer_emails"]:

                    employee = employees[email]

                    assignment = session.get(
                        Interviewer,
                        {
                            "interview_id": interview.interview_id,
                            "employee_id": employee.employee_id
                        }
                    )

                    if assignment is None:

                        session.add(
                            Interviewer(
                                interview_id=interview.interview_id,
                                employee_id=employee.employee_id
                            )
                        )

                        assignments_created += 1

            print("\nInterview generation summary:")
            print(f"New interviews: {inserted_count}")
            print(f"Existing interviews: {existing_count}")
            print(f"New interviewer assignments: {assignments_created}")

    print("\nInterview generation completed!")


if __name__ == "__main__":
    seed_interviews()
