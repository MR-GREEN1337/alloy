.PHONY: install backend web all stop db-migrate db-upgrade db-downgrade

install:
	@echo "Installing dependencies for all services"
	cd backend && uv sync
	cd web && npm install --force

all:
	backend web

ifeq ($(M),)
  MIGRATION_MESSAGE = "auto-migration"
else
  MIGRATION_MESSAGE = "$(M)"
endif

db-migrate:
	@echo "  > Generating new database migration: $(MIGRATION_MESSAGE)..."
	@cd backend && .venv/bin/alembic revision --autogenerate -m "$(MIGRATION_MESSAGE)"

db-upgrade:
	@echo "  > Applying database migrations..."
	@cd backend && .venv/bin/alembic upgrade head

db-downgrade:
	@echo "  > Reverting last database migration..."
	@cd backend && .venv/bin/alembic downgrade -1

backend:
	@echo "Starting backend"
	cd backend && python3.13 -m uvicorn src.main:app --reload --port 8000 --proxy-headers --forwarded-allow-ips "*" &

web:
	@echo "Starting web"
	cd web && npm run dev &

stop:
	@echo "Stopping all services"
	@echo "Stopping backend"
	-pkill -f 'uvicorn.*8000'

	@echo "Stopping web"
	-pkill -f 'node.*web'

	@echo "\033[1;32m🛑🛑🛑 Everything stopped\033[0m"
