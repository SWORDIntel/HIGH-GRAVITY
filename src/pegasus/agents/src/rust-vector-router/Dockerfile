# Multi-stage Dockerfile for Claude Agent Communication System
# Optimized for production deployment with ultra-fast protocol support

# ============================================================================
# Stage 1: Build Environment
# ============================================================================
FROM rust:1.80-slim-bullseye AS rust-builder

# Install system dependencies for Rust builds
RUN apt-get update && apt-get install -y \
    pkg-config \
    libasound2-dev \
    libssl-dev \
    cmake \
    build-essential \
    libopenvino-dev \
    intel-openvino-dev-ubuntu20 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app/rust

# Copy Rust project files
COPY voice-agent-system/Cargo.toml voice-agent-system/Cargo.lock ./
COPY voice-agent-system/src ./src
COPY voice-agent-system/benches ./benches

# Build optimized release
RUN cargo build --release --features gna-support
RUN strip target/release/voice-agent-system

# ============================================================================
# Stage 2: C/C++ Build Environment  
# ============================================================================
FROM gcc:12-bullseye AS c-builder

# Install dependencies for C/C++ compilation
RUN apt-get update && apt-get install -y \
    cmake \
    make \
    libc6-dev \
    linux-headers-generic \
    intel-opencl-icd \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app/c

# Copy C source files
COPY *.c *.h *.S ./
COPY Makefile ./

# Build ultra-fast protocol and agents
RUN make all
RUN make install PREFIX=/usr/local

# ============================================================================
# Stage 3: Python Build Environment
# ============================================================================
FROM python:3.11-slim-bullseye AS python-builder

# Install Python build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    pkg-config \
    libffi-dev \
    libssl-dev \
    libasound2-dev \
    portaudio19-dev \
    libopenvino-dev \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies
COPY voice-recognition-system/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Copy Python source
WORKDIR /app/python
COPY voice-recognition-system/ ./voice-recognition-system/
COPY ENHANCED_AGENT_INTEGRATION.py ./
COPY voice_enhanced_agents.py ./

# Compile Python bytecode
RUN python -m compileall -b .
RUN find . -name "*.py" -delete

# ============================================================================
# Stage 4: Production Runtime Environment
# ============================================================================
FROM ubuntu:22.04 AS production

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    # Core runtime
    ca-certificates \
    curl \
    wget \
    # Audio libraries
    libasound2 \
    pulseaudio \
    alsa-utils \
    # Intel acceleration
    intel-openvino-runtime \
    intel-opencl-icd \
    # Python runtime
    python3.11 \
    python3.11-venv \
    # Monitoring
    procps \
    htop \
    iotop \
    # Security
    sudo \
    # Cleanup
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user for security
RUN groupadd -r claude && useradd -r -g claude -s /bin/bash claude
RUN mkdir -p /home/claude && chown -R claude:claude /home/claude

# Create application structure
RUN mkdir -p /app/{bin,lib,data,config,logs} \
    && chown -R claude:claude /app

# Copy compiled binaries
COPY --from=rust-builder /app/rust/target/release/voice-agent-system /app/bin/
COPY --from=c-builder /usr/local/bin/ultra_* /app/bin/
COPY --from=c-builder /usr/local/lib/libufp.so /app/lib/

# Copy Python environment
COPY --from=python-builder /opt/venv /opt/venv
COPY --from=python-builder /app/python /app/python

# Set environment variables
ENV PATH="/opt/venv/bin:/app/bin:$PATH"
ENV LD_LIBRARY_PATH="/app/lib:$LD_LIBRARY_PATH"
ENV PYTHONPATH="/app/python:$PYTHONPATH"

# Agent configuration
ENV AGENT_HOME="/app"
ENV AGENT_DATA_DIR="/app/data"
ENV AGENT_CONFIG_DIR="/app/config"
ENV AGENT_LOG_DIR="/app/logs"

# Performance tuning
ENV MALLOC_ARENA_MAX=4
ENV OMP_NUM_THREADS=4
ENV MKL_NUM_THREADS=4

# Ultra-fast protocol configuration
ENV UFP_MAX_AGENTS=28
ENV UFP_SHARED_MEMORY_SIZE=67108864
ENV UFP_RING_BUFFER_SIZE=16777216

# Copy configuration files
COPY voice_config.json /app/config/
COPY docker/agent-configs/ /app/config/

# Create data directories with proper permissions
RUN mkdir -p /app/data/{sessions,models,corrections,voice_profiles,processed,raw_audio,training_sets,user_profiles} \
    && mkdir -p /app/logs/{agents,system,audit} \
    && chown -R claude:claude /app

# Health check
COPY docker/healthcheck.sh /app/bin/healthcheck.sh
RUN chmod +x /app/bin/healthcheck.sh

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD /app/bin/healthcheck.sh

# Switch to non-root user
USER claude
WORKDIR /app

# Expose ports for agent communication
EXPOSE 8080 8081 8082 8083 8084 8085

# Default command
CMD ["python3", "/app/python/ENHANCED_AGENT_INTEGRATION.py"]