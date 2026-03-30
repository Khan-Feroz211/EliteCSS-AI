.PHONY: up down build logs logs-backend shell-backend shell-db migrate reset prod-up prod-down prod-build help

help:
	@echo "CSS Prep AI — available commands:"
	@echo "  make up            Start all services"
	@echo "  make down          Stop all services"
	@echo "  make build         Rebuild all Docker images"
	@echo "  make logs          Follow logs from all services"
	@echo "  make logs-backend  Follow backend logs only"
	@echo "  make migrate       Run database migrations"
	@echo "  make shell-backend Open shell inside backend container"
	@echo "  make shell-db      Open psql inside postgres container"
	@echo "  make reset         Stop, remove volumes, and restart fresh"

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

migrate:
	docker-compose exec backend alembic upgrade head

shell-backend:
	docker-compose exec backend /bin/bash

shell-db:
	docker-compose exec postgres psql -U $${POSTGRES_USER:-postgres} -d $${POSTGRES_DB:-css_prep_ai}

reset:
	docker-compose down -v
	docker-compose up -d --build

prod-up:
	docker-compose -f docker-compose.prod.yml up -d

prod-down:
	docker-compose -f docker-compose.prod.yml down

prod-build:
	docker-compose -f docker-compose.prod.yml build --no-cache
