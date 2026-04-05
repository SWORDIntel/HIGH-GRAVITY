#!/usr/bin/env python3
"""
Claude Agent Communication Server - Binary Protocol Edition
Fixed version with proper message framing and binary protocol
"""

import asyncio
import json
import os
import queue
import signal
import socket
import struct
import sys
import threading
import time
from datetime import datetime
from enum import IntEnum

# Protocol constants
PROTOCOL_VERSION = 0x01
MAGIC_HEADER = b"CAGT"  # Claude Agent Protocol
MAX_MESSAGE_SIZE = 1024 * 1024  # 1MB max message size


class MessageType(IntEnum):
    """Binary protocol message types"""

    REGISTER = 0x01
    STATUS = 0x02
    SEND = 0x03
    HEARTBEAT = 0x04
    RESPONSE = 0x05
    ERROR = 0x06
    SHUTDOWN = 0x07


class BinaryProtocol:
    """Handle binary message framing"""

    @staticmethod
    def pack_message(msg_type, payload):
        """Pack message with header: [MAGIC][VERSION][TYPE][LENGTH][PAYLOAD]"""
        if isinstance(payload, dict):
            payload = json.dumps(payload).encode("utf-8")
        elif isinstance(payload, str):
            payload = payload.encode("utf-8")

        # Create header: 4 bytes magic + 1 byte version + 1 byte type + 4 bytes length
        header = MAGIC_HEADER + struct.pack(
            "!BBL", PROTOCOL_VERSION, msg_type, len(payload)
        )
        return header + payload

    @staticmethod
    def unpack_message(data):
        """Unpack binary message, return (msg_type, payload, remaining_data)"""
        if len(data) < 10:  # Minimum header size
            return None, None, data

        # Check magic header
        if data[:4] != MAGIC_HEADER:
            raise ValueError(f"Invalid magic header: {data[:4]}")

        # Unpack header
        version, msg_type, payload_length = struct.unpack("!BBL", data[4:10])

        if version != PROTOCOL_VERSION:
            raise ValueError(f"Unsupported protocol version: {version}")

        # Check if we have complete message
        total_length = 10 + payload_length
        if len(data) < total_length:
            return None, None, data  # Incomplete message

        # Extract payload
        payload = data[10:total_length]
        remaining = data[total_length:]

        # Decode JSON payload if applicable
        try:
            payload = json.loads(payload.decode("utf-8"))
        except:
            payload = payload.decode("utf-8", errors="replace")

        return MessageType(msg_type), payload, remaining


class ConnectionHandler:
    """Handle individual client connections with proper state management"""

    def __init__(self, client_socket, address, server):
        self.socket = client_socket
        self.address = address
        self.server = server
        self.buffer = b""
        self.agent_name = None
        self.last_heartbeat = time.time()
        self.running = True

    def send_message(self, msg_type, payload):
        """Send a properly framed message"""
        try:
            message = BinaryProtocol.pack_message(msg_type, payload)
            self.socket.sendall(message)
            return True
        except Exception as e:
            print(f"Send error to {self.address}: {e}")
            return False

    def handle(self):
        """Main connection handler loop"""
        self.socket.settimeout(1.0)  # Allow periodic heartbeat checks
        print(f"[{datetime.now().isoformat()}] Connection from {self.address}")

        try:
            while self.running and self.server.running:
                # Check heartbeat timeout (30 seconds)
                if time.time() - self.last_heartbeat > 30:
                    print(f"Heartbeat timeout for {self.address}")
                    break

                try:
                    # Receive data
                    data = self.socket.recv(8192)
                    if not data:
                        break

                    # Add to buffer
                    self.buffer += data

                    # Process all complete messages in buffer
                    while self.buffer:
                        msg_type, payload, self.buffer = BinaryProtocol.unpack_message(
                            self.buffer
                        )

                        if msg_type is None:
                            break  # Incomplete message, wait for more data

                        # Process message
                        self.process_message(msg_type, payload)

                except socket.timeout:
                    # Send heartbeat
                    if not self.send_message(
                        MessageType.HEARTBEAT, {"timestamp": time.time()}
                    ):
                        break
                except Exception as e:
                    print(f"Receive error from {self.address}: {e}")
                    break

        finally:
            self.cleanup()

    def process_message(self, msg_type, payload):
        """Process received message based on type"""
        self.last_heartbeat = time.time()
        self.server.message_count += 1

        try:
            if msg_type == MessageType.REGISTER:
                self.agent_name = payload.get("agent")
                agent_type = payload.get("type", "CORE")
                self.server.register_agent(self.agent_name, agent_type, self)
                response = {"status": "registered", "agent": self.agent_name}
                self.send_message(MessageType.RESPONSE, response)

            elif msg_type == MessageType.STATUS:
                status = self.server.get_status()
                self.send_message(MessageType.RESPONSE, status)

            elif msg_type == MessageType.SEND:
                target = payload.get("target")
                if target in self.server.connections:
                    # Forward message to target agent
                    target_conn = self.server.connections[target]
                    if target_conn.send_message(MessageType.SEND, payload):
                        response = {"status": "forwarded", "target": target}
                    else:
                        response = {"status": "failed", "error": "Target unreachable"}
                else:
                    response = {"status": "failed", "error": "Target not found"}
                self.send_message(MessageType.RESPONSE, response)

            elif msg_type == MessageType.HEARTBEAT:
                # Echo heartbeat
                self.send_message(MessageType.HEARTBEAT, {"echo": payload})

            elif msg_type == MessageType.SHUTDOWN:
                self.running = False
                self.send_message(MessageType.RESPONSE, {"status": "shutting_down"})

        except Exception as e:
            error_msg = {"error": str(e), "type": str(msg_type)}
            self.send_message(MessageType.ERROR, error_msg)

    def cleanup(self):
        """Clean up connection resources"""
        print(f"[{datetime.now().isoformat()}] Disconnection from {self.address}")
        if self.agent_name:
            self.server.unregister_agent(self.agent_name)
        try:
            self.socket.close()
        except:
            pass


class AgentServer:
    def __init__(self, host="127.0.0.1", port=9999):
        self.host = host
        self.port = port
        self.agents = {}
        self.connections = {}  # agent_name -> ConnectionHandler
        self.running = True
        self.message_count = 0
        self.start_time = time.time()
        self.thread_pool = []
        self.lock = threading.RLock()

    def register_agent(self, agent_name, agent_type="CORE", connection=None):
        """Register an agent with the server"""
        with self.lock:
            self.agents[agent_name] = {
                "type": agent_type,
                "registered": datetime.now().isoformat(),
                "status": "active",
                "connected": connection is not None,
            }
            if connection:
                self.connections[agent_name] = connection
        return True

    def unregister_agent(self, agent_name):
        """Remove agent registration"""
        with self.lock:
            if agent_name in self.agents:
                self.agents[agent_name]["status"] = "disconnected"
                self.agents[agent_name]["connected"] = False
            if agent_name in self.connections:
                del self.connections[agent_name]

    def get_status(self):
        """Return server status"""
        uptime = time.time() - self.start_time
        with self.lock:
            connected_agents = sum(1 for a in self.agents.values() if a["connected"])

        return {
            "status": "running",
            "protocol_version": PROTOCOL_VERSION,
            "agents_registered": len(self.agents),
            "agents_connected": connected_agents,
            "messages_processed": self.message_count,
            "uptime_seconds": int(uptime),
            "throughput": self.message_count / max(uptime, 1),
            "memory_usage": self._get_memory_usage(),
        }

    def _get_memory_usage(self):
        """Get current memory usage in MB"""
        try:
            import psutil

            process = psutil.Process(os.getpid())
            return process.memory_info().rss / 1024 / 1024
        except:
            return 0

    def run(self):
        """Main server loop"""
        # Register default agents (without connections initially)
        default_agents = [
            "director",
            "project_orchestrator",
            "architect",
            "security",
            "constructor",
            "testbed",
            "optimizer",
            "debugger",
            "deployer",
            "monitor",
            "database",
            "ml_ops",
            "patcher",
            "linter",
            "docgen",
            "infrastructure",
            "api_designer",
            "web",
            "mobile",
            "pygui",
            "tui",
            "data_science",
            "c_internal",
            "python_internal",
            "security_chaos",
            "bastion",
            "oversight",
            "researcher",
            "gnu",
            "npu",
            "planner",
        ]

        for agent in default_agents:
            self.register_agent(agent)

        print(f"═══════════════════════════════════════════════════════════════")
        print(f"   Claude Agent Server v2.0 - Binary Protocol")
        print(f"   Running on {self.host}:{self.port}")
        print(f"═══════════════════════════════════════════════════════════════")
        print(f"✓ Protocol version: {PROTOCOL_VERSION}")
        print(f"✓ {len(self.agents)} agents registered")
        print(f"✓ Max message size: {MAX_MESSAGE_SIZE / 1024:.0f}KB")
        print(f"✓ Heartbeat timeout: 30 seconds")
        print(f"═══════════════════════════════════════════════════════════════")

        # Create server socket
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)

        # Platform-specific TCP keepalive settings
        if hasattr(socket, "TCP_KEEPIDLE"):
            server_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 60)
        if hasattr(socket, "TCP_KEEPINTVL"):
            server_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 10)
        if hasattr(socket, "TCP_KEEPCNT"):
            server_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 6)

        server_socket.bind((self.host, self.port))
        server_socket.listen(50)  # Increased backlog
        server_socket.settimeout(1.0)

        # Status reporting thread
        def status_reporter():
            last_count = 0
            while self.running:
                time.sleep(60)  # Report every minute
                if self.message_count - last_count > 0:
                    status = self.get_status()
                    print(
                        f"[{datetime.now().isoformat()}] Status: "
                        f"{status['messages_processed']} total messages, "
                        f"{status['agents_connected']} connected agents, "
                        f"{status['throughput']:.2f} msg/sec, "
                        f"{status['memory_usage']:.1f}MB RAM"
                    )
                    last_count = self.message_count

        status_thread = threading.Thread(target=status_reporter, daemon=True)
        status_thread.start()

        try:
            while self.running:
                try:
                    client_socket, address = server_socket.accept()

                    # Create connection handler
                    handler = ConnectionHandler(client_socket, address, self)

                    # Handle in separate thread
                    thread = threading.Thread(target=handler.handle)
                    thread.daemon = True
                    thread.start()
                    self.thread_pool.append(thread)

                    # Clean up finished threads periodically
                    if len(self.thread_pool) > 100:
                        self.thread_pool = [t for t in self.thread_pool if t.is_alive()]

                except socket.timeout:
                    continue
                except Exception as e:
                    if self.running:
                        print(f"Server accept error: {e}")

        finally:
            server_socket.close()
            print("Server stopped")


def main():
    """Main entry point with signal handling"""
    server = AgentServer()

    def signal_handler(sig, frame):
        print(
            f"\n[{datetime.now().isoformat()}] Received signal {sig}, shutting down..."
        )
        server.running = False

        # Wait for threads to finish (max 5 seconds)
        timeout = time.time() + 5
        while any(t.is_alive() for t in server.thread_pool) and time.time() < timeout:
            time.sleep(0.1)

        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Create PID file
    pid_file = '${CLAUDE_AGENTS_ROOT:-$(dirname "$0")}/../.server_running'
    with open(pid_file, "w") as f:
        f.write(str(os.getpid()))

    try:
        server.run()
    finally:
        # Clean up PID file
        if os.path.exists(pid_file):
            os.remove(pid_file)


if __name__ == "__main__":
    main()
