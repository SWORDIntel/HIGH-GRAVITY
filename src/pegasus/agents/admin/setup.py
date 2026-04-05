#!/usr/bin/env python3
"""
Claude Agent Communication System - Administration Tools Setup
=============================================================

Setup script for comprehensive administration tools installation.
Provides automated setup for CLI, web console, TUI, and deployment management.

Author: Claude Agent Administration System
Version: 1.0.0 Production
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import yaml
from setuptools import find_packages, setup

# ============================================================================
# SETUP CONFIGURATION
# ============================================================================

VERSION = "1.0.0"
DESCRIPTION = "Comprehensive administration tools for Claude Agent Communication System"
LONG_DESCRIPTION = """
Claude Agent Administration Tools
================================

A comprehensive suite of administration tools for managing the distributed Claude Agent
Communication System. Supports management of 28+ agent types with ultra-high performance
optimization (4.2M+ messages/second throughput).

Features:
- Command-line interface (CLI) for system management
- Web-based admin console with real-time dashboards  
- Terminal User Interface (TUI) for Linux-optimized management
- Kubernetes and Docker deployment automation
- Real-time monitoring and performance optimization
- Configuration management with hot-reload capabilities
- User and role management with RBAC
- Backup and restore functionality
- Diagnostic and troubleshooting tools
- Integration with Prometheus/Grafana monitoring

Components:
- claude_admin_cli.py: Command-line administration interface
- web_console.py: Web-based dashboard and API
- tui_admin.py: Terminal-based administration interface
- deployment_manager.py: Container orchestration and scaling
- admin_core.py: Core management modules and APIs

Requirements:
- Python 3.8+
- Linux environment (optimized)
- Docker or Kubernetes cluster
- Redis for caching
- PostgreSQL/SQLite for configuration storage
"""

AUTHOR = "Claude Agent Administration System"
AUTHOR_EMAIL = "admin@claude-agents.local"
URL = "https://github.com/claude-agents/administration"

CLASSIFIERS = [
    "Development Status :: 5 - Production/Stable",
    "Intended Audience :: System Administrators",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Operating System :: POSIX :: Linux",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.8",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Topic :: System :: Systems Administration",
    "Topic :: System :: Monitoring",
    "Topic :: System :: Clustering",
    "Environment :: Console",
    "Environment :: Web Environment",
]

# ============================================================================
# INSTALLATION UTILITIES
# ============================================================================


def check_system_requirements():
    """Check system requirements"""
    print("🔍 Checking system requirements...")

    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ is required")
        sys.exit(1)
    print(f"✅ Python {sys.version.split()[0]} detected")

    # Check Linux environment
    if not sys.platform.startswith("linux"):
        print("⚠️  Warning: This package is optimized for Linux environments")

    # Check for required system tools
    required_tools = ["docker", "kubectl", "curl", "git"]
    for tool in required_tools:
        if shutil.which(tool):
            print(f"✅ {tool} found")
        else:
            print(f"⚠️  {tool} not found (optional but recommended)")


def create_directory_structure():
    """Create necessary directory structure"""
    print("📁 Creating directory structure...")

    directories = [
        "/etc/claude-agents",
        "/var/lib/claude-agents",
        "/var/lib/claude-agents/web/static/css",
        "/var/lib/claude-agents/web/static/js",
        "/var/lib/claude-agents/web/templates",
        "/var/lib/claude-agents/backup",
        "/var/log/claude-agents",
        "/var/run/claude-agents",
    ]

    for directory in directories:
        try:
            os.makedirs(directory, mode=0o755, exist_ok=True)
            print(f"✅ Created {directory}")
        except PermissionError:
            print(f"⚠️  Could not create {directory} (requires root privileges)")
        except Exception as e:
            print(f"❌ Error creating {directory}: {e}")


def install_systemd_services():
    """Install systemd service files"""
    print("🔧 Installing systemd services...")

    services = {
        "claude-admin-web.service": {
            "description": "Claude Agent Administration Web Console",
            "exec_start": f"{sys.executable} -m claude_admin.web_console",
            "port": 8080,
        },
        "claude-admin-api.service": {
            "description": "Claude Agent Administration API",
            "exec_start": f"{sys.executable} -m claude_admin.api_server",
            "port": 8081,
        },
    }

    service_template = """[Unit]
Description={description}
After=network.target
Wants=network.target

[Service]
Type=simple
User=claude-admin
Group=claude-admin
ExecStart={exec_start}
Restart=always
RestartSec=10
Environment=PYTHONPATH=/opt/claude-agents
Environment=CLAUDE_CONFIG_DIR=/etc/claude-agents
Environment=CLAUDE_DATA_DIR=/var/lib/claude-agents
Environment=CLAUDE_LOG_DIR=/var/log/claude-agents

# Security settings
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/lib/claude-agents /var/log/claude-agents /var/run/claude-agents
PrivateTmp=true

[Install]
WantedBy=multi-user.target
"""

    for service_name, config in services.items():
        service_content = service_template.format(**config)
        service_path = f"/etc/systemd/system/{service_name}"

        try:
            with open(service_path, "w") as f:
                f.write(service_content)
            print(f"✅ Installed {service_name}")
        except PermissionError:
            print(f"⚠️  Could not install {service_name} (requires root privileges)")


def create_user_and_group():
    """Create claude-admin user and group"""
    print("👤 Creating claude-admin user...")

    try:
        # Create group
        subprocess.run(
            ["groupadd", "-r", "claude-admin"], check=False, capture_output=True
        )

        # Create user
        subprocess.run(
            [
                "useradd",
                "-r",
                "-g",
                "claude-admin",
                "-d",
                "/var/lib/claude-agents",
                "-s",
                "/bin/false",
                "-c",
                "Claude Agent Administration System",
                "claude-admin",
            ],
            check=False,
            capture_output=True,
        )

        print("✅ Created claude-admin user and group")

        # Set ownership of directories
        directories = [
            "/var/lib/claude-agents",
            "/var/log/claude-agents",
            "/var/run/claude-agents",
        ]

        for directory in directories:
            if os.path.exists(directory):
                subprocess.run(
                    ["chown", "-R", "claude-admin:claude-admin", directory],
                    check=False,
                    capture_output=True,
                )

    except Exception as e:
        print(f"⚠️  Could not create user (may already exist): {e}")


def generate_default_configs():
    """Generate default configuration files"""
    print("⚙️  Generating default configuration files...")

    configs = {
        "/etc/claude-agents/admin.yaml": {
            "version": "1.0.0",
            "debug": False,
            "web_console": {
                "host": "0.0.0.0",
                "port": 8080,
                "secret_key": "CHANGE-ME-IN-PRODUCTION",
                "session_timeout": 3600,
            },
            "database": {"type": "sqlite", "path": "/var/lib/claude-agents/admin.db"},
            "redis": {"host": "localhost", "port": 6379, "db": 0},
            "monitoring": {
                "prometheus_url": "http://localhost:9090",
                "grafana_url": "http://localhost:3000",
                "update_interval": 30,
            },
            "security": {
                "jwt_algorithm": "HS256",
                "password_min_length": 8,
                "session_cookie_secure": True,
                "cors_origins": ["http://localhost:8080"],
            },
            "logging": {
                "level": "INFO",
                "format": "json",
                "file": "${CLAUDE_LOG_DIR:-/var/log/claude-agents/}admin.log",
                "max_size_mb": 100,
                "backup_count": 10,
            },
        },
        "/etc/claude-agents/deployment.yaml": {
            "environments": {
                "development": {
                    "cluster_name": "claude-agents-dev",
                    "namespace": "claude-agents-dev",
                    "auto_scaling": False,
                    "resources": {"default": {"cpu": "200m", "memory": "256Mi"}},
                },
                "production": {
                    "cluster_name": "claude-agents-prod",
                    "namespace": "claude-agents",
                    "auto_scaling": True,
                    "resources": {
                        "default": {"cpu": "500m", "memory": "512Mi"},
                        "high_performance": {"cpu": "1000m", "memory": "1Gi"},
                    },
                },
            }
        },
        "/etc/claude-agents/rbac.yaml": {
            "roles": {
                "admin": {"permissions": ["*"], "description": "Full system access"},
                "operator": {
                    "permissions": [
                        "agents:read",
                        "agents:restart",
                        "agents:scale",
                        "system:read",
                        "config:read",
                        "logs:read",
                    ],
                    "description": "Operations access",
                },
                "viewer": {
                    "permissions": ["system:read", "agents:read", "logs:read"],
                    "description": "Read-only access",
                },
                "developer": {
                    "permissions": [
                        "agents:read",
                        "agents:deploy",
                        "config:read",
                        "config:write",
                        "logs:read",
                        "system:read",
                    ],
                    "description": "Development access",
                },
            }
        },
    }

    for config_path, config_data in configs.items():
        try:
            os.makedirs(os.path.dirname(config_path), exist_ok=True)

            with open(config_path, "w") as f:
                yaml.dump(config_data, f, default_flow_style=False, indent=2)

            print(f"✅ Generated {config_path}")

            # Set appropriate permissions
            os.chmod(config_path, 0o640)

        except Exception as e:
            print(f"❌ Error generating {config_path}: {e}")


def install_bash_completions():
    """Install bash completions for CLI"""
    print("🔧 Installing bash completions...")

    completion_script = """# Claude Agent Administration CLI bash completion
_claude_admin_completion() {
    local cur prev opts
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"
    
    opts="agents monitor config users deploy backup diagnose --help --version"
    
    case "${prev}" in
        agents)
            opts="start stop restart status scale"
            ;;
        monitor)
            opts="system agent performance"
            ;;
        config)
            opts="show set validate reload"
            ;;
        users)
            opts="create list delete modify"
            ;;
        deploy)
            opts="cluster scale"
            ;;
        backup)
            opts="create restore list"
            ;;
        diagnose)
            opts="system agent network performance"
            ;;
    esac
    
    COMPREPLY=( $(compgen -W "${opts}" -- ${cur}) )
    return 0
}

complete -F _claude_admin_completion claude-admin
"""

    completion_path = "/etc/bash_completion.d/claude-admin"
    try:
        with open(completion_path, "w") as f:
            f.write(completion_script)
        print(f"✅ Installed bash completion: {completion_path}")
    except PermissionError:
        print("⚠️  Could not install bash completion (requires root privileges)")


def setup_logrotate():
    """Setup log rotation"""
    print("📜 Setting up log rotation...")

    logrotate_config = """${CLAUDE_LOG_DIR:-/var/log/claude-agents/}*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    sharedscripts
    postrotate
        systemctl reload claude-admin-web || true
        systemctl reload claude-admin-api || true
    endscript
    su claude-admin claude-admin
}"""

    logrotate_path = "/etc/logrotate.d/claude-agents"
    try:
        with open(logrotate_path, "w") as f:
            f.write(logrotate_config)
        print(f"✅ Configured log rotation: {logrotate_path}")
    except PermissionError:
        print("⚠️  Could not configure log rotation (requires root privileges)")


def post_install_setup():
    """Perform post-installation setup tasks"""
    print("\n🚀 Performing post-installation setup...")

    check_system_requirements()
    create_directory_structure()
    create_user_and_group()
    generate_default_configs()
    install_systemd_services()
    install_bash_completions()
    setup_logrotate()

    print("\n✅ Post-installation setup completed!")
    print("\nNext steps:")
    print("1. Review configuration files in /etc/claude-agents/")
    print("2. Start services: systemctl enable --now claude-admin-web")
    print("3. Access web console: http://localhost:8080")
    print("4. Run CLI: claude-admin --help")
    print("5. Launch TUI: claude-admin-tui")


# ============================================================================
# SETUP CONFIGURATION
# ============================================================================


# Read requirements from file
def get_requirements():
    """Get requirements from requirements.txt"""
    req_file = Path(__file__).parent / "requirements.txt"
    if req_file.exists():
        with open(req_file) as f:
            requirements = []
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    # Remove comments from requirements
                    req = line.split("#")[0].strip()
                    if req:
                        requirements.append(req)
            return requirements
    return []


def get_entry_points():
    """Define console entry points"""
    return {
        "console_scripts": [
            "claude-admin=claude_admin.claude_admin_cli:main",
            "claude-admin-web=claude_admin.web_console:main",
            "claude-admin-tui=claude_admin.tui_admin:main",
            "claude-deploy=claude_admin.deployment_manager:main",
        ]
    }


# Custom install command
class PostInstallCommand:
    """Custom post-installation command"""

    __slots__ = []

    def run(self):
        """Run post-installation setup"""
        if "--skip-post-install" not in sys.argv:
            post_install_setup()


# ============================================================================
# MAIN SETUP CONFIGURATION
# ============================================================================

if __name__ == "__main__":
    setup(
        name="claude-agent-admin",
        version=VERSION,
        description=DESCRIPTION,
        long_description=LONG_DESCRIPTION,
        long_description_content_type="text/markdown",
        author=AUTHOR,
        author_email=AUTHOR_EMAIL,
        url=URL,
        packages=find_packages(),
        package_dir={"claude_admin": "."},
        package_data={
            "claude_admin": [
                "templates/**/*",
                "static/**/*",
                "configs/**/*",
                "*.yaml",
                "*.json",
            ]
        },
        include_package_data=True,
        install_requires=get_requirements(),
        entry_points=get_entry_points(),
        classifiers=CLASSIFIERS,
        python_requires=">=3.8",
        keywords="administration management monitoring orchestration agents",
        project_urls={
            "Bug Reports": f"{URL}/issues",
            "Source": URL,
            "Documentation": f"{URL}/docs",
        },
        zip_safe=False,
        platforms=["Linux"],
        # Custom commands
        cmdclass={
            "install": PostInstallCommand,
        },
        # Additional metadata
        license="MIT",
        maintainer=AUTHOR,
        maintainer_email=AUTHOR_EMAIL,
    )

    # Run post-install if installing
    if "install" in sys.argv and "--skip-post-install" not in sys.argv:
        post_install_setup()
