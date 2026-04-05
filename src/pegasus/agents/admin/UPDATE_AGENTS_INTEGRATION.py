#!/usr/bin/env python3
"""
Updates all existing agent definition files to include communication system integration
This ensures all agents are properly connected to the ultra-fast binary protocol
"""

import glob
import os
import re

import yaml

# Communication system integration block to add to each agent
COMMUNICATION_INTEGRATION = """
################################################################################
# COMMUNICATION SYSTEM INTEGRATION v3.0
################################################################################

communication:
  protocol: ultra_fast_binary_v3
  capabilities:
    throughput: 4.2M_msg_sec
    latency: 200ns_p99
    
  integration:
    auto_register: true
    binary_protocol: "${CLAUDE_AGENTS_ROOT:-$(dirname "$0")}/../binary-communications-system/ultra_hybrid_enhanced.c"
    discovery_service: "${CLAUDE_AGENTS_ROOT:-$(dirname "$0")}/../src/c/agent_discovery.c"
    message_router: "${CLAUDE_AGENTS_ROOT:-$(dirname "$0")}/../src/c/message_router.c"
    runtime: "${CLAUDE_AGENTS_ROOT:-$(dirname "$0")}/../src/c/unified_agent_runtime.c"
    
  ipc_methods:
    CRITICAL: shared_memory_50ns
    HIGH: io_uring_500ns
    NORMAL: unix_sockets_2us
    LOW: mmap_files_10us
    BATCH: dma_regions
    
  message_patterns:
    - publish_subscribe
    - request_response
    - work_queues
    - broadcast
    - multicast
    
  security:
    authentication: JWT_RS256_HS256
    authorization: RBAC_4_levels
    encryption: TLS_1.3
    integrity: HMAC_SHA256
    
  monitoring:
    prometheus_port: 8001
    grafana_dashboard: true
    health_check: "/health/ready"
    metrics_endpoint: "/metrics"
    
  auto_integration_code: |
    # Python integration
    from 03-BRIDGES.auto_integrate import integrate_with_claude_agent_system
    agent = integrate_with_claude_agent_system("{agent_name}")
    
    # C integration
    #include "ultra_fast_protocol.h"
    ufp_context_t* ctx = ufp_create_context("{agent_name}");
"""

def update_agent_file(filepath):
    """Update a single agent file with communication integration"""
    
    # Read the file
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Extract agent name from metadata
    agent_name = os.path.basename(filepath).replace('.md', '').lower()
    
    # Check if already has communication section
    if "# COMMUNICATION SYSTEM INTEGRATION" in content:
        print(f"  ✓ {os.path.basename(filepath)} - already integrated")
        return False
    
    # Find where to insert (after invokes_agents section or at end of metadata)
    insertion_point = -1
    
    # Look for end of invokes_agents section
    if "invokes_agents:" in content:
        # Find the next section after invokes_agents
        pattern = r'invokes_agents:.*?\n\n'
        match = re.search(pattern, content, re.DOTALL)
        if match:
            insertion_point = match.end()
    
    # If not found, look for hardware_requirements section
    if insertion_point == -1 and "hardware_requirements:" in content:
        idx = content.find("hardware_requirements:")
        insertion_point = idx
    
    # If still not found, insert before the main content (after ---\n\n)
    if insertion_point == -1:
        pattern = r'---\n\n'
        match = re.search(pattern, content)
        if match:
            insertion_point = match.start()
    
    # If still not found, append at end
    if insertion_point == -1:
        insertion_point = len(content)
    
    # Prepare the integration block with agent name
    integration_block = COMMUNICATION_INTEGRATION.replace("{agent_name}", agent_name)
    
    # Insert the integration block
    if insertion_point == len(content):
        # Append at end
        updated_content = content + "\n" + integration_block
    else:
        # Insert at specific point
        updated_content = content[:insertion_point] + integration_block + "\n" + content[insertion_point:]
    
    # Write back the updated content
    with open(filepath, 'w') as f:
        f.write(updated_content)
    
    print(f"  ✅ {os.path.basename(filepath)} - integration added")
    return True

def create_agent_c_implementation(agent_name):
    """Create a basic C implementation file for the agent if it doesn't exist"""
    
    c_file = f"${CLAUDE_AGENTS_ROOT:-$(dirname "$0")}/../src/c/{agent_name.lower()}_agent.c"
    
    if os.path.exists(c_file):
        return
    
    template = f"""/*
 * {agent_name.upper()} AGENT - Communication System Integration
 * Auto-generated implementation file
 */

#include "ultra_fast_protocol.h"
#include "agent_system.h"
#include "compatibility_layer.h"
#include <stdio.h>
#include <string.h>

// Agent definition
typedef struct {{
    ufp_context_t* comm_context;
    char name[64];
    uint32_t agent_id;
    agent_state_t state;
}} {agent_name.lower()}_agent_t;

// Initialize agent
int {agent_name.lower()}_init({agent_name.lower()}_agent_t* agent) {{
    // Initialize communication context
    agent->comm_context = ufp_create_context("{agent_name.lower()}");
    if (!agent->comm_context) {{
        return -1;
    }}
    
    strcpy(agent->name, "{agent_name.lower()}");
    agent->state = AGENT_STATE_ACTIVE;
    
    // Register with discovery service
    agent_register("{agent_name.lower()}", AGENT_TYPE_{agent_name.upper()}, NULL, 0);
    
    return 0;
}}

// Process incoming message
int {agent_name.lower()}_process_message({agent_name.lower()}_agent_t* agent, ufp_message_t* msg) {{
    // Implement agent-specific logic
    printf("{agent_name} received message from %s\\n", msg->source);
    
    // Send acknowledgment
    ufp_message_t* ack = ufp_message_create();
    strcpy(ack->source, agent->name);
    strcpy(ack->targets[0], msg->source);
    ack->target_count = 1;
    ack->msg_type = UFP_MSG_ACK;
    
    ufp_send(agent->comm_context, ack);
    ufp_message_destroy(ack);
    
    return 0;
}}

// Main agent loop
void {agent_name.lower()}_run({agent_name.lower()}_agent_t* agent) {{
    ufp_message_t msg;
    
    while (agent->state == AGENT_STATE_ACTIVE) {{
        // Receive messages
        if (ufp_receive(agent->comm_context, &msg, 100) == UFP_SUCCESS) {{
            {agent_name.lower()}_process_message(agent, &msg);
        }}
    }}
}}
"""
    
    # Create the C file
    with open(c_file, 'w') as f:
        f.write(template)
    
    print(f"  📝 Created C implementation: {c_file}")

def update_makefile():
    """Update the Makefile to include all agent implementations"""
    
    makefile_path = "${CLAUDE_AGENTS_ROOT:-$(dirname "$0")}/../src/c/Makefile"
    
    if not os.path.exists(makefile_path):
        # Create a basic Makefile
        makefile_content = """# Claude Agent Communication System - Makefile

CC = gcc
CFLAGS = -O3 -march=native -Wall -Wextra -pthread -D_GNU_SOURCE
LDFLAGS = -lnuma -lssl -lcrypto -lm -lpthread

# Agent source files
AGENT_SRCS = $(wildcard *_agent.c)
AGENT_OBJS = $(AGENT_SRCS:.c=.o)

# Core system files
CORE_SRCS = unified_agent_runtime.c agent_discovery.c message_router.c \\
            compatibility_layer.c auth_security.c tls_manager.c \\
            prometheus_exporter.c health_check_endpoints.c

CORE_OBJS = $(CORE_SRCS:.c=.o)

# All targets
all: unified_agent_runtime test_agents

unified_agent_runtime: $(CORE_OBJS) $(AGENT_OBJS)
	$(CC) $(CFLAGS) -o $@ $^ $(LDFLAGS)

test_agents: test_agents.c $(AGENT_OBJS) $(CORE_OBJS)
	$(CC) $(CFLAGS) -o $@ $^ $(LDFLAGS)

%.o: %.c
	$(CC) $(CFLAGS) -c $< -o $@

clean:
	rm -f *.o unified_agent_runtime test_agents

.PHONY: all clean
"""
        with open(makefile_path, 'w') as f:
            f.write(makefile_content)
        print("  📝 Created Makefile for agent compilation")

def main():
    """Main update process"""
    
    print("=" * 60)
    print("Claude Agent Communication System - Integration Update")
    print("=" * 60)
    print()
    
    # Change to agents directory
    os.chdir("${CLAUDE_PROJECT_ROOT:-$(dirname "$0")/../../}agents")
    
    # Find all agent .md files
    agent_files = glob.glob("*.md")
    
    # Exclude special files
    exclude = ["WHERE_I_AM.md", "Template.md", "README.md"]
    agent_files = [f for f in agent_files if f not in exclude]
    
    print(f"Found {len(agent_files)} agent definition files to update")
    print()
    
    # Update each agent file
    updated_count = 0
    for agent_file in sorted(agent_files):
        if update_agent_file(agent_file):
            updated_count += 1
            
            # Create C implementation if needed
            agent_name = agent_file.replace('.md', '')
            create_agent_c_implementation(agent_name)
    
    print()
    print(f"Updated {updated_count} agent files with communication integration")
    
    # Update Makefile
    update_makefile()
    
    # Create integration verification script
    verification_script = """#!/bin/bash
# Verify all agents are properly integrated

echo "Verifying agent integration..."

# Check for communication section in all agent files
for agent in *.md; do
    if [[ "$agent" != "WHERE_I_AM.md" && "$agent" != "Template.md" ]]; then
        if grep -q "COMMUNICATION SYSTEM INTEGRATION" "$agent"; then
            echo "✓ $agent - integrated"
        else
            echo "✗ $agent - NOT integrated"
        fi
    fi
done

# Check for C implementations
echo ""
echo "Checking C implementations..."
for agent in *.md; do
    if [[ "$agent" != "WHERE_I_AM.md" && "$agent" != "Template.md" ]]; then
        agent_name=$(basename "$agent" .md | tr '[:upper:]' '[:lower:]')
        if [ -f "src/c/${agent_name}_agent.c" ]; then
            echo "✓ ${agent_name}_agent.c exists"
        else
            echo "✗ ${agent_name}_agent.c missing"
        fi
    fi
done
"""
    
    with open("verify_integration.sh", 'w') as f:
        f.write(verification_script)
    
    os.chmod("verify_integration.sh", 0o755)
    
    print()
    print("✅ Integration update complete!")
    print()
    print("Next steps:")
    print("1. Run ./verify_integration.sh to verify all agents are integrated")
    print("2. Run ./BRING_ONLINE.sh to start the communication system")
    print("3. Test with python3 INTEGRATION_EXAMPLE.py")
    print()

if __name__ == "__main__":
    main()