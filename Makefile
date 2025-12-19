# ChainReaction Makefile
# Common commands for Docker and development

.PHONY: help docker-build docker-up docker-down docker-logs docker-clean dev install test lint

# Default target
help:
	@echo "ChainReaction - Available Commands"
	@echo "==================================="
	@echo ""
	@echo "Docker Commands:"
	@echo "  make docker-build    Build all Docker images"
	@echo "  make docker-up       Start all services in detached mode"
	@echo "  make docker-down     Stop all services"
	@echo "  make docker-logs     View logs from all services"
	@echo "  make docker-clean    Stop services and remove volumes"
	@echo ""
	@echo "Development Commands:"
	@echo "  make install         Install Python dependencies"
	@echo "  make dev             Start development servers"
	@echo "  make test            Run tests"
	@echo "  make lint            Run linter"
	@echo ""

# ============================================
# Docker Commands
# ============================================

# Build all Docker images
docker-build:
	docker compose build

# Start all services
docker-up:
	docker compose up -d

# Start with build
docker-up-build:
	docker compose up -d --build

# Stop all services
docker-down:
	docker compose down

# View logs
docker-logs:
	docker compose logs -f

# View logs for specific service
docker-logs-backend:
	docker compose logs -f backend

docker-logs-frontend:
	docker compose logs -f frontend

docker-logs-neo4j:
	docker compose logs -f neo4j

# Clean up everything including volumes
docker-clean:
	docker compose down -v --rmi local
	docker system prune -f

# Restart a specific service
docker-restart-backend:
	docker compose restart backend

docker-restart-frontend:
	docker compose restart frontend

# ============================================
# Development Commands
# ============================================

# Install dependencies
install:
	pip install -e ".[dev]"
	cd frontend && npm install

# Start development servers
dev:
	@echo "Starting backend..."
	python -m uvicorn src.api.main:app --reload &
	@echo "Starting frontend..."
	cd frontend && npm run dev

# Run tests
test:
	pytest tests/ -v

# Run linter
lint:
	ruff check src/ scripts/
	cd frontend && npm run lint

# ============================================
# Data Commands
# ============================================

# Generate small dataset
data-small:
	python scripts/seed_database.py small

# Generate medium dataset
data-medium:
	python scripts/seed_database.py medium

# Generate large dataset
data-large:
	python scripts/seed_database.py large
