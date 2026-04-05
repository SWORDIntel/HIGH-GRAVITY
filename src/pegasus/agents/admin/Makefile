# Claude Agent Communication System - Administration Tools Makefile
# Comprehensive build, test, and deployment automation
# Supports development, testing, and production environments

.PHONY: help install build test lint clean deploy monitor backup status

# ============================================================================
# CONFIGURATION
# ============================================================================

PYTHON := python3
PIP := pip3
DOCKER := docker
DOCKER_COMPOSE := docker-compose
KUBECTL := kubectl

# Project configuration
PROJECT_NAME := claude-agent-admin
VERSION := $(shell python setup.py --version 2>/dev/null || echo "1.0.0")
BUILD_DIR := build
DIST_DIR := dist
VENV_DIR := venv

# Docker configuration
DOCKER_REGISTRY := ghcr.io/claude-agents
DOCKER_TAG := $(VERSION)
DOCKER_PLATFORMS := linux/amd64,linux/arm64

# Kubernetes configuration
K8S_NAMESPACE := claude-agents
K8S_CONTEXT := $(shell kubectl config current-context 2>/dev/null || echo "default")

# Environment detection
ifdef CI
	ENVIRONMENT := ci
else ifdef PRODUCTION
	ENVIRONMENT := production
else
	ENVIRONMENT := development
endif

# Color codes for output
RED := \033[31m
GREEN := \033[32m
YELLOW := \033[33m
BLUE := \033[34m
MAGENTA := \033[35m
CYAN := \033[36m
WHITE := \033[37m
RESET := \033[0m

# ============================================================================
# HELP TARGET
# ============================================================================

help: ## Show this help message
	@echo "$(CYAN)Claude Agent Communication System - Administration Tools$(RESET)"
	@echo "$(CYAN)==========================================================$(RESET)"
	@echo ""
	@echo "$(GREEN)Available commands:$(RESET)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "$(BLUE)%-20s$(RESET) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(GREEN)Environment:$(RESET) $(ENVIRONMENT)"
	@echo "$(GREEN)Version:$(RESET)     $(VERSION)"
	@echo "$(GREEN)Python:$(RESET)      $(shell $(PYTHON) --version 2>/dev/null || echo 'Not found')"
	@echo "$(GREEN)Docker:$(RESET)      $(shell $(DOCKER) --version 2>/dev/null || echo 'Not found')"
	@echo "$(GREEN)Kubernetes:$(RESET)  $(shell $(KUBECTL) version --client --short 2>/dev/null || echo 'Not found')"

# ============================================================================
# DEVELOPMENT ENVIRONMENT
# ============================================================================

venv: ## Create Python virtual environment
	@echo "$(YELLOW)Creating Python virtual environment...$(RESET)"
	$(PYTHON) -m venv $(VENV_DIR)
	@echo "$(GREEN)Virtual environment created. Activate with: source $(VENV_DIR)/bin/activate$(RESET)"

install-dev: ## Install development dependencies
	@echo "$(YELLOW)Installing development dependencies...$(RESET)"
	$(PIP) install -e .[dev]
	$(PIP) install -r requirements.txt
	@echo "$(GREEN)Development dependencies installed$(RESET)"

install: ## Install production dependencies
	@echo "$(YELLOW)Installing production dependencies...$(RESET)"
	$(PIP) install -e .
	@echo "$(GREEN)Production dependencies installed$(RESET)"

setup: ## Complete development environment setup
	@echo "$(YELLOW)Setting up development environment...$(RESET)"
	@make venv
	@echo "$(YELLOW)Activating virtual environment and installing dependencies...$(RESET)"
	@( \
		source $(VENV_DIR)/bin/activate && \
		make install-dev && \
		pre-commit install \
	)
	@echo "$(GREEN)Development environment setup complete!$(RESET)"
	@echo "$(CYAN)Next steps:$(RESET)"
	@echo "  1. $(WHITE)source $(VENV_DIR)/bin/activate$(RESET)"
	@echo "  2. $(WHITE)make run-web$(RESET)"

# ============================================================================
# BUILD AND PACKAGING
# ============================================================================

build: clean ## Build Python package
	@echo "$(YELLOW)Building Python package...$(RESET)"
	$(PYTHON) setup.py sdist bdist_wheel
	@echo "$(GREEN)Package built successfully$(RESET)"

build-docker: ## Build Docker images
	@echo "$(YELLOW)Building Docker images...$(RESET)"
	$(DOCKER) build -t $(DOCKER_REGISTRY)/$(PROJECT_NAME)-web:$(DOCKER_TAG) -f Dockerfile.web .
	$(DOCKER) build -t $(DOCKER_REGISTRY)/$(PROJECT_NAME)-api:$(DOCKER_TAG) -f Dockerfile.api .
	$(DOCKER) build -t $(DOCKER_REGISTRY)/$(PROJECT_NAME)-cli:$(DOCKER_TAG) -f Dockerfile.cli .
	@echo "$(GREEN)Docker images built successfully$(RESET)"

build-multi-arch: ## Build multi-architecture Docker images
	@echo "$(YELLOW)Building multi-architecture Docker images...$(RESET)"
	$(DOCKER) buildx build --platform $(DOCKER_PLATFORMS) \
		-t $(DOCKER_REGISTRY)/$(PROJECT_NAME)-web:$(DOCKER_TAG) \
		-f Dockerfile.web --push .
	$(DOCKER) buildx build --platform $(DOCKER_PLATFORMS) \
		-t $(DOCKER_REGISTRY)/$(PROJECT_NAME)-api:$(DOCKER_TAG) \
		-f Dockerfile.api --push .
	@echo "$(GREEN)Multi-architecture images built and pushed$(RESET)"

# ============================================================================
# TESTING AND QUALITY ASSURANCE
# ============================================================================

test: ## Run test suite
	@echo "$(YELLOW)Running test suite...$(RESET)"
	pytest tests/ -v --cov=claude_admin --cov-report=html --cov-report=term
	@echo "$(GREEN)Tests completed$(RESET)"

test-integration: ## Run integration tests
	@echo "$(YELLOW)Running integration tests...$(RESET)"
	pytest tests/integration/ -v --tb=short
	@echo "$(GREEN)Integration tests completed$(RESET)"

test-e2e: ## Run end-to-end tests
	@echo "$(YELLOW)Running end-to-end tests...$(RESET)"
	@make compose-up-test
	sleep 30  # Wait for services to be ready
	pytest tests/e2e/ -v --tb=short
	@make compose-down
	@echo "$(GREEN)End-to-end tests completed$(RESET)"

lint: ## Run code linting
	@echo "$(YELLOW)Running code linting...$(RESET)"
	black --check .
	flake8 .
	mypy claude_admin/
	@echo "$(GREEN)Linting completed$(RESET)"

format: ## Format code
	@echo "$(YELLOW)Formatting code...$(RESET)"
	black .
	isort .
	@echo "$(GREEN)Code formatted$(RESET)"

security-scan: ## Run security scanning
	@echo "$(YELLOW)Running security scan...$(RESET)"
	bandit -r claude_admin/ -f json -o security-report.json
	safety check --json --output safety-report.json
	@echo "$(GREEN)Security scan completed$(RESET)"

# ============================================================================
# DOCKER COMPOSE OPERATIONS
# ============================================================================

compose-up: ## Start all services with Docker Compose
	@echo "$(YELLOW)Starting services with Docker Compose...$(RESET)"
	$(DOCKER_COMPOSE) up -d
	@echo "$(GREEN)Services started$(RESET)"
	@make status

compose-up-test: ## Start services for testing
	@echo "$(YELLOW)Starting test environment...$(RESET)"
	$(DOCKER_COMPOSE) -f docker-compose.yml -f docker-compose.test.yml up -d
	@echo "$(GREEN)Test environment started$(RESET)"

compose-down: ## Stop all services
	@echo "$(YELLOW)Stopping services...$(RESET)"
	$(DOCKER_COMPOSE) down
	@echo "$(GREEN)Services stopped$(RESET)"

compose-logs: ## Show service logs
	$(DOCKER_COMPOSE) logs -f

compose-build: ## Build Docker Compose services
	@echo "$(YELLOW)Building Docker Compose services...$(RESET)"
	$(DOCKER_COMPOSE) build
	@echo "$(GREEN)Services built$(RESET)"

# ============================================================================
# KUBERNETES OPERATIONS
# ============================================================================

k8s-deploy: ## Deploy to Kubernetes
	@echo "$(YELLOW)Deploying to Kubernetes...$(RESET)"
	@echo "Context: $(K8S_CONTEXT)"
	@echo "Namespace: $(K8S_NAMESPACE)"
	$(KUBECTL) apply -f kubernetes/namespace.yaml
	$(KUBECTL) apply -f kubernetes/ --recursive
	@echo "$(GREEN)Deployed to Kubernetes$(RESET)"

k8s-delete: ## Delete from Kubernetes
	@echo "$(YELLOW)Deleting from Kubernetes...$(RESET)"
	$(KUBECTL) delete -f kubernetes/ --recursive --ignore-not-found
	@echo "$(GREEN)Deleted from Kubernetes$(RESET)"

k8s-status: ## Show Kubernetes deployment status
	@echo "$(CYAN)Kubernetes Status:$(RESET)"
	$(KUBECTL) get pods,svc,ingress -n $(K8S_NAMESPACE)
	@echo ""
	$(KUBECTL) get events -n $(K8S_NAMESPACE) --sort-by='.lastTimestamp' | tail -10

k8s-logs: ## Show Kubernetes logs
	$(KUBECTL) logs -f deployment/claude-admin-web -n $(K8S_NAMESPACE)

k8s-port-forward: ## Port forward to local machine
	@echo "$(YELLOW)Port forwarding web console to localhost:8080...$(RESET)"
	$(KUBECTL) port-forward service/claude-admin-web 8080:80 -n $(K8S_NAMESPACE)

# ============================================================================
# DEVELOPMENT SERVERS
# ============================================================================

run-web: ## Run web console development server
	@echo "$(YELLOW)Starting web console development server...$(RESET)"
	$(PYTHON) -m claude_admin.web_console --debug --reload

run-api: ## Run API development server  
	@echo "$(YELLOW)Starting API development server...$(RESET)"
	$(PYTHON) -m claude_admin.api_server --debug --reload

run-tui: ## Run TUI application
	@echo "$(YELLOW)Starting TUI application...$(RESET)"
	$(PYTHON) -m claude_admin.tui_admin

run-cli: ## Run CLI with sample command
	@echo "$(YELLOW)Running CLI...$(RESET)"
	$(PYTHON) -m claude_admin.claude_admin_cli agents status

# ============================================================================
# MONITORING AND OBSERVABILITY
# ============================================================================

monitor: ## Open monitoring dashboards
	@echo "$(CYAN)Opening monitoring dashboards...$(RESET)"
	@echo "Web Console:   $(WHITE)http://localhost:8080$(RESET)"
	@echo "Prometheus:    $(WHITE)http://localhost:9090$(RESET)"
	@echo "Grafana:       $(WHITE)http://localhost:3000$(RESET) (admin/admin)"
	@echo "Alertmanager:  $(WHITE)http://localhost:9093$(RESET)"
	@if command -v xdg-open > /dev/null; then \
		xdg-open http://localhost:8080 >/dev/null 2>&1 & \
	elif command -v open > /dev/null; then \
		open http://localhost:8080 >/dev/null 2>&1 & \
	fi

status: ## Show system status
	@echo "$(CYAN)Claude Agent Administration System Status$(RESET)"
	@echo "$(CYAN)=========================================$(RESET)"
	@echo ""
	@if $(DOCKER_COMPOSE) ps | grep -q "Up"; then \
		echo "$(GREEN)Docker Compose Services:$(RESET)"; \
		$(DOCKER_COMPOSE) ps; \
		echo ""; \
	fi
	@if $(KUBECTL) get pods -n $(K8S_NAMESPACE) >/dev/null 2>&1; then \
		echo "$(GREEN)Kubernetes Pods:$(RESET)"; \
		$(KUBECTL) get pods -n $(K8S_NAMESPACE); \
		echo ""; \
	fi
	@if curl -sf http://localhost:8080/health >/dev/null 2>&1; then \
		echo "$(GREEN)✓$(RESET) Web Console: $(WHITE)http://localhost:8080$(RESET)"; \
	else \
		echo "$(RED)✗$(RESET) Web Console: Not running"; \
	fi
	@if curl -sf http://localhost:8081/health >/dev/null 2>&1; then \
		echo "$(GREEN)✓$(RESET) API Server:  $(WHITE)http://localhost:8081$(RESET)"; \
	else \
		echo "$(RED)✗$(RESET) API Server:  Not running"; \
	fi
	@if curl -sf http://localhost:9090/-/healthy >/dev/null 2>&1; then \
		echo "$(GREEN)✓$(RESET) Prometheus:  $(WHITE)http://localhost:9090$(RESET)"; \
	else \
		echo "$(RED)✗$(RESET) Prometheus:  Not running"; \
	fi
	@if curl -sf http://localhost:3000/api/health >/dev/null 2>&1; then \
		echo "$(GREEN)✓$(RESET) Grafana:     $(WHITE)http://localhost:3000$(RESET)"; \
	else \
		echo "$(RED)✗$(RESET) Grafana:     Not running"; \
	fi

health-check: ## Perform comprehensive health check
	@echo "$(YELLOW)Performing health check...$(RESET)"
	@$(PYTHON) -c "
import requests
import sys
import json

services = {
    'Web Console': 'http://localhost:8080/health',
    'API Server': 'http://localhost:8081/health',
    'Prometheus': 'http://localhost:9090/-/healthy',
    'Grafana': 'http://localhost:3000/api/health'
}

all_healthy = True
for name, url in services.items():
    try:
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            print(f'$(GREEN)✓$(RESET) {name}: Healthy')
        else:
            print(f'$(RED)✗$(RESET) {name}: Unhealthy (HTTP {resp.status_code})')
            all_healthy = False
    except requests.exceptions.RequestException as e:
        print(f'$(RED)✗$(RESET) {name}: Connection failed')
        all_healthy = False

if all_healthy:
    print('$(GREEN)All services healthy$(RESET)')
    sys.exit(0)
else:
    print('$(RED)Some services unhealthy$(RESET)')
    sys.exit(1)
"

# ============================================================================
# BACKUP AND RESTORE
# ============================================================================

backup: ## Create system backup
	@echo "$(YELLOW)Creating system backup...$(RESET)"
	@mkdir -p backups
	@backup_file="backups/claude-admin-backup-$$(date +%Y%m%d-%H%M%S).tar.gz"; \
	tar -czf "$$backup_file" \
		--exclude=venv \
		--exclude=__pycache__ \
		--exclude=.git \
		--exclude=node_modules \
		--exclude=dist \
		--exclude=build \
		. && \
	echo "$(GREEN)Backup created: $$backup_file$(RESET)"

backup-docker: ## Backup Docker volumes
	@echo "$(YELLOW)Backing up Docker volumes...$(RESET)"
	@mkdir -p backups
	$(DOCKER) run --rm \
		-v claude-admin_postgres-data:/data/postgres \
		-v claude-admin_grafana-data:/data/grafana \
		-v claude-admin_prometheus-data:/data/prometheus \
		-v $(PWD)/backups:/backup \
		alpine:latest \
		tar -czf /backup/docker-volumes-$$(date +%Y%m%d-%H%M%S).tar.gz \
		-C /data .
	@echo "$(GREEN)Docker volumes backup completed$(RESET)"

# ============================================================================
# DEPLOYMENT AND RELEASE
# ============================================================================

deploy-dev: ## Deploy to development environment
	@echo "$(YELLOW)Deploying to development environment...$(RESET)"
	@make build-docker
	@make compose-up
	@make health-check
	@echo "$(GREEN)Development deployment completed$(RESET)"

deploy-staging: ## Deploy to staging environment
	@echo "$(YELLOW)Deploying to staging environment...$(RESET)"
	@make build-docker
	@make k8s-deploy
	@echo "$(GREEN)Staging deployment completed$(RESET)"

deploy-prod: ## Deploy to production environment
	@echo "$(YELLOW)Deploying to production environment...$(RESET)"
	@read -p "Are you sure you want to deploy to production? [y/N]: " confirm && \
		if [ "$$confirm" = "y" ] || [ "$$confirm" = "Y" ]; then \
			make build-multi-arch && \
			make k8s-deploy && \
			echo "$(GREEN)Production deployment completed$(RESET)"; \
		else \
			echo "$(YELLOW)Deployment cancelled$(RESET)"; \
		fi

release: ## Create a new release
	@echo "$(YELLOW)Creating new release...$(RESET)"
	@if [ -z "$(TAG)" ]; then \
		echo "$(RED)Error: TAG is required. Usage: make release TAG=v1.0.0$(RESET)"; \
		exit 1; \
	fi
	@echo "Creating release $(TAG)..."
	git tag -a $(TAG) -m "Release $(TAG)"
	git push origin $(TAG)
	@make build
	@echo "$(GREEN)Release $(TAG) created$(RESET)"

# ============================================================================
# UTILITIES AND MAINTENANCE
# ============================================================================

clean: ## Clean build artifacts
	@echo "$(YELLOW)Cleaning build artifacts...$(RESET)"
	rm -rf $(BUILD_DIR) $(DIST_DIR) *.egg-info
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -type d -exec rm -rf {} +
	find . -name ".pytest_cache" -type d -exec rm -rf {} +
	find . -name ".coverage" -delete
	find . -name "htmlcov" -type d -exec rm -rf {} +
	@echo "$(GREEN)Build artifacts cleaned$(RESET)"

clean-docker: ## Clean Docker resources
	@echo "$(YELLOW)Cleaning Docker resources...$(RESET)"
	$(DOCKER) system prune -f
	$(DOCKER) volume prune -f
	@echo "$(GREEN)Docker resources cleaned$(RESET)"

logs: ## Show application logs
	@if $(DOCKER_COMPOSE) ps | grep -q "Up"; then \
		echo "$(CYAN)Docker Compose Logs:$(RESET)"; \
		$(DOCKER_COMPOSE) logs --tail=100; \
	elif $(KUBECTL) get pods -n $(K8S_NAMESPACE) >/dev/null 2>&1; then \
		echo "$(CYAN)Kubernetes Logs:$(RESET)"; \
		$(KUBECTL) logs -l app=claude-admin --tail=100 -n $(K8S_NAMESPACE); \
	else \
		echo "$(YELLOW)No running services found$(RESET)"; \
	fi

update-deps: ## Update Python dependencies
	@echo "$(YELLOW)Updating Python dependencies...$(RESET)"
	$(PIP) install --upgrade pip
	$(PIP) install --upgrade -r requirements.txt
	@echo "$(GREEN)Dependencies updated$(RESET)"

docs: ## Generate documentation
	@echo "$(YELLOW)Generating documentation...$(RESET)"
	@mkdir -p docs/_build
	sphinx-build -b html docs docs/_build/html
	@echo "$(GREEN)Documentation generated in docs/_build/html$(RESET)"

benchmark: ## Run performance benchmarks
	@echo "$(YELLOW)Running performance benchmarks...$(RESET)"
	$(PYTHON) -m claude_admin.benchmarks.performance_test
	@echo "$(GREEN)Benchmarks completed$(RESET)"

# ============================================================================
# CI/CD INTEGRATION
# ============================================================================

ci-test: ## Run CI test suite
	@echo "$(YELLOW)Running CI test suite...$(RESET)"
	@make lint
	@make security-scan
	@make test
	@make test-integration
	@echo "$(GREEN)CI tests completed$(RESET)"

ci-build: ## Build for CI/CD
	@echo "$(YELLOW)Building for CI/CD...$(RESET)"
	@make clean
	@make build
	@make build-docker
	@echo "$(GREEN)CI build completed$(RESET)"

ci-deploy: ## Deploy from CI/CD
	@echo "$(YELLOW)Deploying from CI/CD...$(RESET)"
	@if [ "$(ENVIRONMENT)" = "production" ]; then \
		make deploy-prod; \
	elif [ "$(ENVIRONMENT)" = "staging" ]; then \
		make deploy-staging; \
	else \
		make deploy-dev; \
	fi
	@echo "$(GREEN)CI deployment completed$(RESET)"

# ============================================================================
# TROUBLESHOOTING
# ============================================================================

debug: ## Start debug session
	@echo "$(YELLOW)Starting debug session...$(RESET)"
	@echo "$(CYAN)Environment Information:$(RESET)"
	@echo "Python Version: $$($(PYTHON) --version)"
	@echo "Pip Version: $$($(PIP) --version)"
	@echo "Docker Version: $$($(DOCKER) --version 2>/dev/null || echo 'Not available')"
	@echo "Current Directory: $$(pwd)"
	@echo "User: $$(whoami)"
	@echo ""
	@echo "$(CYAN)System Resources:$(RESET)"
	@echo "Memory: $$(free -h 2>/dev/null || echo 'Not available')"
	@echo "Disk: $$(df -h . 2>/dev/null || echo 'Not available')"
	@echo ""
	@make status

reset: ## Reset entire environment
	@echo "$(RED)WARNING: This will reset the entire environment!$(RESET)"
	@read -p "Are you sure? [y/N]: " confirm && \
		if [ "$$confirm" = "y" ] || [ "$$confirm" = "Y" ]; then \
			make compose-down || true; \
			make k8s-delete || true; \
			make clean; \
			make clean-docker; \
			rm -rf $(VENV_DIR); \
			echo "$(GREEN)Environment reset completed$(RESET)"; \
		else \
			echo "$(YELLOW)Reset cancelled$(RESET)"; \
		fi

# ============================================================================
# DEFAULT TARGET
# ============================================================================

.DEFAULT_GOAL := help