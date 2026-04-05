/*
 * SECURITY AGENT
 * 
 * Comprehensive security operations and vulnerability management system
 * - Vulnerability scanning and assessment
 * - Threat detection and analysis
 * - Compliance monitoring and reporting  
 * - Security policy enforcement
 * - Incident response coordination
 * - Penetration testing orchestration
 * - Security metrics and analytics
 * 
 * Integrates with security tools and provides enterprise security oversight
 * 
 * Author: Agent Communication System
 * Version: 1.0 Production
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
#include <fcntl.h>
#include <dirent.h>
#include <sys/stat.h>

// Include headers
#include "agent_protocol.h"

// ============================================================================
// CONSTANTS AND CONFIGURATION
// ============================================================================

#define SECURITY_AGENT_ID 3
#define MAX_VULNERABILITIES 4096
#define MAX_THREATS 1024
#define MAX_COMPLIANCE_RULES 512
#define MAX_SECURITY_POLICIES 256
#define MAX_INCIDENTS 512
#define MAX_SCAN_TARGETS 128
#define MAX_SECURITY_SCANS 64
#define MAX_THREAT_INDICATORS 2048
#define MAX_SECURITY_EVENTS 8192
#define SECURITY_HEARTBEAT_INTERVAL_MS 5000
#define VULNERABILITY_SCAN_TIMEOUT_MS 1800000  // 30 minutes
#define THREAT_ANALYSIS_TIMEOUT_MS 300000     // 5 minutes
#define CACHE_LINE_SIZE 64

// Chaos testing constants
#define MAX_CHAOS_TESTS 64
#define MAX_CHAOS_AGENTS 32
#define CHAOS_IPC_BUFFER_SIZE 8192
#define CHAOS_PYTHON_PATH "/usr/bin/python3"

// RBAC constants
#define MAX_USERS 1024
#define MAX_SESSIONS 512
#define MAX_AGENT_PERMISSIONS 31
#define JWT_SECRET_KEY_SIZE 256
#define SESSION_TOKEN_SIZE 64
#define USERNAME_MAX_SIZE 64
#define ROLE_NAME_MAX_SIZE 32

// Vulnerability severity levels
typedef enum {
    VULN_SEVERITY_CRITICAL = 0,
    VULN_SEVERITY_HIGH = 1,
    VULN_SEVERITY_MEDIUM = 2,
    VULN_SEVERITY_LOW = 3,
    VULN_SEVERITY_INFO = 4
} vulnerability_severity_t;

// Threat levels
typedef enum {
    THREAT_LEVEL_CRITICAL = 0,
    THREAT_LEVEL_HIGH = 1,
    THREAT_LEVEL_MEDIUM = 2,
    THREAT_LEVEL_LOW = 3,
    THREAT_LEVEL_INFO = 4
} threat_level_t;

// Security scan types
typedef enum {
    SCAN_TYPE_STATIC_CODE = 1,
    SCAN_TYPE_DYNAMIC_ANALYSIS = 2,
    SCAN_TYPE_DEPENDENCY_CHECK = 3,
    SCAN_TYPE_CONTAINER_SCAN = 4,
    SCAN_TYPE_NETWORK_SCAN = 5,
    SCAN_TYPE_WEB_APPLICATION = 6,
    SCAN_TYPE_INFRASTRUCTURE = 7,
    SCAN_TYPE_COMPLIANCE = 8,
    SCAN_TYPE_PENETRATION_TEST = 9,
    SCAN_TYPE_CONFIGURATION = 10
} security_scan_type_t;

// Compliance frameworks
typedef enum {
    FRAMEWORK_SOX = 1,
    FRAMEWORK_PCI_DSS = 2,
    FRAMEWORK_HIPAA = 3,
    FRAMEWORK_GDPR = 4,
    FRAMEWORK_ISO27001 = 5,
    FRAMEWORK_NIST = 6,
    FRAMEWORK_CIS = 7,
    FRAMEWORK_OWASP = 8,
    FRAMEWORK_CUSTOM = 9
} compliance_framework_t;

// Security event types
typedef enum {
    EVENT_VULNERABILITY_FOUND = 1,
    EVENT_THREAT_DETECTED = 2,
    EVENT_POLICY_VIOLATION = 3,
    EVENT_COMPLIANCE_FAILURE = 4,
    EVENT_INCIDENT_CREATED = 5,
    EVENT_SCAN_COMPLETED = 6,
    EVENT_REMEDIATION_APPLIED = 7,
    EVENT_FALSE_POSITIVE = 8,
    // Chaos testing event types
    EVENT_CHAOS_TEST_STARTED = 9,
    EVENT_CHAOS_TEST_COMPLETED = 10,
    EVENT_CHAOS_FINDING_CRITICAL = 11,
    EVENT_CHAOS_REMEDIATION_READY = 12
} security_event_type_t;

// RBAC role hierarchy
typedef enum {
    RBAC_ROLE_GUEST = 0,        // Read-only access to basic info
    RBAC_ROLE_USER = 1,         // Standard user operations
    RBAC_ROLE_OPERATOR = 2,     // System operations, monitoring
    RBAC_ROLE_ADMIN = 3         // Full administrative access
} rbac_role_t;

// Agent permissions
typedef enum {
    PERM_AGENT_DIRECTOR = 0,
    PERM_AGENT_PROJECT_ORCHESTRATOR = 1,
    PERM_AGENT_ARCHITECT = 2,
    PERM_AGENT_CONSTRUCTOR = 3,
    PERM_AGENT_PATCHER = 4,
    PERM_AGENT_DEBUGGER = 5,
    PERM_AGENT_TESTBED = 6,
    PERM_AGENT_LINTER = 7,
    PERM_AGENT_OPTIMIZER = 8,
    PERM_AGENT_SECURITY = 9,
    PERM_AGENT_BASTION = 10,
    PERM_AGENT_SECURITY_CHAOS = 11,
    PERM_AGENT_OVERSIGHT = 12,
    PERM_AGENT_INFRASTRUCTURE = 13,
    PERM_AGENT_DEPLOYER = 14,
    PERM_AGENT_MONITOR = 15,
    PERM_AGENT_PACKAGER = 16,
    PERM_AGENT_API_DESIGNER = 17,
    PERM_AGENT_DATABASE = 18,
    PERM_AGENT_WEB = 19,
    PERM_AGENT_MOBILE = 20,
    PERM_AGENT_PYGUI = 21,
    PERM_AGENT_TUI = 22,
    PERM_AGENT_DATA_SCIENCE = 23,
    PERM_AGENT_MLOPS = 24,
    PERM_AGENT_DOCGEN = 25,
    PERM_AGENT_RESEARCHER = 26,
    PERM_AGENT_C_INTERNAL = 27,
    PERM_AGENT_PYTHON_INTERNAL = 28,
    PERM_SYSTEM_CONFIG = 29,
    PERM_SYSTEM_SHUTDOWN = 30
} agent_permission_t;

// Incident states
typedef enum {
    INCIDENT_STATE_NEW = 0,
    INCIDENT_STATE_ASSIGNED = 1,
    INCIDENT_STATE_INVESTIGATING = 2,
    INCIDENT_STATE_MITIGATING = 3,
    INCIDENT_STATE_RESOLVED = 4,
    INCIDENT_STATE_CLOSED = 5,
    INCIDENT_STATE_FALSE_POSITIVE = 6
} incident_state_t;

// ============================================================================
// DATA STRUCTURES
// ============================================================================

// Vulnerability record
typedef struct {
    uint32_t vuln_id;
    char cve_id[32];
    char title[256];
    char description[2048];
    
    // Classification
    vulnerability_severity_t severity;
    float cvss_score;
    char category[64];
    char subcategory[64];
    
    // Location
    char file_path[512];
    uint32_t line_number;
    char function_name[128];
    char component[128];
    
    // Detection
    uint64_t discovered_time_ns;
    char detection_method[64];
    char scanner_name[64];
    char scanner_version[32];
    
    // Impact
    char impact_assessment[1024];
    float exploitability_score;
    bool publicly_exploitable;
    bool remote_exploitable;
    
    // Remediation
    char remediation_guidance[2048];
    char fix_recommendation[512];
    uint32_t estimated_effort_hours;
    bool has_patch;
    char patch_version[64];
    
    // Status
    bool verified;
    bool false_positive;
    uint64_t last_seen_ns;
    uint32_t occurrence_count;
    
} vulnerability_record_t;

// Threat intelligence record
typedef struct {
    uint32_t threat_id;
    char threat_name[128];
    char description[1024];
    
    // Classification
    threat_level_t level;
    char category[64];      // malware, phishing, etc.
    char attack_vector[64]; // network, email, etc.
    
    // Indicators
    char indicators[16][256];  // IOCs (IPs, domains, hashes, etc.)
    uint32_t indicator_count;
    
    // Attribution
    char threat_actor[128];
    char campaign[128];
    char ttps[512];  // Tactics, Techniques, Procedures
    
    // Timeline
    uint64_t first_seen_ns;
    uint64_t last_activity_ns;
    bool active;
    
    // Detection
    char detection_rules[2048];
    float confidence_score;
    char source[128];
    
} threat_record_t;

// Security scan configuration
typedef struct {
    uint32_t scan_id;
    char name[128];
    security_scan_type_t type;
    
    // Targets
    char targets[MAX_SCAN_TARGETS][512];
    uint32_t target_count;
    
    // Configuration
    char parameters[2048];
    uint32_t timeout_ms;
    bool deep_scan;
    bool authenticated;
    
    // Scheduling
    bool recurring;
    uint32_t interval_hours;
    uint64_t last_run_ns;
    uint64_t next_run_ns;
    
    // Results
    uint32_t vulnerabilities_found;
    uint32_t threats_identified;
    float risk_score;
    
} security_scan_config_t;

// Compliance rule
typedef struct {
    uint32_t rule_id;
    char rule_name[128];
    char description[512];
    
    // Framework
    compliance_framework_t framework;
    char control_id[32];
    char requirement[1024];
    
    // Implementation
    char check_method[64];   // automated, manual, hybrid
    char validation_script[512];
    uint32_t check_interval_hours;
    
    // Status
    bool compliant;
    uint64_t last_check_ns;
    char findings[2048];
    char remediation_plan[1024];
    
} compliance_rule_t;

// Security incident
typedef struct {
    uint32_t incident_id;
    char title[256];
    char description[2048];
    
    // Classification
    vulnerability_severity_t severity;
    char category[64];
    bool confirmed;
    
    // Timeline
    uint64_t created_time_ns;
    uint64_t first_event_ns;
    uint64_t last_event_ns;
    uint64_t resolved_time_ns;
    
    // Assignment
    char assigned_to[128];
    incident_state_t state;
    
    // Evidence
    char evidence[16][512];
    uint32_t evidence_count;
    
    // Impact
    char affected_systems[1024];
    char business_impact[512];
    bool data_breach;
    
    // Response
    char response_actions[2048];
    char lessons_learned[1024];
    
} security_incident_t;

// Chaos testing configuration
typedef struct {
    uint32_t chaos_test_id;
    char test_type[64];           // "port_scan", "path_traversal", etc
    char target[512];
    uint32_t agent_count;
    uint32_t max_duration_sec;
    bool aggressive_mode;
    char python_module_path[512]; // Path to Python chaos agent
    uint64_t started_time_ns;
    volatile bool completed;
} chaos_test_config_t;

// Chaos test results
typedef struct {
    uint32_t chaos_test_id;
    uint32_t findings_count;
    uint32_t critical_findings;
    uint32_t false_positives;
    float overall_risk_score;
    char remediation_summary[2048];
    uint64_t completion_time_ns;
    uint32_t python_agent_count;    // Actual agents deployed
} chaos_test_result_t;

// IPC message structure for C<->Python communication
typedef struct {
    uint32_t message_type;        // 1=START_TEST, 2=RESULT, 3=STATUS
    uint32_t test_id;
    char payload_json[4096];      // JSON data for Python processing
    uint32_t payload_size;
    uint32_t checksum;
} chaos_ipc_message_t;

// Security metrics
typedef struct __attribute__((aligned(CACHE_LINE_SIZE))) {
    _Atomic uint64_t vulnerabilities_discovered;
    _Atomic uint64_t vulnerabilities_fixed;
    _Atomic uint64_t threats_detected;
    _Atomic uint64_t threats_mitigated;
    _Atomic uint64_t scans_performed;
    _Atomic uint64_t incidents_created;
    _Atomic uint64_t incidents_resolved;
    _Atomic uint32_t critical_vulnerabilities;
    _Atomic uint32_t high_vulnerabilities;
    _Atomic uint32_t active_threats;
    _Atomic uint32_t compliance_violations;
    float mean_time_to_detect_hours;
    float mean_time_to_respond_hours;
    float security_posture_score;
    float compliance_percentage;
} security_metrics_t;

// Security event
typedef struct {
    uint32_t event_id;
    security_event_type_t type;
    uint64_t timestamp_ns;
    
    // Context
    char source[128];
    char target[256];
    char description[512];
    
    // Severity and impact
    vulnerability_severity_t severity;
    float risk_score;
    
    // Correlation
    uint32_t correlation_id;
    bool correlated;
    
} security_event_t;

// RBAC User record
typedef struct {
    uint32_t user_id;
    char username[USERNAME_MAX_SIZE];
    char password_hash[64];           // SHA-256 hash
    rbac_role_t role;
    bool active;
    bool locked;
    uint32_t failed_login_attempts;
    uint64_t last_login_ns;
    uint64_t created_time_ns;
    uint64_t last_activity_ns;
    uint32_t permission_mask;         // Bitfield for agent permissions
} rbac_user_t;

// RBAC Session
typedef struct {
    char session_token[SESSION_TOKEN_SIZE];
    uint32_t user_id;
    rbac_role_t role;
    uint32_t permission_mask;
    uint64_t created_time_ns;
    uint64_t last_access_ns;
    uint64_t expires_ns;
    bool active;
    char client_ip[46];               // IPv6 compatible
    char user_agent[256];
} rbac_session_t;

// Permission matrix for all roles
typedef struct {
    rbac_role_t role;
    uint32_t permission_mask;         // Bitfield representing allowed permissions
    char description[128];
} role_permission_matrix_t;

// JWT token structure
typedef struct {
    char header[256];
    char payload[512];
    char signature[256];
    uint64_t issued_at;
    uint64_t expires_at;
    uint32_t user_id;
    rbac_role_t role;
    uint32_t permission_mask;
} jwt_token_t;

// RBAC audit log entry
typedef struct {
    uint32_t audit_id;
    uint32_t user_id;
    char username[USERNAME_MAX_SIZE];
    char action[128];
    char resource[256];
    bool success;
    char failure_reason[512];
    uint64_t timestamp_ns;
    char client_ip[46];
    agent_permission_t requested_permission;
} rbac_audit_entry_t;

// Main Security Agent service
typedef struct __attribute__((aligned(PAGE_SIZE))) {
    // Identity
    uint32_t agent_id;
    char name[64];
    bool initialized;
    volatile bool running;
    
    // Vulnerability management
    vulnerability_record_t vulnerabilities[MAX_VULNERABILITIES];
    uint32_t vulnerability_count;
    pthread_rwlock_t vulnerabilities_lock;
    
    // Threat intelligence
    threat_record_t threats[MAX_THREATS];
    uint32_t threat_count;
    pthread_rwlock_t threats_lock;
    
    // Security scans
    security_scan_config_t scan_configs[MAX_SECURITY_SCANS];
    uint32_t scan_config_count;
    pthread_rwlock_t scans_lock;
    
    // Compliance management
    compliance_rule_t compliance_rules[MAX_COMPLIANCE_RULES];
    uint32_t compliance_rule_count;
    pthread_rwlock_t compliance_lock;
    
    // Incident management
    security_incident_t incidents[MAX_INCIDENTS];
    uint32_t incident_count;
    pthread_rwlock_t incidents_lock;
    
    // Security events
    security_event_t events[MAX_SECURITY_EVENTS];
    uint32_t event_head;
    uint32_t event_tail;
    uint32_t event_count;
    pthread_rwlock_t events_lock;
    
    // Worker threads
    pthread_t vulnerability_scanner_thread;
    pthread_t threat_monitor_thread;
    pthread_t compliance_checker_thread;
    pthread_t incident_responder_thread;
    
    // Statistics
    security_metrics_t metrics;
    
    // Configuration
    bool auto_remediation_enabled;
    float risk_tolerance_threshold;
    uint32_t max_concurrent_scans;
    bool real_time_monitoring;
    
    // RBAC components
    rbac_user_t users[MAX_USERS];
    uint32_t user_count;
    pthread_rwlock_t users_lock;
    
    rbac_session_t sessions[MAX_SESSIONS];
    uint32_t session_count;
    pthread_rwlock_t sessions_lock;
    
    role_permission_matrix_t role_matrix[4];  // 4 roles
    char jwt_secret_key[JWT_SECRET_KEY_SIZE];
    
    rbac_audit_entry_t audit_log[8192];
    uint32_t audit_head;
    uint32_t audit_tail;
    uint32_t audit_count;
    pthread_rwlock_t audit_lock;
    
} security_service_t;

// Global security instance
static security_service_t* g_security = NULL;

// ============================================================================
// FUNCTION DECLARATIONS
// ============================================================================

// Core security functions
int security_service_init();
void security_service_cleanup();
int start_security_threads();
void print_security_statistics();

// Vulnerability management
uint32_t report_vulnerability(const char* title, const char* description,
                             vulnerability_severity_t severity, const char* file_path,
                             uint32_t line_number, const char* cve_id);
int run_vulnerability_scan(const char* target_path, security_scan_type_t scan_type);

// Threat management
uint32_t report_threat(const char* threat_name, const char* description,
                      threat_level_t level, const char* category);

// Incident management
uint32_t create_security_incident(const char* title, const char* description,
                                 vulnerability_severity_t severity, bool confirmed);

// Security event logging
void log_security_event(security_event_type_t type, const char* source, const char* target,
                        const char* description, vulnerability_severity_t severity, float risk_score);

// RBAC system functions
int rbac_init();
int create_user(const char* username, const char* password, rbac_role_t role);
int authenticate_user(const char* username, const char* password, const char* client_ip,
                      const char* user_agent, char* session_token_out, size_t token_size);
int create_session(uint32_t user_id, rbac_role_t role, uint32_t permission_mask,
                   const char* client_ip, const char* user_agent,
                   char* session_token_out, size_t token_size);
int check_permission(const char* session_token, agent_permission_t permission,
                     const char* resource, const char* client_ip);
int revoke_session(const char* session_token);
void cleanup_expired_sessions();
int update_user_role(uint32_t user_id, rbac_role_t new_role);
void rbac_audit_log(uint32_t user_id, const char* username, const char* action,
                   const char* resource, bool success, const char* failure_reason,
                   const char* client_ip, agent_permission_t permission);
const char* get_permission_name(agent_permission_t permission);
const char* get_role_name(rbac_role_t role);
void print_rbac_statistics();

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

static inline uint64_t get_timestamp_ns() {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (uint64_t)ts.tv_sec * 1000000000ULL + ts.tv_nsec;
}

static uint32_t generate_vulnerability_id() {
    static _Atomic uint32_t id_counter = 1;
    return atomic_fetch_add(&id_counter, 1);
}

static uint32_t generate_threat_id() {
    static _Atomic uint32_t id_counter = 1;
    return atomic_fetch_add(&id_counter, 1);
}

static uint32_t generate_incident_id() {
    static _Atomic uint32_t id_counter = 1;
    return atomic_fetch_add(&id_counter, 1);
}

static uint32_t generate_event_id() {
    static _Atomic uint32_t id_counter = 1;
    return atomic_fetch_add(&id_counter, 1);
}

static float calculate_cvss_score(vulnerability_severity_t severity, bool remote_exploitable,
                                 bool publicly_exploitable) {
    float base_score = 0.0f;
    
    switch (severity) {
        case VULN_SEVERITY_CRITICAL:
            base_score = 9.0f + ((rand() % 10) / 10.0f);  // 9.0-10.0
            break;
        case VULN_SEVERITY_HIGH:
            base_score = 7.0f + ((rand() % 20) / 10.0f);  // 7.0-8.9
            break;
        case VULN_SEVERITY_MEDIUM:
            base_score = 4.0f + ((rand() % 30) / 10.0f);  // 4.0-6.9
            break;
        case VULN_SEVERITY_LOW:
            base_score = 0.1f + ((rand() % 39) / 10.0f);  // 0.1-3.9
            break;
        case VULN_SEVERITY_INFO:
            base_score = 0.0f;
            break;
    }
    
    // Adjust for exploitability
    if (remote_exploitable) base_score += 0.5f;
    if (publicly_exploitable) base_score += 0.3f;
    
    return base_score > 10.0f ? 10.0f : base_score;
}

static float calculate_risk_score(const vulnerability_record_t* vuln) {
    float risk = vuln->cvss_score * vuln->exploitability_score;
    
    // Adjust for exposure
    if (vuln->remote_exploitable) risk *= 1.5f;
    if (vuln->publicly_exploitable) risk *= 1.8f;
    if (vuln->has_patch) risk *= 0.7f;  // Lower risk if patch available
    
    return risk > 10.0f ? 10.0f : risk;
}

// ============================================================================
// SECURITY SERVICE INITIALIZATION
// ============================================================================

int security_service_init() {
    if (g_security) {
        return -EALREADY;
    }
    
    // Allocate security structure with NUMA awareness
    int numa_node = numa_node_of_cpu(sched_getcpu());
    g_security = numa_alloc_onnode(sizeof(security_service_t), numa_node);
    if (!g_security) {
        return -ENOMEM;
    }
    
    memset(g_security, 0, sizeof(security_service_t));
    
    // Initialize basic properties
    g_security->agent_id = SECURITY_AGENT_ID;
    strcpy(g_security->name, "SECURITY");
    g_security->running = true;
    
    // Initialize locks
    pthread_rwlock_init(&g_security->vulnerabilities_lock, NULL);
    pthread_rwlock_init(&g_security->threats_lock, NULL);
    pthread_rwlock_init(&g_security->scans_lock, NULL);
    pthread_rwlock_init(&g_security->compliance_lock, NULL);
    pthread_rwlock_init(&g_security->incidents_lock, NULL);
    pthread_rwlock_init(&g_security->events_lock, NULL);
    pthread_rwlock_init(&g_security->users_lock, NULL);
    pthread_rwlock_init(&g_security->sessions_lock, NULL);
    pthread_rwlock_init(&g_security->audit_lock, NULL);
    
    // Initialize counters
    g_security->vulnerability_count = 0;
    g_security->threat_count = 0;
    g_security->scan_config_count = 0;
    g_security->compliance_rule_count = 0;
    g_security->incident_count = 0;
    g_security->event_head = 0;
    g_security->event_tail = 0;
    g_security->event_count = 0;
    
    // Configuration
    g_security->auto_remediation_enabled = false;  // Require manual approval
    g_security->risk_tolerance_threshold = 7.0f;   // CVSS 7.0 and above require immediate attention
    g_security->max_concurrent_scans = 8;
    g_security->real_time_monitoring = true;
    
    // Initialize metrics
    atomic_store(&g_security->metrics.vulnerabilities_discovered, 0);
    atomic_store(&g_security->metrics.vulnerabilities_fixed, 0);
    atomic_store(&g_security->metrics.threats_detected, 0);
    atomic_store(&g_security->metrics.threats_mitigated, 0);
    atomic_store(&g_security->metrics.scans_performed, 0);
    atomic_store(&g_security->metrics.incidents_created, 0);
    atomic_store(&g_security->metrics.incidents_resolved, 0);
    atomic_store(&g_security->metrics.critical_vulnerabilities, 0);
    atomic_store(&g_security->metrics.high_vulnerabilities, 0);
    atomic_store(&g_security->metrics.active_threats, 0);
    atomic_store(&g_security->metrics.compliance_violations, 0);
    g_security->metrics.mean_time_to_detect_hours = 0.0f;
    g_security->metrics.mean_time_to_respond_hours = 0.0f;
    g_security->metrics.security_posture_score = 85.0f;  // Start with good baseline
    g_security->metrics.compliance_percentage = 90.0f;
    
    // Initialize RBAC system
    if (rbac_init() != 0) {
        printf("Failed to initialize RBAC system\n");
        numa_free(g_security, sizeof(security_service_t));
        g_security = NULL;
        return -EINVAL;
    }
    
    g_security->initialized = true;
    
    printf("Security Service: Initialized on NUMA node %d\n", numa_node);
    return 0;
}

void security_service_cleanup() {
    if (!g_security) {
        return;
    }
    
    g_security->running = false;
    
    // Stop worker threads
    if (g_security->vulnerability_scanner_thread) {
        pthread_join(g_security->vulnerability_scanner_thread, NULL);
    }
    if (g_security->threat_monitor_thread) {
        pthread_join(g_security->threat_monitor_thread, NULL);
    }
    if (g_security->compliance_checker_thread) {
        pthread_join(g_security->compliance_checker_thread, NULL);
    }
    if (g_security->incident_responder_thread) {
        pthread_join(g_security->incident_responder_thread, NULL);
    }
    
    // Cleanup locks
    pthread_rwlock_destroy(&g_security->vulnerabilities_lock);
    pthread_rwlock_destroy(&g_security->threats_lock);
    pthread_rwlock_destroy(&g_security->scans_lock);
    pthread_rwlock_destroy(&g_security->compliance_lock);
    pthread_rwlock_destroy(&g_security->incidents_lock);
    pthread_rwlock_destroy(&g_security->events_lock);
    pthread_rwlock_destroy(&g_security->users_lock);
    pthread_rwlock_destroy(&g_security->sessions_lock);
    pthread_rwlock_destroy(&g_security->audit_lock);
    
    numa_free(g_security, sizeof(security_service_t));
    g_security = NULL;
    
    printf("Security Service: Cleaned up\n");
}

// ============================================================================
// RBAC SYSTEM IMPLEMENTATION
// ============================================================================

static uint32_t generate_user_id() {
    static _Atomic uint32_t id_counter = 1;
    return atomic_fetch_add(&id_counter, 1);
}

static uint32_t generate_audit_id() {
    static _Atomic uint32_t id_counter = 1;
    return atomic_fetch_add(&id_counter, 1);
}

static void generate_session_token(char* token, size_t token_size) {
    const char charset[] = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";
    for (size_t i = 0; i < token_size - 1; i++) {
        token[i] = charset[rand() % (sizeof(charset) - 1)];
    }
    token[token_size - 1] = '\0';
}

static void sha256_hash(const char* input, char* output) {
    // Simplified hash function for demo - use proper SHA-256 in production
    uint32_t hash = 5381;
    const unsigned char* str = (const unsigned char*)input;
    int c;
    
    while ((c = *str++)) {
        hash = ((hash << 5) + hash) + c;
    }
    
    snprintf(output, 64, "%08x%08x%08x%08x%08x%08x%08x%08x", 
             hash, hash ^ 0x12345678, hash ^ 0x87654321, hash ^ 0xABCDEF00,
             hash ^ 0x11111111, hash ^ 0x22222222, hash ^ 0x33333333, hash ^ 0x44444444);
}

int rbac_init() {
    if (!g_security) {
        return -EINVAL;
    }
    
    // Initialize counters
    g_security->user_count = 0;
    g_security->session_count = 0;
    g_security->audit_head = 0;
    g_security->audit_tail = 0;
    g_security->audit_count = 0;
    
    // Initialize permission matrix for each role
    // GUEST role - very limited access
    g_security->role_matrix[RBAC_ROLE_GUEST].role = RBAC_ROLE_GUEST;
    g_security->role_matrix[RBAC_ROLE_GUEST].permission_mask = 
        (1U << PERM_AGENT_MONITOR) |           // Can view monitoring data
        (1U << PERM_AGENT_RESEARCHER);         // Can access research tools
    strcpy(g_security->role_matrix[RBAC_ROLE_GUEST].description, 
           "Guest - Read-only access to monitoring and research");
    
    // USER role - standard development access
    g_security->role_matrix[RBAC_ROLE_USER].role = RBAC_ROLE_USER;
    g_security->role_matrix[RBAC_ROLE_USER].permission_mask = 
        (1U << PERM_AGENT_ARCHITECT) |         // System design
        (1U << PERM_AGENT_CONSTRUCTOR) |       // Project initialization
        (1U << PERM_AGENT_PATCHER) |           // Code fixes
        (1U << PERM_AGENT_DEBUGGER) |          // Debugging
        (1U << PERM_AGENT_TESTBED) |           // Testing
        (1U << PERM_AGENT_LINTER) |            // Code review
        (1U << PERM_AGENT_OPTIMIZER) |         // Performance optimization
        (1U << PERM_AGENT_MONITOR) |           // Monitoring
        (1U << PERM_AGENT_API_DESIGNER) |      // API design
        (1U << PERM_AGENT_DATABASE) |          // Database operations
        (1U << PERM_AGENT_WEB) |               // Web development
        (1U << PERM_AGENT_MOBILE) |            // Mobile development
        (1U << PERM_AGENT_PYGUI) |             // Python GUI
        (1U << PERM_AGENT_TUI) |               // Terminal UI
        (1U << PERM_AGENT_DATA_SCIENCE) |      // Data science
        (1U << PERM_AGENT_MLOPS) |             // ML operations
        (1U << PERM_AGENT_DOCGEN) |            // Documentation
        (1U << PERM_AGENT_RESEARCHER) |        // Research
        (1U << PERM_AGENT_C_INTERNAL) |        // C development
        (1U << PERM_AGENT_PYTHON_INTERNAL);    // Python development
    strcpy(g_security->role_matrix[RBAC_ROLE_USER].description,
           "User - Standard development and analysis access");
    
    // OPERATOR role - system operations
    g_security->role_matrix[RBAC_ROLE_OPERATOR].role = RBAC_ROLE_OPERATOR;
    g_security->role_matrix[RBAC_ROLE_OPERATOR].permission_mask = 
        g_security->role_matrix[RBAC_ROLE_USER].permission_mask |  // All user permissions
        (1U << PERM_AGENT_PROJECT_ORCHESTRATOR) |  // Project coordination
        (1U << PERM_AGENT_SECURITY) |              // Security operations
        (1U << PERM_AGENT_BASTION) |               // Defense systems
        (1U << PERM_AGENT_OVERSIGHT) |             // Quality assurance
        (1U << PERM_AGENT_INFRASTRUCTURE) |        // Infrastructure setup
        (1U << PERM_AGENT_DEPLOYER) |              // Deployment
        (1U << PERM_AGENT_PACKAGER) |              // Package management
        (1U << PERM_SYSTEM_CONFIG);                // System configuration
    strcpy(g_security->role_matrix[RBAC_ROLE_OPERATOR].description,
           "Operator - System operations and security management");
    
    // ADMIN role - full access
    g_security->role_matrix[RBAC_ROLE_ADMIN].role = RBAC_ROLE_ADMIN;
    g_security->role_matrix[RBAC_ROLE_ADMIN].permission_mask = 0xFFFFFFFF;  // All permissions
    strcpy(g_security->role_matrix[RBAC_ROLE_ADMIN].description,
           "Admin - Full system access including critical operations");
    
    // Generate JWT secret key
    generate_session_token(g_security->jwt_secret_key, JWT_SECRET_KEY_SIZE);
    
    // Create default admin user
    create_user("admin", "admin123", RBAC_ROLE_ADMIN);
    
    printf("RBAC: Initialized with 4 roles and permission matrix for 31 agents\n");
    return 0;
}

int create_user(const char* username, const char* password, rbac_role_t role) {
    if (!g_security || !username || !password) {
        return -EINVAL;
    }
    
    if (strlen(username) >= USERNAME_MAX_SIZE) {
        return -EINVAL;
    }
    
    pthread_rwlock_wrlock(&g_security->users_lock);
    
    if (g_security->user_count >= MAX_USERS) {
        pthread_rwlock_unlock(&g_security->users_lock);
        return -ENOSPC;
    }
    
    // Check if username already exists
    for (uint32_t i = 0; i < g_security->user_count; i++) {
        if (strcmp(g_security->users[i].username, username) == 0) {
            pthread_rwlock_unlock(&g_security->users_lock);
            return -EEXIST;
        }
    }
    
    // Find free slot
    rbac_user_t* user = &g_security->users[g_security->user_count];
    
    // Initialize user
    user->user_id = generate_user_id();
    strncpy(user->username, username, sizeof(user->username) - 1);
    user->username[sizeof(user->username) - 1] = '\0';
    
    // Hash password
    sha256_hash(password, user->password_hash);
    
    user->role = role;
    user->active = true;
    user->locked = false;
    user->failed_login_attempts = 0;
    user->created_time_ns = get_timestamp_ns();
    user->last_login_ns = 0;
    user->last_activity_ns = user->created_time_ns;
    
    // Set permission mask based on role
    if (role < 4) {
        user->permission_mask = g_security->role_matrix[role].permission_mask;
    } else {
        user->permission_mask = 0;  // Invalid role
    }
    
    g_security->user_count++;
    uint32_t user_id = user->user_id;
    
    pthread_rwlock_unlock(&g_security->users_lock);
    
    rbac_audit_log(user_id, username, "CREATE_USER", username, true, NULL, "", PERM_SYSTEM_CONFIG);
    
    printf("RBAC: Created user '%s' with role %d (ID: %u)\n", username, role, user_id);
    return user_id;
}

int authenticate_user(const char* username, const char* password, const char* client_ip,
                      const char* user_agent, char* session_token_out, size_t token_size) {
    if (!g_security || !username || !password || !session_token_out) {
        return -EINVAL;
    }
    
    pthread_rwlock_rdlock(&g_security->users_lock);
    
    rbac_user_t* user = NULL;
    uint32_t user_index = 0;
    
    // Find user
    for (uint32_t i = 0; i < g_security->user_count; i++) {
        if (strcmp(g_security->users[i].username, username) == 0) {
            user = &g_security->users[i];
            user_index = i;
            break;
        }
    }
    
    if (!user) {
        pthread_rwlock_unlock(&g_security->users_lock);
        rbac_audit_log(0, username, "LOGIN", "authentication", false, 
                      "User not found", client_ip ? client_ip : "", PERM_SYSTEM_CONFIG);
        return -ENOENT;
    }
    
    if (!user->active || user->locked) {
        pthread_rwlock_unlock(&g_security->users_lock);
        rbac_audit_log(user->user_id, username, "LOGIN", "authentication", false,
                      user->locked ? "Account locked" : "Account inactive",
                      client_ip ? client_ip : "", PERM_SYSTEM_CONFIG);
        return -EACCES;
    }
    
    // Check password
    char password_hash[64];
    sha256_hash(password, password_hash);
    
    if (strcmp(user->password_hash, password_hash) != 0) {
        // Increment failed login attempts
        user->failed_login_attempts++;
        
        if (user->failed_login_attempts >= 5) {
            user->locked = true;
            printf("RBAC: Account '%s' locked due to too many failed attempts\n", username);
        }
        
        pthread_rwlock_unlock(&g_security->users_lock);
        
        rbac_audit_log(user->user_id, username, "LOGIN", "authentication", false,
                      "Invalid password", client_ip ? client_ip : "", PERM_SYSTEM_CONFIG);
        return -EACCES;
    }
    
    // Successful authentication - create session
    user->failed_login_attempts = 0;
    user->last_login_ns = get_timestamp_ns();
    user->last_activity_ns = user->last_login_ns;
    
    uint32_t user_id = user->user_id;
    rbac_role_t role = user->role;
    uint32_t permission_mask = user->permission_mask;
    
    pthread_rwlock_unlock(&g_security->users_lock);
    
    // Create session
    int session_result = create_session(user_id, role, permission_mask, client_ip, user_agent,
                                       session_token_out, token_size);
    
    if (session_result == 0) {
        rbac_audit_log(user_id, username, "LOGIN", "authentication", true, NULL,
                      client_ip ? client_ip : "", PERM_SYSTEM_CONFIG);
        printf("RBAC: User '%s' authenticated successfully (Role: %d)\n", username, role);
    }
    
    return session_result;
}

int create_session(uint32_t user_id, rbac_role_t role, uint32_t permission_mask,
                   const char* client_ip, const char* user_agent,
                   char* session_token_out, size_t token_size) {
    if (!g_security || !session_token_out || token_size < SESSION_TOKEN_SIZE) {
        return -EINVAL;
    }
    
    pthread_rwlock_wrlock(&g_security->sessions_lock);
    
    if (g_security->session_count >= MAX_SESSIONS) {
        // Find and remove expired sessions
        cleanup_expired_sessions();
        
        if (g_security->session_count >= MAX_SESSIONS) {
            pthread_rwlock_unlock(&g_security->sessions_lock);
            return -ENOSPC;
        }
    }
    
    // Find free slot
    rbac_session_t* session = &g_security->sessions[g_security->session_count];
    
    // Generate session token
    generate_session_token(session->session_token, SESSION_TOKEN_SIZE);
    
    // Initialize session
    session->user_id = user_id;
    session->role = role;
    session->permission_mask = permission_mask;
    session->created_time_ns = get_timestamp_ns();
    session->last_access_ns = session->created_time_ns;
    session->expires_ns = session->created_time_ns + (8ULL * 3600 * 1000000000ULL); // 8 hours
    session->active = true;
    
    if (client_ip) {
        strncpy(session->client_ip, client_ip, sizeof(session->client_ip) - 1);
        session->client_ip[sizeof(session->client_ip) - 1] = '\0';
    }
    
    if (user_agent) {
        strncpy(session->user_agent, user_agent, sizeof(session->user_agent) - 1);
        session->user_agent[sizeof(session->user_agent) - 1] = '\0';
    }
    
    // Copy token to output
    strncpy(session_token_out, session->session_token, token_size - 1);
    session_token_out[token_size - 1] = '\0';
    
    g_security->session_count++;
    
    pthread_rwlock_unlock(&g_security->sessions_lock);
    
    printf("RBAC: Created session for user %u (expires in 8 hours)\n", user_id);
    return 0;
}

int check_permission(const char* session_token, agent_permission_t permission,
                     const char* resource, const char* client_ip) {
    if (!g_security || !session_token) {
        return -EINVAL;
    }
    
    pthread_rwlock_rdlock(&g_security->sessions_lock);
    
    rbac_session_t* session = NULL;
    
    // Find session
    for (uint32_t i = 0; i < g_security->session_count; i++) {
        if (strcmp(g_security->sessions[i].session_token, session_token) == 0) {
            session = &g_security->sessions[i];
            break;
        }
    }
    
    if (!session || !session->active) {
        pthread_rwlock_unlock(&g_security->sessions_lock);
        rbac_audit_log(0, "unknown", "ACCESS_DENIED", resource ? resource : "",
                      false, "Invalid session", client_ip ? client_ip : "", permission);
        return -EACCES;
    }
    
    // Check if session is expired
    uint64_t current_time = get_timestamp_ns();
    if (current_time > session->expires_ns) {
        session->active = false;
        pthread_rwlock_unlock(&g_security->sessions_lock);
        rbac_audit_log(session->user_id, "expired", "ACCESS_DENIED", resource ? resource : "",
                      false, "Session expired", client_ip ? client_ip : "", permission);
        return -ETIME;
    }
    
    // Check permission
    bool has_permission = (session->permission_mask & (1U << permission)) != 0;
    
    if (has_permission) {
        // Update last access time
        session->last_access_ns = current_time;
        
        uint32_t user_id = session->user_id;
        pthread_rwlock_unlock(&g_security->sessions_lock);
        
        // Get username for audit log
        pthread_rwlock_rdlock(&g_security->users_lock);
        char username[USERNAME_MAX_SIZE] = "unknown";
        for (uint32_t i = 0; i < g_security->user_count; i++) {
            if (g_security->users[i].user_id == user_id) {
                strncpy(username, g_security->users[i].username, sizeof(username) - 1);
                username[sizeof(username) - 1] = '\0';
                break;
            }
        }
        pthread_rwlock_unlock(&g_security->users_lock);
        
        rbac_audit_log(user_id, username, "ACCESS_GRANTED", resource ? resource : "",
                      true, NULL, client_ip ? client_ip : "", permission);
        return 0;
    } else {
        uint32_t user_id = session->user_id;
        pthread_rwlock_unlock(&g_security->sessions_lock);
        
        // Get username for audit log
        pthread_rwlock_rdlock(&g_security->users_lock);
        char username[USERNAME_MAX_SIZE] = "unknown";
        for (uint32_t i = 0; i < g_security->user_count; i++) {
            if (g_security->users[i].user_id == user_id) {
                strncpy(username, g_security->users[i].username, sizeof(username) - 1);
                username[sizeof(username) - 1] = '\0';
                break;
            }
        }
        pthread_rwlock_unlock(&g_security->users_lock);
        
        rbac_audit_log(user_id, username, "ACCESS_DENIED", resource ? resource : "",
                      false, "Insufficient permissions", client_ip ? client_ip : "", permission);
        return -EPERM;
    }
}

int revoke_session(const char* session_token) {
    if (!g_security || !session_token) {
        return -EINVAL;
    }
    
    pthread_rwlock_wrlock(&g_security->sessions_lock);
    
    for (uint32_t i = 0; i < g_security->session_count; i++) {
        if (strcmp(g_security->sessions[i].session_token, session_token) == 0) {
            g_security->sessions[i].active = false;
            uint32_t user_id = g_security->sessions[i].user_id;
            pthread_rwlock_unlock(&g_security->sessions_lock);
            
            rbac_audit_log(user_id, "system", "LOGOUT", "session_revoked", true, NULL, "", PERM_SYSTEM_CONFIG);
            printf("RBAC: Revoked session for user %u\n", user_id);
            return 0;
        }
    }
    
    pthread_rwlock_unlock(&g_security->sessions_lock);
    return -ENOENT;
}

void cleanup_expired_sessions() {
    if (!g_security) {
        return;
    }
    
    uint64_t current_time = get_timestamp_ns();
    uint32_t removed_count = 0;
    
    // Mark expired sessions as inactive
    for (uint32_t i = 0; i < g_security->session_count; i++) {
        if (g_security->sessions[i].active && current_time > g_security->sessions[i].expires_ns) {
            g_security->sessions[i].active = false;
            removed_count++;
        }
    }
    
    if (removed_count > 0) {
        printf("RBAC: Cleaned up %u expired sessions\n", removed_count);
    }
}

int update_user_role(uint32_t user_id, rbac_role_t new_role) {
    if (!g_security) {
        return -EINVAL;
    }
    
    if (new_role >= 4) {  // Invalid role
        return -EINVAL;
    }
    
    pthread_rwlock_wrlock(&g_security->users_lock);
    
    rbac_user_t* user = NULL;
    for (uint32_t i = 0; i < g_security->user_count; i++) {
        if (g_security->users[i].user_id == user_id) {
            user = &g_security->users[i];
            break;
        }
    }
    
    if (!user) {
        pthread_rwlock_unlock(&g_security->users_lock);
        return -ENOENT;
    }
    
    rbac_role_t old_role = user->role;
    user->role = new_role;
    user->permission_mask = g_security->role_matrix[new_role].permission_mask;
    user->last_activity_ns = get_timestamp_ns();
    
    char username[USERNAME_MAX_SIZE];
    strncpy(username, user->username, sizeof(username) - 1);
    username[sizeof(username) - 1] = '\0';
    
    pthread_rwlock_unlock(&g_security->users_lock);
    
    // Update all active sessions for this user
    pthread_rwlock_wrlock(&g_security->sessions_lock);
    
    for (uint32_t i = 0; i < g_security->session_count; i++) {
        if (g_security->sessions[i].user_id == user_id && g_security->sessions[i].active) {
            g_security->sessions[i].role = new_role;
            g_security->sessions[i].permission_mask = g_security->role_matrix[new_role].permission_mask;
        }
    }
    
    pthread_rwlock_unlock(&g_security->sessions_lock);
    
    char audit_msg[256];
    snprintf(audit_msg, sizeof(audit_msg), "Role changed from %d to %d", old_role, new_role);
    
    rbac_audit_log(user_id, username, "ROLE_UPDATE", username, true, NULL, "", PERM_SYSTEM_CONFIG);
    
    printf("RBAC: Updated user %u ('%s') role from %d to %d\n", user_id, username, old_role, new_role);
    return 0;
}

void rbac_audit_log(uint32_t user_id, const char* username, const char* action,
                   const char* resource, bool success, const char* failure_reason,
                   const char* client_ip, agent_permission_t permission) {
    if (!g_security) {
        return;
    }
    
    pthread_rwlock_wrlock(&g_security->audit_lock);
    
    // Find next slot (circular buffer)
    uint32_t next_index = (g_security->audit_tail + 1) % 8192;
    
    if (next_index == g_security->audit_head && g_security->audit_count == 8192) {
        // Buffer full, advance head
        g_security->audit_head = (g_security->audit_head + 1) % 8192;
    } else if (g_security->audit_count < 8192) {
        g_security->audit_count++;
    }
    
    // Add new audit entry
    rbac_audit_entry_t* entry = &g_security->audit_log[g_security->audit_tail];
    
    entry->audit_id = generate_audit_id();
    entry->user_id = user_id;
    entry->success = success;
    entry->timestamp_ns = get_timestamp_ns();
    entry->requested_permission = permission;
    
    if (username) {
        strncpy(entry->username, username, sizeof(entry->username) - 1);
        entry->username[sizeof(entry->username) - 1] = '\0';
    } else {
        strcpy(entry->username, "unknown");
    }
    
    if (action) {
        strncpy(entry->action, action, sizeof(entry->action) - 1);
        entry->action[sizeof(entry->action) - 1] = '\0';
    }
    
    if (resource) {
        strncpy(entry->resource, resource, sizeof(entry->resource) - 1);
        entry->resource[sizeof(entry->resource) - 1] = '\0';
    }
    
    if (failure_reason) {
        strncpy(entry->failure_reason, failure_reason, sizeof(entry->failure_reason) - 1);
        entry->failure_reason[sizeof(entry->failure_reason) - 1] = '\0';
    } else {
        entry->failure_reason[0] = '\0';
    }
    
    if (client_ip) {
        strncpy(entry->client_ip, client_ip, sizeof(entry->client_ip) - 1);
        entry->client_ip[sizeof(entry->client_ip) - 1] = '\0';
    } else {
        entry->client_ip[0] = '\0';
    }
    
    g_security->audit_tail = next_index;
    
    pthread_rwlock_unlock(&g_security->audit_lock);
}

// Helper function to get agent permission name
const char* get_permission_name(agent_permission_t permission) {
    static const char* permission_names[] = {
        "DIRECTOR", "PROJECT_ORCHESTRATOR", "ARCHITECT", "CONSTRUCTOR",
        "PATCHER", "DEBUGGER", "TESTBED", "LINTER", "OPTIMIZER",
        "SECURITY", "BASTION", "SECURITY_CHAOS", "OVERSIGHT",
        "INFRASTRUCTURE", "DEPLOYER", "MONITOR", "PACKAGER",
        "API_DESIGNER", "DATABASE", "WEB", "MOBILE", "PYGUI", "TUI",
        "DATA_SCIENCE", "MLOPS", "DOCGEN", "RESEARCHER",
        "C_INTERNAL", "PYTHON_INTERNAL", "SYSTEM_CONFIG", "SYSTEM_SHUTDOWN"
    };
    
    if (permission < sizeof(permission_names) / sizeof(permission_names[0])) {
        return permission_names[permission];
    }
    return "UNKNOWN";
}

// Helper function to get role name
const char* get_role_name(rbac_role_t role) {
    static const char* role_names[] = {"GUEST", "USER", "OPERATOR", "ADMIN"};
    if (role < 4) {
        return role_names[role];
    }
    return "UNKNOWN";
}

void print_rbac_statistics() {
    if (!g_security) {
        printf("Security service not initialized\n");
        return;
    }
    
    printf("\n=== RBAC System Statistics ===\n");
    
    // User statistics
    pthread_rwlock_rdlock(&g_security->users_lock);
    
    uint32_t active_users = 0;
    uint32_t locked_users = 0;
    uint32_t role_counts[4] = {0};
    
    for (uint32_t i = 0; i < g_security->user_count; i++) {
        if (g_security->users[i].active) {
            active_users++;
            if (g_security->users[i].role < 4) {
                role_counts[g_security->users[i].role]++;
            }
        }
        if (g_security->users[i].locked) {
            locked_users++;
        }
    }
    
    printf("Total users: %u\n", g_security->user_count);
    printf("Active users: %u\n", active_users);
    printf("Locked users: %u\n", locked_users);
    
    printf("\nUsers by role:\n");
    for (int i = 0; i < 4; i++) {
        printf("  %s: %u\n", get_role_name((rbac_role_t)i), role_counts[i]);
    }
    
    pthread_rwlock_unlock(&g_security->users_lock);
    
    // Session statistics
    pthread_rwlock_rdlock(&g_security->sessions_lock);
    
    uint32_t active_sessions = 0;
    uint64_t current_time = get_timestamp_ns();
    
    for (uint32_t i = 0; i < g_security->session_count; i++) {
        if (g_security->sessions[i].active && current_time <= g_security->sessions[i].expires_ns) {
            active_sessions++;
        }
    }
    
    printf("\nSession statistics:\n");
    printf("Total sessions: %u\n", g_security->session_count);
    printf("Active sessions: %u\n", active_sessions);
    
    pthread_rwlock_unlock(&g_security->sessions_lock);
    
    // Permission matrix
    printf("\nRole Permission Matrix:\n");
    printf("%-12s %-40s %-12s\n", "Role", "Description", "Permissions");
    printf("%-12s %-40s %-12s\n", "------------", "----------------------------------------", "------------");
    
    for (int i = 0; i < 4; i++) {
        uint32_t perm_count = __builtin_popcount(g_security->role_matrix[i].permission_mask);
        printf("%-12s %-40s %-12u\n", 
               get_role_name((rbac_role_t)i),
               g_security->role_matrix[i].description,
               perm_count);
    }
    
    // Recent audit entries
    printf("\nRecent audit log entries:\n");
    printf("%-8s %-16s %-16s %-20s %-8s %-20s\n", 
           "ID", "Username", "Action", "Resource", "Success", "Permission");
    printf("%-8s %-16s %-16s %-20s %-8s %-20s\n", 
           "--------", "----------------", "----------------", "--------------------", 
           "--------", "--------------------");
    
    pthread_rwlock_rdlock(&g_security->audit_lock);
    
    uint32_t entries_to_show = g_security->audit_count < 10 ? g_security->audit_count : 10;
    uint32_t start_index = g_security->audit_count > 10 ? 
                          (g_security->audit_tail + 8192 - 10) % 8192 : 
                          g_security->audit_head;
    
    for (uint32_t i = 0; i < entries_to_show; i++) {
        uint32_t index = (start_index + i) % 8192;
        rbac_audit_entry_t* entry = &g_security->audit_log[index];
        
        printf("%-8u %-16s %-16s %-20s %-8s %-20s\n",
               entry->audit_id, entry->username, entry->action, entry->resource,
               entry->success ? "Yes" : "No", get_permission_name(entry->requested_permission));
    }
    
    pthread_rwlock_unlock(&g_security->audit_lock);
    
    printf("\n");
}

// ============================================================================
// VULNERABILITY MANAGEMENT
// ============================================================================

uint32_t report_vulnerability(const char* title, const char* description,
                             vulnerability_severity_t severity, const char* file_path,
                             uint32_t line_number, const char* cve_id) {
    if (!g_security || !title) {
        return 0;
    }
    
    pthread_rwlock_wrlock(&g_security->vulnerabilities_lock);
    
    if (g_security->vulnerability_count >= MAX_VULNERABILITIES) {
        pthread_rwlock_unlock(&g_security->vulnerabilities_lock);
        return 0;
    }
    
    // Find free slot
    vulnerability_record_t* vuln = &g_security->vulnerabilities[g_security->vulnerability_count];
    
    // Initialize vulnerability record
    vuln->vuln_id = generate_vulnerability_id();
    strncpy(vuln->title, title, sizeof(vuln->title) - 1);
    vuln->title[sizeof(vuln->title) - 1] = '\0';
    
    if (description) {
        strncpy(vuln->description, description, sizeof(vuln->description) - 1);
        vuln->description[sizeof(vuln->description) - 1] = '\0';
    }
    
    vuln->severity = severity;
    vuln->discovered_time_ns = get_timestamp_ns();
    vuln->last_seen_ns = vuln->discovered_time_ns;
    vuln->line_number = line_number;
    vuln->occurrence_count = 1;
    
    if (file_path) {
        strncpy(vuln->file_path, file_path, sizeof(vuln->file_path) - 1);
        vuln->file_path[sizeof(vuln->file_path) - 1] = '\0';
    }
    
    if (cve_id) {
        strncpy(vuln->cve_id, cve_id, sizeof(vuln->cve_id) - 1);
        vuln->cve_id[sizeof(vuln->cve_id) - 1] = '\0';
    }
    
    // Set exploitability characteristics
    vuln->remote_exploitable = (rand() % 100) < 30;  // 30% chance
    vuln->publicly_exploitable = (rand() % 100) < 15; // 15% chance  
    vuln->exploitability_score = 0.3f + ((float)(rand() % 70) / 100.0f); // 0.3-1.0
    
    // Calculate CVSS score
    vuln->cvss_score = calculate_cvss_score(severity, vuln->remote_exploitable,
                                           vuln->publicly_exploitable);
    
    vuln->verified = false;
    vuln->false_positive = false;
    vuln->has_patch = (rand() % 100) < 60;  // 60% have patches available
    
    // Set detection method
    strcpy(vuln->detection_method, "Static Analysis");
    strcpy(vuln->scanner_name, "Security Agent");
    strcpy(vuln->scanner_version, "1.0");
    
    g_security->vulnerability_count++;
    
    // Update metrics
    atomic_fetch_add(&g_security->metrics.vulnerabilities_discovered, 1);
    
    if (severity == VULN_SEVERITY_CRITICAL) {
        atomic_fetch_add(&g_security->metrics.critical_vulnerabilities, 1);
    } else if (severity == VULN_SEVERITY_HIGH) {
        atomic_fetch_add(&g_security->metrics.high_vulnerabilities, 1);
    }
    
    uint32_t vuln_id = vuln->vuln_id;
    
    pthread_rwlock_unlock(&g_security->vulnerabilities_lock);
    
    printf("Security: Reported %s vulnerability '%s' (ID: %u, CVSS: %.1f)\n",
           severity == VULN_SEVERITY_CRITICAL ? "CRITICAL" :
           severity == VULN_SEVERITY_HIGH ? "HIGH" :
           severity == VULN_SEVERITY_MEDIUM ? "MEDIUM" :
           severity == VULN_SEVERITY_LOW ? "LOW" : "INFO",
           title, vuln_id, vuln->cvss_score);
    
    // Create security event
    log_security_event(EVENT_VULNERABILITY_FOUND, "Security Agent", file_path ? file_path : "unknown",
                      title, severity, calculate_risk_score(vuln));
    
    // Create incident if severity is high enough
    if (severity <= VULN_SEVERITY_HIGH || vuln->cvss_score >= g_security->risk_tolerance_threshold) {
        char incident_title[256];
        snprintf(incident_title, sizeof(incident_title), "High-Risk Vulnerability: %s", title);
        
        char incident_desc[2048];
        snprintf(incident_desc, sizeof(incident_desc),
                "Critical vulnerability discovered:\nTitle: %s\nFile: %s\nLine: %u\nCVSS: %.1f\nDescription: %s",
                title, file_path ? file_path : "N/A", line_number, vuln->cvss_score,
                description ? description : "N/A");
        
        create_security_incident(incident_title, incident_desc, severity, false);
    }
    
    return vuln_id;
}

int run_vulnerability_scan(const char* target_path, security_scan_type_t scan_type) {
    if (!g_security || !target_path) {
        return -EINVAL;
    }
    
    printf("Security: Starting %s vulnerability scan on '%s'\n",
           scan_type == SCAN_TYPE_STATIC_CODE ? "static code" :
           scan_type == SCAN_TYPE_DYNAMIC_ANALYSIS ? "dynamic analysis" :
           scan_type == SCAN_TYPE_DEPENDENCY_CHECK ? "dependency" : "general",
           target_path);
    
    // Simulate vulnerability scan
    uint32_t vulnerabilities_found = 0;
    uint32_t scan_duration_ms = 5000 + (rand() % 15000); // 5-20 seconds
    
    uint64_t scan_start = get_timestamp_ns();
    
    // Simulate scanning with progress updates
    for (int progress = 0; progress <= 100; progress += 20) {
        usleep(scan_duration_ms * 1000 / 5);  // Spread over scan duration
        
        if (progress > 0 && (rand() % 100) < 25) {  // 25% chance to find vulnerability
            vulnerability_severity_t severity = (vulnerability_severity_t)(rand() % 5);
            
            char vuln_title[256];
            char vuln_desc[512];
            
            switch (scan_type) {
                case SCAN_TYPE_STATIC_CODE:
                    snprintf(vuln_title, sizeof(vuln_title), "Code Security Issue #%d", rand() % 1000);
                    strcpy(vuln_desc, "Potential security vulnerability detected in source code");
                    break;
                case SCAN_TYPE_DEPENDENCY_CHECK:
                    snprintf(vuln_title, sizeof(vuln_title), "Vulnerable Dependency #%d", rand() % 1000);
                    strcpy(vuln_desc, "Known vulnerability in external dependency");
                    break;
                case SCAN_TYPE_CONTAINER_SCAN:
                    snprintf(vuln_title, sizeof(vuln_title), "Container Security Issue #%d", rand() % 1000);
                    strcpy(vuln_desc, "Security vulnerability in container image");
                    break;
                default:
                    snprintf(vuln_title, sizeof(vuln_title), "Security Issue #%d", rand() % 1000);
                    strcpy(vuln_desc, "Security vulnerability detected");
                    break;
            }
            
            uint32_t vuln_id = report_vulnerability(vuln_title, vuln_desc, severity,
                                                   target_path, rand() % 1000, NULL);
            if (vuln_id > 0) {
                vulnerabilities_found++;
            }
        }
    }
    
    uint64_t scan_end = get_timestamp_ns();
    uint32_t actual_duration = (scan_end - scan_start) / 1000000; // Convert to ms
    
    atomic_fetch_add(&g_security->metrics.scans_performed, 1);
    
    printf("Security: Completed vulnerability scan in %ums, found %u vulnerabilities\n",
           actual_duration, vulnerabilities_found);
    
    // Log scan completion event
    char event_desc[512];
    snprintf(event_desc, sizeof(event_desc), 
            "Vulnerability scan completed: %u vulnerabilities found in %ums",
            vulnerabilities_found, actual_duration);
    
    log_security_event(EVENT_SCAN_COMPLETED, "Security Agent", target_path, event_desc,
                      VULN_SEVERITY_INFO, 0.0f);
    
    return vulnerabilities_found;
}

// ============================================================================
// THREAT DETECTION AND MANAGEMENT
// ============================================================================

uint32_t report_threat(const char* threat_name, const char* description,
                      threat_level_t level, const char* category) {
    if (!g_security || !threat_name) {
        return 0;
    }
    
    pthread_rwlock_wrlock(&g_security->threats_lock);
    
    if (g_security->threat_count >= MAX_THREATS) {
        pthread_rwlock_unlock(&g_security->threats_lock);
        return 0;
    }
    
    // Find free slot
    threat_record_t* threat = &g_security->threats[g_security->threat_count];
    
    // Initialize threat record
    threat->threat_id = generate_threat_id();
    strncpy(threat->threat_name, threat_name, sizeof(threat->threat_name) - 1);
    threat->threat_name[sizeof(threat->threat_name) - 1] = '\0';
    
    if (description) {
        strncpy(threat->description, description, sizeof(threat->description) - 1);
        threat->description[sizeof(threat->description) - 1] = '\0';
    }
    
    threat->level = level;
    threat->first_seen_ns = get_timestamp_ns();
    threat->last_activity_ns = threat->first_seen_ns;
    threat->active = true;
    threat->confidence_score = 0.7f + ((float)(rand() % 30) / 100.0f); // 0.7-1.0
    
    if (category) {
        strncpy(threat->category, category, sizeof(threat->category) - 1);
        threat->category[sizeof(threat->category) - 1] = '\0';
    }
    
    strcpy(threat->source, "Security Agent");
    threat->indicator_count = 0;
    
    g_security->threat_count++;
    
    // Update metrics
    atomic_fetch_add(&g_security->metrics.threats_detected, 1);
    atomic_fetch_add(&g_security->metrics.active_threats, 1);
    
    uint32_t threat_id = threat->threat_id;
    
    pthread_rwlock_unlock(&g_security->threats_lock);
    
    printf("Security: Reported %s threat '%s' (ID: %u, Confidence: %.1f%%)\n",
           level == THREAT_LEVEL_CRITICAL ? "CRITICAL" :
           level == THREAT_LEVEL_HIGH ? "HIGH" :
           level == THREAT_LEVEL_MEDIUM ? "MEDIUM" :
           level == THREAT_LEVEL_LOW ? "LOW" : "INFO",
           threat_name, threat_id, threat->confidence_score * 100.0f);
    
    // Create security event
    log_security_event(EVENT_THREAT_DETECTED, "Security Agent", "system",
                      threat_name, (vulnerability_severity_t)level, threat->confidence_score * 10.0f);
    
    // Create incident for high-level threats
    if (level <= THREAT_LEVEL_HIGH) {
        char incident_title[256];
        snprintf(incident_title, sizeof(incident_title), "Security Threat: %s", threat_name);
        
        char incident_desc[2048];
        snprintf(incident_desc, sizeof(incident_desc),
                "High-priority security threat detected:\nThreat: %s\nCategory: %s\nConfidence: %.1f%%\nDescription: %s",
                threat_name, category ? category : "Unknown", threat->confidence_score * 100.0f,
                description ? description : "N/A");
        
        create_security_incident(incident_title, incident_desc, (vulnerability_severity_t)level, true);
    }
    
    return threat_id;
}

// ============================================================================
// INCIDENT MANAGEMENT
// ============================================================================

uint32_t create_security_incident(const char* title, const char* description,
                                 vulnerability_severity_t severity, bool confirmed) {
    if (!g_security || !title) {
        return 0;
    }
    
    pthread_rwlock_wrlock(&g_security->incidents_lock);
    
    if (g_security->incident_count >= MAX_INCIDENTS) {
        pthread_rwlock_unlock(&g_security->incidents_lock);
        return 0;
    }
    
    // Find free slot
    security_incident_t* incident = &g_security->incidents[g_security->incident_count];
    
    // Initialize incident
    incident->incident_id = generate_incident_id();
    strncpy(incident->title, title, sizeof(incident->title) - 1);
    incident->title[sizeof(incident->title) - 1] = '\0';
    
    if (description) {
        strncpy(incident->description, description, sizeof(incident->description) - 1);
        incident->description[sizeof(incident->description) - 1] = '\0';
    }
    
    incident->severity = severity;
    incident->confirmed = confirmed;
    incident->created_time_ns = get_timestamp_ns();
    incident->first_event_ns = incident->created_time_ns;
    incident->last_event_ns = incident->created_time_ns;
    incident->state = INCIDENT_STATE_NEW;
    incident->evidence_count = 0;
    incident->data_breach = false;
    
    strcpy(incident->assigned_to, "Security Team");
    
    g_security->incident_count++;
    
    // Update metrics
    atomic_fetch_add(&g_security->metrics.incidents_created, 1);
    
    uint32_t incident_id = incident->incident_id;
    
    pthread_rwlock_unlock(&g_security->incidents_lock);
    
    printf("Security: Created %s incident '%s' (ID: %u)\n",
           severity == VULN_SEVERITY_CRITICAL ? "CRITICAL" :
           severity == VULN_SEVERITY_HIGH ? "HIGH" :
           severity == VULN_SEVERITY_MEDIUM ? "MEDIUM" : "LOW",
           title, incident_id);
    
    // Log incident creation event
    log_security_event(EVENT_INCIDENT_CREATED, "Security Agent", "system", title,
                      severity, severity == VULN_SEVERITY_CRITICAL ? 10.0f : 
                               severity == VULN_SEVERITY_HIGH ? 8.0f : 5.0f);
    
    return incident_id;
}

// ============================================================================
// SECURITY EVENT LOGGING
// ============================================================================

void log_security_event(security_event_type_t type, const char* source, const char* target,
                        const char* description, vulnerability_severity_t severity, float risk_score) {
    if (!g_security) {
        return;
    }
    
    pthread_rwlock_wrlock(&g_security->events_lock);
    
    // Find next slot (circular buffer)
    uint32_t next_index = (g_security->event_tail + 1) % MAX_SECURITY_EVENTS;
    
    if (next_index == g_security->event_head && g_security->event_count == MAX_SECURITY_EVENTS) {
        // Buffer full, advance head to overwrite oldest event
        g_security->event_head = (g_security->event_head + 1) % MAX_SECURITY_EVENTS;
    } else if (g_security->event_count < MAX_SECURITY_EVENTS) {
        g_security->event_count++;
    }
    
    // Add new event
    security_event_t* event = &g_security->events[g_security->event_tail];
    
    event->event_id = generate_event_id();
    event->type = type;
    event->timestamp_ns = get_timestamp_ns();
    event->severity = severity;
    event->risk_score = risk_score;
    event->correlation_id = 0;  // Could be set for related events
    event->correlated = false;
    
    if (source) {
        strncpy(event->source, source, sizeof(event->source) - 1);
        event->source[sizeof(event->source) - 1] = '\0';
    }
    
    if (target) {
        strncpy(event->target, target, sizeof(event->target) - 1);
        event->target[sizeof(event->target) - 1] = '\0';
    }
    
    if (description) {
        strncpy(event->description, description, sizeof(event->description) - 1);
        event->description[sizeof(event->description) - 1] = '\0';
    }
    
    g_security->event_tail = next_index;
    
    pthread_rwlock_unlock(&g_security->events_lock);
}

// ============================================================================
// WORKER THREADS
// ============================================================================

static void* vulnerability_scanner_thread(void* arg) {
    (void)arg;
    
    pthread_setname_np(pthread_self(), "vuln_scanner");
    
    while (g_security->running) {
        // Periodic vulnerability scanning
        sleep(300);  // Every 5 minutes
        
        if (!g_security->running) break;
        
        // Simulate periodic scans
        const char* scan_targets[] = {
            "/src/core",
            "/src/api", 
            "/src/web",
            "/config",
            "/dependencies"
        };
        
        int target_index = rand() % 5;
        security_scan_type_t scan_type = (security_scan_type_t)(1 + (rand() % 3)); // 1-3
        
        run_vulnerability_scan(scan_targets[target_index], scan_type);
    }
    
    return NULL;
}

static void* threat_monitor_thread(void* arg) {
    (void)arg;
    
    pthread_setname_np(pthread_self(), "threat_monitor");
    
    while (g_security->running) {
        // Periodic threat detection
        sleep(120);  // Every 2 minutes
        
        if (!g_security->running) break;
        
        // Simulate threat detection
        if ((rand() % 100) < 5) {  // 5% chance each cycle
            const char* threat_types[] = {
                "Suspicious Network Activity",
                "Malware Detected",
                "Brute Force Attack",
                "Data Exfiltration Attempt",
                "Privilege Escalation"
            };
            
            const char* threat_categories[] = {
                "network_intrusion",
                "malware",
                "brute_force",
                "data_breach",
                "privilege_escalation"
            };
            
            int threat_index = rand() % 5;
            threat_level_t level = (threat_level_t)(rand() % 4);  // 0-3 (exclude INFO)
            
            report_threat(threat_types[threat_index],
                         "Automated threat detection system identified suspicious activity",
                         level, threat_categories[threat_index]);
        }
    }
    
    return NULL;
}

int start_security_threads() {
    if (!g_security) {
        return -EINVAL;
    }
    
    // Start vulnerability scanner thread
    int ret = pthread_create(&g_security->vulnerability_scanner_thread, NULL,
                           vulnerability_scanner_thread, NULL);
    if (ret != 0) {
        printf("Security: Failed to start vulnerability scanner thread: %s\n", strerror(ret));
        return ret;
    }
    
    // Start threat monitor thread
    ret = pthread_create(&g_security->threat_monitor_thread, NULL,
                        threat_monitor_thread, NULL);
    if (ret != 0) {
        printf("Security: Failed to start threat monitor thread: %s\n", strerror(ret));
        return ret;
    }
    
    printf("Security: Started monitoring threads\n");
    return 0;
}

// ============================================================================
// STATISTICS AND REPORTING
// ============================================================================

void print_security_statistics() {
    if (!g_security) {
        printf("Security service not initialized\n");
        return;
    }
    
    printf("\n=== Security Service Statistics ===\n");
    printf("Vulnerabilities discovered: %lu\n", atomic_load(&g_security->metrics.vulnerabilities_discovered));
    printf("Vulnerabilities fixed: %lu\n", atomic_load(&g_security->metrics.vulnerabilities_fixed));
    printf("Threats detected: %lu\n", atomic_load(&g_security->metrics.threats_detected));
    printf("Threats mitigated: %lu\n", atomic_load(&g_security->metrics.threats_mitigated));
    printf("Security scans performed: %lu\n", atomic_load(&g_security->metrics.scans_performed));
    printf("Incidents created: %lu\n", atomic_load(&g_security->metrics.incidents_created));
    printf("Incidents resolved: %lu\n", atomic_load(&g_security->metrics.incidents_resolved));
    printf("Critical vulnerabilities: %u\n", atomic_load(&g_security->metrics.critical_vulnerabilities));
    printf("High vulnerabilities: %u\n", atomic_load(&g_security->metrics.high_vulnerabilities));
    printf("Active threats: %u\n", atomic_load(&g_security->metrics.active_threats));
    printf("Security posture score: %.1f%%\n", g_security->metrics.security_posture_score);
    
    // Vulnerability summary
    printf("\nVulnerabilities by Severity:\n");
    printf("%-12s %-8s %-8s %-10s %-15s\n", "Severity", "Count", "CVSS", "Remote", "Patch Available");
    printf("%-12s %-8s %-8s %-10s %-15s\n", "------------", "--------", "--------", "----------", "---------------");
    
    pthread_rwlock_rdlock(&g_security->vulnerabilities_lock);
    
    uint32_t severity_counts[5] = {0};
    uint32_t remote_exploitable[5] = {0};
    uint32_t patches_available[5] = {0};
    float avg_cvss[5] = {0};
    uint32_t cvss_count[5] = {0};
    
    for (uint32_t i = 0; i < g_security->vulnerability_count; i++) {
        vulnerability_record_t* vuln = &g_security->vulnerabilities[i];
        
        severity_counts[vuln->severity]++;
        if (vuln->remote_exploitable) remote_exploitable[vuln->severity]++;
        if (vuln->has_patch) patches_available[vuln->severity]++;
        avg_cvss[vuln->severity] += vuln->cvss_score;
        cvss_count[vuln->severity]++;
    }
    
    const char* severity_names[] = {"Critical", "High", "Medium", "Low", "Info"};
    
    for (int i = 0; i < 5; i++) {
        float avg_score = cvss_count[i] > 0 ? avg_cvss[i] / cvss_count[i] : 0.0f;
        
        printf("%-12s %-8u %-8.1f %-10u %-15u\n",
               severity_names[i], severity_counts[i], avg_score,
               remote_exploitable[i], patches_available[i]);
    }
    
    pthread_rwlock_unlock(&g_security->vulnerabilities_lock);
    
    // Threat summary
    printf("\nActive Threats:\n");
    printf("%-8s %-30s %-12s %-12s %-10s\n", "ID", "Name", "Level", "Category", "Confidence");
    printf("%-8s %-30s %-12s %-12s %-10s\n", "--------", "------------------------------",
           "------------", "------------", "----------");
    
    pthread_rwlock_rdlock(&g_security->threats_lock);
    
    for (uint32_t i = 0; i < g_security->threat_count && i < 10; i++) {  // Show top 10
        threat_record_t* threat = &g_security->threats[i];
        
        if (!threat->active) continue;
        
        const char* level_str = threat->level == THREAT_LEVEL_CRITICAL ? "Critical" :
                               threat->level == THREAT_LEVEL_HIGH ? "High" :
                               threat->level == THREAT_LEVEL_MEDIUM ? "Medium" :
                               threat->level == THREAT_LEVEL_LOW ? "Low" : "Info";
        
        printf("%-8u %-30s %-12s %-12s %-9.1f%%\n",
               threat->threat_id, threat->threat_name, level_str,
               threat->category, threat->confidence_score * 100.0f);
    }
    
    pthread_rwlock_unlock(&g_security->threats_lock);
    
    // Recent incidents
    printf("\nRecent Security Incidents:\n");
    printf("%-8s %-30s %-12s %-12s\n", "ID", "Title", "Severity", "State");
    printf("%-8s %-30s %-12s %-12s\n", "--------", "------------------------------",
           "------------", "------------");
    
    pthread_rwlock_rdlock(&g_security->incidents_lock);
    
    for (uint32_t i = 0; i < g_security->incident_count && i < 10; i++) {  // Show recent 10
        security_incident_t* incident = &g_security->incidents[i];
        
        const char* severity_str = incident->severity == VULN_SEVERITY_CRITICAL ? "Critical" :
                                  incident->severity == VULN_SEVERITY_HIGH ? "High" :
                                  incident->severity == VULN_SEVERITY_MEDIUM ? "Medium" : "Low";
        
        const char* state_str = incident->state == INCIDENT_STATE_NEW ? "New" :
                               incident->state == INCIDENT_STATE_ASSIGNED ? "Assigned" :
                               incident->state == INCIDENT_STATE_INVESTIGATING ? "Investigating" :
                               incident->state == INCIDENT_STATE_RESOLVED ? "Resolved" : "Closed";
        
        printf("%-8u %-30s %-12s %-12s\n",
               incident->incident_id, incident->title, severity_str, state_str);
    }
    
    pthread_rwlock_unlock(&g_security->incidents_lock);
    
    printf("\n");
}

// ============================================================================
// EXAMPLE USAGE AND TESTING
// ============================================================================

#ifdef SECURITY_TEST_MODE

int main() {
    printf("Security Agent Test\n");
    printf("==================\n");
    
    // Initialize security service
    if (security_service_init() != 0) {
        printf("Failed to initialize security service\n");
        return 1;
    }
    
    // Start security monitoring threads
    if (start_security_threads() != 0) {
        printf("Failed to start security threads\n");
        return 1;
    }
    
    // Simulate some security activities
    printf("\nSimulating security activities...\n");
    
    // Report some test vulnerabilities
    report_vulnerability("Buffer Overflow in Authentication", 
                        "Potential buffer overflow vulnerability in user authentication module",
                        VULN_SEVERITY_CRITICAL, "/src/auth.c", 247, "CVE-2023-1234");
    
    report_vulnerability("SQL Injection in User Query",
                        "Unsanitized user input in database query could lead to SQL injection",
                        VULN_SEVERITY_HIGH, "/src/database.c", 156, NULL);
    
    report_vulnerability("Information Disclosure in Logs",
                        "Sensitive information being logged in application logs",
                        VULN_SEVERITY_MEDIUM, "/src/logging.c", 89, NULL);
    
    // Report some threats
    report_threat("Suspicious Login Pattern",
                 "Multiple failed login attempts from unknown IP addresses",
                 THREAT_LEVEL_HIGH, "brute_force");
    
    report_threat("Malicious File Upload",
                 "Potentially malicious file uploaded through web interface", 
                 THREAT_LEVEL_CRITICAL, "malware");
    
    // Run some vulnerability scans
    run_vulnerability_scan("/src", SCAN_TYPE_STATIC_CODE);
    run_vulnerability_scan("/dependencies", SCAN_TYPE_DEPENDENCY_CHECK);
    run_vulnerability_scan("/containers", SCAN_TYPE_CONTAINER_SCAN);
    
    // Let threads run for a while
    printf("\nMonitoring security events for 30 seconds...\n");
    
    for (int i = 0; i < 30; i++) {
        sleep(1);
        
        if (i % 10 == 9) {  // Print stats every 10 seconds
            print_security_statistics();
        }
    }
    
    // Test RBAC system
    printf("\nTesting RBAC system...\n");
    
    // Create test users
    create_user("developer", "dev123", RBAC_ROLE_USER);
    create_user("operator", "op123", RBAC_ROLE_OPERATOR);
    create_user("guest_user", "guest123", RBAC_ROLE_GUEST);
    
    // Test authentication and sessions
    char session_token[SESSION_TOKEN_SIZE];
    
    printf("\nTesting authentication...\n");
    if (authenticate_user("developer", "dev123", "192.168.1.100", "TestClient/1.0", 
                         session_token, SESSION_TOKEN_SIZE) == 0) {
        printf("Developer authentication successful\n");
        
        // Test permissions
        printf("Testing permissions for developer:\n");
        
        // Should have access to architect
        if (check_permission(session_token, PERM_AGENT_ARCHITECT, "test_resource", "192.168.1.100") == 0) {
            printf("  - ARCHITECT access: GRANTED\n");
        } else {
            printf("  - ARCHITECT access: DENIED\n");
        }
        
        // Should NOT have access to director
        if (check_permission(session_token, PERM_AGENT_DIRECTOR, "test_resource", "192.168.1.100") == 0) {
            printf("  - DIRECTOR access: GRANTED\n");
        } else {
            printf("  - DIRECTOR access: DENIED (correct)\n");
        }
        
        // Should NOT have access to system shutdown
        if (check_permission(session_token, PERM_SYSTEM_SHUTDOWN, "test_resource", "192.168.1.100") == 0) {
            printf("  - SYSTEM_SHUTDOWN access: GRANTED\n");
        } else {
            printf("  - SYSTEM_SHUTDOWN access: DENIED (correct)\n");
        }
    }
    
    // Test operator permissions
    char op_session_token[SESSION_TOKEN_SIZE];
    if (authenticate_user("operator", "op123", "192.168.1.101", "TestClient/1.0", 
                         op_session_token, SESSION_TOKEN_SIZE) == 0) {
        printf("\nTesting operator permissions:\n");
        
        // Should have access to security
        if (check_permission(op_session_token, PERM_AGENT_SECURITY, "security_ops", "192.168.1.101") == 0) {
            printf("  - SECURITY access: GRANTED\n");
        } else {
            printf("  - SECURITY access: DENIED\n");
        }
        
        // Should have access to infrastructure
        if (check_permission(op_session_token, PERM_AGENT_INFRASTRUCTURE, "infra_ops", "192.168.1.101") == 0) {
            printf("  - INFRASTRUCTURE access: GRANTED\n");
        } else {
            printf("  - INFRASTRUCTURE access: DENIED\n");
        }
        
        // Should NOT have access to system shutdown (admin only)
        if (check_permission(op_session_token, PERM_SYSTEM_SHUTDOWN, "shutdown_ops", "192.168.1.101") == 0) {
            printf("  - SYSTEM_SHUTDOWN access: GRANTED\n");
        } else {
            printf("  - SYSTEM_SHUTDOWN access: DENIED (correct)\n");
        }
    }
    
    // Test admin permissions
    char admin_session_token[SESSION_TOKEN_SIZE];
    if (authenticate_user("admin", "admin123", "192.168.1.1", "TestClient/1.0", 
                         admin_session_token, SESSION_TOKEN_SIZE) == 0) {
        printf("\nTesting admin permissions:\n");
        
        // Should have access to everything
        if (check_permission(admin_session_token, PERM_SYSTEM_SHUTDOWN, "shutdown_ops", "192.168.1.1") == 0) {
            printf("  - SYSTEM_SHUTDOWN access: GRANTED\n");
        } else {
            printf("  - SYSTEM_SHUTDOWN access: DENIED\n");
        }
        
        if (check_permission(admin_session_token, PERM_AGENT_DIRECTOR, "director_ops", "192.168.1.1") == 0) {
            printf("  - DIRECTOR access: GRANTED\n");
        } else {
            printf("  - DIRECTOR access: DENIED\n");
        }
    }
    
    // Test role updates
    printf("\nTesting role updates...\n");
    uint32_t dev_user_id = 2; // Should be the developer user
    if (update_user_role(dev_user_id, RBAC_ROLE_OPERATOR) == 0) {
        printf("Successfully updated developer to operator role\n");
    }
    
    // Print RBAC statistics
    print_rbac_statistics();
    
    // Final statistics
    print_security_statistics();
    
    // Cleanup
    security_service_cleanup();
    
    return 0;
}

#endif