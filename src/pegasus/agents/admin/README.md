# Claude Agent Communication System - Administration Tools

Comprehensive administration tools for managing the distributed Claude Agent Communication System. Designed to handle 28+ agent types with ultra-high performance optimization (4.2M+ messages/second throughput).

## 🚀 Features

### Command-Line Interface (CLI)
- Complete agent lifecycle management (start/stop/restart/configure)
- Real-time system monitoring and diagnostics  
- Configuration management with hot-reload capabilities
- User and role management with RBAC
- Deployment and scaling automation
- Backup and restore operations
- Performance tuning and optimization tools

### Web Administration Console
- Real-time dashboards with live metrics visualization
- Interactive agent management interface
- WebSocket-based real-time updates
- User-friendly configuration editor
- Performance monitoring with charts and graphs
- Log viewer with filtering and search
- Role-based access control

### Terminal User Interface (TUI)
- Linux-optimized terminal dashboard
- Vim-like keybindings for efficient navigation
- Real-time metrics with color-coded health indicators
- Interactive agent management
- Resource utilization monitoring
- Zero-flicker rendering with ncurses optimization

### Deployment Management
- Kubernetes and Docker orchestration
- Blue-green and canary deployment strategies
- Automatic scaling based on performance metrics
- Rolling updates with zero downtime
- Multi-region deployment support
- Infrastructure as code integration

## 📋 Requirements

### System Requirements
- **Operating System**: Linux (Ubuntu 20.04+, RHEL 8+, CentOS 8+)
- **Python**: 3.8 or higher
- **Memory**: 4GB RAM minimum, 8GB recommended
- **Storage**: 10GB available space
- **Network**: High-bandwidth network interface for 4.2M+ msg/sec

### Dependencies
- Docker 20.10+ or Kubernetes 1.20+
- Redis 6.0+ (for caching and session management)
- PostgreSQL 13+ or SQLite 3.35+ (for configuration storage)
- Prometheus 2.30+ and Grafana 8.0+ (for monitoring)

### Optional Dependencies
- LDAP server (for enterprise authentication)
- HashiCorp Vault (for secret management)
- Elasticsearch (for log aggregation)

## 🔧 Installation

### Quick Install
```bash
# Clone the repository
git clone https://github.com/claude-agents/administration.git
cd administration/admin

# Install with automatic setup
pip install -e .

# Or install from PyPI
pip install claude-agent-admin
```

### Manual Installation
```bash
# Install Python dependencies
pip install -r requirements.txt

# Run setup script (requires root for system integration)
sudo python setup.py install

# Create configuration
sudo mkdir -p /etc/claude-agents
sudo cp configs/* /etc/claude-agents/

# Start services
sudo systemctl enable --now claude-admin-web
sudo systemctl enable --now claude-admin-api
```

### Docker Installation
```bash
# Build Docker image
docker build -t claude-admin:latest .

# Run web console
docker run -d \
  --name claude-admin-web \
  -p 8080:8080 \
  -v /etc/claude-agents:/etc/claude-agents \
  -v /var/lib/claude-agents:/var/lib/claude-agents \
  claude-admin:latest

# Access at http://localhost:8080
```

### Kubernetes Deployment
```bash
# Deploy to Kubernetes
kubectl apply -f kubernetes/

# Forward port for access
kubectl port-forward service/claude-admin-web 8080:80

# Access at http://localhost:8080
```

## 🎯 Quick Start

### 1. Command-Line Interface
```bash
# Check system status
claude-admin monitor system

# List all agents
claude-admin agents status

# Start specific agent
claude-admin agents start director --scale 2

# Scale agent instances
claude-admin deploy scale web --replicas 5

# Create system backup
claude-admin backup create --type full

# Run system diagnostics
claude-admin diagnose system --depth comprehensive
```

### 2. Web Console
```bash
# Start web console
claude-admin-web

# Access dashboard
open http://localhost:8080

# Default credentials (change immediately):
# Username: admin
# Password: admin123
```

### 3. Terminal Interface
```bash
# Launch TUI dashboard
claude-admin-tui

# Navigation:
# 1-5: Switch views (Dashboard/Agents/Performance/Logs/Config)
# j/k: Navigate up/down
# Tab: Next component
# r: Refresh data
# h: Help
# q: Quit
```

## 📊 System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Web Administration Console                 │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────────┐ │
│  │ Dashboard   │ │ Agent Mgmt  │ │    Real-time Monitor    │ │
│  └─────────────┘ └─────────────┘ └─────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                                │
┌─────────────────────────────────────────────────────────────┐
│                    Administration Core API                   │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────────┐ │
│  │ Agent Mgr   │ │ Config Mgr  │ │    System Monitor       │ │
│  └─────────────┘ └─────────────┘ └─────────────────────────┘ │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────────┐ │
│  │ Deploy Mgr  │ │ User Mgr    │ │    Diagnostic Tools     │ │
│  └─────────────┘ └─────────────┘ └─────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                                │
┌─────────────────────────────────────────────────────────────┐
│                Claude Agent Communication System            │
│         ┌───────────────────────────────────────┐           │
│         │    Ultra-Fast Protocol (4.2M msg/s)   │           │
│         └───────────────────────────────────────┘           │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────────────────┐ │
│  │Director │ │Security │ │Database │ │   ... 25 more       │ │
│  │ Agent   │ │ Agent   │ │ Agent   │ │      Agents         │ │
│  └─────────┘ └─────────┘ └─────────┘ └─────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## 🛠 Configuration

### Main Configuration (`/etc/claude-agents/admin.yaml`)
```yaml
version: '1.0.0'
debug: false

web_console:
  host: '0.0.0.0'
  port: 8080
  secret_key: 'your-secret-key-here'
  session_timeout: 3600

database:
  type: 'postgresql'  # or 'sqlite'
  host: 'localhost'
  port: 5432
  database: 'claude_admin'
  username: 'claude_admin'
  password: 'secure-password'

redis:
  host: 'localhost'
  port: 6379
  db: 0

monitoring:
  prometheus_url: 'http://localhost:9090'
  grafana_url: 'http://localhost:3000'
  update_interval: 30

security:
  jwt_algorithm: 'HS256'
  password_min_length: 8
  session_cookie_secure: true
  cors_origins: ['https://admin.claude-agents.local']

logging:
  level: 'INFO'
  format: 'json'
  file: '/var/log/claude-agents/admin.log'
  max_size_mb: 100
  backup_count: 10
```

### Agent Resources (`/etc/claude-agents/resources.yaml`)
```yaml
agent_resources:
  director:
    cpu: '500m'
    memory: '512Mi' 
    replicas: 1
    min_replicas: 1
    max_replicas: 3
    
  web:
    cpu: '300m'
    memory: '512Mi'
    replicas: 3
    min_replicas: 2
    max_replicas: 10
    
  database:
    cpu: '1000m'
    memory: '2Gi'
    replicas: 1
    min_replicas: 1
    max_replicas: 3
    
  # Configure remaining 25+ agent types...
```

### RBAC Configuration (`/etc/claude-agents/rbac.yaml`)
```yaml
roles:
  admin:
    permissions: ['*']
    description: 'Full system access'
    
  operator:
    permissions:
      - 'agents:read'
      - 'agents:restart'
      - 'agents:scale'
      - 'system:read'
      - 'config:read'
      - 'logs:read'
    description: 'Operations access'
    
  viewer:
    permissions:
      - 'system:read'
      - 'agents:read'
      - 'logs:read'
    description: 'Read-only access'
```

## 📈 Monitoring Integration

### Prometheus Metrics
The administration system exports comprehensive metrics:

```yaml
# System metrics
claude_admin_agents_total{type="active"}
claude_admin_agents_total{type="failed"}
claude_admin_system_cpu_utilization
claude_admin_system_memory_utilization
claude_admin_throughput_messages_per_second
claude_admin_latency_p99_nanoseconds

# Agent-specific metrics  
claude_agent_status{name="director",state="active"}
claude_agent_cpu_usage{name="web"}
claude_agent_memory_usage{name="database"}
claude_agent_health_score{name="security"}

# Deployment metrics
claude_deployment_total{strategy="rolling"}
claude_scaling_events_total{action="scale_up"}
claude_backup_operations_total{type="full"}
```

### Grafana Dashboards
Pre-configured dashboards available:
- **System Overview**: High-level cluster health
- **Agent Status**: Individual agent monitoring
- **Performance Metrics**: Throughput and latency tracking
- **Resource Utilization**: CPU, memory, network usage
- **Deployment Activity**: Scaling and deployment events
- **User Activity**: Authentication and access logs

## 🔐 Security Features

### Authentication & Authorization
- JWT-based authentication with configurable expiration
- Role-based access control (RBAC) with fine-grained permissions
- LDAP/Active Directory integration support
- API key authentication for programmatic access
- Session management with automatic timeout

### Security Best Practices
- TLS encryption for all web traffic
- Secure password policies with complexity requirements
- Failed login attempt monitoring and lockout
- Audit logging of all administrative actions
- Container security scanning integration
- Secret management with HashiCorp Vault support

### Network Security
- IP allowlisting for administrative access
- VPN integration support
- Network segmentation recommendations
- Firewall rule templates
- Service mesh integration (Istio support)

## 🚀 Performance Optimization

### High-Performance Features
- **Ultra-Fast Protocol Integration**: Direct access to 4.2M+ msg/sec transport
- **Real-time Metrics**: Sub-second dashboard updates
- **Efficient Caching**: Redis-based caching for frequently accessed data
- **Batch Operations**: Bulk agent management operations
- **Connection Pooling**: Optimized database and API connections

### Scaling Guidelines
```yaml
# Production scaling recommendations
web_console:
  replicas: 3
  resources:
    cpu: '500m'
    memory: '1Gi'
    
api_server:
  replicas: 5
  resources:
    cpu: '300m'
    memory: '512Mi'
    
database:
  # PostgreSQL with read replicas
  primary:
    cpu: '2000m'
    memory: '4Gi'
  replicas: 2
  
redis:
  # Redis cluster for HA
  nodes: 3
  memory: '2Gi'
```

## 🔧 Troubleshooting

### Common Issues

#### Web Console Not Accessible
```bash
# Check service status
systemctl status claude-admin-web

# Check logs
tail -f /var/log/claude-agents/admin.log

# Test port binding
ss -tlnp | grep 8080

# Restart service
systemctl restart claude-admin-web
```

#### Agents Not Responding
```bash
# Check agent status
claude-admin agents status

# Restart problematic agent
claude-admin agents restart <agent-name>

# Check system resources
claude-admin diagnose system

# View agent logs
claude-admin logs --agent <agent-name> --tail 100
```

#### Database Connection Issues
```bash
# Test database connection
claude-admin diagnose database

# Reset database schema
claude-admin database migrate

# Check Redis connectivity  
redis-cli ping
```

#### Performance Issues
```bash
# Run performance analysis
claude-admin monitor performance

# Check resource utilization
claude-admin diagnose system --depth comprehensive

# Optimize configuration
claude-admin optimize --auto-tune
```

### Debug Mode
```bash
# Enable debug logging
export CLAUDE_DEBUG=1
export CLAUDE_LOG_LEVEL=DEBUG

# Run with verbose output
claude-admin --debug monitor system
```

## 📚 API Reference

### REST API Endpoints

#### System Status
```http
GET /api/system/status
GET /api/system/performance
GET /api/system/health
```

#### Agent Management
```http
GET /api/agents
POST /api/agents/{type}/start
POST /api/agents/{name}/stop
POST /api/agents/{name}/restart
GET /api/agents/{name}/status
POST /api/agents/{type}/scale
```

#### Configuration
```http
GET /api/config/{component}
POST /api/config/{component}
PUT /api/config/{component}/{key}
POST /api/config/reload
```

#### User Management
```http
GET /api/users
POST /api/users
PUT /api/users/{id}
DELETE /api/users/{id}
POST /api/auth/login
POST /api/auth/logout
```

### WebSocket Events
```javascript
// Connect with authentication
const socket = io('ws://localhost:8080', {
  auth: { token: 'jwt-token-here' }
});

// Subscribe to system updates
socket.emit('subscribe', { type: 'system_status' });
socket.on('system_status', (data) => {
  console.log('System status:', data);
});

// Subscribe to agent updates
socket.emit('subscribe', { type: 'agent_status' });
socket.on('agent_update', (data) => {
  console.log('Agent update:', data);
});
```

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Development Setup
```bash
# Clone repository
git clone https://github.com/claude-agents/administration.git
cd administration/admin

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install in development mode
pip install -e .[dev]

# Run tests
pytest

# Run linting
flake8 .
black .

# Start development server
python -m claude_admin.web_console --debug
```

### Code Quality
- **Testing**: Comprehensive test suite with >90% coverage
- **Linting**: Black code formatting and flake8 linting
- **Type Hints**: Full type hint coverage with mypy checking
- **Documentation**: Sphinx-generated API documentation
- **CI/CD**: GitHub Actions with automated testing and deployment

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

### Community Support
- **Documentation**: [https://docs.claude-agents.local](https://docs.claude-agents.local)
- **GitHub Issues**: [Report bugs and feature requests](https://github.com/claude-agents/administration/issues)
- **Discussions**: [Community forum](https://github.com/claude-agents/administration/discussions)

### Enterprise Support
For enterprise deployments requiring:
- 24/7 technical support
- Custom integration development
- Performance optimization consulting
- Security compliance assistance
- Training and onboarding

Contact: support@claude-agents.local

## 🗓 Roadmap

### Version 1.1.0 (Q2 2024)
- [ ] Enhanced auto-scaling algorithms
- [ ] Multi-cloud deployment support
- [ ] Advanced anomaly detection
- [ ] Custom dashboard builder
- [ ] Mobile-responsive web interface

### Version 1.2.0 (Q3 2024)  
- [ ] Machine learning-based capacity planning
- [ ] GitOps integration
- [ ] Advanced security scanning
- [ ] Cost optimization recommendations
- [ ] Disaster recovery automation

### Version 2.0.0 (Q4 2024)
- [ ] Complete UI redesign
- [ ] Microservices architecture
- [ ] Real-time collaboration features
- [ ] Advanced AI-powered insights
- [ ] Edge deployment support

---

**Claude Agent Communication System Administration Tools v1.0.0**  
Built with ❤️ for ultra-high performance distributed systems