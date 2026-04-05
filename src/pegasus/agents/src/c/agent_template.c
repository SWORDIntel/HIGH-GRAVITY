/*
 * AGENT TEMPLATE for Binary Communication System Integration
 *
 * Template for creating new C agents with binary protocol integration
 * Based on pattern analysis of 30 existing agent implementations
 *
 * Author: Agent Communication System
 * Version: 1.0 Template
 */

#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <stdbool.h>
#include <stdatomic.h>
#include <pthread.h>
#include <sys/time.h>
#include <sys/mman.h>
#include <unistd.h>
#include <errno.h>
#include "compatibility_layer.h"
#include <sched.h>
#include <signal.h>
#include <math.h>

// Include binary protocol headers
#include "agent_protocol.h"

// ============================================================================
// AGENT CONFIGURATION - CUSTOMIZE THIS SECTION
// ============================================================================

// REQUIRED: Update these for each new agent
#define AGENT_ID 999               // Unique agent ID (update per agent)
#define AGENT_NAME "TEMPLATE"      // Agent name in CAPS
#define AGENT_VERSION "8.0.0"      // Standard version

// Agent-specific constants
#define MAX_OPERATIONS 1024        // Customize per agent needs
#define MAX_RESOURCES 512          // Customize per agent needs
#define OPERATION_TIMEOUT_MS 5000  // 5 second timeout

// Performance targets (customize per agent)
#define TARGET_RESPONSE_TIME_MS 500    // <500ms response time
#define TARGET_SUCCESS_RATE 95         // >95% success rate
#define TARGET_THROUGHPUT 1000         // 1000 ops/sec

// ============================================================================
// CORE DATA STRUCTURES - CUSTOMIZE FOR AGENT FUNCTIONALITY
// ============================================================================

// Agent state structure
typedef struct {
    atomic_bool initialized;
    atomic_bool active;
    atomic_uint64_t operation_count;
    atomic_uint64_t success_count;
    atomic_uint64_t error_count;

    // Agent-specific state variables (customize)
    uint32_t resource_count;
    uint32_t active_operations;

    // Performance metrics
    struct {
        uint64_t total_operations;
        uint64_t total_response_time_ns;
        uint64_t min_response_time_ns;
        uint64_t max_response_time_ns;
        double avg_response_time_ms;
        double success_rate;
        double current_throughput;
    } metrics;

    // Threading
    pthread_mutex_t state_mutex;
    pthread_cond_t state_cond;

} agent_state_t;

// Global agent state
static agent_state_t g_agent_state = {
    .initialized = ATOMIC_VAR_INIT(false),
    .active = ATOMIC_VAR_INIT(false),
    .operation_count = ATOMIC_VAR_INIT(0),
    .success_count = ATOMIC_VAR_INIT(0),
    .error_count = ATOMIC_VAR_INIT(0),
    .state_mutex = PTHREAD_MUTEX_INITIALIZER,
    .state_cond = PTHREAD_COND_INITIALIZER
};

// Operation result structure (customize per agent)
typedef struct {
    int result_code;
    uint64_t execution_time_ns;
    char description[256];
    void* data;
    size_t data_size;
} operation_result_t;

// ============================================================================
// CORE UTILITY FUNCTIONS - STANDARD ACROSS ALL AGENTS
// ============================================================================

// High-precision timing
static uint64_t get_timestamp_ns(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (uint64_t)ts.tv_sec * 1000000000ULL + (uint64_t)ts.tv_nsec;
}

// Update performance metrics
static void update_metrics(uint64_t response_time_ns, bool success) {
    pthread_mutex_lock(&g_agent_state.state_mutex);

    g_agent_state.metrics.total_operations++;
    g_agent_state.metrics.total_response_time_ns += response_time_ns;

    if (success) {
        atomic_fetch_add(&g_agent_state.success_count, 1);
    } else {
        atomic_fetch_add(&g_agent_state.error_count, 1);
    }

    // Update min/max response times
    if (g_agent_state.metrics.min_response_time_ns == 0 ||
        response_time_ns < g_agent_state.metrics.min_response_time_ns) {
        g_agent_state.metrics.min_response_time_ns = response_time_ns;
    }

    if (response_time_ns > g_agent_state.metrics.max_response_time_ns) {
        g_agent_state.metrics.max_response_time_ns = response_time_ns;
    }

    // Calculate averages
    if (g_agent_state.metrics.total_operations > 0) {
        g_agent_state.metrics.avg_response_time_ms =
            (double)g_agent_state.metrics.total_response_time_ns /
            (double)g_agent_state.metrics.total_operations / 1000000.0;

        g_agent_state.metrics.success_rate =
            (double)atomic_load(&g_agent_state.success_count) * 100.0 /
            (double)g_agent_state.metrics.total_operations;
    }

    pthread_mutex_unlock(&g_agent_state.state_mutex);
}

// ============================================================================
// AGENT-SPECIFIC OPERATIONS - CUSTOMIZE THESE FUNCTIONS
// ============================================================================

// Primary agent operation (customize this)
static operation_result_t perform_agent_operation(const char* operation_type,
                                                  const void* input_data,
                                                  size_t input_size) {
    operation_result_t result = {0};
    uint64_t start_time = get_timestamp_ns();

    printf("[%s] Performing operation: %s\n", AGENT_NAME, operation_type);

    // CUSTOMIZE: Add your agent-specific logic here
    if (strcmp(operation_type, "analyze") == 0) {
        // Example analysis operation
        result.result_code = 0;
        strcpy(result.description, "Analysis completed successfully");

        // Simulate work
        usleep(10000); // 10ms simulated work

    } else if (strcmp(operation_type, "optimize") == 0) {
        // Example optimization operation
        result.result_code = 0;
        strcpy(result.description, "Optimization completed successfully");

        // Simulate work
        usleep(50000); // 50ms simulated work

    } else {
        // Unknown operation
        result.result_code = -1;
        snprintf(result.description, sizeof(result.description),
                "Unknown operation: %s", operation_type);
    }

    result.execution_time_ns = get_timestamp_ns() - start_time;

    // Update metrics
    update_metrics(result.execution_time_ns, result.result_code == 0);

    // Increment operation counter
    atomic_fetch_add(&g_agent_state.operation_count, 1);

    return result;
}

// Secondary agent operations (add more as needed)
static int validate_input(const void* input_data, size_t input_size) {
    if (!input_data || input_size == 0) {
        return -1;
    }

    // CUSTOMIZE: Add agent-specific validation logic

    return 0;
}

static int cleanup_resources(void) {
    // CUSTOMIZE: Add agent-specific cleanup logic
    printf("[%s] Cleaning up resources\n", AGENT_NAME);
    return 0;
}

// ============================================================================
// BINARY PROTOCOL INTEGRATION - STANDARD INTERFACE
// ============================================================================

// Handle incoming binary protocol messages
int handle_agent_message(enhanced_msg_header_t* header, uint8_t* payload) {
    if (!header || !payload) {
        return -1;
    }

    printf("[%s] Received message (type: 0x%08X, size: %u)\n",
           AGENT_NAME, header->msg_type, header->payload_len);

    // Parse operation type from payload
    if (header->payload_len < 4) {
        return -1; // Invalid payload
    }

    uint32_t operation_code = *(uint32_t*)payload;
    const char* operation_data = (char*)(payload + 4);
    size_t data_size = header->payload_len - 4;

    // Map operation codes to operation types (customize per agent)
    const char* operation_type = "unknown";
    switch (operation_code) {
        case 0x1001: operation_type = "analyze"; break;
        case 0x1002: operation_type = "optimize"; break;
        case 0x1003: operation_type = "validate"; break;
        // CUSTOMIZE: Add more operation codes
        default: break;
    }

    // Perform the operation
    operation_result_t result = perform_agent_operation(operation_type,
                                                       operation_data,
                                                       data_size);

    // Send response (if needed)
    // This would be implemented based on the binary protocol response mechanism

    return result.result_code;
}

// Agent discovery and capability registration
int register_agent_capabilities(void) {
    printf("[%s] Registering agent capabilities\n", AGENT_NAME);

    // CUSTOMIZE: Register agent-specific capabilities
    // This would use the binary protocol's discovery mechanism

    return 0;
}

// ============================================================================
// AGENT LIFECYCLE MANAGEMENT - STANDARD INTERFACE
// ============================================================================

// Initialize the agent
int agent_init(void) {
    if (atomic_load(&g_agent_state.initialized)) {
        return 0; // Already initialized
    }

    printf("[%s] Initializing agent (version %s)\n", AGENT_NAME, AGENT_VERSION);

    // Initialize state
    memset(&g_agent_state.metrics, 0, sizeof(g_agent_state.metrics));
    g_agent_state.resource_count = 0;
    g_agent_state.active_operations = 0;

    // CUSTOMIZE: Add agent-specific initialization

    // Register with binary protocol system
    if (register_agent_capabilities() != 0) {
        printf("[%s] Failed to register capabilities\n", AGENT_NAME);
        return -1;
    }

    atomic_store(&g_agent_state.initialized, true);
    atomic_store(&g_agent_state.active, true);

    printf("[%s] Agent initialized successfully\n", AGENT_NAME);
    return 0;
}

// Start the agent
int agent_start(void) {
    if (!atomic_load(&g_agent_state.initialized)) {
        return -1;
    }

    printf("[%s] Starting agent operations\n", AGENT_NAME);

    // CUSTOMIZE: Add agent-specific startup logic

    return 0;
}

// Stop the agent
int agent_stop(void) {
    printf("[%s] Stopping agent operations\n", AGENT_NAME);

    atomic_store(&g_agent_state.active, false);

    // CUSTOMIZE: Add agent-specific shutdown logic
    cleanup_resources();

    return 0;
}

// Get agent status and metrics
int agent_get_status(char* status_buffer, size_t buffer_size) {
    if (!status_buffer || buffer_size == 0) {
        return -1;
    }

    pthread_mutex_lock(&g_agent_state.state_mutex);

    int written = snprintf(status_buffer, buffer_size,
        "Agent: %s v%s\n"
        "Status: %s\n"
        "Operations: %lu (Success: %lu, Errors: %lu)\n"
        "Success Rate: %.2f%%\n"
        "Avg Response Time: %.2f ms\n"
        "Min/Max Response: %.2f/%.2f ms\n"
        "Active Resources: %u\n",
        AGENT_NAME, AGENT_VERSION,
        atomic_load(&g_agent_state.active) ? "ACTIVE" : "INACTIVE",
        g_agent_state.metrics.total_operations,
        atomic_load(&g_agent_state.success_count),
        atomic_load(&g_agent_state.error_count),
        g_agent_state.metrics.success_rate,
        g_agent_state.metrics.avg_response_time_ms,
        g_agent_state.metrics.min_response_time_ns / 1000000.0,
        g_agent_state.metrics.max_response_time_ns / 1000000.0,
        g_agent_state.resource_count
    );

    pthread_mutex_unlock(&g_agent_state.state_mutex);

    return written;
}

// ============================================================================
// MAIN FUNCTION - TESTING AND DEMONSTRATION
// ============================================================================

#ifdef AGENT_STANDALONE_TEST
int main(void) {
    printf("=== %s AGENT STANDALONE TEST ===\n", AGENT_NAME);

    // Initialize agent
    if (agent_init() != 0) {
        printf("Failed to initialize agent\n");
        return 1;
    }

    // Start agent
    if (agent_start() != 0) {
        printf("Failed to start agent\n");
        return 1;
    }

    // Test operations
    printf("\nTesting agent operations:\n");

    const char* test_data = "test input data";
    operation_result_t result;

    result = perform_agent_operation("analyze", test_data, strlen(test_data));
    printf("Analysis result: %d (%s)\n", result.result_code, result.description);

    result = perform_agent_operation("optimize", test_data, strlen(test_data));
    printf("Optimization result: %d (%s)\n", result.result_code, result.description);

    // Get status
    char status[1024];
    agent_get_status(status, sizeof(status));
    printf("\nAgent Status:\n%s\n", status);

    // Stop agent
    agent_stop();

    printf("=== AGENT TEST COMPLETE ===\n");
    return 0;
}
#endif

/*
 * TEMPLATE USAGE INSTRUCTIONS:
 *
 * 1. Copy this file to: {agent_name}_agent.c (e.g., hardware-intel_agent.c)
 *
 * 2. Update AGENT CONFIGURATION section:
 *    - Change AGENT_ID to unique value
 *    - Change AGENT_NAME to your agent name
 *    - Update constants for your agent's needs
 *
 * 3. Customize CORE DATA STRUCTURES:
 *    - Add agent-specific state variables
 *    - Modify operation_result_t structure
 *
 * 4. Implement AGENT-SPECIFIC OPERATIONS:
 *    - Replace perform_agent_operation() with your logic
 *    - Add validation and cleanup functions
 *
 * 5. Update BINARY PROTOCOL INTEGRATION:
 *    - Add operation codes for your agent
 *    - Implement capability registration
 *
 * 6. Test with: gcc -DAGENT_STANDALONE_TEST -o test_agent {agent_name}_agent.c
 *
 * 7. Integrate with binary system by including in build
 */