# HIGH-GRAVITY Project

## Project Overview

HIGH-GRAVITY is a sophisticated local identity proxy, optimization shield, and cyber-intelligence gateway for Windsurf. It is designed to provide a secure and efficient way to interact with various AI models while maintaining user privacy and control.

The project is built with Python and utilizes a modular architecture with several key components:

*   **Pegasus Dashboard:** A terminal-based dashboard (`hg.py`) for monitoring and controlling the system.
*   **High-Performance Proxy:** A FastAPI-based proxy (`tools/integration/highgravity_proxy.py`) that handles request routing, response streaming, and model remapping.
*   **Pegasus Swarm:** A collection of specialized agents that perform tasks such as security auditing, research, and context optimization.
*   **Quantum Infrastructure (QIHSE):** An advanced search and acceleration engine.
*   **Claude Interface:** A unified interface for interacting with Claude models.

The system is designed to be self-contained and high-performance, with features like:

*   **True Response Streaming:** Zero-buffer architecture for low-latency responses.
*   **Smart Model Remapping:** Dynamic fallback to available models.
*   **Shadow Profiles:** Session spoofing for enhanced anonymity.
*   **Unleash Shield:** Local mocking of enterprise SaaS features.
*   **Stealth Hardening:** Techniques to defeat TLS/timing fingerprinting.

## Building and Running

### Dependencies

*   Python 3
*   `rich`
*   `fastapi`
*   `uvicorn`
*   `aiohttp`
*   `requests`

You can install the dependencies using pip:

```bash
pip install rich fastapi uvicorn aiohttp requests
```

### Deploy Shield

To deploy the process-level Bash shield for the language server, run the following command:

```bash
bash tools/integration/deploy_lsp_shim.sh
```

### Launch Dashboard

To launch the Pegasus Dashboard, run the following command:

```bash
python3 hg.py
```

The dashboard provides a real-time view of the system's status, including metrics on requests, cache hits, and active agents.

## Development Conventions

*   **Code Style:** The Python code follows standard PEP 8 conventions.
*   **Testing:** The project includes a `tests` directory, but the specific testing practices are not immediately clear from the file list.
*   **Configuration:** Configuration files are located in the `config` directory.
*   **Logging:** The system uses a central logging file at `logs/proxy.log`.
*   **Modularity:** The project is highly modular, with different components organized into separate directories.
