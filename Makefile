.PHONY: install test lint format clean run simulate all

# Variables
PYTHON = python
PIP = pip
PYTEST = pytest
BLACK = black
ISORT = isort
FLAKE8 = flake8
MYPY = mypy

# Instalación
install:
	$(PIP) install -r requirements.txt

# Tests
test:
	$(PYTEST) tests/

# Linting y formateo
lint:
	$(FLAKE8) src/
	$(MYPY) src/

format:
	$(BLACK) src/
	$(ISORT) src/

# Limpieza
clean:
	find . -type d -name "__pycache__" -exec rm -r {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete
	find . -type f -name ".coverage" -delete
	find . -type d -name "*.egg-info" -exec rm -r {} +
	find . -type d -name "*.egg" -exec rm -r {} +
	find . -type d -name ".pytest_cache" -exec rm -r {} +
	find . -type d -name ".mypy_cache" -exec rm -r {} +

# Ejecución
run:
	$(PYTHON) -m streamlit run src/app.py

# Simulación
simulate:
	$(PYTHON) src/simulation/conveyor.py

# Docker
docker-build:
	docker build -t paletizacion_dhl .

docker-run:
	docker run -p 8501:8501 paletizacion_dhl

all: install lint test 