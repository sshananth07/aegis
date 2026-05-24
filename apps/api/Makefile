PYTHON ?= python
VENV := .venv
ifeq ($(OS),Windows_NT)
	VENV_PYTHON := $(VENV)/Scripts/python.exe
	VENV_UVICORN := $(VENV)/Scripts/uvicorn.exe
	VENV_ALEMBIC := $(VENV)/Scripts/alembic.exe
else
	VENV_PYTHON := $(VENV)/bin/python
	VENV_UVICORN := $(VENV)/bin/uvicorn
	VENV_ALEMBIC := $(VENV)/bin/alembic
endif

venv:
	$(PYTHON) -m venv $(VENV)
	$(VENV_PYTHON) -m pip install --upgrade pip
	$(VENV_PYTHON) -m pip install -r requirements.txt

dev:
	$(VENV_UVICORN) app.main:app --reload --port 8000

migrate:
	$(VENV_ALEMBIC) upgrade head

migration:
	$(VENV_ALEMBIC) revision --autogenerate -m "$(name)"

check:
	$(VENV_PYTHON) -m compileall app
	$(VENV_PYTHON) -c "from fastapi.testclient import TestClient; from app.main import app; response = TestClient(app).get('/health'); assert response.status_code == 200"
