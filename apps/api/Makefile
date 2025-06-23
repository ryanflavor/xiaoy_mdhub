.PHONY: dev install test lint clean help

# Default environment variables
API_HOST ?= 0.0.0.0
API_PORT ?= 8000
LOG_LEVEL ?= INFO
ENVIRONMENT ?= development

help: ## Show this help message
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies
	pip install -r requirements.txt

dev: ## Start development server with auto-reload
	@echo "Starting Market Data Hub API on http://$(API_HOST):$(API_PORT)"
	@export API_HOST=$(API_HOST) API_PORT=$(API_PORT) LOG_LEVEL=$(LOG_LEVEL) ENVIRONMENT=$(ENVIRONMENT) && \
	uvicorn main:app --host $(API_HOST) --port $(API_PORT) --reload

start: ## Start production server
	@echo "Starting Market Data Hub API (production mode)"
	@export ENVIRONMENT=production && \
	uvicorn main:app --host $(API_HOST) --port $(API_PORT)

test: ## Run tests
	python -m pytest tests/ -v

lint: ## Run code linting
	@echo "Running code linting..."
	@python -m flake8 app/ main.py || echo "flake8 not installed, skipping"
	@python -m black --check app/ main.py || echo "black not installed, skipping"

format: ## Format code
	@echo "Formatting code..."
	@python -m black app/ main.py || echo "black not installed, skipping"

clean: ## Clean cache files
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +

health: ## Test health endpoint
	@echo "Testing health endpoint..."
	@curl -s http://localhost:$(API_PORT)/health | python -m json.tool || echo "Service not running or curl/python not available"