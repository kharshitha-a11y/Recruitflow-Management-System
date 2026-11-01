
from sqlalchemy import inspect

from app.database import engine


EXPECTED_TABLES = {
    "departments",
    "employees",
    "requisitions",
    "candidates",
    "applications",
    "application_stage_history",
    "interviews",
    "interviewers",
    "scorecards",
    "offers"
}


def verify_schema():

    inspector = inspect(engine)

    existing_tables = set(
        inspector.get_table_names(schema="public")
    )

    missing_tables = EXPECTED_TABLES - existing_tables

    unexpected_tables = existing_tables - EXPECTED_TABLES

    print("\nRECRUITFLOW DATABASE VALIDATION")
    print("--------------------------------")

    print(f"Expected tables: {len(EXPECTED_TABLES)}")
    print(f"Existing tables: {len(existing_tables)}")

    for table in sorted(EXPECTED_TABLES):

        if table in existing_tables:
            print(f"[PASS] {table}")

        else:
            print(f"[FAIL] {table}")

    if missing_tables:
        print("\nMissing tables:", missing_tables)

    if unexpected_tables:
        print("\nAdditional tables:", unexpected_tables)

    if not missing_tables:
        print("\nDatabase schema validation successful!")

    else:
        print("\nDatabase schema validation failed!")


if __name__ == "__main__":
    verify_schema()
