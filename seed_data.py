
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import engine

from app.models import (
    Department,
    Employee,
    Requisition,
    Candidate
)


def seed_master_data():

    with Session(engine) as session:

        with session.begin():

            print("Starting sample data insertion...")

            # 1. Departments
            departments = [
                "Engineering",
                "Human Resources"
            ]

            for name in departments:

                existing = session.scalar(
                    select(Department).where(
                        Department.department_name == name
                    )
                )

                if not existing:
                    session.add(
                        Department(department_name=name)
                    )

            session.flush()

            engineering = session.scalar(
                select(Department).where(
                    Department.department_name == "Engineering"
                )
            )

            hr = session.scalar(
                select(Department).where(
                    Department.department_name == "Human Resources"
                )
            )

            print("Departments processed.")

            # 2. Employees
            employees = [
                {
                    "full_name": "Rahul Sharma",
                    "email": "rahul@recruitflow.com",
                    "department_id": engineering.department_id,
                    "role": "Hiring Manager"
                },
                {
                    "full_name": "Priya Kumar",
                    "email": "priya@recruitflow.com",
                    "department_id": hr.department_id,
                    "role": "Recruiter"
                },
                {
                    "full_name": "Arjun Reddy",
                    "email": "arjun@recruitflow.com",
                    "department_id": engineering.department_id,
                    "role": "Interviewer"
                }
            ]

            for data in employees:

                existing = session.scalar(
                    select(Employee).where(
                        Employee.email == data["email"]
                    )
                )

                if not existing:
                    session.add(Employee(**data))

            session.flush()

            rahul = session.scalar(
                select(Employee).where(
                    Employee.email == "rahul@recruitflow.com"
                )
            )

            print("Employees processed.")

            # 3. Requisitions
            requisitions = [
                {
                    "job_title": "Python Developer",
                    "department_id": engineering.department_id,
                    "hiring_manager_id": rahul.employee_id,
                    "employment_type": "Full-time",
                    "location": "Hyderabad",
                    "openings": 3,
                    "experience_min": 0,
                    "experience_max": 2,
                    "salary_min": Decimal("300000"),
                    "salary_max": Decimal("600000"),
                    "status": "open"
                },
                {
                    "job_title": "Data Analyst",
                    "department_id": engineering.department_id,
                    "hiring_manager_id": rahul.employee_id,
                    "employment_type": "Full-time",
                    "location": "Bangalore",
                    "openings": 2,
                    "experience_min": 0,
                    "experience_max": 3,
                    "salary_min": Decimal("350000"),
                    "salary_max": Decimal("650000"),
                    "status": "open"
                }
            ]

            for data in requisitions:

                existing = session.scalar(
                    select(Requisition).where(
                        Requisition.job_title == data["job_title"],
                        Requisition.department_id == data["department_id"]
                    )
                )

                if not existing:
                    session.add(Requisition(**data))

            session.flush()

            print("Requisitions processed.")

            # 4. Candidates
            candidates = [
                {
                    "full_name": "Sai Kumar",
                    "email": "sai@example.com",
                    "phone": "9876543210",
                    "experience_years": Decimal("1.0"),
                    "highest_qualification": "B.Tech",
                    "current_location": "Hyderabad"
                },
                {
                    "full_name": "Ananya Reddy",
                    "email": "ananya@example.com",
                    "phone": "9876543211",
                    "experience_years": Decimal("0.5"),
                    "highest_qualification": "MCA",
                    "current_location": "Bangalore"
                },
                {
                    "full_name": "Vikram Singh",
                    "email": "vikram@example.com",
                    "phone": "9876543212",
                    "experience_years": Decimal("2.0"),
                    "highest_qualification": "B.Tech",
                    "current_location": "Hyderabad"
                }
            ]

            for data in candidates:

                existing = session.scalar(
                    select(Candidate).where(
                        Candidate.email == data["email"]
                    )
                )

                if not existing:
                    session.add(Candidate(**data))

            print("Candidates processed.")

        print("\nSample master data inserted successfully!")


if __name__ == "__main__":
    seed_master_data()
