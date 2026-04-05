# Makefile for Claude Agent Communication System Monitoring
# Provides easy commands for building and managing the monitoring stack

.PHONY: help build start stop clean status logs dashboard-import agent-exporter transport-exporter

# Default target
help:
	@echo "Claude Agent Monitoring System"
	@echo "================================"
	@echo ""
	@echo "Available targets:"
	@echo "  build              - Build all custom components"
	@echo "  start              - Start the monitoring stack"
	@echo "  stop               - Stop the monitoring stack"
	@echo "  restart            - Restart the monitoring stack"
	@echo "  status             - Show service status"
	@echo "  logs               - Show logs from all services"
	@echo "  logs-service       - Show logs from specific service (make logs-service SERVICE=prometheus)"
	@echo "  clean              - Clean up containers and volumes"
	@echo "  deep-clean         - Remove all containers, volumes, and images"
	@echo "  dashboard-import   - Import Grafana dashboards"
	@echo "  agent-exporter     - Build Python agent metrics exporter"
	@echo "  transport-exporter - Build C transport metrics exporter"
	@echo "  capacity-planner   - Start capacity planning analysis"
	@echo "  test-alerts        - Test alert configuration"
	@echo "  backup             - Backup monitoring data"
	@echo "  restore            - Restore monitoring data from backup"
	@echo ""

# Build all custom components
build: agent-exporter transport-exporter
	@echo "Building monitoring stack components..."
	docker-compose -f docker-compose.monitoring.yml build

# Build Python agent metrics exporter
agent-exporter:
	@echo "Building agent metrics exporter..."
	docker build -t claude-agent-exporter -f Dockerfile.agent-exporter .

# Build C transport metrics exporter  
transport-exporter:
	@echo "Building transport metrics exporter..."
	gcc -o transport_metrics_exporter transport_metrics_exporter.c \
		-lpthread -lm -std=c11 -O3 -DSTANDALONE
	docker build -t claude-transport-exporter -f Dockerfile.transport-exporter .

# Start the monitoring stack
start:
	@echo "Starting Claude Agent Monitoring Stack..."
	docker-compose -f docker-compose.monitoring.yml up -d
	@echo ""
	@echo "Monitoring services started!"
	@echo "  Grafana:      http://localhost:3000 (admin/claude-agents-2024)"
	@echo "  Prometheus:   http://localhost:9090"
	@echo "  AlertManager: http://localhost:9093"
	@echo "  Jaeger:       http://localhost:16686"
	@echo ""

# Stop the monitoring stack
stop:
	@echo "Stopping monitoring stack..."
	docker-compose -f docker-compose.monitoring.yml down

# Restart the monitoring stack
restart: stop start

# Show service status
status:
	@echo "Monitoring Stack Status:"
	@echo "========================"
	docker-compose -f docker-compose.monitoring.yml ps
	@echo ""
	@echo "Resource Usage:"
	@echo "==============="
	docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}"

# Show logs from all services
logs:
	docker-compose -f docker-compose.monitoring.yml logs --tail=100 -f

# Show logs from specific service
logs-service:
ifndef SERVICE
	@echo "Usage: make logs-service SERVICE=<service-name>"
	@echo "Available services: prometheus grafana alertmanager jaeger otel-collector"
else
	docker-compose -f docker-compose.monitoring.yml logs --tail=100 -f $(SERVICE)
endif

# Clean up containers and volumes
clean:
	@echo "Cleaning up monitoring stack..."
	docker-compose -f docker-compose.monitoring.yml down -v
	docker system prune -f

# Deep clean - remove everything
deep-clean:
	@echo "Performing deep clean..."
	docker-compose -f docker-compose.monitoring.yml down -v --rmi all
	docker volume prune -f
	docker image prune -a -f

# Import Grafana dashboards
dashboard-import:
	@echo "Importing Grafana dashboards..."
	@if [ -f "grafana_dashboards.json" ]; then \
		echo "Dashboards will be automatically imported on Grafana startup"; \
	else \
		echo "Dashboard file not found!"; \
	fi

# Start capacity planning analysis
capacity-planner:
	@echo "Starting capacity planning analysis..."
	python3 -m pip install -r requirements-capacity.txt
	python3 capacity_planning.py

# Test alert configuration
test-alerts:
	@echo "Testing AlertManager configuration..."
	docker run --rm -v $(PWD)/alertmanager.yml:/etc/alertmanager/alertmanager.yml \
		prom/alertmanager:latest amtool check-config /etc/alertmanager/alertmanager.yml
	@echo "Testing Prometheus alert rules..."
	docker run --rm -v $(PWD)/alert_rules.yml:/etc/prometheus/alert_rules.yml \
		prom/prometheus:latest promtool check rules /etc/prometheus/alert_rules.yml

# Backup monitoring data
backup:
	@echo "Creating backup of monitoring data..."
	mkdir -p backups/$(shell date +%Y%m%d_%H%M%S)
	docker run --rm -v claude-monitoring_prometheus_data:/data -v $(PWD)/backups:/backup \
		alpine:latest tar czf /backup/$(shell date +%Y%m%d_%H%M%S)/prometheus_data.tar.gz -C /data .
	docker run --rm -v claude-monitoring_grafana_data:/data -v $(PWD)/backups:/backup \
		alpine:latest tar czf /backup/$(shell date +%Y%m%d_%H%M%S)/grafana_data.tar.gz -C /data .
	@echo "Backup completed in backups/$(shell date +%Y%m%d_%H%M%S)/"

# Restore monitoring data from backup
restore:
ifndef BACKUP_DIR
	@echo "Usage: make restore BACKUP_DIR=<backup-directory>"
	@echo "Available backups:"
	@ls -la backups/ 2>/dev/null || echo "No backups found"
else
	@echo "Restoring from backup: $(BACKUP_DIR)"
	docker run --rm -v claude-monitoring_prometheus_data:/data -v $(PWD)/backups/$(BACKUP_DIR):/backup \
		alpine:latest tar xzf /backup/prometheus_data.tar.gz -C /data
	docker run --rm -v claude-monitoring_grafana_data:/data -v $(PWD)/backups/$(BACKUP_DIR):/backup \
		alpine:latest tar xzf /backup/grafana_data.tar.gz -C /data
	@echo "Restore completed"
endif

# Check monitoring stack health
health-check:
	@echo "Performing health check..."
	@echo "Prometheus:"
	@curl -s http://localhost:9090/api/v1/query\?query\=up | jq -r '.data.result[] | "  " + .metric.job + ": " + .value[1]'
	@echo ""
	@echo "Grafana:"
	@curl -s http://localhost:3000/api/health | jq -r '"  Status: " + .status'
	@echo ""
	@echo "AlertManager:"
	@curl -s http://localhost:9093/api/v1/status | jq -r '"  Version: " + .data.versionInfo.version'

# Show monitoring endpoints
endpoints:
	@echo "Monitoring Endpoints:"
	@echo "===================="
	@echo "Web Interfaces:"
	@echo "  Grafana:      http://localhost:3000"
	@echo "  Prometheus:   http://localhost:9090" 
	@echo "  AlertManager: http://localhost:9093"
	@echo "  Jaeger:       http://localhost:16686"
	@echo ""
	@echo "Metrics Endpoints:"
	@echo "  Agent Exporter:     http://localhost:8000/metrics"
	@echo "  Transport Exporter: http://localhost:8001/metrics"
	@echo "  Node Exporter:      http://localhost:9100/metrics"
	@echo "  cAdvisor:           http://localhost:8080/metrics"
	@echo ""
	@echo "API Endpoints:"
	@echo "  Prometheus API:     http://localhost:9090/api/v1/"
	@echo "  AlertManager API:   http://localhost:9093/api/v1/"
	@echo "  OTLP gRPC:          http://localhost:4317"
	@echo "  OTLP HTTP:          http://localhost:4318"

# Generate sample load for testing
generate-load:
	@echo "Generating sample load for testing..."
	python3 -c """
import time
import random
import requests
import threading

def send_metrics():
    while True:
        # Simulate varying load
        throughput = random.randint(3000000, 5000000)  # 3-5M msg/sec
        cpu_usage = random.randint(20, 90)
        memory_usage = random.randint(30, 80)
        
        print(f'Simulating: {throughput} msg/s, CPU: {cpu_usage}%, Memory: {memory_usage}%')
        time.sleep(5)

# Run for 5 minutes
thread = threading.Thread(target=send_metrics)
thread.daemon = True
thread.start()
time.sleep(300)
"""

# Performance benchmark
benchmark:
	@echo "Running monitoring performance benchmark..."
	@echo "Testing metric ingestion rate..."
	time for i in {1..1000}; do \
		curl -s http://localhost:8000/metrics > /dev/null; \
	done
	@echo ""
	@echo "Testing query performance..."
	time curl -s "http://localhost:9090/api/v1/query?query=up" > /dev/null
	@echo "Benchmark completed"

# Update configuration
update-config:
	@echo "Updating monitoring configuration..."
	docker-compose -f docker-compose.monitoring.yml exec prometheus \
		curl -X POST http://localhost:9090/-/reload
	docker-compose -f docker-compose.monitoring.yml exec alertmanager \
		curl -X POST http://localhost:9093/-/reload
	@echo "Configuration reloaded"

# Show resource usage
resources:
	@echo "Monitoring Stack Resource Usage:"
	@echo "================================"
	docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.NetIO}}\t{{.BlockIO}}"
	@echo ""
	@echo "Volume Usage:"
	docker system df -v | grep claude-monitoring

# Show version information
version:
	@echo "Claude Agent Monitoring System"
	@echo "Version: 3.0.0"
	@echo "Build Date: 2024-08-08"
	@echo ""
	@echo "Component Versions:"
	@echo "  Prometheus: 2.45.0"
	@echo "  Grafana: 10.0.0"
	@echo "  AlertManager: 0.25.0"
	@echo "  Jaeger: 1.47"
	@echo "  OpenTelemetry: 0.81.0"