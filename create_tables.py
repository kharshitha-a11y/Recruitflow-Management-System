from app.database import engine
from app.models.base import Base

from app.models import (
    Department,
    Employee,
    Requisition,
    Candidate,
    Application,
    ApplicationStageHistory,
    Interview,
    Interviewer,
    Scorecard,
    Offer
)


def create_tables():

    print("Creating database tables...")

    Base.metadata.create_all(bind=engine)

    print("Database tables created successfully!")


if __name__ == "__main__":
    create_tables()