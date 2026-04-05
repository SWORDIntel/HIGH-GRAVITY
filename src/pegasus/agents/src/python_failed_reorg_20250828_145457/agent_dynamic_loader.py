"""Dynamic Agent Class Loader - Handles naming inconsistencies"""

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


def get_agent_executor_class(agent_name: str):
    """Get the correct PythonExecutor class name for an agent"""
    class_mapping = {
        "androidmobile": "ANDROIDMOBILEPythonExecutor",
        "apidesigner": "APIDESIGNERPythonExecutor",
        "architect": "ARCHITECTPythonExecutor",
        "bastion": "BASTIONPythonExecutor",
        "constructor": "CONSTRUCTORPythonExecutor",
        "cryptoexpert": "CRYPTOEXPERTPythonExecutor",
        "cso": "CSOPythonExecutor",
        "database": "DatabasePythonExecutor",
        "datascience": "DATASCIENCEPythonExecutor",
        "debugger": "DEBUGGERPythonExecutor",
        "deployer": "DEPLOYERPythonExecutor",
        "director": "DirectorPythonExecutor",
        "docgen": "DOCGENPythonExecutor",
        "gna": "GNAPythonExecutor",
        "infrastructure": "INFRASTRUCTUREPythonExecutor",
        "intergration": "INTERGRATIONPythonExecutor",
        "leadengineer": "LEADENGINEERPythonExecutor",
        "linter": "LINTERPythonExecutor",
        "mlops": "MLOPSPythonExecutor",
        "monitor": "MONITORPythonExecutor",
        "npu": "NPUPythonExecutor",
        "optimizer": "OPTIMIZERPythonExecutor",
        "organization": "ORGANIZATIONPythonExecutor",
        "oversight": "OVERSIGHTPythonExecutor",
        "packager": "PACKAGERPythonExecutor",
        "patcher": "PATCHERPythonExecutor",
        "planner": "PLANNERPythonExecutor",
        "projectorchestrator": "PROJECTORCHESTRATORPythonExecutor",
        "pygui": "PYGUIPythonExecutor",
        "python-internal": "PYTHONINTERNALPythonExecutor",
        "qadirector": "QADIRECTORPythonExecutor",
        "quantumguard": "QUANTUMGUARDPythonExecutor",
        "redteamorchestrator": "REDTEAMORCHESTRATORPythonExecutor",
        "researcher": "RESEARCHERPythonExecutor",
        "security": "SecurityPythonExecutor",
        "securityauditor": "SECURITYAUDITORPythonExecutor",
        "securitychaosagent": "SecurityChaosAgentPythonExecutor",
        "testbed": "TESTBEDPythonExecutor",
        "tui": "TUIPythonExecutor",
        "web": "WEBPythonExecutor",
    }
    return class_mapping.get(agent_name)


async def invoke_agent_dynamically(
    agent_name: str, action: str, context: Dict[str, Any]
) -> Dict[str, Any]:
    """Dynamically invoke an agent with correct class name"""
    class_name = get_agent_executor_class(agent_name)
    if not class_name:
        return {
            "status": "error",
            "message": f"Unknown agent: {agent_name}",
            "agent": agent_name,
        }

    try:
        # Dynamic import and instantiation
        module_name = f"{agent_name}_impl"
        module = __import__(module_name, fromlist=[class_name])
        executor_class = getattr(module, class_name)
        executor = executor_class()

        # Execute the action using the correct method name
        result = await executor.execute_command(action, context)
        return result

    except ImportError as e:
        # Agent implementation file doesn't exist - provide helpful feedback
        logger.warning(f"Agent {agent_name} implementation not found: {e}")
        return {
            "status": "error",
            "message": f"Agent {agent_name} implementation not available",
            "agent": agent_name,
            "action": action,
            "type": "missing_implementation",
            "suggestion": f"Create {agent_name}_impl.py to enable this agent",
        }
    except Exception as e:
        logger.error(f"Error invoking {agent_name}: {e}")
        return {
            "status": "error",
            "message": str(e),
            "agent": agent_name,
            "action": action,
        }
