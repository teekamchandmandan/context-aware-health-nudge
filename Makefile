.PHONY: setup dev

setup:
	@echo "Setting up backend..."
	cd server && python3 -m venv .venv
	cd server && .venv/bin/pip install -r requirements.txt
	@if [ ! -f server/.env ]; then cp server/.env.example server/.env; echo "Created server/.env from template"; fi
	@echo "Seeding/Restoring the database..."
	cd server && .venv/bin/python -m app.seed
	@echo "Setting up client..."
	cd client && npm install

dev:
	@echo "Starting both frontend and backend in parallel..."
	@cd server && .venv/bin/uvicorn app.main:app --reload & cd client && npm run dev & wait
