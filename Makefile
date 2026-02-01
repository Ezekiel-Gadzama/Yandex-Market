.PHONY: help build up down logs restart clean dev prod

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

build: ## Build Docker images
	docker-compose build

up: ## Start containers in production mode
	docker-compose up -d

down: ## Stop containers
	docker-compose down

logs: ## View logs
	docker-compose logs -f

restart: ## Restart containers
	docker-compose restart

clean: ## Stop and remove containers, volumes
	docker-compose down -v

dev: ## Start in development mode with hot-reload
	docker-compose -f docker-compose.dev.yml up -d

dev-logs: ## View development logs
	docker-compose -f docker-compose.dev.yml logs -f

dev-down: ## Stop development containers
	docker-compose -f docker-compose.dev.yml down

rebuild: ## Rebuild and restart containers
	docker-compose up -d --build

shell-backend: ## Access backend container shell
	docker-compose exec backend bash

shell-frontend: ## Access frontend container shell
	docker-compose exec frontend sh

ps: ## Show running containers
	docker-compose ps
