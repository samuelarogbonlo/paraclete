.PHONY: help setup backend mobile test clean all

help:
	@echo "Paraclete Development Commands"
	@echo "=============================="
	@echo "make setup    - Install dependencies (Python + Flutter)"
	@echo "make backend  - Start backend (FastAPI + PostgreSQL + Redis)"
	@echo "make mobile   - Run Flutter mobile app"
	@echo "make test     - Run all tests (backend + mobile)"
	@echo "make all      - Start backend + mobile together"
	@echo "make clean    - Stop services and clean up"

setup:
	@echo "Creating Python virtual environment..."
	cd backend && python3 -m venv venv
	@echo "Installing Python dependencies..."
	cd backend && . venv/bin/activate && pip install -r requirements.txt
	@echo "Installing Flutter dependencies..."
	cd mobile && flutter pub get
	@echo "Setup complete!"

backend:
	@echo "Starting backend services (FastAPI + PostgreSQL + Redis)..."
	cd backend && docker-compose up

mobile:
	@echo "Running Flutter mobile app..."
	cd mobile && flutter run

test:
	@echo "Running backend tests..."
	cd backend && . venv/bin/activate && python -m pytest
	@echo "Running mobile tests..."
	cd mobile && flutter test
	@echo "All tests complete!"

all:
	@echo "Starting full stack..."
	@make -j2 backend mobile

clean:
	@echo "Stopping services..."
	cd backend && docker-compose down
	@echo "Cleaned up!"
