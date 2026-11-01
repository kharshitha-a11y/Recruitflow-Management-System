
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import engine

from app.models import (
    Candidate,
    Requisition,
    Application,
    Interview,
    Employee,
    Interviewer,
    Scorecard
)


def seed_scorecards():

    with Session(engine) as session:

        with session.begin():

            print("Starting scorecard data generation...")

            # 1. Define interviewer evaluations
            evaluations = [
                {
                    "candidate_email": "sai@example.com",
                    "job_title": "Python Developer",
                    "interviewer_email": "arjun@recruitflow.com",
                    "technical_score": Decimal("9.00"),
                    "communication_score": Decimal("8.00"),
                    "problem_solving_score": Decimal("9.00"),
                    "recommendation": "strong_hire",
                    "feedback": "Strong Python fundamentals and problem-solving."
                },
                {
                    "candidate_email": "ananya@example.com",
                    "job_title": "Python Developer",
                    "interviewer_email": "arjun@recruitflow.com",
                    "technical_score": Decimal("8.00"),
                    "communication_score": Decimal("8.00"),
                    "problem_solving_score": Decimal("7.00"),
                    "recommendation": "hire",
                    "feedback": "Good technical knowledge and communication."
                },
                {
                    "candidate_email": "ananya@example.com",
                    "job_title": "Python Developer",
                    "interviewer_email": "priya@recruitflow.com",
                    "technical_score": Decimal("9.00"),
                    "communication_score": Decimal("8.00"),
                    "problem_solving_score": Decimal("9.00"),
                    "recommendation": "strong_hire",
                    "feedback": "Excellent overall performance."
                },
                {
                    "candidate_email": "vikram@example.com",
                    "job_title": "Data Analyst",
                    "interviewer_email": "arjun@recruitflow.com",
                    "technical_score": Decimal("7.00"),
                    "communication_score": Decimal("8.00"),
                    "problem_solving_score": Decimal("7.00"),
                    "recommendation": "hold",
                    "feedback": "Good communication; needs improvement in technical skills."
                }
            ]

            inserted_count = 0
            existing_count = 0

            # 2. Process each evaluation
            for data in evaluations:

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

                employee = session.scalar(
                    select(Employee).where(
                        Employee.email == data["interviewer_email"]
                    )
                )

                if not candidate or not requisition or not employee:
                    raise ValueError(
                        "Candidate, requisition or interviewer missing."
                    )

                # 3. Find application
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

                # 4. Find interview
                interview = session.scalar(
                    select(Interview).where(
                        Interview.application_id == application.application_id,
                        Interview.interview_round == 1
                    )
                )

                if interview is None:
                    raise ValueError(
                        f"Interview not found for {candidate.full_name}"
                    )

                # 5. Verify interviewer assignment
                assignment = session.get(
                    Interviewer,
                    {
                        "interview_id": interview.interview_id,
                        "employee_id": employee.employee_id
                    }
                )

                if assignment is None:
                    raise ValueError(
                        f"{employee.full_name} is not assigned to "
                        f"{candidate.full_name}'s interview."
                    )

                # 6. Check existing scorecard
                existing = session.scalar(
                    select(Scorecard).where(
                        Scorecard.interview_id == interview.interview_id,
                        Scorecard.employee_id == employee.employee_id
                    )
                )

                if existing:
                    existing_count += 1
                    print(
                        f"Scorecard already exists: "
                        f"{candidate.full_name} - {employee.full_name}"
                    )
                    continue

                # 7. Calculate overall score
                overall_score = (
                    data["technical_score"]
                    + data["communication_score"]
                    + data["problem_solving_score"]
                ) / Decimal("3")

                overall_score = overall_score.quantize(
                    Decimal("0.01")
                )

                # 8. Create scorecard
                scorecard = Scorecard(
                    interview_id=interview.interview_id,
                    employee_id=employee.employee_id,
                    technical_score=data["technical_score"],
                    communication_score=data["communication_score"],
                    problem_solving_score=data["problem_solving_score"],
                    overall_score=overall_score,
                    recommendation=data["recommendation"],
                    feedback=data["feedback"]
                )

                session.add(scorecard)

                inserted_count += 1

                print(
                    f"Created scorecard: {candidate.full_name} - "
                    f"{employee.full_name}"
                )

            print("\nScorecard generation summary:")
            print(f"New scorecards: {inserted_count}")
            print(f"Existing scorecards: {existing_count}")

    print("\nScorecard generation completed!")


if __name__ == "__main__":
    seed_scorecards()
