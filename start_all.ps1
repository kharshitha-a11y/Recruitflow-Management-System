# =============================================================================
# RecruitFlow – Start Full Stack Enterprise Environment (Single-URL Architecture)
# Launches FastAPI Backend (8000), Streamlit Frontend (8501), and
# Unified Reverse Proxy (10000) concurrently.
# =============================================================================

Write-Host "======================================================" -ForegroundColor Cyan
Write-Host "    RecruitFlow Enterprise Single-URL Architecture     " -ForegroundColor Cyan
Write-Host "======================================================" -ForegroundColor Cyan

# 1. Start FastAPI Backend (Port 8000)
Write-Host "[1/3] Launching FastAPI Backend on http://localhost:8000..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Write-Host 'RecruitFlow Backend Server (Port 8000)' -ForegroundColor Cyan; cd '$PSScriptRoot'; .venv\Scripts\uvicorn.exe app.main:app --port 8000 --reload"

# Wait 2 seconds for backend initialization
Start-Sleep -Seconds 2

# 2. Start Streamlit Frontend (Port 8501)
Write-Host "[2/3] Launching Streamlit Frontend on http://localhost:8501..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Write-Host 'RecruitFlow Streamlit UI (Port 8501)' -ForegroundColor Cyan; cd '$PSScriptRoot'; .venv\Scripts\streamlit.exe run frontend/app.py --server.port 8501 --server.headless true"

# Wait 2 seconds for frontend initialization
Start-Sleep -Seconds 2

# 3. Start Unified Reverse Proxy (Port 10000)
Write-Host "[3/3] Launching Unified Reverse Proxy on http://localhost:10000..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Write-Host 'RecruitFlow Unified Reverse Proxy (Port 10000)' -ForegroundColor Cyan; cd '$PSScriptRoot'; .venv\Scripts\python.exe proxy_server.py"

Write-Host ""
Write-Host "======================================================" -ForegroundColor Cyan
Write-Host "          ALL SERVICES LAUNCHED SUCCESSFULLY          " -ForegroundColor Green
Write-Host "======================================================" -ForegroundColor Cyan
Write-Host "  ★ UNIFIED APPLICATION URL : http://localhost:10000" -ForegroundColor Yellow
Write-Host "  • Streamlit Frontend UI   : http://localhost:10000/" -ForegroundColor White
Write-Host "  • FastAPI REST Endpoints  : http://localhost:10000/api/" -ForegroundColor White
Write-Host "  • Swagger Documentation   : http://localhost:10000/docs" -ForegroundColor White
Write-Host "  • ReDoc Documentation     : http://localhost:10000/redoc" -ForegroundColor White
Write-Host "  • API Health Endpoint     : http://localhost:10000/health" -ForegroundColor White
Write-Host "------------------------------------------------------" -ForegroundColor Gray
Write-Host "  (Direct Standalone Ports: Backend=8000, Frontend=8501)" -ForegroundColor DarkGray
Write-Host "======================================================" -ForegroundColor Cyan
