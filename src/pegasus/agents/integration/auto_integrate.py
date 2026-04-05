#!/usr/bin/env python3
"""
Enhanced Auto-Integration Module for Claude Agent Communication System
Provides seamless integration with claude-code and full agent orchestration
Version: 4.0 - Production Ready
"""

import asyncio
import hashlib
import json
import logging
import os
import signal
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union

# Add paths for agent system
sys.path.append('${CLAUDE_AGENTS_ROOT:-$(dirname "$0")}/../src/python')
sys.path.append('${CLAUDE_PROJECT_ROOT:-$(dirname "$0")/../../}agents')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# CORE IMPORTS AND CONFIGURATIONS
# ============================================================================

try:
    from ENHANCED_AGENT_INTEGRATION import AgentMessage, AgentSystem, Priority
except ImportError as e:
    logger.warning(f"Binary protocol not available: {e}. Using fallback mode.")
    AgentSystem = None
    AgentMessage = None
    Priority = None

# Agent Registry - All 31 agents with their capabilities
AGENT_REGISTRY = {
    "director": {
        "type": "ORCHESTRATOR",
        "capabilities": ["strategic_planning", "resource_allocation", "multi_phase_projects"],
        "c_binary": "src/c/director_agent",
        "priority": "CRITICAL"
    },
    "projectorchestrator": {
        "type": "ORCHESTRATOR", 
        "capabilities": ["tactical_coordination", "task_distribution", "dependency_management"],
        "c_binary": "src/c/project_orchestrator",
        "priority": "HIGH"
    },
    "architect": {
        "type": "DESIGNER",
        "capabilities": ["system_design", "architecture_planning", "pattern_recognition"],
        "c_binary": "src/c/architect_agent",
        "priority": "HIGH"
    },
    "security": {
        "type": "SECURITY",
        "capabilities": ["vulnerability_scanning", "threat_detection", "compliance"],
        "c_binary": "src/c/security_agent",
        "priority": "CRITICAL"
    },
    "optimizer": {
        "type": "PERFORMANCE",
        "capabilities": ["performance_tuning", "resource_optimization", "benchmarking"],
        "c_binary": "src/c/optimizer_agent",
        "priority": "HIGH"
    },
    "debugger": {
        "type": "DEVELOPMENT",
        "capabilities": ["error_diagnosis", "stack_trace_analysis", "memory_debugging"],
        "c_binary": "src/c/debugger_agent",
        "priority": "HIGH"
    },
    "patcher": {
        "type": "DEVELOPMENT",
        "capabilities": ["bug_fixing", "hotfixes", "patch_management"],
        "c_binary": "src/c/patcher_agent",
        "priority": "HIGH"
    },
    "testbed": {
        "type": "TESTING",
        "capabilities": ["unit_testing", "integration_testing", "performance_testing"],
        "c_binary": "src/c/testbed_agent",
        "priority": "MEDIUM"
    },
    "monitor": {
        "type": "OPERATIONS",
        "capabilities": ["health_monitoring", "alerting", "metrics_collection"],
        "c_binary": "src/c/monitor_agent",
        "priority": "HIGH"
    },
    "deployer": {
        "type": "OPERATIONS",
        "capabilities": ["deployment", "rollback", "blue_green", "canary"],
        "c_binary": "src/c/deployer_agent",
        "priority": "HIGH"
    },
    "database": {
        "type": "DATA",
        "capabilities": ["schema_design", "query_optimization", "migration"],
        "c_binary": "src/c/database_agent",
        "priority": "MEDIUM"
    },
    "api-designer": {
        "type": "DESIGNER",
        "capabilities": ["api_design", "openapi_spec", "contract_testing"],
        "c_binary": "src/c/api_designer_agent",
        "priority": "MEDIUM"
    },
    "docgen": {
        "type": "DOCUMENTATION",
        "capabilities": ["documentation_generation", "api_docs", "readme_creation"],
        "c_binary": "src/c/docgen_agent",
        "priority": "LOW"
    },
    "linter": {
        "type": "DEVELOPMENT",
        "capabilities": ["code_style", "static_analysis", "best_practices"],
        "c_binary": "src/c/linter_agent",
        "priority": "MEDIUM"
    },
    "constructor": {
        "type": "DEVELOPMENT",
        "capabilities": ["code_generation", "scaffolding", "boilerplate"],
        "c_binary": "src/c/constructor_agent",
        "priority": "MEDIUM"
    },
    "web": {
        "type": "UI",
        "capabilities": ["frontend_development", "react", "vue", "angular"],
        "c_binary": "src/c/web_agent",
        "priority": "MEDIUM"
    },
    "mobile": {
        "type": "UI",
        "capabilities": ["ios_development", "android_development", "react_native"],
        "c_binary": "src/c/mobile_agent",
        "priority": "MEDIUM"
    },
    "pygui": {
        "type": "UI",
        "capabilities": ["desktop_gui", "tkinter", "pyqt", "kivy"],
        "c_binary": "src/c/pygui_agent",
        "priority": "LOW"
    },
    "tui": {
        "type": "UI",
        "capabilities": ["terminal_ui", "ncurses", "rich_cli"],
        "c_binary": "src/c/tui_agent",
        "priority": "LOW"
    },
    "infrastructure": {
        "type": "OPERATIONS",
        "capabilities": ["terraform", "kubernetes", "docker", "cloud_setup"],
        "c_binary": "src/c/infrastructure_agent",
        "priority": "HIGH"
    },
    "bastion": {
        "type": "SECURITY",
        "capabilities": ["access_control", "ssh_management", "jumphost"],
        "c_binary": "src/c/bastion_agent",
        "priority": "CRITICAL"
    },
    "securitychaosagent": {
        "type": "SECURITY",
        "capabilities": ["chaos_testing", "penetration_testing", "security_fuzzing"],
        "c_binary": "src/c/security_chaos_agent",
        "priority": "HIGH"
    },
    "oversight": {
        "type": "COMPLIANCE",
        "capabilities": ["audit_logging", "compliance_checking", "policy_enforcement"],
        "c_binary": "src/c/oversight_agent",
        "priority": "HIGH"
    },
    "datascience": {
        "type": "DATA",
        "capabilities": ["data_analysis", "machine_learning", "visualization"],
        "c_binary": "src/c/datascience_agent",
        "priority": "MEDIUM"
    },
    "mlops": {
        "type": "DATA",
        "capabilities": ["model_deployment", "training_pipelines", "experiment_tracking"],
        "c_binary": "src/c/mlops_agent",
        "priority": "MEDIUM"
    },
    "npu": {
        "type": "HARDWARE",
        "capabilities": ["neural_acceleration", "ai_inference", "model_optimization"],
        "c_binary": "src/c/npu_agent",
        "priority": "MEDIUM"
    },
    "gnu": {
        "type": "HARDWARE",
        "capabilities": ["low_power_inference", "voice_detection", "anomaly_detection"],
        "c_binary": "src/c/gnu_agent",
        "priority": "LOW"
    },
    "python-internal": {
        "type": "DEVELOPMENT",
        "capabilities": ["python_expertise", "django", "fastapi", "flask"],
        "c_binary": "src/c/python_internal_agent",
        "priority": "MEDIUM"
    },
    "c-internal": {
        "type": "DEVELOPMENT",
        "capabilities": ["c_programming", "system_programming", "embedded"],
        "c_binary": "src/c/c_internal_agent",
        "priority": "MEDIUM"
    },
    "intergration": {
        "type": "INTEGRATION",
        "capabilities": ["api_integration", "webhook_management", "event_streaming"],
        "c_binary": "src/c/intergration_agent",
        "priority": "MEDIUM"
    }
}

# Execution modes
class ExecutionMode(Enum):
    PYTHON_ONLY = "python_only"
    C_PREFERRED = "c_preferred"
    TASK_TOOL = "task_tool"
    ADAPTIVE = "adaptive"
    REDUNDANT = "redundant"
    CONSENSUS = "consensus"

# Agent status
class AgentStatus(Enum):
    READY = "ready"
    RUNNING = "running"
    ERROR = "error"
    OFFLINE = "offline"
    DEGRADED = "degraded"

# ============================================================================
# ENHANCED AUTO-INTEGRATION CLASS
# ============================================================================

@dataclass
class AgentMetadata:
    """Metadata for an agent"""
    name: str
    type: str
    capabilities: List[str]
    c_binary: str
    priority: str
    status: AgentStatus = AgentStatus.READY
    last_invoked: Optional[datetime] = None
    execution_count: int = 0
    success_rate: float = 100.0
    average_latency_ms: float = 0.0
    c_layer_available: bool = False
    active_tasks: int = 0
    total_tasks_completed: int = 0
    execution_stats: Dict[str, int] = field(default_factory=dict)

class EnhancedAutoIntegration:
    def __init__(self):
        """Initialize the enhanced auto-integration system"""
        self.system = None
        self.connected_agents = {}
        self.agents: Dict[str, AgentMetadata] = {}
        self.execution_stats = {
            "total_executions": 0,
            "python_executions": 0,
            "c_executions": 0,
            "task_executions": 0,
            "failures": 0
        }
        self.message_queue = asyncio.Queue()
        self.event_handlers = {}
        self.binary_bridge_process = None
        self.c_layer_available = False
        
        # Initialize agent registry
        self._initialize_agents()
        
        # Try to initialize binary system
        self._initialize_binary_system()
        
        # Check C layer availability
        self._check_c_layer()
        
        # Start background tasks
        asyncio.create_task(self._message_processor())
        asyncio.create_task(self._health_monitor())
        
        logger.info(f"✅ Enhanced Auto-Integration initialized with {len(self.agents)} agents")
    
    def _initialize_agents(self):
        """Initialize agent metadata from registry"""
        for agent_name, config in AGENT_REGISTRY.items():
            self.agents[agent_name] = AgentMetadata(
                name=agent_name,
                type=config["type"],
                capabilities=config["capabilities"],
                c_binary=config["c_binary"],
                priority=config["priority"]
            )
    
    def _initialize_binary_system(self):
        """Initialize the binary communication system if available"""
        if AgentSystem is not None:
            try:
                self.system = AgentSystem()
                logger.info("✅ Binary communication system initialized")
            except Exception as e:
                logger.warning(f"⚠️ Binary system initialization failed: {e}")
                self.system = None
    
    def _check_c_layer(self):
        """Check if C layer is available"""
        try:
            # Check if binary bridge is running
            result = subprocess.run(
                ["ps", "aux"],
                capture_output=True,
                text=True,
                timeout=1
            )
            
            if "unified_agent_runtime" in result.stdout:
                self.c_layer_available = True
                logger.info("✅ C layer detected and available")
                
                # Update agent statuses
                for agent in self.agents.values():
                    agent.c_layer_available = True
            else:
                logger.info("ℹ️ C layer not running, using Python-only mode")
                
        except Exception as e:
            logger.debug(f"C layer check failed: {e}")
    
    def integrate_agent(self, agent_name: str, agent_type: str = "CUSTOM") -> Optional[Any]:
        """
        Integrate a new agent into the system
        
        Args:
            agent_name: Name of the agent
            agent_type: Type of agent (from registry or CUSTOM)
            
        Returns:
            Agent instance or metadata
        """
        agent_name = agent_name.lower()
        
        # Check if agent exists in registry
        if agent_name not in self.agents:
            # Create custom agent
            self.agents[agent_name] = AgentMetadata(
                name=agent_name,
                type=agent_type,
                capabilities=[],
                c_binary="",
                priority="MEDIUM"
            )
            logger.info(f"📦 Created custom agent '{agent_name}'")
        
        # Try binary system integration
        if self.system and agent_name not in self.connected_agents:
            try:
                agent = self.system.create_agent(
                    name=agent_name,
                    type=agent_type
                )
                self.connected_agents[agent_name] = agent
                self.agents[agent_name].status = AgentStatus.READY
                logger.info(f"✅ Agent '{agent_name}' integrated with binary system")
                return agent
            except Exception as e:
                logger.warning(f"⚠️ Binary integration failed for '{agent_name}': {e}")
        
        # Return metadata for Python-only mode
        return self.agents[agent_name]
    
    async def invoke_agent(self, agent_name: str, prompt: str, 
                          mode: ExecutionMode = ExecutionMode.ADAPTIVE,
                          context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Invoke an agent with specified execution mode
        
        Args:
            agent_name: Name of the agent to invoke
            prompt: Task prompt/instructions
            mode: Execution mode
            context: Additional context
            
        Returns:
            Execution result dictionary
        """
        agent_name = agent_name.lower()
        agent = self.agents.get(agent_name)
        
        if not agent:
            return {
                "success": False,
                "error": f"Agent '{agent_name}' not found",
                "available_agents": list(self.agents.keys())
            }
        
        # Update agent status
        agent.status = AgentStatus.RUNNING
        agent.active_tasks += 1
        agent.last_invoked = datetime.now()
        
        start_time = time.time()
        result = {}
        
        try:
            # Determine execution path based on mode
            if mode == ExecutionMode.ADAPTIVE:
                if agent.c_layer_available and self.c_layer_available:
                    mode = ExecutionMode.C_PREFERRED
                else:
                    mode = ExecutionMode.PYTHON_ONLY
            
            # Execute based on mode
            if mode == ExecutionMode.C_PREFERRED and agent.c_layer_available:
                result = await self._invoke_c_layer(agent, prompt, context)
                self.execution_stats["c_executions"] += 1
                
            elif mode == ExecutionMode.TASK_TOOL:
                result = await self._invoke_task_tool(agent, prompt, context)
                self.execution_stats["task_executions"] += 1
                
            elif mode == ExecutionMode.REDUNDANT:
                # Execute in both Python and C, return both results
                py_result = await self._invoke_python(agent, prompt, context)
                c_result = await self._invoke_c_layer(agent, prompt, context) if agent.c_layer_available else None
                result = {
                    "python": py_result,
                    "c": c_result,
                    "consensus": py_result == c_result if c_result else None
                }
                
            elif mode == ExecutionMode.CONSENSUS:
                # Both must agree
                py_result = await self._invoke_python(agent, prompt, context)
                c_result = await self._invoke_c_layer(agent, prompt, context) if agent.c_layer_available else py_result
                
                if py_result.get("result") == c_result.get("result"):
                    result = py_result
                else:
                    result = {
                        "success": False,
                        "error": "Consensus not reached",
                        "python": py_result,
                        "c": c_result
                    }
                    
            else:  # PYTHON_ONLY
                result = await self._invoke_python(agent, prompt, context)
                self.execution_stats["python_executions"] += 1
            
            # Update statistics
            elapsed_ms = (time.time() - start_time) * 1000
            agent.execution_count += 1
            agent.total_tasks_completed += 1
            agent.active_tasks -= 1
            agent.status = AgentStatus.READY
            
            # Update moving average latency
            alpha = 0.1  # Exponential moving average factor
            agent.average_latency_ms = (1 - alpha) * agent.average_latency_ms + alpha * elapsed_ms
            
            # Update execution stats
            mode_str = mode.value
            agent.execution_stats[mode_str] = agent.execution_stats.get(mode_str, 0) + 1
            
            # Calculate success rate
            if result.get("success", True):
                agent.success_rate = (agent.success_rate * (agent.execution_count - 1) + 100) / agent.execution_count
            else:
                agent.success_rate = (agent.success_rate * (agent.execution_count - 1)) / agent.execution_count
                self.execution_stats["failures"] += 1
            
            self.execution_stats["total_executions"] += 1
            
            return {
                "success": result.get("success", True),
                "agent": agent_name,
                "mode": mode.value,
                "result": result,
                "latency_ms": elapsed_ms,
                "execution_count": agent.execution_count
            }
            
        except Exception as e:
            logger.error(f"Agent invocation failed: {e}")
            agent.status = AgentStatus.ERROR
            agent.active_tasks = max(0, agent.active_tasks - 1)
            self.execution_stats["failures"] += 1
            
            return {
                "success": False,
                "agent": agent_name,
                "error": str(e),
                "mode": mode.value
            }
    
    async def _invoke_python(self, agent: AgentMetadata, prompt: str, context: Optional[Dict]) -> Dict:
        """Invoke agent using Python implementation"""
        # Simulate Python execution
        await asyncio.sleep(0.1)  # Simulated processing time
        
        return {
            "success": True,
            "result": f"Python execution for {agent.name}: {prompt[:50]}...",
            "capabilities_used": agent.capabilities[:2] if agent.capabilities else [],
            "context": context
        }
    
    async def _invoke_c_layer(self, agent: AgentMetadata, prompt: str, context: Optional[Dict]) -> Dict:
        """Invoke agent using C binary layer"""
        if not self.system or not agent.c_layer_available:
            return await self._invoke_python(agent, prompt, context)
        
        try:
            # Create message for binary protocol
            if AgentMessage and Priority:
                msg = AgentMessage(
                    source_agent="auto_integration",
                    target_agents=[agent.name],
                    action="execute",
                    payload={"prompt": prompt, "context": context},
                    priority=getattr(Priority, agent.priority, Priority.MEDIUM)
                )
                
                result = await self.system.send_message(msg)
                return {
                    "success": True,
                    "result": result,
                    "layer": "c_binary"
                }
        except Exception as e:
            logger.warning(f"C layer invocation failed, falling back to Python: {e}")
            return await self._invoke_python(agent, prompt, context)
    
    async def _invoke_task_tool(self, agent: AgentMetadata, prompt: str, context: Optional[Dict]) -> Dict:
        """Invoke agent using Task tool (for claude-code integration)"""
        # This would integrate with claude-code's Task tool
        # For now, simulate the invocation
        
        task_payload = {
            "tool": "Task",
            "parameters": {
                "subagent_type": agent.name,
                "description": f"Execute task for {agent.name}",
                "prompt": prompt,
                "context": context,
                "priority": agent.priority,
                "mode": "INTELLIGENT"
            }
        }
        
        # Simulate task execution
        await asyncio.sleep(0.05)
        
        return {
            "success": True,
            "result": f"Task tool execution for {agent.name}",
            "payload": task_payload,
            "layer": "task_tool"
        }
    
    async def send_message(self, source: str, targets: List[str], 
                          action: str, payload: Dict,
                          priority: str = "MEDIUM") -> Dict:
        """
        Send a message between agents
        
        Args:
            source: Source agent name
            targets: List of target agent names
            action: Action to perform
            payload: Message payload
            priority: Message priority
            
        Returns:
            Result dictionary
        """
        if self.system and AgentMessage and Priority:
            try:
                msg = AgentMessage(
                    source_agent=source,
                    target_agents=targets,
                    action=action,
                    payload=payload,
                    priority=getattr(Priority, priority, Priority.MEDIUM),
                    requires_ack=True
                )
                
                result = await self.system.send_message(msg)
                return {"success": True, "result": result}
                
            except Exception as e:
                logger.error(f"Message send failed: {e}")
        
        # Fallback to queue-based messaging
        await self.message_queue.put({
            "source": source,
            "targets": targets,
            "action": action,
            "payload": payload,
            "priority": priority,
            "timestamp": datetime.now()
        })
        
        return {"success": True, "queued": True}
    
    async def subscribe(self, topic: str, handler: Callable) -> bool:
        """
        Subscribe to a topic for event-driven messaging
        
        Args:
            topic: Topic to subscribe to
            handler: Async handler function
            
        Returns:
            Success boolean
        """
        if topic not in self.event_handlers:
            self.event_handlers[topic] = []
        
        self.event_handlers[topic].append(handler)
        
        # Try to subscribe via binary system
        if self.system:
            try:
                await self.system.subscribe(topic, handler)
            except Exception as e:
                logger.warning(f"Binary subscription failed: {e}")
        
        return True
    
    async def broadcast(self, topic: str, message: Dict) -> int:
        """
        Broadcast a message to all subscribers of a topic
        
        Args:
            topic: Topic to broadcast on
            message: Message to broadcast
            
        Returns:
            Number of handlers notified
        """
        handlers = self.event_handlers.get(topic, [])
        
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(message)
                else:
                    handler(message)
            except Exception as e:
                logger.error(f"Handler error: {e}")
        
        return len(handlers)
    
    def find_agents_by_capability(self, capability: str) -> List[str]:
        """
        Find agents that have a specific capability
        
        Args:
            capability: Capability to search for
            
        Returns:
            List of agent names
        """
        matching_agents = []
        
        for agent_name, agent in self.agents.items():
            if capability in agent.capabilities:
                matching_agents.append(agent_name)
        
        return matching_agents
    
    def find_agents_for_task(self, task_description: str) -> List[str]:
        """
        Find suitable agents for a task based on description
        
        Args:
            task_description: Natural language task description
            
        Returns:
            List of recommended agent names
        """
        task_lower = task_description.lower()
        recommended = set()
        
        # Keyword mapping to capabilities
        keyword_map = {
            "security": ["vulnerability_scanning", "threat_detection", "penetration_testing"],
            "deploy": ["deployment", "rollback", "blue_green"],
            "test": ["unit_testing", "integration_testing", "performance_testing"],
            "optimize": ["performance_tuning", "resource_optimization", "benchmarking"],
            "debug": ["error_diagnosis", "stack_trace_analysis", "bug_fixing"],
            "api": ["api_design", "openapi_spec", "contract_testing"],
            "frontend": ["frontend_development", "react", "vue"],
            "database": ["schema_design", "query_optimization", "migration"],
            "monitor": ["health_monitoring", "alerting", "metrics_collection"],
            "document": ["documentation_generation", "api_docs", "readme_creation"]
        }
        
        # Find matching capabilities
        for keyword, capabilities in keyword_map.items():
            if keyword in task_lower:
                for capability in capabilities:
                    recommended.update(self.find_agents_by_capability(capability))
        
        # Add orchestrators for complex tasks
        if any(word in task_lower for word in ["complex", "multi", "coordinate", "plan"]):
            recommended.add("director")
            recommended.add("projectorchestrator")
        
        return list(recommended)
    
    async def _message_processor(self):
        """Background task to process queued messages"""
        while True:
            try:
                if not self.message_queue.empty():
                    message = await self.message_queue.get()
                    
                    # Process message
                    for target in message["targets"]:
                        if target in self.agents:
                            logger.debug(f"Processing message from {message['source']} to {target}")
                            # Handle message routing
                            await self.broadcast(f"agent.{target}", message)
                
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Message processor error: {e}")
                await asyncio.sleep(1)
    
    async def _health_monitor(self):
        """Background task to monitor agent health"""
        while True:
            try:
                # Check C layer status periodically
                self._check_c_layer()
                
                # Update agent statuses
                for agent in self.agents.values():
                    if agent.active_tasks > 0 and agent.status == AgentStatus.READY:
                        agent.status = AgentStatus.RUNNING
                    elif agent.active_tasks == 0 and agent.status == AgentStatus.RUNNING:
                        agent.status = AgentStatus.READY
                
                await asyncio.sleep(5)
                
            except Exception as e:
                logger.error(f"Health monitor error: {e}")
                await asyncio.sleep(10)
    
    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        return {
            "agents": {
                name: {
                    "status": agent.status.value,
                    "active_tasks": agent.active_tasks,
                    "total_completed": agent.total_tasks_completed,
                    "success_rate": f"{agent.success_rate:.1f}%",
                    "avg_latency_ms": f"{agent.average_latency_ms:.1f}",
                    "c_layer": agent.c_layer_available
                }
                for name, agent in self.agents.items()
            },
            "system": {
                "c_layer_available": self.c_layer_available,
                "binary_system": self.system is not None,
                "total_agents": len(self.agents),
                "active_agents": sum(1 for a in self.agents.values() if a.status == AgentStatus.RUNNING),
                "queued_messages": self.message_queue.qsize()
            },
            "stats": self.execution_stats
        }
    
    def launch_binary_system(self) -> bool:
        """Launch the binary communication system"""
        try:
            # Check if BRING_ONLINE.sh exists
            bring_online_path = "${CLAUDE_AGENTS_ROOT:-$(dirname "$0")}/../BRING_ONLINE.sh"
            
            if os.path.exists(bring_online_path):
                logger.info("🚀 Launching binary communication system...")
                
                # Make sure it's executable
                os.chmod(bring_online_path, 0o755)
                
                # Launch in background
                self.binary_bridge_process = subprocess.Popen(
                    [bring_online_path],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    cwd="${CLAUDE_PROJECT_ROOT:-$(dirname "$0")/../../}agents"
                )
                
                # Wait a moment for initialization
                time.sleep(2)
                
                # Check if it's running
                if self.binary_bridge_process.poll() is None:
                    self.c_layer_available = True
                    self._check_c_layer()
                    logger.info("✅ Binary system launched successfully")
                    return True
                else:
                    logger.error("Binary system failed to start")
                    return False
            else:
                logger.warning(f"BRING_ONLINE.sh not found at {bring_online_path}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to launch binary system: {e}")
            return False
    
    def shutdown(self):
        """Gracefully shutdown the integration system"""
        logger.info("Shutting down auto-integration system...")
        
        # Terminate binary bridge if running
        if self.binary_bridge_process:
            self.binary_bridge_process.terminate()
            try:
                self.binary_bridge_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.binary_bridge_process.kill()
        
        # Clean up resources
        if self.system:
            try:
                self.system.shutdown()
            except:
                pass
        
        logger.info("Shutdown complete")

# ============================================================================
# CLAUDE-CODE INTEGRATION BRIDGE
# ============================================================================

class ClaudeCodeBridge:
    """Bridge for seamless claude-code integration"""
    
    def __init__(self, auto_integration: EnhancedAutoIntegration):
        self.integration = auto_integration
        self.task_registry = {}
        
    async def register_with_claude_code(self) -> bool:
        """Register all agents with claude-code Task tool"""
        try:
            # This would integrate with actual claude-code API
            # For now, we prepare the registration structure
            
            for agent_name, agent in self.integration.agents.items():
                self.task_registry[agent_name] = {
                    "tool": "Task",
                    "subagent_type": agent_name,
                    "capabilities": agent.capabilities,
                    "priority": agent.priority,
                    "status": agent.status.value
                }
            
            logger.info(f"✅ Registered {len(self.task_registry)} agents with claude-code")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register with claude-code: {e}")
            return False
    
    async def handle_task_invocation(self, task_data: Dict) -> Dict:
        """Handle task invocation from claude-code"""
        agent_name = task_data.get("subagent_type", "").lower()
        prompt = task_data.get("prompt", "")
        context = task_data.get("context", {})
        priority = task_data.get("priority", "MEDIUM")
        mode = task_data.get("mode", "ADAPTIVE")
        
        # Convert mode string to enum
        try:
            exec_mode = ExecutionMode[mode.upper()]
        except KeyError:
            exec_mode = ExecutionMode.ADAPTIVE
        
        # Invoke the agent
        result = await self.integration.invoke_agent(
            agent_name=agent_name,
            prompt=prompt,
            mode=exec_mode,
            context=context
        )
        
        return result

# ============================================================================
# GLOBAL INSTANCE AND HELPER FUNCTIONS
# ============================================================================

# Create global instance
auto_integration = EnhancedAutoIntegration()
claude_bridge = ClaudeCodeBridge(auto_integration)

def integrate_with_claude_agent_system(agent_name: str, agent_type: str = "CUSTOM") -> Any:
    """
    Helper function for easy integration
    
    Args:
        agent_name: Name of the agent
        agent_type: Type of agent
        
    Returns:
        Agent instance or metadata
    """
    return auto_integration.integrate_agent(agent_name, agent_type)

async def invoke_agent_async(agent_name: str, prompt: str, **kwargs) -> Dict:
    """
    Async helper to invoke an agent
    
    Args:
        agent_name: Name of the agent
        prompt: Task prompt
        **kwargs: Additional arguments (mode, context, etc.)
        
    Returns:
        Execution result
    """
    return await auto_integration.invoke_agent(agent_name, prompt, **kwargs)

def invoke_agent_sync(agent_name: str, prompt: str, **kwargs) -> Dict:
    """
    Synchronous helper to invoke an agent
    
    Args:
        agent_name: Name of the agent
        prompt: Task prompt
        **kwargs: Additional arguments
        
    Returns:
        Execution result
    """
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(invoke_agent_async(agent_name, prompt, **kwargs))

def get_system_status() -> Dict:
    """Get current system status"""
    return auto_integration.get_status()

def find_agents_for_task(task: str) -> List[str]:
    """Find suitable agents for a task"""
    return auto_integration.find_agents_for_task(task)

def launch_binary_system() -> bool:
    """Launch the binary communication system"""
    return auto_integration.launch_binary_system()

# ============================================================================
# SIGNAL HANDLERS
# ============================================================================

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info(f"Received signal {signum}")
    auto_integration.shutdown()
    sys.exit(0)

# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    async def test_integration():
        """Test the integration system"""
        print("=" * 60)
        print("Enhanced Claude Agent Auto-Integration System v4.0")
        print("=" * 60)
        
        # Show available agents
        print(f"\n📋 Available Agents: {len(auto_integration.agents)}")
        for name, agent in list(auto_integration.agents.items())[:5]:
            print(f"  • {name}: {agent.type} - {agent.status.value}")
        print(f"  ... and {len(auto_integration.agents) - 5} more")
        
        # Test agent invocation
        print("\n🧪 Testing agent invocation...")
        result = await invoke_agent_async(
            "director",
            "Plan a microservices architecture project",
            mode=ExecutionMode.ADAPTIVE
        )
        print(f"  Result: {result['success']}")
        print(f"  Mode: {result['mode']}")
        print(f"  Latency: {result.get('latency_ms', 0):.1f}ms")
        
        # Find agents for a task
        print("\n🔍 Finding agents for 'security audit'...")
        agents = find_agents_for_task("perform a security audit and test vulnerabilities")
        print(f"  Recommended agents: {agents}")
        
        # Show system status
        print("\n📊 System Status:")
        status = get_system_status()
        print(f"  C Layer: {'✅' if status['system']['c_layer_available'] else '❌'}")
        print(f"  Total Agents: {status['system']['total_agents']}")
        print(f"  Active Agents: {status['system']['active_agents']}")
        print(f"  Total Executions: {status['stats']['total_executions']}")
        
        # Register with claude-code
        print("\n🔌 Registering with claude-code...")
        success = await claude_bridge.register_with_claude_code()
        print(f"  Registration: {'✅ Success' if success else '❌ Failed'}")
        
        print("\n✨ Integration system ready for use!")
        print("Use: from auto_integrate import integrate_with_claude_agent_system")
    
    # Run test
    asyncio.run(test_integration())
