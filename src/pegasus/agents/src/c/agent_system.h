/*
 * AGENT SYSTEM INTEGRATION HEADER
 * 
 * Unified interface for the complete Claude Agent Communication System
 * - Service discovery and registration
 * - Message routing and communication
 * - Agent orchestration and coordination
 * - Security and compliance management
 * - Performance monitoring and optimization
 * 
 * This header provides the complete API for integrating all agent components
 * 
 * Author: Agent Communication System
 * Version: 1.0 Production
 */

#ifndef AGENT_SYSTEM_H
#define AGENT_SYSTEM_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#include <pthread.h>

#ifdef __cplusplus
extern "C" {
#endif

// ============================================================================
// SYSTEM CONSTANTS AND CONFIGURATION
// ============================================================================

#define AGENT_SYSTEM_VERSION_MAJOR 1
#define AGENT_SYSTEM_VERSION_MINOR 0
#define AGENT_SYSTEM_VERSION_PATCH 0

// System limits
#define MAX_AGENTS 512
#define MAX_AGENT_NAME 64
#define MAX_TOPICS 1024
#define MAX_WORKFLOWS 256
#define MAX_PROJECTS 128
#define MAX_VULNERABILITIES 4096
#define MAX_MESSAGE_SIZE (16 * 1024 * 1024)

// Performance constants
#define CACHE_LINE_SIZE 64
#define PAGE_SIZE 4096

// ============================================================================
// AGENT TYPES AND CAPABILITIES
// ============================================================================

typedef enum {
    AGENT_TYPE_DIRECTOR = 1,
    AGENT_TYPE_PROJECT_ORCHESTRATOR = 2,
    AGENT_TYPE_SECURITY = 3,
    AGENT_TYPE_SECURITY_CHAOS = 4,
    AGENT_TYPE_TESTBED = 5,
    AGENT_TYPE_TUI = 6,
    AGENT_TYPE_WEB = 7,
    AGENT_TYPE_C_INTERNAL = 8,
    AGENT_TYPE_PYTHON_INTERNAL = 9,
    AGENT_TYPE_MONITOR = 10,
    AGENT_TYPE_OPTIMIZER = 11,
    AGENT_TYPE_PATCHER = 12,
    AGENT_TYPE_PYGUI = 13,
    AGENT_TYPE_RED_TEAM_ORCHESTRATOR = 14,
    AGENT_TYPE_RESEARCHER = 15,
    AGENT_TYPE_DOCGEN = 16,
    AGENT_TYPE_INFRASTRUCTURE = 17,
    AGENT_TYPE_INTEGRATION = 18,
    AGENT_TYPE_LINTER = 19,
    AGENT_TYPE_ML_OPS = 20,
    AGENT_TYPE_MOBILE = 21,
    AGENT_TYPE_CONSTRUCTOR = 22,
    AGENT_TYPE_DATA_SCIENCE = 23,
    AGENT_TYPE_DATABASE = 24,
    AGENT_TYPE_DEBUGGER = 25,
    AGENT_TYPE_DEPLOYER = 26,
    AGENT_TYPE_API_DESIGNER = 27,
    AGENT_TYPE_ARCHITECT = 28
} agent_type_t;

typedef enum {
    AGENT_STATE_INITIALIZING = 0,
    AGENT_STATE_ACTIVE = 1,
    AGENT_STATE_DEGRADED = 2,
    AGENT_STATE_UNAVAILABLE = 3,
    AGENT_STATE_FAILED = 4,
    AGENT_STATE_SHUTTING_DOWN = 5
} agent_state_t;

// ============================================================================
// MESSAGE SYSTEM TYPES
// ============================================================================

typedef enum {
    MSG_TYPE_REQUEST = 1,
    MSG_TYPE_RESPONSE = 2,
    MSG_TYPE_PUBLISH = 3,
    MSG_TYPE_SUBSCRIBE = 4,
    MSG_TYPE_WORK_ITEM = 5,
    MSG_TYPE_HEARTBEAT = 6,
    MSG_TYPE_EMERGENCY = 7
} message_type_t;

typedef enum {
    PRIORITY_EMERGENCY = 0,
    PRIORITY_CRITICAL = 1,
    PRIORITY_HIGH = 2,
    PRIORITY_NORMAL = 3,
    PRIORITY_LOW = 4,
    PRIORITY_BACKGROUND = 5
} message_priority_t;

typedef enum {
    ROUTE_ROUND_ROBIN = 0,
    ROUTE_LEAST_LOADED = 1,
    ROUTE_HIGHEST_PRIORITY = 2,
    ROUTE_RANDOM = 3,
    ROUTE_CONSISTENT_HASH = 4
} routing_strategy_t;

// ============================================================================
// SECURITY SYSTEM TYPES
// ============================================================================

typedef enum {
    VULN_SEVERITY_CRITICAL = 0,
    VULN_SEVERITY_HIGH = 1,
    VULN_SEVERITY_MEDIUM = 2,
    VULN_SEVERITY_LOW = 3,
    VULN_SEVERITY_INFO = 4
} vulnerability_severity_t;

typedef enum {
    THREAT_LEVEL_CRITICAL = 0,
    THREAT_LEVEL_HIGH = 1,
    THREAT_LEVEL_MEDIUM = 2,
    THREAT_LEVEL_LOW = 3,
    THREAT_LEVEL_INFO = 4
} threat_level_t;

typedef enum {
    SCAN_TYPE_STATIC_CODE = 1,
    SCAN_TYPE_DYNAMIC_ANALYSIS = 2,
    SCAN_TYPE_DEPENDENCY_CHECK = 3,
    SCAN_TYPE_CONTAINER_SCAN = 4,
    SCAN_TYPE_NETWORK_SCAN = 5,
    SCAN_TYPE_WEB_APPLICATION = 6,
    SCAN_TYPE_INFRASTRUCTURE = 7,
    SCAN_TYPE_COMPLIANCE = 8,
    SCAN_TYPE_PENETRATION_TEST = 9
} security_scan_type_t;

// ============================================================================
// WORKFLOW AND PROJECT TYPES
// ============================================================================

typedef enum {
    STRATEGY_SEQUENTIAL = 0,
    STRATEGY_PARALLEL_UNLIMITED = 1,
    STRATEGY_PARALLEL_LIMITED = 2,
    STRATEGY_PIPELINE = 3,
    STRATEGY_ADAPTIVE = 4
} execution_strategy_t;

typedef enum {
    TASK_STATE_PENDING = 0,
    TASK_STATE_QUEUED = 1,
    TASK_STATE_ASSIGNED = 2,
    TASK_STATE_RUNNING = 3,
    TASK_STATE_COMPLETED = 4,
    TASK_STATE_FAILED = 5,
    TASK_STATE_CANCELLED = 6
} task_state_t;

typedef enum {
    WORKFLOW_STATE_CREATED = 0,
    WORKFLOW_STATE_PLANNED = 1,
    WORKFLOW_STATE_RUNNING = 2,
    WORKFLOW_STATE_PAUSED = 3,
    WORKFLOW_STATE_COMPLETED = 4,
    WORKFLOW_STATE_FAILED = 5,
    WORKFLOW_STATE_CANCELLED = 6
} workflow_state_t;

typedef enum {
    TASK_TYPE_ANALYSIS = 1,
    TASK_TYPE_BUILD = 2,
    TASK_TYPE_TEST = 3,
    TASK_TYPE_DEPLOY = 4,
    TASK_TYPE_SECURITY = 5,
    TASK_TYPE_DOCUMENTATION = 6,
    TASK_TYPE_INTEGRATION = 7,
    TASK_TYPE_VALIDATION = 8
} task_type_t;

// ============================================================================
// DATA STRUCTURES
// ============================================================================

// Agent capability descriptor
typedef struct {
    char name[64];
    uint32_t version;
    float performance_rating;  // 0.0 - 1.0
    uint32_t max_concurrent_tasks;
} agent_capability_t;

// Agent endpoint information  
typedef struct {
    char protocol[16];     // "ipc", "tcp", "udp", "shared_mem"
    char address[64];      // "/tmp/agent.sock", "127.0.0.1:8080", etc.
    uint16_t port;
    uint32_t flags;
} agent_endpoint_t;

// Agent health metrics
typedef struct {
    uint64_t requests_handled;
    uint64_t errors_count;
    uint64_t last_heartbeat_ns;
    uint32_t response_time_avg_us;
    uint32_t cpu_usage_percent;
    uint32_t memory_usage_mb;
    uint32_t active_connections;
    uint32_t queue_depth;
    float load_factor;
} agent_health_t;

// Message structure
typedef struct {
    uint32_t message_id;
    message_type_t msg_type;
    message_priority_t priority;
    uint32_t source_agent_id;
    uint32_t target_agent_id;
    uint32_t correlation_id;
    uint64_t timestamp_ns;
    uint32_t ttl_ms;
    char topic[128];
    void* payload;
    size_t payload_size;
    uint32_t flags;
} agent_message_t;

// Statistics structures
typedef struct {
    uint64_t messages_sent;
    uint64_t messages_received;
    uint64_t bytes_sent;
    uint64_t bytes_received;
    uint64_t errors;
    double avg_latency_ns;
    double throughput_msgs_per_sec;
} agent_stats_t;

typedef struct {
    uint64_t vulnerabilities_discovered;
    uint64_t vulnerabilities_fixed;
    uint64_t threats_detected;
    uint64_t threats_mitigated;
    uint64_t scans_performed;
    uint64_t incidents_created;
    uint32_t critical_vulnerabilities;
    uint32_t active_threats;
    float security_posture_score;
} security_stats_t;

typedef struct {
    uint64_t workflows_created;
    uint64_t workflows_completed;
    uint64_t workflows_failed;
    uint64_t tasks_executed;
    uint32_t active_workflows;
    double avg_workflow_completion_time_ms;
    double resource_utilization_percentage;
} orchestration_stats_t;

// System-wide statistics
typedef struct {
    uint32_t active_agents;
    uint32_t total_agents_registered;
    agent_stats_t messaging_stats;
    security_stats_t security_stats;
    orchestration_stats_t orchestration_stats;
    double system_efficiency_score;
    double overall_health_score;
} system_stats_t;

// ============================================================================
// ERROR CODES
// ============================================================================

typedef enum {
    AGENT_SUCCESS = 0,
    AGENT_ERROR_INVALID_PARAM = -1,
    AGENT_ERROR_OUT_OF_MEMORY = -2,
    AGENT_ERROR_NOT_FOUND = -3,
    AGENT_ERROR_ALREADY_EXISTS = -4,
    AGENT_ERROR_PERMISSION_DENIED = -5,
    AGENT_ERROR_TIMEOUT = -6,
    AGENT_ERROR_NETWORK = -7,
    AGENT_ERROR_PROTOCOL = -8,
    AGENT_ERROR_CAPACITY_EXCEEDED = -9,
    AGENT_ERROR_NOT_INITIALIZED = -10,
    AGENT_ERROR_INTERNAL = -11
} agent_error_t;

// ============================================================================
// CORE SYSTEM FUNCTIONS
// ============================================================================

/**
 * Initialize the complete agent system
 * @return AGENT_SUCCESS on success, error code otherwise
 */
agent_error_t agent_system_init(void);

/**
 * Cleanup the complete agent system
 */
void agent_system_cleanup(void);

/**
 * Get system version string
 * @return Version string
 */
const char* agent_system_version(void);

/**
 * Get comprehensive system statistics
 * @param stats Output statistics structure
 * @return AGENT_SUCCESS on success, error code otherwise
 */
agent_error_t agent_system_get_stats(system_stats_t* stats);

/**
 * Print comprehensive system status and statistics
 */
void agent_system_print_status(void);

// ============================================================================
// SERVICE DISCOVERY FUNCTIONS
// ============================================================================

/**
 * Register an agent with the discovery service
 * @param name Agent name
 * @param type Agent type
 * @param instance_id Instance identifier
 * @param capabilities Array of agent capabilities
 * @param capability_count Number of capabilities
 * @param endpoints Array of network endpoints
 * @param endpoint_count Number of endpoints
 * @return Agent ID on success, 0 on error
 */
uint32_t agent_register(const char* name, agent_type_t type, uint32_t instance_id,
                       const agent_capability_t* capabilities, uint32_t capability_count,
                       const agent_endpoint_t* endpoints, uint32_t endpoint_count);

/**
 * Discover agent by name
 * @param name Agent name to find
 * @return Agent handle or NULL if not found
 */
void* agent_discover_by_name(const char* name);

/**
 * Discover agent by type
 * @param type Agent type to find
 * @return Agent handle or NULL if not found
 */
void* agent_discover_by_type(agent_type_t type);

/**
 * Discover agents by capability
 * @param capability_name Capability to search for
 * @param results Array to store found agents
 * @param max_results Maximum results to return
 * @return Number of agents found
 */
int agent_discover_by_capability(const char* capability_name, void** results, uint32_t max_results);

/**
 * Update agent health metrics
 * @param agent_id Agent ID
 * @param health Health metrics
 */
void agent_update_health(uint32_t agent_id, const agent_health_t* health);

/**
 * Check if agent is healthy
 * @param agent_id Agent ID
 * @return true if healthy, false otherwise
 */
bool agent_is_healthy(uint32_t agent_id);

// ============================================================================
// MESSAGE ROUTING FUNCTIONS
// ============================================================================

/**
 * Create a topic for publish/subscribe messaging
 * @param topic_name Name of the topic
 * @param strategy Routing strategy
 * @param persistent Whether messages should be persistent
 * @return AGENT_SUCCESS on success, error code otherwise
 */
agent_error_t message_create_topic(const char* topic_name, routing_strategy_t strategy, bool persistent);

/**
 * Subscribe to a topic
 * @param topic_name Topic name
 * @param agent_id Subscribing agent ID
 * @param agent_name Subscribing agent name
 * @return AGENT_SUCCESS on success, error code otherwise
 */
agent_error_t message_subscribe(const char* topic_name, uint32_t agent_id, const char* agent_name);

/**
 * Publish message to topic
 * @param topic_name Topic name
 * @param source_agent_id Source agent ID
 * @param payload Message payload
 * @param payload_size Payload size
 * @param priority Message priority
 * @return Number of subscribers message was delivered to, negative on error
 */
int message_publish(const char* topic_name, uint32_t source_agent_id,
                   const void* payload, size_t payload_size, message_priority_t priority);

/**
 * Send request message
 * @param target_agent_id Target agent ID
 * @param payload Request payload
 * @param payload_size Payload size
 * @param timeout_ms Request timeout
 * @param correlation_id Output correlation ID for response matching
 * @return AGENT_SUCCESS on success, error code otherwise
 */
agent_error_t message_send_request(uint32_t target_agent_id, const void* payload, size_t payload_size,
                                  uint32_t timeout_ms, uint32_t* correlation_id);

/**
 * Send response message
 * @param correlation_id Correlation ID from original request
 * @param payload Response payload
 * @param payload_size Payload size
 * @return AGENT_SUCCESS on success, error code otherwise
 */
agent_error_t message_send_response(uint32_t correlation_id, const void* payload, size_t payload_size);

/**
 * Create work queue for task distribution
 * @param queue_name Queue name
 * @param strategy Distribution strategy
 * @return AGENT_SUCCESS on success, error code otherwise
 */
agent_error_t message_create_work_queue(const char* queue_name, routing_strategy_t strategy);

/**
 * Register worker for work queue
 * @param queue_name Queue name
 * @param worker_agent_id Worker agent ID
 * @return AGENT_SUCCESS on success, error code otherwise
 */
agent_error_t message_register_worker(const char* queue_name, uint32_t worker_agent_id);

/**
 * Distribute work item to queue
 * @param queue_name Queue name
 * @param work_item Work item payload
 * @param item_size Work item size
 * @return Selected worker agent ID, 0 on error
 */
uint32_t message_distribute_work(const char* queue_name, const void* work_item, size_t item_size);

// ============================================================================
// DIRECTOR FUNCTIONS
// ============================================================================

/**
 * Create execution plan
 * @param name Plan name
 * @param description Plan description
 * @param priority Plan priority
 * @return Plan ID on success, 0 on error
 */
uint32_t director_create_plan(const char* name, const char* description, message_priority_t priority);

/**
 * Add execution step to plan
 * @param plan_id Plan ID
 * @param step_name Step name
 * @param description Step description
 * @param required_agent_type Required agent type
 * @param capability Required capability
 * @param action Action to execute
 * @param parameters Action parameters
 * @param timeout_ms Step timeout
 * @param priority Step priority
 * @return Step ID on success, negative on error
 */
int director_add_step(uint32_t plan_id, const char* step_name, const char* description,
                     agent_type_t required_agent_type, const char* capability,
                     const char* action, const char* parameters,
                     uint32_t timeout_ms, message_priority_t priority);

/**
 * Add step dependency
 * @param plan_id Plan ID
 * @param step_id Step ID
 * @param dependency_step_id Dependency step ID
 * @return AGENT_SUCCESS on success, error code otherwise
 */
agent_error_t director_add_dependency(uint32_t plan_id, uint32_t step_id, uint32_t dependency_step_id);

/**
 * Start plan execution
 * @param plan_id Plan ID
 * @return AGENT_SUCCESS on success, error code otherwise
 */
agent_error_t director_start_plan(uint32_t plan_id);

/**
 * Get plan execution status
 * @param plan_id Plan ID
 * @return Current plan state
 */
workflow_state_t director_get_plan_state(uint32_t plan_id);

// ============================================================================
// PROJECT ORCHESTRATOR FUNCTIONS
// ============================================================================

/**
 * Create project
 * @param name Project name
 * @param description Project description
 * @param max_concurrent_workflows Maximum concurrent workflows
 * @return Project ID on success, 0 on error
 */
uint32_t orchestrator_create_project(const char* name, const char* description, uint32_t max_concurrent_workflows);

/**
 * Activate project
 * @param project_id Project ID
 * @return AGENT_SUCCESS on success, error code otherwise
 */
agent_error_t orchestrator_activate_project(uint32_t project_id);

/**
 * Create workflow
 * @param project_id Project ID
 * @param name Workflow name
 * @param description Workflow description
 * @param strategy Execution strategy
 * @param max_parallel_tasks Maximum parallel tasks
 * @return Workflow ID on success, 0 on error
 */
uint32_t orchestrator_create_workflow(uint32_t project_id, const char* name, const char* description,
                                     execution_strategy_t strategy, uint32_t max_parallel_tasks);

/**
 * Add task to workflow
 * @param workflow_id Workflow ID
 * @param task_name Task name
 * @param description Task description
 * @param type Task type
 * @param priority Task priority
 * @param required_agent_type Required agent type
 * @param capability Required capability
 * @param action Action to execute
 * @param parameters Action parameters
 * @param timeout_ms Task timeout
 * @return Task ID on success, negative on error
 */
int orchestrator_add_task(uint32_t workflow_id, const char* task_name, const char* description,
                         task_type_t type, message_priority_t priority,
                         agent_type_t required_agent_type, const char* capability,
                         const char* action, const char* parameters, uint32_t timeout_ms);

/**
 * Add task dependency
 * @param workflow_id Workflow ID
 * @param task_id Task ID
 * @param dependency_task_id Dependency task ID
 * @return AGENT_SUCCESS on success, error code otherwise
 */
agent_error_t orchestrator_add_task_dependency(uint32_t workflow_id, uint32_t task_id, uint32_t dependency_task_id);

/**
 * Start workflow execution
 * @param workflow_id Workflow ID
 * @return AGENT_SUCCESS on success, error code otherwise
 */
agent_error_t orchestrator_start_workflow(uint32_t workflow_id);

/**
 * Get workflow state
 * @param workflow_id Workflow ID
 * @return Current workflow state
 */
workflow_state_t orchestrator_get_workflow_state(uint32_t workflow_id);

// ============================================================================
// SECURITY FUNCTIONS
// ============================================================================

/**
 * Report vulnerability
 * @param title Vulnerability title
 * @param description Vulnerability description
 * @param severity Severity level
 * @param file_path File path where found
 * @param line_number Line number
 * @param cve_id CVE identifier (optional)
 * @return Vulnerability ID on success, 0 on error
 */
uint32_t security_report_vulnerability(const char* title, const char* description,
                                      vulnerability_severity_t severity, const char* file_path,
                                      uint32_t line_number, const char* cve_id);

/**
 * Run vulnerability scan
 * @param target_path Target path to scan
 * @param scan_type Type of scan to perform
 * @return Number of vulnerabilities found, negative on error
 */
int security_run_scan(const char* target_path, security_scan_type_t scan_type);

/**
 * Report security threat
 * @param threat_name Threat name
 * @param description Threat description
 * @param level Threat level
 * @param category Threat category
 * @return Threat ID on success, 0 on error
 */
uint32_t security_report_threat(const char* threat_name, const char* description,
                               threat_level_t level, const char* category);

/**
 * Create security incident
 * @param title Incident title
 * @param description Incident description
 * @param severity Incident severity
 * @param confirmed Whether incident is confirmed
 * @return Incident ID on success, 0 on error
 */
uint32_t security_create_incident(const char* title, const char* description,
                                 vulnerability_severity_t severity, bool confirmed);

/**
 * Get security metrics
 * @param stats Output security statistics
 * @return AGENT_SUCCESS on success, error code otherwise
 */
agent_error_t security_get_stats(security_stats_t* stats);

// ============================================================================
// MONITORING AND DIAGNOSTICS
// ============================================================================

/**
 * Enable system monitoring
 * @param enable Whether to enable monitoring
 * @return AGENT_SUCCESS on success, error code otherwise
 */
agent_error_t agent_system_enable_monitoring(bool enable);

/**
 * Set log level for system components
 * @param level Log level (0=ERROR, 1=WARN, 2=INFO, 3=DEBUG)
 * @return AGENT_SUCCESS on success, error code otherwise
 */
agent_error_t agent_system_set_log_level(int level);

/**
 * Enable performance profiling
 * @param enable Whether to enable profiling
 * @return AGENT_SUCCESS on success, error code otherwise
 */
agent_error_t agent_system_enable_profiling(bool enable);

/**
 * Generate system health report
 * @param report_buffer Buffer to store report
 * @param buffer_size Size of report buffer
 * @return Length of report generated, negative on error
 */
ssize_t agent_system_generate_health_report(char* report_buffer, size_t buffer_size);

/**
 * Run system diagnostics
 * @return AGENT_SUCCESS if system is healthy, error code otherwise
 */
agent_error_t agent_system_run_diagnostics(void);

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

/**
 * Convert error code to string
 * @param error Error code
 * @return Error description string
 */
const char* agent_error_string(agent_error_t error);

/**
 * Convert agent type to string
 * @param type Agent type
 * @return Agent type name
 */
const char* agent_type_string(agent_type_t type);

/**
 * Convert message priority to string
 * @param priority Message priority
 * @return Priority name
 */
const char* message_priority_string(message_priority_t priority);

/**
 * Convert vulnerability severity to string
 * @param severity Vulnerability severity
 * @return Severity name
 */
const char* vulnerability_severity_string(vulnerability_severity_t severity);

/**
 * Get current timestamp in nanoseconds
 * @return Current timestamp
 */
uint64_t agent_get_timestamp_ns(void);

/**
 * Generate unique message ID
 * @return Unique message ID
 */
uint32_t agent_generate_message_id(void);

/**
 * Generate unique correlation ID
 * @return Unique correlation ID
 */
uint32_t agent_generate_correlation_id(void);

// ============================================================================
// CALLBACK TYPES
// ============================================================================

/**
 * Message received callback
 * @param message Received message
 * @param user_data User-provided data
 */
typedef void (*agent_message_callback_t)(const agent_message_t* message, void* user_data);

/**
 * Agent state changed callback
 * @param agent_id Agent ID
 * @param old_state Previous state
 * @param new_state New state
 * @param user_data User-provided data
 */
typedef void (*agent_state_callback_t)(uint32_t agent_id, agent_state_t old_state,
                                       agent_state_t new_state, void* user_data);

/**
 * Security event callback
 * @param event_type Type of security event
 * @param severity Event severity
 * @param description Event description
 * @param user_data User-provided data
 */
typedef void (*security_event_callback_t)(int event_type, vulnerability_severity_t severity,
                                         const char* description, void* user_data);

/**
 * Register message callback
 * @param callback Callback function
 * @param user_data User data to pass to callback
 * @return AGENT_SUCCESS on success, error code otherwise
 */
agent_error_t agent_register_message_callback(agent_message_callback_t callback, void* user_data);

/**
 * Register state change callback
 * @param callback Callback function
 * @param user_data User data to pass to callback
 * @return AGENT_SUCCESS on success, error code otherwise
 */
agent_error_t agent_register_state_callback(agent_state_callback_t callback, void* user_data);

/**
 * Register security event callback
 * @param callback Callback function
 * @param user_data User data to pass to callback
 * @return AGENT_SUCCESS on success, error code otherwise
 */
agent_error_t agent_register_security_callback(security_event_callback_t callback, void* user_data);

// ============================================================================
// ADVANCED FEATURES
// ============================================================================

/**
 * Enable automatic load balancing
 * @param enable Whether to enable load balancing
 * @return AGENT_SUCCESS on success, error code otherwise
 */
agent_error_t agent_system_enable_load_balancing(bool enable);

/**
 * Enable automatic failover
 * @param enable Whether to enable failover
 * @return AGENT_SUCCESS on success, error code otherwise
 */
agent_error_t agent_system_enable_failover(bool enable);

/**
 * Set CPU affinity for system threads
 * @param cpu_mask CPU affinity mask
 * @return AGENT_SUCCESS on success, error code otherwise
 */
agent_error_t agent_system_set_cpu_affinity(uint64_t cpu_mask);

/**
 * Enable NUMA optimization
 * @param enable Whether to enable NUMA optimization
 * @return AGENT_SUCCESS on success, error code otherwise
 */
agent_error_t agent_system_enable_numa_optimization(bool enable);

/**
 * Set message compression threshold
 * @param threshold_bytes Messages larger than this will be compressed
 * @return AGENT_SUCCESS on success, error code otherwise
 */
agent_error_t agent_system_set_compression_threshold(size_t threshold_bytes);

/**
 * Enable message persistence
 * @param enable Whether to enable message persistence
 * @param storage_path Path for persistent storage
 * @return AGENT_SUCCESS on success, error code otherwise
 */
agent_error_t agent_system_enable_persistence(bool enable, const char* storage_path);

#ifdef __cplusplus
}
#endif

#endif // AGENT_SYSTEM_H