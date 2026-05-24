# Aegis API

Use the project-local virtual environment for API development so dependency pins
do not collide with globally installed Python packages.

```bash
make venv
make dev
```

On Windows without `make`, run:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\uvicorn.exe app.main:app --reload --port 8000
```

For deployments, set `CORS_ORIGINS` to the comma-separated list of frontend
origins allowed to call the API, for example:

```env
CORS_ORIGINS=https://your-frontend.example.com
```
