# Makefile for Telegram Raffle Bot

.PHONY: help setup install clean run dev test db-init db-migrate db-reset check services-start services-stop lint format

# Default target
.DEFAULT_GOAL := help

help: ## Show this help message
	@echo "Telegram Raffle Bot - Available Commands:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

setup: ## Initial setup (install dependencies, create venv, .env)
	@./scripts/setup.sh

install: ## Install Python dependencies
	@pip install -r requirements.txt

clean: ## Clean temporary files and caches
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete
	@find . -type f -name "*.pyo" -delete
	@find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@echo "✓ Cleaned temporary files"

run: ## Run the bot
	@./scripts/run.sh

dev: ## Run bot in development mode with auto-reload
	@source venv/bin/activate && PYTHONPATH=. python app/main.py

test: ## Run tests
	@PYTHONPATH=. pytest tests/ -v

db-init: ## Initialize database
	@PYTHONPATH=. python scripts/init_db.py

db-migrate: ## Create new migration
	@PYTHONPATH=. alembic revision --autogenerate -m "$(msg)"

db-upgrade: ## Apply database migrations
	@PYTHONPATH=. alembic upgrade head

db-downgrade: ## Rollback last migration
	@PYTHONPATH=. alembic downgrade -1

db-reset: ## Reset database (WARNING: deletes all data)
	@echo "⚠️  This will delete all data!"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		psql -U postgres -c "DROP DATABASE IF EXISTS raffle_bot;"; \
		psql -U postgres -c "CREATE DATABASE raffle_bot;"; \
		PYTHONPATH=. python scripts/init_db.py; \
		echo "✓ Database reset complete"; \
	else \
		echo "Cancelled"; \
	fi

check: ## Check if services are running
	@./scripts/check_services.sh

services-start: ## Start PostgreSQL and Redis (macOS)
	@brew services start postgresql@16
	@brew services start redis
	@echo "✓ Services started"

services-stop: ## Stop PostgreSQL and Redis (macOS)
	@brew services stop postgresql@16
	@brew services stop redis
	@echo "✓ Services stopped"

services-restart: ## Restart PostgreSQL and Redis (macOS)
	@brew services restart postgresql@16
	@brew services restart redis
	@echo "✓ Services restarted"

install-services: ## Install PostgreSQL and Redis (macOS)
	@./scripts/install_services_macos.sh

lint: ## Run code linters
	@echo "Running flake8..."
	@flake8 app/ --count --select=E9,F63,F7,F82 --show-source --statistics || true
	@echo "Running pylint..."
	@pylint app/ --disable=all --enable=W,E || true

format: ## Format code with black
	@black app/
	@echo "✓ Code formatted"

logs: ## Show bot logs
	@tail -f logs/bot_$$(date +%Y-%m-%d).log

venv: ## Create virtual environment
	@python3 -m venv venv
	@echo "✓ Virtual environment created"
	@echo "Activate with: source venv/bin/activate"

requirements: ## Update requirements.txt
	@pip freeze > requirements.txt
	@echo "✓ requirements.txt updated"

docker-up: ## Start with Docker
	@docker-compose up -d
	@docker-compose logs -f bot

docker-down: ## Stop Docker containers
	@docker-compose down

docker-logs: ## Show Docker logs
	@docker-compose logs -f bot

docker-rebuild: ## Rebuild Docker containers
	@docker-compose down
	@docker-compose build --no-cache
	@docker-compose up -d

backup: ## Backup database
	@mkdir -p backups
	@pg_dump -U postgres raffle_bot > backups/backup_$$(date +%Y%m%d_%H%M%S).sql
	@echo "✓ Database backed up to backups/"

restore: ## Restore database from backup (usage: make restore file=backup.sql)
	@psql -U postgres raffle_bot < $(file)
	@echo "✓ Database restored from $(file)"
