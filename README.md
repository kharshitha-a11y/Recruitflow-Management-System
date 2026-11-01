RecruitFlow -- Recruitment Management System
A full-stack recruitment management platform that helps teams manage the
recruitment lifecycle---from job requisitions and candidate tracking to
interviews, offers, and recruitment analytics.

Live application:
https://recruitflow-management-system.onrender.com\
API documentation:
https://recruitflow-management-system.onrender.com/docs\
Source code:
https://github.com/kharshitha-a11y/Recruitflow-Management-System
Features
- Recruitment dashboard -- View recruitment KPIs, hiring trends,
  and pipeline metrics.
- Candidate management -- Maintain candidate profiles and track
  their application history.
- Application pipeline -- Track candidates through recruitment
  stages.
- Requisition management -- Create and manage job openings and
  hiring requirements.
- Interview management -- Schedule interviews, assign
  interviewers, and manage scorecards.
- Offer management -- Track offer preparation and outcomes.
- Anomaly monitoring -- Identify and review recruitment
  data-quality issues.
- REST API -- FastAPI endpoints with interactive Swagger
  documentation.
- Interactive analytics -- Streamlit dashboards and Plotly
  visualizations backed by PostgreSQL.
Technology Stack
  Layer                   Technologies
  Frontend                Streamlit, Plotly
Backend                 Python, FastAPI
Database                PostgreSQL, SQLAlchemy
Testing                 Pytest
Deployment              Docker, Docker Compose, Render
Web serving / routing   Nginx, Supervisor
Architecture
The Streamlit interface communicates with the FastAPI backend. FastAPI
uses SQLAlchemy to access the PostgreSQL database.
User
  |
  v
Streamlit frontend
  |
  v
FastAPI REST API
  |
  v
SQLAlchemy
  |
  v
PostgreSQL
In the hosted deployment, Nginx routes frontend and API traffic through
a single public Render URL.
Project Structure
Recruitflow-Management-System/
├── app/                    # FastAPI application and backend modules
├── frontend/               # Streamlit interface, pages and components
├── generator/              # Data / project generation utilities
├── tests/                  # Automated tests and test fixtures
├── validation/             # Validation utilities
├── create_tables.py        # Database table creation
├── seed_data.py            # Master/sample data seeding
├── seed_applications.py    # Application sample data
├── seed_interviews.py      # Interview sample data
├── seed_offers.py          # Offer sample data
├── seed_scorecards.py      # Scorecard sample data
├── verify_schema.py        # Database schema verification
├── verify_full_system.py   # Full-system verification script
├── requirements.txt        # Python dependencies
├── Dockerfile
├── docker-compose.yml
├── render.yaml
├── nginx.conf
├── supervisord.conf
├── entrypoint.sh
├── start_all.ps1
├── start_backend.ps1
├── start_frontend.ps1
├── run_tests.ps1
├── .env.example
└── README.md
Run Locally (Windows / PowerShell)
1. Prerequisites
- Python 3.11 (recommended for the pinned dependencies)
- PostgreSQL
- Git
2. Clone the repository
git clone https://github.com/kharshitha-a11y/Recruitflow-Management-System.git
cd Recruitflow-Management-System
3. Create and activate a virtual environment
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
4. Install dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt
5. Configure environment variables
Copy the example file:
Copy-Item .env.example .env
Edit .env with your local PostgreSQL database details. For example:
DB_HOST=localhost
DB_PORT=5432
DB_NAME=recruitflow
DB_USER=postgres
DB_PASSWORD=replace_with_your_local_password
Create the recruitflow database in PostgreSQL before continuing. Keep
.env private; never commit real credentials.
6. Create tables and load sample data
python create_tables.py
python seed_data.py
Optional sample data scripts are available for applications, interviews,
offers, and scorecards. Run them only when you want the corresponding
sample records.
7. Start the application
Start both services using the project script:
.\start_all.ps1
Alternatively, start the services separately in two PowerShell
terminals:
.\start_backend.ps1
.\start_frontend.ps1
The local services are expected at:
- Streamlit frontend: http://localhost:8501
- FastAPI backend: http://localhost:8000
- Swagger API docs: http://localhost:8000/docs
Deployment
The project includes a Dockerfile, docker-compose.yml,
render.yaml, Nginx configuration, and Supervisor configuration for
deployment.

The hosted instance is available at:
- Application: https://recruitflow-management-system.onrender.com
- API health check:
  https://recruitflow-management-system.onrender.com/health
- Swagger docs:
  https://recruitflow-management-system.onrender.com/docs
The deployed service requires its own PostgreSQL database and
environment variables configured in the hosting platform. Do not place
database credentials in source control.
Testing and Validation
Run the project's test script from PowerShell:
.\run_tests.ps1
Database schema validation:
python verify_schema.py
A full-system verification script is also included:
python verify_full_system.py
The full-system verification script may require environment and database
configuration matching the target environment. Test results should be
confirmed in the environment where the checks are run.
Main Modules
  Module         Purpose
  Dashboard      Recruitment KPIs and analytics
Candidates     Candidate profiles and history
Requisitions   Job openings and hiring requirements
Applications   Recruitment-stage tracking
Interviews     Scheduling and evaluation
Offers         Offer lifecycle tracking
Anomalies      Recruitment data-quality monitoring
Security Notes
- Store secrets in environment variables or the hosting provider's
  secret configuration.
- Do not commit .env, database passwords, API keys, or production
  connection strings.
- Use .env.example as a template only.
Author
Harshitha
