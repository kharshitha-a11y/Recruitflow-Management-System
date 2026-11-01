# RecruitFlow Management System

A full-stack recruitment management platform designed to streamline and manage the complete recruitment lifecycle. RecruitFlow provides candidate management, application tracking, interview scheduling, offer management, anomaly monitoring, and interactive recruitment analytics.

## 🚀 Features

- **Interactive Dashboard** – View recruitment KPIs, hiring trends, pipeline performance, and analytics.
- **Candidate Management** – Search, view, and manage candidate profiles and application history.
- **Application Pipeline** – Track applications across multiple recruitment stages.
- **Requisition Management** – Create and manage job requisitions and monitor open positions.
- **Interview Management** – Schedule interviews, assign interviewers, and manage evaluation scorecards.
- **Offer Management** – Manage the complete offer lifecycle, including approval, release, acceptance, and rejection.
- **Anomaly Monitoring** – Detect and investigate data quality issues and recruitment anomalies.
- **REST API** – Comprehensive FastAPI backend with interactive Swagger documentation.
- **Dynamic Analytics** – Interactive charts and metrics powered by real-time PostgreSQL data.

## 🛠️ Technology Stack

### Frontend
- Streamlit
- Plotly

### Backend
- FastAPI
- Python

### Database
- PostgreSQL
- SQLAlchemy

### Testing & Deployment
- Pytest
- Docker
- Docker Compose

## 🏗️ Architecture

```text
User
  │
  ▼
Streamlit Frontend
  │
  ▼
FastAPI Backend
  │
  ▼
PostgreSQL Database
```

## 📁 Project Structure

```text
RecruitFlow/
├── frontend/              # Streamlit frontend application
│   ├── components/        # Reusable UI components
│   ├── pages/             # Application pages
│   └── api_client.py      # Backend API integration
│
├── backend/               # FastAPI backend application
│   ├── routers/           # API routes
│   ├── models/            # Database models
│   └── services/          # Business logic
│
├── tests/                 # Automated test suite
├── Dockerfile
├── docker-compose.yml
├── render.yaml
├── start_all.ps1
├── start_backend.ps1
├── start_frontend.ps1
└── README.md
```

## ⚙️ Getting Started

### Prerequisites

Make sure you have installed:

- Python
- PostgreSQL
- Git

### Run the Complete Application

Clone the repository:

```bash
git clone https://github.com/kharshitha-a11y/RecruitFlow-Management-System.git
cd RecruitFlow-Management-System
```

Start the complete application:

```powershell
.\start_all.ps1
```

Alternatively, start the services separately:

### Start the Backend

```powershell
.\start_backend.ps1
```

The FastAPI API will be available at:

- API: `http://localhost:8000`
- Swagger Documentation: `http://localhost:8000/docs`

### Start the Frontend

```powershell
.\start_frontend.ps1
```

The Streamlit application will be available at:

`http://localhost:8501`

## 🧪 Testing

Run the complete test suite:

```powershell
.\run_tests.ps1
```

The project includes automated tests for:

- Business rules
- API endpoints
- Database integrity
- Anomaly detection
- End-to-end workflows
- Frontend components

## 📊 Key Modules

| Module | Description |
|--------|-------------|
| Dashboard | Recruitment metrics and interactive analytics |
| Candidates | Candidate profile and application management |
| Applications | Multi-stage recruitment pipeline tracking |
| Requisitions | Job requisition and position management |
| Interviews | Interview scheduling and scorecard evaluation |
| Offers | Complete offer lifecycle management |
| Anomalies | Data quality and anomaly monitoring |

## 🔗 API Documentation

FastAPI provides interactive API documentation through Swagger UI:

`http://localhost:8000/docs`

## 📌 Project Highlights

- Full-stack application with a three-tier architecture
- Dynamic frontend connected to REST APIs
- PostgreSQL relational database
- Interactive data visualizations
- Recruitment lifecycle management
- Automated anomaly detection
- Comprehensive automated testing
- Docker-ready deployment configuration

## 👩‍💻 Author

**Harshitha**

AI & Machine Learning Undergraduate

---

⭐ If you found this project useful, consider giving it a star!