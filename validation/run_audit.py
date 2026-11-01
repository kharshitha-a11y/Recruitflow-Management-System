"""
validation/run_audit.py
=======================
CLI tool to run anomaly detection scan and output Data Quality Report.
"""

from sqlalchemy.orm import Session
from app.database import engine
from validation.validation_service import run_detection_and_persist


def main():
    print("=" * 60)
    print("RECRUITFLOW DATA QUALITY & ANOMALY DETECTION SCAN")
    print("=" * 60)

    with Session(engine) as session:
        report = run_detection_and_persist(session, save_to_db=True)

        print(f"\nTotal Records Inspected:    {report['total_records_inspected']:,}")
        for entity, count in report['records_inspected_by_entity'].items():
            print(f"  - {entity.capitalize():<16}: {count:,}")

        print(f"\nTotal Anomalies Found:       {report['total_anomalies_found']:,}")
        print(f"New Anomalies Stored:        {report['new_anomalies_detected']:,}")
        print(f"Previously Active:           {report['previously_existing_active_anomalies']:,}")
        print(f"Unique Anomalous Entities:   {report['unique_anomalous_entities']:,}")
        print(f"Clean Records Count:         {report['clean_records_count']:,}")
        print(f"DATA QUALITY PERCENTAGE:     {report['data_quality_percentage']:.2f}%")

        print("\nAnomalies by Severity:")
        for sev, count in report['anomalies_by_severity'].items():
            print(f"  - {sev:<10}: {count:,}")

        print("\nAnomalies by Rule Category:")
        for code, count in report['anomalies_by_category'].items():
            label = report['category_descriptions'].get(code, code)
            print(f"  - {code} ({label:<32}): {count:,}")

        print("\nAnomalies by Investigation Status:")
        for st, count in report['anomalies_by_status'].items():
            print(f"  - {st:<16}: {count:,}")

    print("\nScan completed successfully.")


if __name__ == "__main__":
    main()

