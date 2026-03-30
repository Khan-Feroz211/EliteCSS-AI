.PHONY: up down build logs logs-backend logs-mlflow logs-prometheus logs-grafana shell-backend shell-db migrate reset prod-up prod-down prod-build mlflow grafana prometheus help

help:
	@echo "CSS Prep AI — available commands:"
	@echo "  make up               Start all services"
	@echo "  make down             Stop all services"
	@echo "  make build            Rebuild all Docker images"
	@echo "  make logs             Follow logs from all services"
	@echo "  make logs-backend     Follow backend logs only"
	@echo "  make logs-mlflow      Follow MLflow logs"
	@echo "  make logs-prometheus  Follow Prometheus logs"
	@echo "  make logs-grafana     Follow Grafana logs"
	@echo "  make migrate          Run database migrations"
	@echo "  make shell-backend    Open shell inside backend container"
	@echo "  make shell-db         Open psql inside postgres container"
	@echo "  make reset            Stop, remove volumes, and restart fresh"
	@echo "  make mlflow           Open MLflow UI"
	@echo "  make grafana          Open Grafana UI"
	@echo "  make prometheus       Open Prometheus UI"

up:
	docker-compose up -d

down:
	docker-compose down

build:
	docker-compose build --no-cache

logs:
	docker-compose logs -f

logs-backend:
	docker-compose logs -f backend

logs-mlflow:
	docker-compose logs -f mlflow

logs-prometheus:
	docker-compose logs -f prometheus

logs-grafana:
	docker-compose logs -f grafana

migrate:
	docker-compose exec backend alembic upgrade head

shell-backend:
	docker-compose exec backend /bin/bash

shell-db:
	docker-compose exec postgres psql -U $${POSTGRES_USER:-postgres} -d $${POSTGRES_DB:-css_prep_ai}

reset:
	docker-compose down -v
	docker-compose up -d --build

mlflow:
	open http://localhost:5001

grafana:
	open http://localhost:3001

prometheus:
	open http://localhost:9090

prod-up:
	docker-compose -f docker-compose.prod.yml up -d

prod-down:
	docker-compose -f docker-compose.prod.yml down

prod-build:
	docker-compose -f docker-compose.prod.yml build --no-cache
