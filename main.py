"""
main.py
=======
RecruitFlow entry point forwarding to app.main:app.
Supports running via:
  uvicorn main:app --reload
  uvicorn app.main:app --reload
  python main.py
"""

from app.main import PROJECT_CONFIG, app

if __name__ == "__main__":
    import uvicorn

    print("RecruitFlow API is starting!")
    print("\nProject configuration:")
    for key, value in PROJECT_CONFIG.items():
        print(f"  {key}: {value}")

    print("\nStarting API server at http://localhost:8000")
    print("Interactive docs at  http://localhost:8000/docs\n")

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
