# RecruitFlow - Start FastAPI Backend Server
Write-Host "Starting RecruitFlow FastAPI backend on http://localhost:8000..." -ForegroundColor Green
Write-Host "Swagger UI available at: http://localhost:8000/docs" -ForegroundColor Yellow
& .venv\Scripts\uvicorn.exe app.main:app --port 8000 --reload

