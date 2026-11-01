
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import engine

from app.models import (
    Candidate,
    Requisition,
    Employee,
    Application,
    ApplicationStageHistory
)


def seed_applications():

    with Session(engine) as session:

        with session.begin():

            print("Starting application data generation...")

            # 1. Fetch candidates
            candidates = {
                email: session.scalar(
                    select(Candidate).where(
                        Candidate.email == email
                    )
                )
                for email in [
                    "sai@example.com",
                    "ananya@example.com",
                    "vikram@example.com"
                ]
            }

            # 2. Fetch requisitions
            requisitions = {
                title: session.scalar(
                    select(Requisition).where(
                        Requisition.job_title == title
                    )
                )
                for title in [
                    "Python Developer",
                    "Data Analyst"
                ]
            }

            # 3. Fetch recruiter
            recruiter = session.scalar(
                select(Employee).where(
                    Employee.email == "priya@recruitflow.com"
                )
            )

            # 4. Validate master data
            if any(value is None for value in candidates.values()):
                raise ValueError("One or more candidates are missing.")

            if any(value is None for value in requisitions.values()):
                raise ValueError("One or more requisitions are missing.")

            if recruiter is None:
                raise ValueError("Recruiter Priya was not found.")

            # 5. Define application records
            application_data = [
                {
                    "candidate_email": "sai@example.com",
                    "job_title": "Python Developer",
                    "source": "LinkedIn"
                },
                {
                    "candidate_email": "sai@example.com",
                    "job_title": "Data Analyst",
                    "source": "Company Website"
                },
                {
                    "candidate_email": "ananya@example.com",
                    "job_title": "Python Developer",
                    "source": "Internshala"
                },
                {
                    "candidate_email": "vikram@example.com",
                    "job_title": "Data Analyst",
                    "source": "Referral"
                }
            ]

            inserted_count = 0
            existing_count = 0

            # 6. Insert applications
            for data in application_data:

                candidate = candidates[data["candidate_email"]]
                requisition = requisitions[data["job_title"]]

                existing = session.scalar(
                    select(Application).where(
                        Application.candidate_id == candidate.candidate_id,
                        Application.requisition_id == requisition.requisition_id
                    )
                )

                if existing:
                    existing_count += 1
                    print(
                        f"Already exists: {candidate.full_name} - "
                        f"{requisition.job_title}"
                    )
                    continue

                application = Application(
                    candidate_id=candidate.candidate_id,
                    requisition_id=requisition.requisition_id,
                    current_stage="applied",
                    status="active",
                    source=data["source"]
                )

                session.add(application)
                session.flush()

                # 7. Create initial stage history
                history = ApplicationStageHistory(
                    application_id=application.application_id,
                    previous_stage=None,
                    new_stage="applied",
                    changed_by=recruiter.employee_id,
                    remarks="Application received successfully."
                )

                session.add(history)

                inserted_count += 1

                print(
                    f"Created application: {candidate.full_name} - "
                    f"{requisition.job_title}"
                )

            print("\nApplication generation summary:")
            print(f"New applications: {inserted_count}")
            print(f"Already existing: {existing_count}")

    print("\nApplication data generation completed!")


if __name__ == "__main__":
    seed_applications()
