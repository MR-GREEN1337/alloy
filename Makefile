.PHONY: install backend web all stop

install:
	@echo "Installing dependencies for all services"
	cd backend && uv sync
	cd web && npm install --force

all:
	backend web

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
