/*
 * DIRECTOR AGENT
 * 
 * Main orchestrator for the Claude Agent Communication System
 * - Strategic planning and execution coordination
 * - Multi-agent workflow orchestration
 * - Resource allocation and load balancing
 * - Cross-agent dependency management
 * - Performance monitoring and optimization
 * - Emergency response coordination
 * 
 * Integrates with discovery service, message router, and all other agents
 * 
 * Author: Agent Communication System
 * Version: 1.0 Production
 */

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

// Include headers
#include "agent_protocol.h"

// Include advanced features when enabled
#ifdef ENABLE_STREAMING_PIPELINE
extern int streaming_pipeline_init(uint32_t partition_count, const char* kafka_brokers, const char* topic);
extern void streaming_pipeline_start(void);
extern void streaming_pipeline_shutdown(void);
#endif

#ifdef ENABLE_NEURAL_SEARCH
extern int nas_init(void);
extern void nas_get_stats(uint32_t* architectures_evaluated, double* best_fitness, uint32_t* generation);
extern void nas_shutdown(void);
#endif

#ifdef ENABLE_DIGITAL_TWIN
extern int digital_twin_init(void);
extern void* digital_twin_create(const char* name, int type);
extern void digital_twin_get_stats(uint64_t* total_syncs, double* avg_latency_ms, uint64_t* predictions, uint64_t* anomalies);
extern void digital_twin_shutdown(void);
#endif

#ifdef ENABLE_MULTIMODAL_FUSION
extern int multimodal_fusion_init(void);
extern void* fusion_create_instance(int strategy);
extern int fusion_process(void* fusion);
extern void multimodal_fusion_shutdown(void);
#endif

// Forward declare external functions
extern int discovery_service_init();
extern void discovery_service_cleanup();
extern int register_agent(const char* name, int type, uint32_t instance_id,
                         const void* capabilities, uint32_t capability_count,
                         const void* endpoints, uint32_t endpoint_count);
extern void* discover_agent_by_name(const char* name);
extern void* discover_agent_by_type(int type);
extern int router_service_init();
extern void router_service_cleanup();
extern int create_topic(const char* topic_name, int strategy, bool persistent);
extern int subscribe_to_topic(const char* topic_name, uint32_t agent_id, const char* agent_name);
extern int publish_to_topic(const char* topic_name, uint32_t source_agent_id,
                           const void* payload, size_t payload_size, int priority);

// ============================================================================
// CONSTANTS AND CONFIGURATION
// ============================================================================

#define DIRECTOR_AGENT_ID 1
#define MAX_EXECUTION_PLANS 64
#define MAX_PLAN_STEPS 128
#define MAX_ACTIVE_WORKFLOWS 32
#define MAX_RESOURCE_POOLS 16
#define MAX_AGENT_CAPABILITIES 256
#define DIRECTOR_HEARTBEAT_INTERVAL_MS 1000
#define PLAN_EXECUTION_TIMEOUT_MS 300000  // 5 minutes
#define CACHE_LINE_SIZE 64

// Advanced feature integration flags
#define ENABLE_STREAMING_PIPELINE 1
#define ENABLE_NEURAL_SEARCH 1
#define ENABLE_DIGITAL_TWIN 1
#define ENABLE_MULTIMODAL_FUSION 1

// Agent types (matching discovery service)
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

// Plan execution states
typedef enum {
    PLAN_STATE_PENDING = 0,
    PLAN_STATE_RUNNING = 1,
    PLAN_STATE_PAUSED = 2,
    PLAN_STATE_COMPLETED = 3,
    PLAN_STATE_FAILED = 4,
    PLAN_STATE_CANCELLED = 5
} plan_state_t;

// Step execution states
typedef enum {
    STEP_STATE_WAITING = 0,
    STEP_STATE_READY = 1,
    STEP_STATE_EXECUTING = 2,
    STEP_STATE_COMPLETED = 3,
    STEP_STATE_FAILED = 4,
    STEP_STATE_SKIPPED = 5
} step_state_t;

// Task priorities
typedef enum {
    TASK_PRIORITY_EMERGENCY = 0,
    TASK_PRIORITY_CRITICAL = 1,
    TASK_PRIORITY_HIGH = 2,
    TASK_PRIORITY_NORMAL = 3,
    TASK_PRIORITY_LOW = 4,
    TASK_PRIORITY_BACKGROUND = 5
} task_priority_t;

// ============================================================================
// DATA STRUCTURES
// ============================================================================

// Resource pool for agent allocation
typedef struct {
    char name[64];
    agent_type_t agent_type;
    uint32_t total_capacity;
    uint32_t available_capacity;
    uint32_t agents[32];  // Agent IDs
    uint32_t agent_count;
    float avg_load_factor;
    pthread_mutex_t lock;
} resource_pool_t;

// Execution plan step
typedef struct {
    uint32_t step_id;
    char name[128];
    char description[512];
    
    // Dependencies
    uint32_t dependencies[16];
    uint32_t dependency_count;
    
    // Agent assignment
    agent_type_t required_agent_type;
    uint32_t assigned_agent_id;
    char capability_required[64];
    
    // Execution details
    char action[64];
    char parameters[1024];
    uint32_t timeout_ms;
    task_priority_t priority;
    
    // State
    step_state_t state;
    uint64_t start_time_ns;
    uint64_t end_time_ns;
    int exit_code;
    char result[2048];
    char error_message[512];
    
    // Metrics
    uint32_t retry_count;
    uint32_t max_retries;
    float estimated_duration_ms;
    float actual_duration_ms;
    
} execution_step_t;

// Strategic execution plan
typedef struct __attribute__((aligned(CACHE_LINE_SIZE))) {
    uint32_t plan_id;
    char name[128];
    char description[1024];
    
    // Plan metadata
    uint64_t creation_time_ns;
    uint64_t start_time_ns;
    uint64_t end_time_ns;
    uint32_t creator_agent_id;
    task_priority_t priority;
    
    // Steps
    execution_step_t steps[MAX_PLAN_STEPS];
    uint32_t step_count;
    
    // State
    plan_state_t state;
    uint32_t current_step_index;
    uint32_t completed_steps;
    uint32_t failed_steps;
    
    // Execution context
    char context[2048];
    float progress_percentage;
    uint32_t estimated_completion_ms;
    
    // Resource allocation
    uint32_t allocated_resources[MAX_RESOURCE_POOLS];
    
    // Synchronization
    pthread_mutex_t lock;
    
} execution_plan_t;

// Agent capability descriptor
typedef struct {
    char name[64];
    float performance_rating;  // 0.0 - 1.0
    uint32_t concurrent_capacity;
    uint32_t current_load;
    bool available;
} agent_capability_t;

// Agent performance metrics
typedef struct __attribute__((aligned(CACHE_LINE_SIZE))) {
    _Atomic uint64_t tasks_completed;
    _Atomic uint64_t tasks_failed;
    _Atomic uint64_t total_execution_time_ms;
    _Atomic uint32_t avg_response_time_ms;
    _Atomic uint32_t current_load_percent;
    _Atomic uint32_t queue_depth;
    float reliability_score;
    float performance_score;
    uint64_t last_update_ns;
} agent_metrics_t;

// Director statistics
typedef struct __attribute__((aligned(CACHE_LINE_SIZE))) {
    _Atomic uint64_t plans_created;
    _Atomic uint64_t plans_completed;
    _Atomic uint64_t plans_failed;
    _Atomic uint64_t steps_executed;
    _Atomic uint64_t agents_coordinated;
    _Atomic uint64_t resources_allocated;
    _Atomic uint64_t emergency_responses;
    _Atomic uint32_t active_plans;
    _Atomic uint32_t active_workflows;
    double avg_plan_completion_time_ms;
    double system_efficiency_score;
} director_stats_t;

// Main Director service structure
typedef struct __attribute__((aligned(PAGE_SIZE))) {
    // Identity
    uint32_t agent_id;
    char name[64];
    bool initialized;
    volatile bool running;
    
    // Plans and workflows
    execution_plan_t execution_plans[MAX_EXECUTION_PLANS];
    uint32_t active_plan_count;
    pthread_rwlock_t plans_lock;
    
    // Resource management
    resource_pool_t resource_pools[MAX_RESOURCE_POOLS];
    uint32_t resource_pool_count;
    pthread_rwlock_t resources_lock;
    
    // Agent tracking
    agent_capability_t known_capabilities[MAX_AGENT_CAPABILITIES];
    uint32_t capability_count;
    agent_metrics_t agent_metrics[256];  // By agent ID
    
    // Execution threads
    pthread_t plan_executor_thread;
    pthread_t resource_monitor_thread;
    pthread_t heartbeat_thread;
    
    // Statistics
    director_stats_t stats;
    
    // Configuration
    uint32_t max_concurrent_plans;
    uint32_t default_step_timeout_ms;
    float load_balancing_threshold;
    bool emergency_mode;
    
} director_service_t;

// Global director instance
static director_service_t* g_director = NULL;

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

static inline uint64_t get_timestamp_ns() {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (uint64_t)ts.tv_sec * 1000000000ULL + ts.tv_nsec;
}

static uint32_t generate_plan_id() {
    static _Atomic uint32_t id_counter = 1;
    return atomic_fetch_add(&id_counter, 1);
}

static uint32_t generate_step_id() {
    static _Atomic uint32_t id_counter = 1;
    return atomic_fetch_add(&id_counter, 1);
}

static float calculate_plan_progress(const execution_plan_t* plan) {
    if (plan->step_count == 0) return 0.0f;
    
    uint32_t total_weight = 0;
    uint32_t completed_weight = 0;
    
    for (uint32_t i = 0; i < plan->step_count; i++) {
        uint32_t weight = (plan->steps[i].priority == TASK_PRIORITY_CRITICAL) ? 3 : 1;
        total_weight += weight;
        
        if (plan->steps[i].state == STEP_STATE_COMPLETED) {
            completed_weight += weight;
        } else if (plan->steps[i].state == STEP_STATE_EXECUTING) {
            completed_weight += weight / 2;  // 50% for in-progress
        }
    }
    
    return total_weight > 0 ? (float)completed_weight / total_weight * 100.0f : 0.0f;
}

// ============================================================================
// DIRECTOR SERVICE INITIALIZATION
// ============================================================================

int director_service_init() {
    if (g_director) {
        return -EALREADY;
    }
    
    // Allocate director structure with NUMA awareness
    int numa_node = numa_node_of_cpu(sched_getcpu());
    g_director = numa_alloc_onnode(sizeof(director_service_t), numa_node);
    if (!g_director) {
        return -ENOMEM;
    }
    
    memset(g_director, 0, sizeof(director_service_t));
    
    // Initialize basic properties
    g_director->agent_id = DIRECTOR_AGENT_ID;
    strcpy(g_director->name, "DIRECTOR");
    g_director->running = true;
    
    // Initialize locks
    pthread_rwlock_init(&g_director->plans_lock, NULL);
    pthread_rwlock_init(&g_director->resources_lock, NULL);
    
    for (int i = 0; i < MAX_EXECUTION_PLANS; i++) {
        pthread_mutex_init(&g_director->execution_plans[i].lock, NULL);
    }
    
    for (int i = 0; i < MAX_RESOURCE_POOLS; i++) {
        pthread_mutex_init(&g_director->resource_pools[i].lock, NULL);
    }
    
    // Configuration
    g_director->max_concurrent_plans = MAX_ACTIVE_WORKFLOWS;
    g_director->default_step_timeout_ms = 60000;  // 1 minute
    g_director->load_balancing_threshold = 0.8f;
    g_director->emergency_mode = false;
    
    // Initialize discovery and router services
    if (discovery_service_init() != 0) {
        printf("Director: Warning - Discovery service initialization failed\n");
    }
    
    if (router_service_init() != 0) {
        printf("Director: Warning - Router service initialization failed\n");
    }
    
    // Initialize advanced features
#ifdef ENABLE_STREAMING_PIPELINE
    if (streaming_pipeline_init(16, "localhost:9092", "agent-events") != 0) {
        printf("Director: Warning - Streaming pipeline initialization failed\n");
    } else {
        printf("Director: Streaming pipeline initialized (10M+ events/sec capacity)\n");
    }
#endif

#ifdef ENABLE_NEURAL_SEARCH
    if (nas_init() != 0) {
        printf("Director: Warning - Neural architecture search initialization failed\n");
    } else {
        printf("Director: Neural architecture search initialized (1000+ arch/hour)\n");
    }
#endif

#ifdef ENABLE_DIGITAL_TWIN
    if (digital_twin_init() != 0) {
        printf("Director: Warning - Digital twin system initialization failed\n");
    } else {
        printf("Director: Digital twin system initialized (<10ms sync)\n");
        // Create director's own digital twin
        digital_twin_create("director-agent", 0);
    }
#endif

#ifdef ENABLE_MULTIMODAL_FUSION
    if (multimodal_fusion_init() != 0) {
        printf("Director: Warning - Multi-modal fusion initialization failed\n");
    } else {
        printf("Director: Multi-modal fusion initialized (<50ms processing)\n");
    }
#endif
    
    g_director->initialized = true;
    
    printf("Director Service: Initialized on NUMA node %d\n", numa_node);
    return 0;
}

void director_service_cleanup() {
    if (!g_director) {
        return;
    }
    
    g_director->running = false;
    
    // Stop threads
    if (g_director->plan_executor_thread) {
        pthread_join(g_director->plan_executor_thread, NULL);
    }
    if (g_director->resource_monitor_thread) {
        pthread_join(g_director->resource_monitor_thread, NULL);
    }
    if (g_director->heartbeat_thread) {
        pthread_join(g_director->heartbeat_thread, NULL);
    }
    
    // Cleanup locks
    pthread_rwlock_destroy(&g_director->plans_lock);
    pthread_rwlock_destroy(&g_director->resources_lock);
    
    for (int i = 0; i < MAX_EXECUTION_PLANS; i++) {
        pthread_mutex_destroy(&g_director->execution_plans[i].lock);
    }
    
    for (int i = 0; i < MAX_RESOURCE_POOLS; i++) {
        pthread_mutex_destroy(&g_director->resource_pools[i].lock);
    }
    
    // Cleanup advanced features
#ifdef ENABLE_STREAMING_PIPELINE
    streaming_pipeline_shutdown();
    printf("Director: Streaming pipeline shutdown\n");
#endif

#ifdef ENABLE_NEURAL_SEARCH
    nas_shutdown();
    printf("Director: Neural architecture search shutdown\n");
#endif

#ifdef ENABLE_DIGITAL_TWIN
    digital_twin_shutdown();
    printf("Director: Digital twin system shutdown\n");
#endif

#ifdef ENABLE_MULTIMODAL_FUSION
    multimodal_fusion_shutdown();
    printf("Director: Multi-modal fusion shutdown\n");
#endif
    
    // Cleanup services
    router_service_cleanup();
    discovery_service_cleanup();
    
    numa_free(g_director, sizeof(director_service_t));
    g_director = NULL;
    
    printf("Director Service: Cleaned up\n");
}

// ============================================================================
// RESOURCE POOL MANAGEMENT
// ============================================================================

int create_resource_pool(const char* name, agent_type_t agent_type, uint32_t capacity) {
    if (!g_director || !name) {
        return -EINVAL;
    }
    
    pthread_rwlock_wrlock(&g_director->resources_lock);
    
    if (g_director->resource_pool_count >= MAX_RESOURCE_POOLS) {
        pthread_rwlock_unlock(&g_director->resources_lock);
        return -ENOSPC;
    }
    
    // Find free slot
    resource_pool_t* pool = NULL;
    for (uint32_t i = 0; i < MAX_RESOURCE_POOLS; i++) {
        if (g_director->resource_pools[i].name[0] == '\0') {
            pool = &g_director->resource_pools[i];
            break;
        }
    }
    
    if (!pool) {
        pthread_rwlock_unlock(&g_director->resources_lock);
        return -ENOSPC;
    }
    
    // Initialize pool
    strncpy(pool->name, name, sizeof(pool->name) - 1);
    pool->name[sizeof(pool->name) - 1] = '\0';
    pool->agent_type = agent_type;
    pool->total_capacity = capacity;
    pool->available_capacity = capacity;
    pool->agent_count = 0;
    pool->avg_load_factor = 0.0f;
    pthread_mutex_init(&pool->lock, NULL);
    
    g_director->resource_pool_count++;
    
    pthread_rwlock_unlock(&g_director->resources_lock);
    
    printf("Director: Created resource pool '%s' for agent type %u (capacity: %u)\n",
           name, agent_type, capacity);
    
    return 0;
}

int allocate_agent_from_pool(agent_type_t agent_type, uint32_t* allocated_agent_id) {
    if (!g_director || !allocated_agent_id) {
        return -EINVAL;
    }
    
    pthread_rwlock_rdlock(&g_director->resources_lock);
    
    // Find appropriate resource pool
    resource_pool_t* best_pool = NULL;
    float best_load = 1.0f;
    
    for (uint32_t i = 0; i < g_director->resource_pool_count; i++) {
        resource_pool_t* pool = &g_director->resource_pools[i];
        
        if (pool->agent_type == agent_type && pool->available_capacity > 0) {
            if (pool->avg_load_factor < best_load) {
                best_load = pool->avg_load_factor;
                best_pool = pool;
            }
        }
    }
    
    if (!best_pool) {
        pthread_rwlock_unlock(&g_director->resources_lock);
        return -ENOENT;  // No available agents
    }
    
    pthread_mutex_lock(&best_pool->lock);
    
    if (best_pool->available_capacity == 0) {
        pthread_mutex_unlock(&best_pool->lock);
        pthread_rwlock_unlock(&g_director->resources_lock);
        return -EBUSY;
    }
    
    // Here we would discover an actual agent using the discovery service
    // For now, simulate allocation
    *allocated_agent_id = best_pool->agent_type * 100 + best_pool->agent_count + 1;
    best_pool->available_capacity--;
    
    atomic_fetch_add(&g_director->stats.resources_allocated, 1);
    
    pthread_mutex_unlock(&best_pool->lock);
    pthread_rwlock_unlock(&g_director->resources_lock);
    
    return 0;
}

void release_agent_to_pool(uint32_t agent_id) {
    if (!g_director) {
        return;
    }
    
    pthread_rwlock_rdlock(&g_director->resources_lock);
    
    // Find the pool containing this agent
    for (uint32_t i = 0; i < g_director->resource_pool_count; i++) {
        resource_pool_t* pool = &g_director->resource_pools[i];
        
        pthread_mutex_lock(&pool->lock);
        
        // Simple check - in real implementation would track actual assignments
        if (agent_id / 100 == pool->agent_type) {
            pool->available_capacity++;
            pthread_mutex_unlock(&pool->lock);
            break;
        }
        
        pthread_mutex_unlock(&pool->lock);
    }
    
    pthread_rwlock_unlock(&g_director->resources_lock);
}

// ============================================================================
// EXECUTION PLAN MANAGEMENT
// ============================================================================

uint32_t create_execution_plan(const char* name, const char* description,
                              task_priority_t priority) {
    if (!g_director || !name) {
        return 0;  // Invalid plan ID
    }
    
    pthread_rwlock_wrlock(&g_director->plans_lock);
    
    if (g_director->active_plan_count >= MAX_EXECUTION_PLANS) {
        pthread_rwlock_unlock(&g_director->plans_lock);
        return 0;
    }
    
    // Find free plan slot
    execution_plan_t* plan = NULL;
    for (uint32_t i = 0; i < MAX_EXECUTION_PLANS; i++) {
        if (g_director->execution_plans[i].plan_id == 0) {
            plan = &g_director->execution_plans[i];
            break;
        }
    }
    
    if (!plan) {
        pthread_rwlock_unlock(&g_director->plans_lock);
        return 0;
    }
    
    // Initialize plan
    pthread_mutex_lock(&plan->lock);
    
    plan->plan_id = generate_plan_id();
    strncpy(plan->name, name, sizeof(plan->name) - 1);
    plan->name[sizeof(plan->name) - 1] = '\0';
    
    if (description) {
        strncpy(plan->description, description, sizeof(plan->description) - 1);
        plan->description[sizeof(plan->description) - 1] = '\0';
    }
    
    plan->creation_time_ns = get_timestamp_ns();
    plan->creator_agent_id = DIRECTOR_AGENT_ID;
    plan->priority = priority;
    plan->state = PLAN_STATE_PENDING;
    plan->current_step_index = 0;
    plan->completed_steps = 0;
    plan->failed_steps = 0;
    plan->step_count = 0;
    plan->progress_percentage = 0.0f;
    plan->estimated_completion_ms = 0;
    
    g_director->active_plan_count++;
    atomic_fetch_add(&g_director->stats.plans_created, 1);
    atomic_fetch_add(&g_director->stats.active_plans, 1);
    
    uint32_t plan_id = plan->plan_id;
    
    pthread_mutex_unlock(&plan->lock);
    pthread_rwlock_unlock(&g_director->plans_lock);
    
    printf("Director: Created execution plan '%s' (ID: %u, Priority: %u)\n",
           name, plan_id, priority);
    
    return plan_id;
}

int add_execution_step(uint32_t plan_id, const char* step_name, const char* description,
                      agent_type_t required_agent_type, const char* capability,
                      const char* action, const char* parameters,
                      uint32_t timeout_ms, task_priority_t priority) {
    if (!g_director || !step_name || !action) {
        return -EINVAL;
    }
    
    // Find plan
    execution_plan_t* plan = NULL;
    pthread_rwlock_rdlock(&g_director->plans_lock);
    
    for (uint32_t i = 0; i < MAX_EXECUTION_PLANS; i++) {
        if (g_director->execution_plans[i].plan_id == plan_id) {
            plan = &g_director->execution_plans[i];
            break;
        }
    }
    
    if (!plan) {
        pthread_rwlock_unlock(&g_director->plans_lock);
        return -ENOENT;
    }
    
    pthread_mutex_lock(&plan->lock);
    
    if (plan->step_count >= MAX_PLAN_STEPS) {
        pthread_mutex_unlock(&plan->lock);
        pthread_rwlock_unlock(&g_director->plans_lock);
        return -ENOSPC;
    }
    
    // Add step
    execution_step_t* step = &plan->steps[plan->step_count];
    
    step->step_id = generate_step_id();
    strncpy(step->name, step_name, sizeof(step->name) - 1);
    step->name[sizeof(step->name) - 1] = '\0';
    
    if (description) {
        strncpy(step->description, description, sizeof(step->description) - 1);
        step->description[sizeof(step->description) - 1] = '\0';
    }
    
    step->required_agent_type = required_agent_type;
    step->assigned_agent_id = 0;  // Will be assigned during execution
    
    if (capability) {
        strncpy(step->capability_required, capability, sizeof(step->capability_required) - 1);
        step->capability_required[sizeof(step->capability_required) - 1] = '\0';
    }
    
    strncpy(step->action, action, sizeof(step->action) - 1);
    step->action[sizeof(step->action) - 1] = '\0';
    
    if (parameters) {
        strncpy(step->parameters, parameters, sizeof(step->parameters) - 1);
        step->parameters[sizeof(step->parameters) - 1] = '\0';
    }
    
    step->timeout_ms = timeout_ms > 0 ? timeout_ms : g_director->default_step_timeout_ms;
    step->priority = priority;
    step->state = STEP_STATE_WAITING;
    step->retry_count = 0;
    step->max_retries = 3;
    step->dependency_count = 0;
    
    plan->step_count++;
    
    pthread_mutex_unlock(&plan->lock);
    pthread_rwlock_unlock(&g_director->plans_lock);
    
    printf("Director: Added step '%s' to plan %u (Agent type: %u)\n",
           step_name, plan_id, required_agent_type);
    
    return step->step_id;
}

int add_step_dependency(uint32_t plan_id, uint32_t step_id, uint32_t dependency_step_id) {
    if (!g_director) {
        return -EINVAL;
    }
    
    // Find plan and steps
    execution_plan_t* plan = NULL;
    pthread_rwlock_rdlock(&g_director->plans_lock);
    
    for (uint32_t i = 0; i < MAX_EXECUTION_PLANS; i++) {
        if (g_director->execution_plans[i].plan_id == plan_id) {
            plan = &g_director->execution_plans[i];
            break;
        }
    }
    
    if (!plan) {
        pthread_rwlock_unlock(&g_director->plans_lock);
        return -ENOENT;
    }
    
    pthread_mutex_lock(&plan->lock);
    
    execution_step_t* step = NULL;
    for (uint32_t i = 0; i < plan->step_count; i++) {
        if (plan->steps[i].step_id == step_id) {
            step = &plan->steps[i];
            break;
        }
    }
    
    if (!step || step->dependency_count >= 16) {
        pthread_mutex_unlock(&plan->lock);
        pthread_rwlock_unlock(&g_director->plans_lock);
        return -EINVAL;
    }
    
    // Add dependency
    step->dependencies[step->dependency_count++] = dependency_step_id;
    
    pthread_mutex_unlock(&plan->lock);
    pthread_rwlock_unlock(&g_director->plans_lock);
    
    return 0;
}

// ============================================================================
// PLAN EXECUTION ENGINE
// ============================================================================

static bool are_dependencies_satisfied(const execution_plan_t* plan, const execution_step_t* step) {
    for (uint32_t i = 0; i < step->dependency_count; i++) {
        uint32_t dep_step_id = step->dependencies[i];
        
        // Find dependency step
        bool dep_completed = false;
        for (uint32_t j = 0; j < plan->step_count; j++) {
            if (plan->steps[j].step_id == dep_step_id) {
                dep_completed = (plan->steps[j].state == STEP_STATE_COMPLETED);
                break;
            }
        }
        
        if (!dep_completed) {
            return false;
        }
    }
    
    return true;
}

static int execute_step(execution_step_t* step) {
    printf("Director: Executing step '%s' (Action: %s)\n", step->name, step->action);
    
    step->state = STEP_STATE_EXECUTING;
    step->start_time_ns = get_timestamp_ns();
    
    // Allocate agent for execution
    uint32_t agent_id = 0;
    int result = allocate_agent_from_pool(step->required_agent_type, &agent_id);
    if (result != 0) {
        step->state = STEP_STATE_FAILED;
        strcpy(step->error_message, "Failed to allocate agent");
        return -1;
    }
    
    step->assigned_agent_id = agent_id;
    
    // Here we would send the actual execution request to the agent
    // For demonstration, simulate execution time
    
    // Simulate work based on action type
    uint32_t execution_time_ms = 1000;  // Default 1 second
    
    if (strstr(step->action, "analyze")) {
        execution_time_ms = 2000;
    } else if (strstr(step->action, "build")) {
        execution_time_ms = 5000;
    } else if (strstr(step->action, "test")) {
        execution_time_ms = 3000;
    } else if (strstr(step->action, "deploy")) {
        execution_time_ms = 4000;
    }
    
    // Simulate execution
    usleep(execution_time_ms * 1000);
    
    // Simulate success/failure (95% success rate)
    bool success = (rand() % 100) < 95;
    
    step->end_time_ns = get_timestamp_ns();
    step->actual_duration_ms = (step->end_time_ns - step->start_time_ns) / 1000000.0f;
    
    if (success) {
        step->state = STEP_STATE_COMPLETED;
        step->exit_code = 0;
        snprintf(step->result, sizeof(step->result), "Step completed successfully in %.1fms", 
                step->actual_duration_ms);
    } else {
        step->state = STEP_STATE_FAILED;
        step->exit_code = 1;
        strcpy(step->error_message, "Simulated execution failure");
    }
    
    // Release agent
    release_agent_to_pool(agent_id);
    
    atomic_fetch_add(&g_director->stats.steps_executed, 1);
    
    return success ? 0 : -1;
}

static void* plan_executor_thread(void* arg) {
    (void)arg;
    
    pthread_setname_np(pthread_self(), "plan_executor");
    
    while (g_director->running) {
        bool found_work = false;
        
        pthread_rwlock_rdlock(&g_director->plans_lock);
        
        // Process active plans
        for (uint32_t i = 0; i < MAX_EXECUTION_PLANS && g_director->running; i++) {
            execution_plan_t* plan = &g_director->execution_plans[i];
            
            if (plan->plan_id == 0 || plan->state != PLAN_STATE_RUNNING) {
                continue;
            }
            
            pthread_mutex_lock(&plan->lock);
            
            // Find ready steps
            for (uint32_t j = 0; j < plan->step_count; j++) {
                execution_step_t* step = &plan->steps[j];
                
                if (step->state == STEP_STATE_WAITING &&
                    are_dependencies_satisfied(plan, step)) {
                    
                    step->state = STEP_STATE_READY;
                    found_work = true;
                    
                    // Execute step
                    int result = execute_step(step);
                    
                    if (result == 0) {
                        plan->completed_steps++;
                    } else {
                        plan->failed_steps++;
                        
                        // Retry logic
                        if (step->retry_count < step->max_retries) {
                            step->retry_count++;
                            step->state = STEP_STATE_WAITING;
                            printf("Director: Retrying step '%s' (attempt %u/%u)\n",
                                   step->name, step->retry_count + 1, step->max_retries + 1);
                        }
                    }
                    
                    break;  // Process one step at a time
                }
            }
            
            // Update plan progress
            plan->progress_percentage = calculate_plan_progress(plan);
            
            // Check if plan is complete
            if (plan->completed_steps + plan->failed_steps >= plan->step_count) {
                bool has_failed_steps = false;
                for (uint32_t j = 0; j < plan->step_count; j++) {
                    if (plan->steps[j].state == STEP_STATE_FAILED) {
                        has_failed_steps = true;
                        break;
                    }
                }
                
                if (has_failed_steps) {
                    plan->state = PLAN_STATE_FAILED;
                    atomic_fetch_add(&g_director->stats.plans_failed, 1);
                } else {
                    plan->state = PLAN_STATE_COMPLETED;
                    atomic_fetch_add(&g_director->stats.plans_completed, 1);
                }
                
                plan->end_time_ns = get_timestamp_ns();
                atomic_fetch_sub(&g_director->stats.active_plans, 1);
                
                printf("Director: Plan '%s' %s (%.1f%% complete)\n",
                       plan->name,
                       plan->state == PLAN_STATE_COMPLETED ? "COMPLETED" : "FAILED",
                       plan->progress_percentage);
            }
            
            pthread_mutex_unlock(&plan->lock);
        }
        
        pthread_rwlock_unlock(&g_director->plans_lock);
        
        if (!found_work) {
            usleep(100000);  // Sleep 100ms if no work
        }
    }
    
    return NULL;
}

int start_plan_execution(uint32_t plan_id) {
    if (!g_director) {
        return -EINVAL;
    }
    
    // Find plan
    execution_plan_t* plan = NULL;
    pthread_rwlock_rdlock(&g_director->plans_lock);
    
    for (uint32_t i = 0; i < MAX_EXECUTION_PLANS; i++) {
        if (g_director->execution_plans[i].plan_id == plan_id) {
            plan = &g_director->execution_plans[i];
            break;
        }
    }
    
    if (!plan) {
        pthread_rwlock_unlock(&g_director->plans_lock);
        return -ENOENT;
    }
    
    pthread_mutex_lock(&plan->lock);
    
    if (plan->state != PLAN_STATE_PENDING) {
        pthread_mutex_unlock(&plan->lock);
        pthread_rwlock_unlock(&g_director->plans_lock);
        return -EINVAL;  // Plan already started or completed
    }
    
    plan->state = PLAN_STATE_RUNNING;
    plan->start_time_ns = get_timestamp_ns();
    
    pthread_mutex_unlock(&plan->lock);
    pthread_rwlock_unlock(&g_director->plans_lock);
    
    printf("Director: Started execution of plan '%s' (ID: %u)\n", plan->name, plan_id);
    
    return 0;
}

// ============================================================================
// STRATEGIC DECISION ENGINE
// ============================================================================

typedef struct {
    char scenario_name[128];
    float complexity_score;      // 0.0 - 1.0
    float risk_score;           // 0.0 - 1.0  
    float urgency_score;        // 0.0 - 1.0
    uint32_t resource_requirements;
    uint32_t estimated_duration_ms;
    bool requires_coordination;
} decision_scenario_t;

static int evaluate_strategic_decision(const char* context, decision_scenario_t* scenario) {
    if (!context || !scenario) {
        return -EINVAL;
    }
    
    printf("Director: Evaluating strategic decision for context '%s'\n", context);
    
    // Initialize scenario
    strncpy(scenario->scenario_name, context, sizeof(scenario->scenario_name) - 1);
    scenario->scenario_name[sizeof(scenario->scenario_name) - 1] = '\0';
    
    // Analyze context keywords to determine scenario complexity
    scenario->complexity_score = 0.3f; // Base complexity
    scenario->risk_score = 0.2f;       // Base risk
    scenario->urgency_score = 0.5f;    // Base urgency
    scenario->resource_requirements = 1;
    scenario->estimated_duration_ms = 60000; // 1 minute default
    scenario->requires_coordination = false;
    
    // Context-based decision logic
    if (strstr(context, "emergency") || strstr(context, "critical") || strstr(context, "urgent")) {
        scenario->urgency_score = 0.9f + (float)(rand() % 10) / 100.0f;
        scenario->risk_score = 0.6f + (float)(rand() % 40) / 100.0f;
        scenario->resource_requirements = 3 + (rand() % 3);
        scenario->estimated_duration_ms = 30000 + (rand() % 120000); // 30s - 2.5min
        scenario->requires_coordination = true;
    } else if (strstr(context, "build") || strstr(context, "compile") || strstr(context, "deploy")) {
        scenario->complexity_score = 0.6f + (float)(rand() % 30) / 100.0f;
        scenario->risk_score = 0.3f + (float)(rand() % 40) / 100.0f;
        scenario->resource_requirements = 2 + (rand() % 4);
        scenario->estimated_duration_ms = 120000 + (rand() % 480000); // 2-10min
        scenario->requires_coordination = (scenario->complexity_score > 0.7f);
    } else if (strstr(context, "test") || strstr(context, "validate") || strstr(context, "verify")) {
        scenario->complexity_score = 0.4f + (float)(rand() % 40) / 100.0f;
        scenario->risk_score = 0.2f + (float)(rand() % 30) / 100.0f;
        scenario->resource_requirements = 1 + (rand() % 3);
        scenario->estimated_duration_ms = 60000 + (rand() % 300000); // 1-6min
        scenario->requires_coordination = (scenario->resource_requirements > 2);
    } else if (strstr(context, "security") || strstr(context, "scan") || strstr(context, "audit")) {
        scenario->complexity_score = 0.7f + (float)(rand() % 30) / 100.0f;
        scenario->risk_score = 0.5f + (float)(rand() % 50) / 100.0f;
        scenario->urgency_score = 0.8f + (float)(rand() % 20) / 100.0f;
        scenario->resource_requirements = 2 + (rand() % 4);
        scenario->estimated_duration_ms = 180000 + (rand() % 600000); // 3-13min
        scenario->requires_coordination = true;
    } else if (strstr(context, "analyze") || strstr(context, "review") || strstr(context, "inspect")) {
        scenario->complexity_score = 0.5f + (float)(rand() % 40) / 100.0f;
        scenario->risk_score = 0.1f + (float)(rand() % 30) / 100.0f;
        scenario->resource_requirements = 1 + (rand() % 2);
        scenario->estimated_duration_ms = 90000 + (rand() % 240000); // 1.5-5.5min
        scenario->requires_coordination = false;
    }
    
    printf("Director: Decision analysis - Complexity: %.2f, Risk: %.2f, Urgency: %.2f, Resources: %u\n",
           scenario->complexity_score, scenario->risk_score, scenario->urgency_score, 
           scenario->resource_requirements);
    
    return 0;
}

static uint32_t create_strategic_execution_plan(const decision_scenario_t* scenario) {
    if (!scenario) {
        return 0;
    }
    
    // Determine plan priority based on scenario analysis
    task_priority_t priority = TASK_PRIORITY_NORMAL;
    if (scenario->urgency_score > 0.8f) {
        priority = TASK_PRIORITY_EMERGENCY;
    } else if (scenario->urgency_score > 0.6f || scenario->risk_score > 0.7f) {
        priority = TASK_PRIORITY_CRITICAL;
    } else if (scenario->complexity_score > 0.7f) {
        priority = TASK_PRIORITY_HIGH;
    }
    
    char plan_desc[1024];
    snprintf(plan_desc, sizeof(plan_desc), 
            "Strategic execution plan for %s (Complexity: %.2f, Risk: %.2f, Urgency: %.2f)",
            scenario->scenario_name, scenario->complexity_score, 
            scenario->risk_score, scenario->urgency_score);
    
    uint32_t plan_id = create_execution_plan(scenario->scenario_name, plan_desc, priority);
    if (plan_id == 0) {
        printf("Director: Failed to create strategic plan\n");
        return 0;
    }
    
    // Add steps based on scenario requirements
    if (scenario->requires_coordination) {
        add_execution_step(plan_id, "Coordinate Resources",
                          "Allocate and coordinate required resources across agents",
                          AGENT_TYPE_PROJECT_ORCHESTRATOR, "coordination",
                          "coordinate", "type=resources sync=true",
                          30000, TASK_PRIORITY_HIGH);
    }
    
    if (scenario->complexity_score > 0.6f) {
        add_execution_step(plan_id, "Architecture Review",
                          "Review system architecture and design patterns",
                          AGENT_TYPE_ARCHITECT, "system_analysis",
                          "analyze_architecture", "depth=full patterns=true",
                          scenario->estimated_duration_ms / 3, priority);
    }
    
    if (scenario->risk_score > 0.5f) {
        add_execution_step(plan_id, "Risk Assessment",
                          "Assess and mitigate potential risks",
                          AGENT_TYPE_SECURITY, "risk_analysis",
                          "assess_risks", "scope=comprehensive mitigation=true",
                          scenario->estimated_duration_ms / 4, TASK_PRIORITY_CRITICAL);
    }
    
    // Add main execution step
    add_execution_step(plan_id, "Main Execution",
                      "Execute primary task objective",
                      AGENT_TYPE_PROJECT_ORCHESTRATOR, "execution",
                      "execute", "target=main comprehensive=true",
                      scenario->estimated_duration_ms, priority);
    
    if (scenario->complexity_score > 0.7f || scenario->risk_score > 0.6f) {
        add_execution_step(plan_id, "Validation & Verification",
                          "Validate results and verify success criteria",
                          AGENT_TYPE_TESTBED, "validation",
                          "validate", "criteria=success deep_check=true",
                          scenario->estimated_duration_ms / 5, TASK_PRIORITY_HIGH);
    }
    
    printf("Director: Created strategic plan %u with scenario-based steps\n", plan_id);
    return plan_id;
}

static void* strategic_decision_engine_thread(void* arg) {
    (void)arg;
    
    pthread_setname_np(pthread_self(), "strategic_engine");
    
    while (g_director && g_director->running) {
        // Monitor for strategic decision opportunities
        sleep(5); // Check every 5 seconds
        
        // Analyze current system state
        uint32_t active_plans = atomic_load(&g_director->stats.active_plans);
        uint64_t completed_plans = atomic_load(&g_director->stats.plans_completed);
        uint64_t failed_plans = atomic_load(&g_director->stats.plans_failed);
        
        // Calculate success rate and system health
        float success_rate = (completed_plans + failed_plans > 0) ? 
                           (float)completed_plans / (completed_plans + failed_plans) : 1.0f;
        
        // Make strategic decisions based on system health
        if (success_rate < 0.8f && failed_plans > 5) {
            printf("Director: Low success rate (%.1f%%) detected, initiating strategic response\n", 
                   success_rate * 100.0f);
            
            decision_scenario_t scenario;
            if (evaluate_strategic_decision("system_health_recovery", &scenario) == 0) {
                uint32_t recovery_plan = create_strategic_execution_plan(&scenario);
                if (recovery_plan > 0) {
                    start_plan_execution(recovery_plan);
                }
            }
        }
        
        if (active_plans > g_director->max_concurrent_plans * 0.9f) {
            printf("Director: High system load detected, optimizing resource allocation\n");
            
            decision_scenario_t scenario;
            if (evaluate_strategic_decision("resource_optimization", &scenario) == 0) {
                uint32_t optimization_plan = create_strategic_execution_plan(&scenario);
                if (optimization_plan > 0) {
                    start_plan_execution(optimization_plan);
                }
            }
        }
        
        // Emergency mode detection and response
        if (!g_director->emergency_mode) {
            uint64_t emergency_count = atomic_load(&g_director->stats.emergency_responses);
            if (emergency_count > 0 && success_rate < 0.5f) {
                printf("Director: Entering emergency mode due to system instability\n");
                g_director->emergency_mode = true;
                
                decision_scenario_t scenario;
                if (evaluate_strategic_decision("emergency_response", &scenario) == 0) {
                    scenario.urgency_score = 1.0f;
                    scenario.requires_coordination = true;
                    uint32_t emergency_plan = create_strategic_execution_plan(&scenario);
                    if (emergency_plan > 0) {
                        start_plan_execution(emergency_plan);
                    }
                }
            }
        } else {
            // Exit emergency mode when system stabilizes
            if (success_rate > 0.9f && active_plans < g_director->max_concurrent_plans * 0.5f) {
                printf("Director: Exiting emergency mode - system stabilized\n");
                g_director->emergency_mode = false;
            }
        }
    }
    
    return NULL;
}

// ============================================================================
// MULTI-PHASE PLANNING ENGINE
// ============================================================================

typedef enum {
    PHASE_ANALYSIS = 1,
    PHASE_PLANNING = 2,
    PHASE_PREPARATION = 3,
    PHASE_EXECUTION = 4,
    PHASE_VALIDATION = 5,
    PHASE_COMPLETION = 6
} execution_phase_t;

typedef struct {
    execution_phase_t phase;
    char phase_name[64];
    uint32_t estimated_duration_ms;
    float success_probability;
    bool phase_completed;
    uint64_t phase_start_time;
    uint64_t phase_end_time;
} plan_phase_t;

static int create_multi_phase_plan(const char* objective, const char* requirements) {
    if (!objective) {
        return 0;
    }
    
    printf("Director: Creating multi-phase plan for objective '%s'\n", objective);
    
    char plan_name[128];
    snprintf(plan_name, sizeof(plan_name), "Multi-Phase: %s", objective);
    
    uint32_t plan_id = create_execution_plan(plan_name, requirements, TASK_PRIORITY_HIGH);
    if (plan_id == 0) {
        return 0;
    }
    
    // Phase 1: Analysis
    uint32_t analysis_step = add_execution_step(plan_id, "Phase 1: Analysis",
                                               "Comprehensive system and requirement analysis",
                                               AGENT_TYPE_ARCHITECT, "system_analysis",
                                               "analyze_comprehensive", requirements,
                                               90000, TASK_PRIORITY_HIGH);
    
    // Phase 2: Planning
    uint32_t planning_step = add_execution_step(plan_id, "Phase 2: Planning",
                                               "Strategic planning and resource allocation",
                                               AGENT_TYPE_PROJECT_ORCHESTRATOR, "strategic_planning",
                                               "create_detailed_plan", "based_on=analysis",
                                               60000, TASK_PRIORITY_HIGH);
    add_step_dependency(plan_id, planning_step, analysis_step);
    
    // Phase 3: Preparation
    uint32_t prep_step = add_execution_step(plan_id, "Phase 3: Preparation",
                                           "Environment setup and resource preparation",
                                           AGENT_TYPE_INFRASTRUCTURE, "environment_prep",
                                           "prepare_environment", "comprehensive=true",
                                           120000, TASK_PRIORITY_HIGH);
    add_step_dependency(plan_id, prep_step, planning_step);
    
    // Phase 4: Execution
    uint32_t exec_step = add_execution_step(plan_id, "Phase 4: Execution",
                                           "Primary objective execution",
                                           AGENT_TYPE_PROJECT_ORCHESTRATOR, "execution",
                                           "execute_primary_objective", objective,
                                           300000, TASK_PRIORITY_CRITICAL);
    add_step_dependency(plan_id, exec_step, prep_step);
    
    // Phase 5: Validation
    uint32_t validation_step = add_execution_step(plan_id, "Phase 5: Validation",
                                                 "Results validation and quality assurance",
                                                 AGENT_TYPE_TESTBED, "comprehensive_validation",
                                                 "validate_results", "criteria=success quality=high",
                                                 120000, TASK_PRIORITY_HIGH);
    add_step_dependency(plan_id, validation_step, exec_step);
    
    // Phase 6: Completion
    uint32_t completion_step = add_execution_step(plan_id, "Phase 6: Completion",
                                                 "Finalization and documentation",
                                                 AGENT_TYPE_DOCGEN, "documentation",
                                                 "generate_completion_docs", "comprehensive=true",
                                                 60000, TASK_PRIORITY_NORMAL);
    add_step_dependency(plan_id, completion_step, validation_step);
    
    printf("Director: Created multi-phase plan %u with 6 sequential phases\n", plan_id);
    return plan_id;
}

// ============================================================================
// DIRECTOR CONTROL FUNCTIONS
// ============================================================================

int start_director_threads() {
    if (!g_director) {
        return -EINVAL;
    }
    
    // Start plan executor thread
    int ret = pthread_create(&g_director->plan_executor_thread, NULL,
                           plan_executor_thread, NULL);
    if (ret != 0) {
        printf("Director: Failed to start plan executor thread: %s\n", strerror(ret));
        return ret;
    }
    
    // Start strategic decision engine thread
    ret = pthread_create(&g_director->resource_monitor_thread, NULL,
                        strategic_decision_engine_thread, NULL);
    if (ret != 0) {
        printf("Director: Failed to start strategic decision engine: %s\n", strerror(ret));
        return ret;
    }
    
    printf("Director: Started execution threads with strategic decision engine\n");
    return 0;
}

// ============================================================================
// PUBLIC API FOR STRATEGIC DECISIONS
// ============================================================================

uint32_t director_make_strategic_decision(const char* context, const char* requirements) {
    if (!g_director || !context) {
        return 0;
    }
    
    decision_scenario_t scenario;
    if (evaluate_strategic_decision(context, &scenario) != 0) {
        return 0;
    }
    
    // Choose between single-phase or multi-phase execution
    if (scenario.complexity_score > 0.7f || scenario.requires_coordination) {
        return create_multi_phase_plan(context, requirements);
    } else {
        return create_strategic_execution_plan(&scenario);
    }
}

int director_evaluate_system_health() {
    if (!g_director) {
        return -1;
    }
    
    uint64_t total_plans = atomic_load(&g_director->stats.plans_completed) + 
                          atomic_load(&g_director->stats.plans_failed);
    
    if (total_plans == 0) {
        return 100; // Perfect health with no history
    }
    
    float success_rate = (float)atomic_load(&g_director->stats.plans_completed) / total_plans;
    uint32_t active_load = atomic_load(&g_director->stats.active_plans);
    float load_factor = (float)active_load / g_director->max_concurrent_plans;
    
    // Calculate health score (0-100)
    float health_score = (success_rate * 0.7f) + ((1.0f - load_factor) * 0.3f);
    health_score *= 100.0f;
    
    return (int)fmaxf(0.0f, fminf(100.0f, health_score));
}

// ============================================================================
// STATISTICS AND MONITORING
// ============================================================================

void print_director_statistics() {
    if (!g_director) {
        printf("Director service not initialized\n");
        return;
    }
    
    printf("\n=== Director Service Statistics ===\n");
    printf("Plans created: %lu\n", atomic_load(&g_director->stats.plans_created));
    printf("Plans completed: %lu\n", atomic_load(&g_director->stats.plans_completed));
    printf("Plans failed: %lu\n", atomic_load(&g_director->stats.plans_failed));
    printf("Steps executed: %lu\n", atomic_load(&g_director->stats.steps_executed));
    printf("Active plans: %u\n", atomic_load(&g_director->stats.active_plans));
    printf("Resources allocated: %lu\n", atomic_load(&g_director->stats.resources_allocated));
    
    // Plan status summary
    printf("\nActive Execution Plans:\n");
    printf("%-8s %-25s %-12s %-8s %-8s %-10s\n",
           "ID", "Name", "State", "Steps", "Progress", "Priority");
    printf("%-8s %-25s %-12s %-8s %-8s %-10s\n",
           "--------", "-------------------------", "------------",
           "--------", "--------", "----------");
    
    pthread_rwlock_rdlock(&g_director->plans_lock);
    
    for (uint32_t i = 0; i < MAX_EXECUTION_PLANS; i++) {
        execution_plan_t* plan = &g_director->execution_plans[i];
        
        if (plan->plan_id == 0) continue;
        
        const char* state_str = "UNKNOWN";
        switch (plan->state) {
            case PLAN_STATE_PENDING: state_str = "PENDING"; break;
            case PLAN_STATE_RUNNING: state_str = "RUNNING"; break;
            case PLAN_STATE_PAUSED: state_str = "PAUSED"; break;
            case PLAN_STATE_COMPLETED: state_str = "COMPLETED"; break;
            case PLAN_STATE_FAILED: state_str = "FAILED"; break;
            case PLAN_STATE_CANCELLED: state_str = "CANCELLED"; break;
        }
        
        printf("%-8u %-25s %-12s %-8u %-7.1f%% %-10u\n",
               plan->plan_id, plan->name, state_str, plan->step_count,
               plan->progress_percentage, plan->priority);
    }
    
    pthread_rwlock_unlock(&g_director->plans_lock);
    
    // Resource pool status
    printf("\nResource Pools:\n");
    printf("%-20s %-12s %-10s %-10s %-10s\n",
           "Name", "Agent Type", "Capacity", "Available", "Load");
    printf("%-20s %-12s %-10s %-10s %-10s\n",
           "--------------------", "------------", "----------",
           "----------", "----------");
    
    pthread_rwlock_rdlock(&g_director->resources_lock);
    
    for (uint32_t i = 0; i < g_director->resource_pool_count; i++) {
        resource_pool_t* pool = &g_director->resource_pools[i];
        
        printf("%-20s %-12u %-10u %-10u %-9.1f%%\n",
               pool->name, pool->agent_type, pool->total_capacity,
               pool->available_capacity, pool->avg_load_factor * 100.0f);
    }
    
    pthread_rwlock_unlock(&g_director->resources_lock);
    
    printf("\n");
}

// ============================================================================
// EXAMPLE USAGE AND TESTING
// ============================================================================

#ifdef DIRECTOR_TEST_MODE

int main() {
    printf("Director Agent Test\n");
    printf("==================\n");
    
    // Initialize director service
    if (director_service_init() != 0) {
        printf("Failed to initialize director service\n");
        return 1;
    }
    
    // Create resource pools
    create_resource_pool("Security Pool", AGENT_TYPE_SECURITY, 3);
    create_resource_pool("Build Pool", AGENT_TYPE_C_INTERNAL, 2);
    create_resource_pool("Test Pool", AGENT_TYPE_TESTBED, 4);
    create_resource_pool("Analysis Pool", AGENT_TYPE_LINTER, 2);
    
    // Create a comprehensive execution plan
    uint32_t plan_id = create_execution_plan("Full Development Cycle", 
                                           "Complete development workflow with security, build, test, and analysis",
                                           TASK_PRIORITY_HIGH);
    
    if (plan_id == 0) {
        printf("Failed to create execution plan\n");
        return 1;
    }
    
    // Add execution steps
    uint32_t step1 = add_execution_step(plan_id, "Security Analysis", 
                                       "Perform initial security scan",
                                       AGENT_TYPE_SECURITY, "vulnerability_scan",
                                       "analyze_security", "target=codebase scan_depth=full",
                                       30000, TASK_PRIORITY_CRITICAL);
    
    uint32_t step2 = add_execution_step(plan_id, "Code Compilation",
                                       "Compile the project",
                                       AGENT_TYPE_C_INTERNAL, "compilation",
                                       "build", "target=release optimization=O3",
                                       60000, TASK_PRIORITY_HIGH);
    
    uint32_t step3 = add_execution_step(plan_id, "Unit Testing",
                                       "Run comprehensive test suite",
                                       AGENT_TYPE_TESTBED, "unit_testing",
                                       "test", "suite=all coverage=85",
                                       120000, TASK_PRIORITY_HIGH);
    
    uint32_t step4 = add_execution_step(plan_id, "Code Quality Analysis",
                                       "Analyze code quality and style",
                                       AGENT_TYPE_LINTER, "static_analysis",
                                       "analyze", "rules=strict format=report",
                                       45000, TASK_PRIORITY_NORMAL);
    
    uint32_t step5 = add_execution_step(plan_id, "Performance Testing",
                                       "Benchmark performance",
                                       AGENT_TYPE_TESTBED, "performance_testing",
                                       "benchmark", "duration=300 threads=8",
                                       180000, TASK_PRIORITY_NORMAL);
    
    // Add dependencies
    add_step_dependency(plan_id, step2, step1);  // Build after security
    add_step_dependency(plan_id, step3, step2);  // Test after build
    add_step_dependency(plan_id, step4, step2);  // Analysis after build
    add_step_dependency(plan_id, step5, step3);  // Performance test after unit tests
    
    printf("Created execution plan with %u steps\n", 5);
    
    // Start execution threads
    if (start_director_threads() != 0) {
        printf("Failed to start director threads\n");
        return 1;
    }
    
    // Start plan execution
    if (start_plan_execution(plan_id) != 0) {
        printf("Failed to start plan execution\n");
        return 1;
    }
    
    // Monitor execution
    printf("\nMonitoring plan execution...\n");
    
    for (int i = 0; i < 30; i++) {  // Monitor for 30 seconds
        sleep(1);
        
        if (i % 5 == 0) {  // Print stats every 5 seconds
            print_director_statistics();
        }
        
        // Check if plan completed
        pthread_rwlock_rdlock(&g_director->plans_lock);
        bool plan_done = false;
        for (uint32_t j = 0; j < MAX_EXECUTION_PLANS; j++) {
            if (g_director->execution_plans[j].plan_id == plan_id) {
                plan_state_t state = g_director->execution_plans[j].state;
                plan_done = (state == PLAN_STATE_COMPLETED || state == PLAN_STATE_FAILED);
                break;
            }
        }
        pthread_rwlock_unlock(&g_director->plans_lock);
        
        if (plan_done) {
            printf("Plan execution completed!\n");
            break;
        }
    }
    
    // Final statistics
    print_director_statistics();
    
    // Cleanup
    director_service_cleanup();
    
    return 0;
}

#endif