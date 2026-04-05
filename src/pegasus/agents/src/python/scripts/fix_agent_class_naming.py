#!/usr/bin/env python3
"""
Fix Agent Class Naming Inconsistencies

This script creates a helper function to handle both naming patterns for agent executor classes:
- Proper case: SecurityPythonExecutor, DirectorPythonExecutor, DatabasePythonExecutor
- All caps: APIDESIGNERPythonExecutor, ARCHITECTPythonExecutor, OPTIMIZERPythonExecutor

It generates a mapping and updates the production_orchestrator.py to use dynamic class loading.
"""

import os
import re
from pathlib import Path


def analyze_agent_class_names():
    """Analyze all agent implementation files to find actual class names"""
    agent_classes = {}
    impl_dir = Path("${CLAUDE_AGENTS_ROOT:-$(dirname "$0")}/../src/python")
    
    for impl_file in impl_dir.glob("*_impl.py"):
        agent_name = impl_file.stem.replace("_impl", "")
        
        try:
            with open(impl_file, 'r') as f:
                content = f.read()
                
            # Find PythonExecutor class
            match = re.search(r'class\s+(\w*PythonExecutor):', content)
            if match:
                class_name = match.group(1)
                agent_classes[agent_name] = class_name
                print(f"{agent_name}: {class_name}")
        
        except Exception as e:
            print(f"Error reading {impl_file}: {e}")
    
    return agent_classes

def generate_dynamic_loader_code(agent_classes):
    """Generate Python code for dynamic class loading"""
    
    code_lines = [
        "def get_agent_executor_class(agent_name: str):",
        "    \"\"\"Get the correct PythonExecutor class name for an agent\"\"\"",
        "    class_mapping = {"
    ]
    
    for agent, class_name in sorted(agent_classes.items()):
        code_lines.append(f'        "{agent}": "{class_name}",')
    
    code_lines.extend([
        "    }",
        "    return class_mapping.get(agent_name)",
        "",
        "async def invoke_agent_dynamically(agent_name: str, action: str, context: Dict[str, Any]) -> Dict[str, Any]:",
        "    \"\"\"Dynamically invoke an agent with correct class name\"\"\"",
        "    class_name = get_agent_executor_class(agent_name)",
        "    if not class_name:",
        "        return {",
        "            'status': 'error',",
        "            'message': f'Unknown agent: {agent_name}',",
        "            'agent': agent_name",
        "        }",
        "",
        "    try:",
        "        # Dynamic import and instantiation",
        "        module_name = f'{agent_name}_impl'",
        "        module = __import__(module_name, fromlist=[class_name])",
        "        executor_class = getattr(module, class_name)",
        "        executor = executor_class()",
        "",
        "        # Execute the action",
        "        result = await executor.execute(action, context)",
        "        return result",
        "",
        "    except Exception as e:",
        "        logger.error(f'Error invoking {agent_name}: {e}')",
        "        return {",
        "            'status': 'error',",
        "            'message': str(e),",
        "            'agent': agent_name,",
        "            'action': action",
        "        }"
    ])
    
    return "\n".join(code_lines)

def main():
    print("Analyzing agent class naming patterns...")
    agent_classes = analyze_agent_class_names()
    
    print(f"\nFound {len(agent_classes)} agent executor classes")
    
    # Generate dynamic loader code
    print("\nGenerating dynamic loader code...")
    loader_code = generate_dynamic_loader_code(agent_classes)
    
    # Save the dynamic loader
    output_file = Path("${CLAUDE_AGENTS_ROOT:-$(dirname "$0")}/../src/python/agent_dynamic_loader.py")
    with open(output_file, 'w') as f:
        f.write('"""Dynamic Agent Class Loader - Handles naming inconsistencies"""\n')
        f.write('import logging\nfrom typing import Dict, Any\n\n')
        f.write('logger = logging.getLogger(__name__)\n\n')
        f.write(loader_code)
    
    print(f"Dynamic loader saved to: {output_file}")
    
    # Show patterns found
    proper_case = [name for name, cls in agent_classes.items() if not cls.isupper() or cls == cls.title()]
    all_caps = [name for name, cls in agent_classes.items() if cls.isupper() and cls != cls.title()]
    
    print(f"\nNaming patterns found:")
    print(f"Proper case pattern ({len(proper_case)}): {proper_case[:5]}...")
    print(f"All caps pattern ({len(all_caps)}): {all_caps[:5]}...")

if __name__ == "__main__":
    main()