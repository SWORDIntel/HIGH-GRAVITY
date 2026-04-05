/*
 * PROJECT ORCHESTRATOR AGENT
 * 
 * Advanced workflow orchestration and task coordination system
 * - Multi-agent project workflows
 * - Task dependency management  
 * - Resource allocation and scheduling
 * - Progress tracking and reporting
 * - Parallel execution optimization
 * - Rollback and recovery mechanisms
 * 
 * Works in coordination with the Director agent for enterprise workflows
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

// Include headers
#include "agent_protocol.h"

// ============================================================================
// CONSTANTS AND CONFIGURATION
// ============================================================================

#define PROJECT_ORCHESTRATOR_AGENT_ID 2
#define MAX_PROJECTS 128
#define MAX_WORKFLOWS 256
#define MAX_WORKFLOW_TASKS 512
#define MAX_TASK_DEPENDENCIES 32
#define MAX_PARALLEL_EXECUTORS 16
#define MAX_RESOURCE_TYPES 64
#define MAX_PROJECT_NAME 128
#define MAX_TASK_NAME 128
#define MAX_CHECKPOINT_STATES 64
#define ORCHESTRATOR_HEARTBEAT_INTERVAL_MS 2000
#define TASK_EXECUTION_TIMEOUT_MS 600000  // 10 minutes
#define WORKFLOW_RECOVERY_TIMEOUT_MS 30000 // 30 seconds
#define CACHE_LINE_SIZE 64

// Workflow execution strategies
typedef enum {
    STRATEGY_SEQUENTIAL = 0,
    STRATEGY_PARALLEL_UNLIMITED = 1,
    STRATEGY_PARALLEL_LIMITED = 2,
    STRATEGY_PIPELINE = 3,
    STRATEGY_ADAPTIVE = 4
} execution_strategy_t;

// Task types
typedef enum {
    TASK_TYPE_ANALYSIS = 1,
    TASK_TYPE_BUILD = 2,
    TASK_TYPE_TEST = 3,
    TASK_TYPE_DEPLOY = 4,
    TASK_TYPE_SECURITY = 5,
    TASK_TYPE_DOCUMENTATION = 6,
    TASK_TYPE_INTEGRATION = 7,
    TASK_TYPE_VALIDATION = 8,
    TASK_TYPE_OPTIMIZATION = 9,
    TASK_TYPE_MONITORING = 10
} task_type_t;

// Task states
typedef enum {
    TASK_STATE_PENDING = 0,
    TASK_STATE_QUEUED = 1,
    TASK_STATE_ASSIGNED = 2,
    TASK_STATE_RUNNING = 3,
    TASK_STATE_COMPLETED = 4,
    TASK_STATE_FAILED = 5,
    TASK_STATE_CANCELLED = 6,
    TASK_STATE_RETRYING = 7,
    TASK_STATE_PAUSED = 8
} task_state_t;

// Workflow states
typedef enum {
    WORKFLOW_STATE_CREATED = 0,
    WORKFLOW_STATE_PLANNED = 1,
    WORKFLOW_STATE_RUNNING = 2,
    WORKFLOW_STATE_PAUSED = 3,
    WORKFLOW_STATE_COMPLETED = 4,
    WORKFLOW_STATE_FAILED = 5,
    WORKFLOW_STATE_CANCELLED = 6,
    WORKFLOW_STATE_RECOVERING = 7
} workflow_state_t;

// Project states
typedef enum {
    PROJECT_STATE_INITIALIZING = 0,
    PROJECT_STATE_ACTIVE = 1,
    PROJECT_STATE_PAUSED = 2,
    PROJECT_STATE_COMPLETED = 3,
    PROJECT_STATE_ARCHIVED = 4,
    PROJECT_STATE_FAILED = 5
} project_state_t;

// Task priorities
typedef enum {
    PRIORITY_EMERGENCY = 0,
    PRIORITY_CRITICAL = 1,
    PRIORITY_HIGH = 2,
    PRIORITY_NORMAL = 3,
    PRIORITY_LOW = 4,
    PRIORITY_BACKGROUND = 5
} task_priority_t;

// ============================================================================
// DATA STRUCTURES
// ============================================================================

// Resource requirement specification
typedef struct {
    char resource_type[32];
    uint32_t quantity_required;
    uint32_t quantity_allocated;
    float performance_requirement;  // 0.0 - 1.0
    bool exclusive_access;
} resource_requirement_t;

// Task execution metrics
typedef struct __attribute__((aligned(CACHE_LINE_SIZE))) {
    _Atomic uint64_t start_time_ns;
    _Atomic uint64_t end_time_ns;
    _Atomic uint32_t retry_count;
    _Atomic uint32_t execution_time_ms;
    _Atomic uint32_t queue_time_ms;
    _Atomic uint32_t cpu_time_ms;
    _Atomic uint32_t memory_peak_mb;
    _Atomic uint32_t disk_io_mb;
    _Atomic uint32_t network_io_mb;
    float efficiency_score;
    float quality_score;
} task_metrics_t;

// Workflow task definition
typedef struct {
    uint32_t task_id;
    char name[MAX_TASK_NAME];
    char description[512];
    
    // Classification
    task_type_t type;
    task_priority_t priority;
    
    // Dependencies
    uint32_t dependencies[MAX_TASK_DEPENDENCIES];
    uint32_t dependency_count;
    uint32_t dependents[MAX_TASK_DEPENDENCIES];
    uint32_t dependent_count;
    
    // Execution requirements
    uint32_t required_agent_type;
    char required_capability[64];
    uint32_t timeout_ms;
    uint32_t max_retries;
    bool can_run_parallel;
    
    // Resource requirements
    resource_requirement_t resource_requirements[8];
    uint32_t resource_requirement_count;
    
    // Execution details
    char action[128];
    char parameters[2048];
    char working_directory[256];
    char environment_vars[1024];
    
    // State and assignment
    task_state_t state;
    uint32_t assigned_agent_id;
    uint32_t execution_node_id;
    
    // Results
    int exit_code;
    char result_data[4096];
    char error_message[1024];
    
    // Metrics
    task_metrics_t metrics;
    
    // Checkpointing
    bool supports_checkpointing;
    char checkpoint_data[2048];
    uint64_t last_checkpoint_ns;
    
} workflow_task_t;

// Workflow execution context
typedef struct __attribute__((aligned(CACHE_LINE_SIZE))) {
    uint32_t workflow_id;
    char name[128];
    char description[1024];
    
    // Configuration
    execution_strategy_t strategy;
    uint32_t max_parallel_tasks;
    uint32_t max_execution_time_ms;
    bool fault_tolerant;
    bool supports_rollback;
    
    // Tasks
    workflow_task_t tasks[MAX_WORKFLOW_TASKS];
    uint32_t task_count;
    
    // Execution state
    workflow_state_t state;
    uint64_t creation_time_ns;
    uint64_t start_time_ns;
    uint64_t end_time_ns;
    
    // Progress tracking
    uint32_t tasks_pending;
    uint32_t tasks_running;
    uint32_t tasks_completed;
    uint32_t tasks_failed;
    float progress_percentage;
    uint32_t estimated_completion_ms;
    
    // Resource allocation
    uint32_t allocated_resources[MAX_RESOURCE_TYPES];
    uint32_t resource_allocation_count;
    
    // Recovery and rollback
    uint32_t checkpoint_count;
    uint64_t last_checkpoint_ns;
    char recovery_state[4096];
    
    // Synchronization
    pthread_mutex_t lock;
    pthread_cond_t state_changed;
    
} workflow_context_t;

// Project context
typedef struct {
    uint32_t project_id;
    char name[MAX_PROJECT_NAME];
    char description[2048];
    
    // Configuration
    uint32_t max_concurrent_workflows;
    uint32_t default_task_timeout_ms;
    bool auto_recovery_enabled;
    float quality_threshold;
    
    // Workflows
    uint32_t workflow_ids[MAX_WORKFLOWS];
    uint32_t workflow_count;
    uint32_t active_workflow_count;
    
    // State
    project_state_t state;
    uint64_t creation_time_ns;
    uint64_t completion_time_ns;
    
    // Metrics
    uint32_t total_tasks_executed;
    uint32_t total_tasks_failed;
    float overall_success_rate;
    float average_execution_time_ms;
    
    // Synchronization
    pthread_rwlock_t lock;
    
} project_context_t;

// Orchestrator statistics
typedef struct __attribute__((aligned(CACHE_LINE_SIZE))) {
    _Atomic uint64_t projects_created;
    _Atomic uint64_t workflows_created;
    _Atomic uint64_t workflows_completed;
    _Atomic uint64_t workflows_failed;
    _Atomic uint64_t tasks_executed;
    _Atomic uint64_t tasks_failed;
    _Atomic uint64_t tasks_retried;
    _Atomic uint64_t checkpoints_created;
    _Atomic uint64_t recoveries_performed;
    _Atomic uint32_t active_workflows;
    _Atomic uint32_t active_tasks;
    double avg_workflow_completion_time_ms;
    double system_throughput_tasks_per_sec;
    double resource_utilization_percentage;
} orchestrator_stats_t;

// Execution thread context
typedef struct {
    int thread_id;
    int cpu_id;
    pthread_t thread;
    bool running;
    uint32_t assigned_workflow_id;
    _Atomic uint64_t tasks_processed;
    _Atomic uint64_t processing_time_ns;
} executor_thread_t;

// Main Project Orchestrator service
typedef struct __attribute__((aligned(PAGE_SIZE))) {
    // Identity
    uint32_t agent_id;
    char name[64];
    bool initialized;
    volatile bool running;
    
    // Projects and workflows
    project_context_t projects[MAX_PROJECTS];
    workflow_context_t workflows[MAX_WORKFLOWS];
    uint32_t project_count;
    uint32_t workflow_count;
    
    // Synchronization
    pthread_rwlock_t projects_lock;
    pthread_rwlock_t workflows_lock;
    
    // Execution threads
    executor_thread_t executors[MAX_PARALLEL_EXECUTORS];
    uint32_t executor_count;
    
    // Task scheduling
    uint32_t task_queue[MAX_WORKFLOW_TASKS];
    uint32_t queue_head;
    uint32_t queue_tail;
    uint32_t queue_size;
    pthread_mutex_t queue_lock;
    pthread_cond_t queue_not_empty;
    
    // Statistics
    orchestrator_stats_t stats;
    
    // Configuration
    uint32_t max_concurrent_workflows;
    uint32_t default_workflow_timeout_ms;
    float failure_threshold_percentage;
    bool auto_scaling_enabled;
    
} orchestrator_service_t;

// Global orchestrator instance
static orchestrator_service_t* g_orchestrator = NULL;

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

static inline uint64_t get_timestamp_ns() {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (uint64_t)ts.tv_sec * 1000000000ULL + ts.tv_nsec;
}

static uint32_t generate_project_id() {
    static _Atomic uint32_t id_counter = 1;
    return atomic_fetch_add(&id_counter, 1);
}

static uint32_t generate_workflow_id() {
    static _Atomic uint32_t id_counter = 1;
    return atomic_fetch_add(&id_counter, 1);
}

static uint32_t generate_task_id() {
    static _Atomic uint32_t id_counter = 1;
    return atomic_fetch_add(&id_counter, 1);
}

static float calculate_workflow_progress(const workflow_context_t* workflow) {
    if (workflow->task_count == 0) return 0.0f;
    
    float total_weight = 0.0f;
    float completed_weight = 0.0f;
    
    for (uint32_t i = 0; i < workflow->task_count; i++) {
        const workflow_task_t* task = &workflow->tasks[i];
        
        // Weight by priority (higher priority = more weight)
        float weight = 1.0f;
        switch (task->priority) {
            case PRIORITY_EMERGENCY: weight = 5.0f; break;
            case PRIORITY_CRITICAL: weight = 4.0f; break;
            case PRIORITY_HIGH: weight = 3.0f; break;
            case PRIORITY_NORMAL: weight = 2.0f; break;
            case PRIORITY_LOW: weight = 1.5f; break;
            case PRIORITY_BACKGROUND: weight = 1.0f; break;
        }
        
        total_weight += weight;
        
        if (task->state == TASK_STATE_COMPLETED) {
            completed_weight += weight;
        } else if (task->state == TASK_STATE_RUNNING) {
            completed_weight += weight * 0.5f;  // 50% for running tasks
        } else if (task->state == TASK_STATE_ASSIGNED || task->state == TASK_STATE_QUEUED) {
            completed_weight += weight * 0.1f;  // 10% for queued tasks
        }
    }
    
    return total_weight > 0.0f ? (completed_weight / total_weight) * 100.0f : 0.0f;
}

// ============================================================================
// ORCHESTRATOR SERVICE INITIALIZATION
// ============================================================================

int orchestrator_service_init() {
    if (g_orchestrator) {
        return -EALREADY;
    }
    
    // Allocate orchestrator structure with NUMA awareness
    int numa_node = numa_node_of_cpu(sched_getcpu());
    g_orchestrator = numa_alloc_onnode(sizeof(orchestrator_service_t), numa_node);
    if (!g_orchestrator) {
        return -ENOMEM;
    }
    
    memset(g_orchestrator, 0, sizeof(orchestrator_service_t));
    
    // Initialize basic properties
    g_orchestrator->agent_id = PROJECT_ORCHESTRATOR_AGENT_ID;
    strcpy(g_orchestrator->name, "PROJECT_ORCHESTRATOR");
    g_orchestrator->running = true;
    
    // Initialize locks
    pthread_rwlock_init(&g_orchestrator->projects_lock, NULL);
    pthread_rwlock_init(&g_orchestrator->workflows_lock, NULL);
    pthread_mutex_init(&g_orchestrator->queue_lock, NULL);
    pthread_cond_init(&g_orchestrator->queue_not_empty, NULL);
    
    // Initialize project and workflow locks
    for (int i = 0; i < MAX_PROJECTS; i++) {
        pthread_rwlock_init(&g_orchestrator->projects[i].lock, NULL);
    }
    
    for (int i = 0; i < MAX_WORKFLOWS; i++) {
        pthread_mutex_init(&g_orchestrator->workflows[i].lock, NULL);
        pthread_cond_init(&g_orchestrator->workflows[i].state_changed, NULL);
    }
    
    // Initialize task queue
    g_orchestrator->queue_head = 0;
    g_orchestrator->queue_tail = 0;
    g_orchestrator->queue_size = 0;
    
    // Configuration
    g_orchestrator->max_concurrent_workflows = MAX_WORKFLOWS / 4;
    g_orchestrator->default_workflow_timeout_ms = TASK_EXECUTION_TIMEOUT_MS;
    g_orchestrator->failure_threshold_percentage = 10.0f;  // 10% failure threshold
    g_orchestrator->auto_scaling_enabled = true;
    
    // Initialize executor threads
    g_orchestrator->executor_count = MAX_PARALLEL_EXECUTORS;
    for (uint32_t i = 0; i < g_orchestrator->executor_count; i++) {
        g_orchestrator->executors[i].thread_id = i;
        g_orchestrator->executors[i].cpu_id = i % sysconf(_SC_NPROCESSORS_ONLN);
        g_orchestrator->executors[i].running = true;
        g_orchestrator->executors[i].assigned_workflow_id = 0;
    }
    
    g_orchestrator->initialized = true;
    
    printf("Project Orchestrator Service: Initialized on NUMA node %d\n", numa_node);
    return 0;
}

void orchestrator_service_cleanup() {
    if (!g_orchestrator) {
        return;
    }
    
    g_orchestrator->running = false;
    
    // Stop executor threads
    for (uint32_t i = 0; i < g_orchestrator->executor_count; i++) {
        if (g_orchestrator->executors[i].thread) {
            g_orchestrator->executors[i].running = false;
            pthread_join(g_orchestrator->executors[i].thread, NULL);
        }
    }
    
    // Signal waiting threads
    pthread_cond_broadcast(&g_orchestrator->queue_not_empty);
    
    // Cleanup locks
    pthread_rwlock_destroy(&g_orchestrator->projects_lock);
    pthread_rwlock_destroy(&g_orchestrator->workflows_lock);
    pthread_mutex_destroy(&g_orchestrator->queue_lock);
    pthread_cond_destroy(&g_orchestrator->queue_not_empty);
    
    for (int i = 0; i < MAX_PROJECTS; i++) {
        pthread_rwlock_destroy(&g_orchestrator->projects[i].lock);
    }
    
    for (int i = 0; i < MAX_WORKFLOWS; i++) {
        pthread_mutex_destroy(&g_orchestrator->workflows[i].lock);
        pthread_cond_destroy(&g_orchestrator->workflows[i].state_changed);
    }
    
    numa_free(g_orchestrator, sizeof(orchestrator_service_t));
    g_orchestrator = NULL;
    
    printf("Project Orchestrator Service: Cleaned up\n");
}

// ============================================================================
// PROJECT MANAGEMENT
// ============================================================================

uint32_t create_project(const char* name, const char* description,
                       uint32_t max_concurrent_workflows) {
    if (!g_orchestrator || !name) {
        return 0;  // Invalid project ID
    }
    
    pthread_rwlock_wrlock(&g_orchestrator->projects_lock);
    
    if (g_orchestrator->project_count >= MAX_PROJECTS) {
        pthread_rwlock_unlock(&g_orchestrator->projects_lock);
        return 0;
    }
    
    // Find free project slot
    project_context_t* project = NULL;
    for (uint32_t i = 0; i < MAX_PROJECTS; i++) {
        if (g_orchestrator->projects[i].project_id == 0) {
            project = &g_orchestrator->projects[i];
            break;
        }
    }
    
    if (!project) {
        pthread_rwlock_unlock(&g_orchestrator->projects_lock);
        return 0;
    }
    
    // Initialize project
    pthread_rwlock_wrlock(&project->lock);
    
    project->project_id = generate_project_id();
    strncpy(project->name, name, MAX_PROJECT_NAME - 1);
    project->name[MAX_PROJECT_NAME - 1] = '\0';
    
    if (description) {
        strncpy(project->description, description, sizeof(project->description) - 1);
        project->description[sizeof(project->description) - 1] = '\0';
    }
    
    project->max_concurrent_workflows = max_concurrent_workflows > 0 ? 
                                       max_concurrent_workflows : g_orchestrator->max_concurrent_workflows;
    project->default_task_timeout_ms = g_orchestrator->default_workflow_timeout_ms;
    project->auto_recovery_enabled = true;
    project->quality_threshold = 0.95f;
    project->workflow_count = 0;
    project->active_workflow_count = 0;
    project->state = PROJECT_STATE_INITIALIZING;
    project->creation_time_ns = get_timestamp_ns();
    project->total_tasks_executed = 0;
    project->total_tasks_failed = 0;
    project->overall_success_rate = 1.0f;
    project->average_execution_time_ms = 0.0f;
    
    g_orchestrator->project_count++;
    atomic_fetch_add(&g_orchestrator->stats.projects_created, 1);
    
    uint32_t project_id = project->project_id;
    
    pthread_rwlock_unlock(&project->lock);
    pthread_rwlock_unlock(&g_orchestrator->projects_lock);
    
    printf("Orchestrator: Created project '%s' (ID: %u, Max workflows: %u)\n",
           name, project_id, project->max_concurrent_workflows);
    
    return project_id;
}

int activate_project(uint32_t project_id) {
    if (!g_orchestrator) {
        return -EINVAL;
    }
    
    pthread_rwlock_rdlock(&g_orchestrator->projects_lock);
    
    project_context_t* project = NULL;
    for (uint32_t i = 0; i < MAX_PROJECTS; i++) {
        if (g_orchestrator->projects[i].project_id == project_id) {
            project = &g_orchestrator->projects[i];
            break;
        }
    }
    
    if (!project) {
        pthread_rwlock_unlock(&g_orchestrator->projects_lock);
        return -ENOENT;
    }
    
    pthread_rwlock_wrlock(&project->lock);
    
    if (project->state != PROJECT_STATE_INITIALIZING) {
        pthread_rwlock_unlock(&project->lock);
        pthread_rwlock_unlock(&g_orchestrator->projects_lock);
        return -EINVAL;  // Project already active or completed
    }
    
    project->state = PROJECT_STATE_ACTIVE;
    
    pthread_rwlock_unlock(&project->lock);
    pthread_rwlock_unlock(&g_orchestrator->projects_lock);
    
    printf("Orchestrator: Activated project ID %u\n", project_id);
    return 0;
}

// ============================================================================
// WORKFLOW MANAGEMENT
// ============================================================================

uint32_t create_workflow(uint32_t project_id, const char* name, const char* description,
                        execution_strategy_t strategy, uint32_t max_parallel_tasks) {
    if (!g_orchestrator || !name) {
        return 0;  // Invalid workflow ID
    }
    
    // Verify project exists and is active
    pthread_rwlock_rdlock(&g_orchestrator->projects_lock);
    
    project_context_t* project = NULL;
    for (uint32_t i = 0; i < MAX_PROJECTS; i++) {
        if (g_orchestrator->projects[i].project_id == project_id) {
            project = &g_orchestrator->projects[i];
            break;
        }
    }
    
    if (!project || project->state != PROJECT_STATE_ACTIVE) {
        pthread_rwlock_unlock(&g_orchestrator->projects_lock);
        return 0;
    }
    
    // Check project workflow limit
    if (project->active_workflow_count >= project->max_concurrent_workflows) {
        pthread_rwlock_unlock(&g_orchestrator->projects_lock);
        return 0;  // Project at workflow capacity
    }
    
    pthread_rwlock_unlock(&g_orchestrator->projects_lock);
    
    // Create workflow
    pthread_rwlock_wrlock(&g_orchestrator->workflows_lock);
    
    if (g_orchestrator->workflow_count >= MAX_WORKFLOWS) {
        pthread_rwlock_unlock(&g_orchestrator->workflows_lock);
        return 0;
    }
    
    // Find free workflow slot
    workflow_context_t* workflow = NULL;
    for (uint32_t i = 0; i < MAX_WORKFLOWS; i++) {
        if (g_orchestrator->workflows[i].workflow_id == 0) {
            workflow = &g_orchestrator->workflows[i];
            break;
        }
    }
    
    if (!workflow) {
        pthread_rwlock_unlock(&g_orchestrator->workflows_lock);
        return 0;
    }
    
    // Initialize workflow
    pthread_mutex_lock(&workflow->lock);
    
    workflow->workflow_id = generate_workflow_id();
    strncpy(workflow->name, name, sizeof(workflow->name) - 1);
    workflow->name[sizeof(workflow->name) - 1] = '\0';
    
    if (description) {
        strncpy(workflow->description, description, sizeof(workflow->description) - 1);
        workflow->description[sizeof(workflow->description) - 1] = '\0';
    }
    
    workflow->strategy = strategy;
    workflow->max_parallel_tasks = max_parallel_tasks > 0 ? max_parallel_tasks : MAX_PARALLEL_EXECUTORS;
    workflow->max_execution_time_ms = g_orchestrator->default_workflow_timeout_ms;
    workflow->fault_tolerant = true;
    workflow->supports_rollback = true;
    workflow->task_count = 0;
    workflow->state = WORKFLOW_STATE_CREATED;
    workflow->creation_time_ns = get_timestamp_ns();
    workflow->tasks_pending = 0;
    workflow->tasks_running = 0;
    workflow->tasks_completed = 0;
    workflow->tasks_failed = 0;
    workflow->progress_percentage = 0.0f;
    workflow->estimated_completion_ms = 0;
    workflow->checkpoint_count = 0;
    
    g_orchestrator->workflow_count++;
    atomic_fetch_add(&g_orchestrator->stats.workflows_created, 1);
    
    // Add workflow to project
    pthread_rwlock_wrlock(&project->lock);
    project->workflow_ids[project->workflow_count++] = workflow->workflow_id;
    project->active_workflow_count++;
    pthread_rwlock_unlock(&project->lock);
    
    uint32_t workflow_id = workflow->workflow_id;
    
    pthread_mutex_unlock(&workflow->lock);
    pthread_rwlock_unlock(&g_orchestrator->workflows_lock);
    
    printf("Orchestrator: Created workflow '%s' (ID: %u, Strategy: %u, Max parallel: %u)\n",
           name, workflow_id, strategy, workflow->max_parallel_tasks);
    
    return workflow_id;
}

int add_workflow_task(uint32_t workflow_id, const char* task_name, const char* description,
                     task_type_t type, task_priority_t priority,
                     uint32_t required_agent_type, const char* capability,
                     const char* action, const char* parameters,
                     uint32_t timeout_ms) {
    if (!g_orchestrator || !task_name || !action) {
        return -EINVAL;
    }
    
    // Find workflow
    workflow_context_t* workflow = NULL;
    pthread_rwlock_rdlock(&g_orchestrator->workflows_lock);
    
    for (uint32_t i = 0; i < MAX_WORKFLOWS; i++) {
        if (g_orchestrator->workflows[i].workflow_id == workflow_id) {
            workflow = &g_orchestrator->workflows[i];
            break;
        }
    }
    
    if (!workflow) {
        pthread_rwlock_unlock(&g_orchestrator->workflows_lock);
        return -ENOENT;
    }
    
    pthread_mutex_lock(&workflow->lock);
    
    if (workflow->task_count >= MAX_WORKFLOW_TASKS) {
        pthread_mutex_unlock(&workflow->lock);
        pthread_rwlock_unlock(&g_orchestrator->workflows_lock);
        return -ENOSPC;
    }
    
    if (workflow->state != WORKFLOW_STATE_CREATED && workflow->state != WORKFLOW_STATE_PLANNED) {
        pthread_mutex_unlock(&workflow->lock);
        pthread_rwlock_unlock(&g_orchestrator->workflows_lock);
        return -EINVAL;  // Workflow already started
    }
    
    // Add task
    workflow_task_t* task = &workflow->tasks[workflow->task_count];
    
    task->task_id = generate_task_id();
    strncpy(task->name, task_name, MAX_TASK_NAME - 1);
    task->name[MAX_TASK_NAME - 1] = '\0';
    
    if (description) {
        strncpy(task->description, description, sizeof(task->description) - 1);
        task->description[sizeof(task->description) - 1] = '\0';
    }
    
    task->type = type;
    task->priority = priority;
    task->required_agent_type = required_agent_type;
    
    if (capability) {
        strncpy(task->required_capability, capability, sizeof(task->required_capability) - 1);
        task->required_capability[sizeof(task->required_capability) - 1] = '\0';
    }
    
    strncpy(task->action, action, sizeof(task->action) - 1);
    task->action[sizeof(task->action) - 1] = '\0';
    
    if (parameters) {
        strncpy(task->parameters, parameters, sizeof(task->parameters) - 1);
        task->parameters[sizeof(task->parameters) - 1] = '\0';
    }
    
    task->timeout_ms = timeout_ms > 0 ? timeout_ms : TASK_EXECUTION_TIMEOUT_MS;
    task->max_retries = 3;
    task->can_run_parallel = (strategy == STRATEGY_PARALLEL_UNLIMITED || 
                             strategy == STRATEGY_PARALLEL_LIMITED ||
                             strategy == STRATEGY_ADAPTIVE);
    task->state = TASK_STATE_PENDING;
    task->assigned_agent_id = 0;
    task->execution_node_id = 0;
    task->dependency_count = 0;
    task->dependent_count = 0;
    task->exit_code = -1;
    task->resource_requirement_count = 0;
    task->supports_checkpointing = false;
    
    // Initialize metrics
    atomic_store(&task->metrics.start_time_ns, 0);
    atomic_store(&task->metrics.end_time_ns, 0);
    atomic_store(&task->metrics.retry_count, 0);
    atomic_store(&task->metrics.execution_time_ms, 0);
    atomic_store(&task->metrics.queue_time_ms, 0);
    atomic_store(&task->metrics.cpu_time_ms, 0);
    atomic_store(&task->metrics.memory_peak_mb, 0);
    task->metrics.efficiency_score = 0.0f;
    task->metrics.quality_score = 0.0f;
    
    workflow->task_count++;
    workflow->tasks_pending++;
    
    uint32_t task_id = task->task_id;
    
    pthread_mutex_unlock(&workflow->lock);
    pthread_rwlock_unlock(&g_orchestrator->workflows_lock);
    
    printf("Orchestrator: Added task '%s' to workflow %u (Type: %u, Priority: %u)\n",
           task_name, workflow_id, type, priority);
    
    return task_id;
}

int add_task_dependency(uint32_t workflow_id, uint32_t task_id, uint32_t dependency_task_id) {
    if (!g_orchestrator) {
        return -EINVAL;
    }
    
    // Find workflow
    workflow_context_t* workflow = NULL;
    pthread_rwlock_rdlock(&g_orchestrator->workflows_lock);
    
    for (uint32_t i = 0; i < MAX_WORKFLOWS; i++) {
        if (g_orchestrator->workflows[i].workflow_id == workflow_id) {
            workflow = &g_orchestrator->workflows[i];
            break;
        }
    }
    
    if (!workflow) {
        pthread_rwlock_unlock(&g_orchestrator->workflows_lock);
        return -ENOENT;
    }
    
    pthread_mutex_lock(&workflow->lock);
    
    // Find tasks
    workflow_task_t* task = NULL;
    workflow_task_t* dependency_task = NULL;
    
    for (uint32_t i = 0; i < workflow->task_count; i++) {
        if (workflow->tasks[i].task_id == task_id) {
            task = &workflow->tasks[i];
        }
        if (workflow->tasks[i].task_id == dependency_task_id) {
            dependency_task = &workflow->tasks[i];
        }
    }
    
    if (!task || !dependency_task) {
        pthread_mutex_unlock(&workflow->lock);
        pthread_rwlock_unlock(&g_orchestrator->workflows_lock);
        return -ENOENT;
    }
    
    if (task->dependency_count >= MAX_TASK_DEPENDENCIES ||
        dependency_task->dependent_count >= MAX_TASK_DEPENDENCIES) {
        pthread_mutex_unlock(&workflow->lock);
        pthread_rwlock_unlock(&g_orchestrator->workflows_lock);
        return -ENOSPC;
    }
    
    // Add dependency relationship
    task->dependencies[task->dependency_count++] = dependency_task_id;
    dependency_task->dependents[dependency_task->dependent_count++] = task_id;
    
    pthread_mutex_unlock(&workflow->lock);
    pthread_rwlock_unlock(&g_orchestrator->workflows_lock);
    
    return 0;
}

// ============================================================================
// DAG-BASED WORKFLOW EXECUTION ENGINE
// ============================================================================

// DAG node structure
typedef struct dag_node {
    uint32_t task_id;
    uint32_t level;              // Topological level (0 = no dependencies)
    uint32_t in_degree;          // Number of incoming edges
    uint32_t out_degree;         // Number of outgoing edges
    struct dag_node* incoming[MAX_TASK_DEPENDENCIES];
    struct dag_node* outgoing[MAX_TASK_DEPENDENCIES];
    bool visited;
    bool in_critical_path;
    float earliest_start_time;
    float latest_start_time;
    float slack_time;
} dag_node_t;

// DAG execution context
typedef struct {
    dag_node_t nodes[MAX_WORKFLOW_TASKS];
    uint32_t node_count;
    uint32_t max_level;
    uint32_t critical_path_length;
    float total_estimated_time;
    bool is_acyclic;
} workflow_dag_t;

static int build_workflow_dag(workflow_context_t* workflow, workflow_dag_t* dag) {
    if (!workflow || !dag) {
        return -EINVAL;
    }
    
    printf("Orchestrator: Building DAG for workflow '%s' with %u tasks\n", 
           workflow->name, workflow->task_count);
    
    memset(dag, 0, sizeof(workflow_dag_t));
    dag->node_count = workflow->task_count;
    dag->is_acyclic = true;
    
    // Initialize DAG nodes
    for (uint32_t i = 0; i < workflow->task_count; i++) {
        dag_node_t* node = &dag->nodes[i];
        node->task_id = workflow->tasks[i].task_id;
        node->level = 0;
        node->in_degree = workflow->tasks[i].dependency_count;
        node->out_degree = workflow->tasks[i].dependent_count;
        node->visited = false;
        node->in_critical_path = false;
        node->earliest_start_time = 0.0f;
        node->latest_start_time = 0.0f;
        node->slack_time = 0.0f;
    }
    
    // Build dependency edges
    for (uint32_t i = 0; i < workflow->task_count; i++) {
        workflow_task_t* task = &workflow->tasks[i];
        dag_node_t* node = &dag->nodes[i];
        
        uint32_t incoming_idx = 0, outgoing_idx = 0;
        
        // Set incoming edges (dependencies)
        for (uint32_t j = 0; j < task->dependency_count; j++) {
            uint32_t dep_task_id = task->dependencies[j];
            
            // Find the dependency node
            for (uint32_t k = 0; k < dag->node_count; k++) {
                if (dag->nodes[k].task_id == dep_task_id) {
                    node->incoming[incoming_idx++] = &dag->nodes[k];
                    break;
                }
            }
        }
        
        // Set outgoing edges (dependents)
        for (uint32_t j = 0; j < task->dependent_count; j++) {
            uint32_t dep_task_id = task->dependents[j];
            
            // Find the dependent node
            for (uint32_t k = 0; k < dag->node_count; k++) {
                if (dag->nodes[k].task_id == dep_task_id) {
                    node->outgoing[outgoing_idx++] = &dag->nodes[k];
                    break;
                }
            }
        }
    }
    
    printf("Orchestrator: DAG built with %u nodes\n", dag->node_count);
    return 0;
}

static int detect_cycles_dfs(dag_node_t* node, int* color, workflow_dag_t* dag) {
    color[node - dag->nodes] = 1; // Gray (visiting)
    
    for (uint32_t i = 0; i < node->out_degree; i++) {
        dag_node_t* neighbor = node->outgoing[i];
        int neighbor_idx = neighbor - dag->nodes;
        
        if (color[neighbor_idx] == 1) {
            // Back edge found - cycle detected
            return -1;
        }
        if (color[neighbor_idx] == 0 && detect_cycles_dfs(neighbor, color, dag) == -1) {
            return -1;
        }
    }
    
    color[node - dag->nodes] = 2; // Black (visited)
    return 0;
}

static int validate_dag_acyclic(workflow_dag_t* dag) {
    if (!dag) {
        return -EINVAL;
    }
    
    // Color array: 0=white, 1=gray, 2=black
    int* color = calloc(dag->node_count, sizeof(int));
    if (!color) {
        return -ENOMEM;
    }
    
    // DFS cycle detection
    for (uint32_t i = 0; i < dag->node_count; i++) {
        if (color[i] == 0) {
            if (detect_cycles_dfs(&dag->nodes[i], color, dag) == -1) {
                dag->is_acyclic = false;
                free(color);
                printf("Orchestrator: ERROR - Cycle detected in workflow DAG\n");
                return -1;
            }
        }
    }
    
    free(color);
    dag->is_acyclic = true;
    printf("Orchestrator: DAG validated as acyclic\n");
    return 0;
}

static int calculate_topological_levels(workflow_dag_t* dag) {
    if (!dag || !dag->is_acyclic) {
        return -EINVAL;
    }
    
    // Kahn's algorithm for topological sorting with level calculation
    uint32_t* in_degree = malloc(dag->node_count * sizeof(uint32_t));
    if (!in_degree) {
        return -ENOMEM;
    }
    
    // Initialize in-degrees
    for (uint32_t i = 0; i < dag->node_count; i++) {
        in_degree[i] = dag->nodes[i].in_degree;
        dag->nodes[i].level = 0;
    }
    
    // Queue for nodes with no incoming edges
    uint32_t* queue = malloc(dag->node_count * sizeof(uint32_t));
    uint32_t queue_start = 0, queue_end = 0;
    
    // Find initial nodes (no dependencies)
    for (uint32_t i = 0; i < dag->node_count; i++) {
        if (in_degree[i] == 0) {
            queue[queue_end++] = i;
            dag->nodes[i].level = 0;
        }
    }
    
    dag->max_level = 0;
    
    // Process nodes level by level
    while (queue_start < queue_end) {
        uint32_t node_idx = queue[queue_start++];
        dag_node_t* node = &dag->nodes[node_idx];
        
        // Update levels of dependent nodes
        for (uint32_t i = 0; i < node->out_degree; i++) {
            dag_node_t* dependent = node->outgoing[i];
            uint32_t dep_idx = dependent - dag->nodes;
            
            in_degree[dep_idx]--;
            
            // Update level (max of all dependency levels + 1)
            if (dependent->level <= node->level) {
                dependent->level = node->level + 1;
                dag->max_level = (dependent->level > dag->max_level) ? 
                                dependent->level : dag->max_level;
            }
            
            if (in_degree[dep_idx] == 0) {
                queue[queue_end++] = dep_idx;
            }
        }
    }
    
    free(in_degree);
    free(queue);
    
    printf("Orchestrator: Calculated topological levels (max level: %u)\n", dag->max_level);
    return 0;
}

static int calculate_critical_path(workflow_context_t* workflow, workflow_dag_t* dag) {
    if (!workflow || !dag || !dag->is_acyclic) {
        return -EINVAL;
    }
    
    // Forward pass - calculate earliest start times
    for (uint32_t level = 0; level <= dag->max_level; level++) {
        for (uint32_t i = 0; i < dag->node_count; i++) {
            dag_node_t* node = &dag->nodes[i];
            
            if (node->level == level) {
                float max_finish_time = 0.0f;
                
                // Find maximum finish time of all dependencies
                for (uint32_t j = 0; j < node->in_degree; j++) {
                    dag_node_t* dep_node = node->incoming[j];
                    
                    // Get task duration
                    float task_duration = 60000.0f; // Default 1 minute
                    for (uint32_t k = 0; k < workflow->task_count; k++) {
                        if (workflow->tasks[k].task_id == dep_node->task_id) {
                            task_duration = (float)workflow->tasks[k].timeout_ms;
                            break;
                        }
                    }
                    
                    float finish_time = dep_node->earliest_start_time + task_duration;
                    max_finish_time = (finish_time > max_finish_time) ? finish_time : max_finish_time;
                }
                
                node->earliest_start_time = max_finish_time;
            }
        }
    }
    
    // Find total project duration
    float max_project_duration = 0.0f;
    for (uint32_t i = 0; i < dag->node_count; i++) {
        dag_node_t* node = &dag->nodes[i];
        
        if (node->out_degree == 0) { // End node
            float task_duration = 60000.0f;
            for (uint32_t j = 0; j < workflow->task_count; j++) {
                if (workflow->tasks[j].task_id == node->task_id) {
                    task_duration = (float)workflow->tasks[j].timeout_ms;
                    break;
                }
            }
            
            float finish_time = node->earliest_start_time + task_duration;
            max_project_duration = (finish_time > max_project_duration) ? 
                                  finish_time : max_project_duration;
        }
    }
    
    dag->total_estimated_time = max_project_duration;
    
    // Backward pass - calculate latest start times and slack
    for (uint32_t i = 0; i < dag->node_count; i++) {
        dag_node_t* node = &dag->nodes[i];
        
        if (node->out_degree == 0) {
            node->latest_start_time = node->earliest_start_time;
        } else {
            node->latest_start_time = max_project_duration;
            
            for (uint32_t j = 0; j < node->out_degree; j++) {
                dag_node_t* dep_node = node->outgoing[j];
                float start_time = dep_node->latest_start_time;
                
                // Get current node's task duration
                float task_duration = 60000.0f;
                for (uint32_t k = 0; k < workflow->task_count; k++) {
                    if (workflow->tasks[k].task_id == node->task_id) {
                        task_duration = (float)workflow->tasks[k].timeout_ms;
                        break;
                    }
                }
                
                float required_start = start_time - task_duration;
                node->latest_start_time = (required_start < node->latest_start_time) ? 
                                         required_start : node->latest_start_time;
            }
        }
        
        // Calculate slack time
        node->slack_time = node->latest_start_time - node->earliest_start_time;
        
        // Mark critical path nodes (zero slack)
        node->in_critical_path = (node->slack_time < 1000.0f); // Less than 1 second slack
    }
    
    // Count critical path nodes
    uint32_t critical_nodes = 0;
    for (uint32_t i = 0; i < dag->node_count; i++) {
        if (dag->nodes[i].in_critical_path) {
            critical_nodes++;
        }
    }
    
    dag->critical_path_length = critical_nodes;
    
    printf("Orchestrator: Critical path calculated - %u nodes, %.1fs total duration\n", 
           critical_nodes, dag->total_estimated_time / 1000.0f);
    
    return 0;
}

static bool are_task_dependencies_satisfied(const workflow_context_t* workflow, 
                                           const workflow_task_t* task) {
    for (uint32_t i = 0; i < task->dependency_count; i++) {
        uint32_t dep_task_id = task->dependencies[i];
        
        // Find dependency task
        bool dep_completed = false;
        for (uint32_t j = 0; j < workflow->task_count; j++) {
            if (workflow->tasks[j].task_id == dep_task_id) {
                dep_completed = (workflow->tasks[j].state == TASK_STATE_COMPLETED);
                break;
            }
        }
        
        if (!dep_completed) {
            return false;
        }
    }
    
    return true;
}

static workflow_task_t* select_next_task_dag_priority(workflow_context_t* workflow, 
                                                     workflow_dag_t* dag) {
    if (!workflow || !dag) {
        return NULL;
    }
    
    workflow_task_t* best_task = NULL;
    float best_priority_score = -1.0f;
    
    for (uint32_t i = 0; i < workflow->task_count; i++) {
        workflow_task_t* task = &workflow->tasks[i];
        
        if (task->state != TASK_STATE_PENDING) {
            continue;
        }
        
        if (!are_task_dependencies_satisfied(workflow, task)) {
            continue;
        }
        
        // Find corresponding DAG node
        dag_node_t* dag_node = NULL;
        for (uint32_t j = 0; j < dag->node_count; j++) {
            if (dag->nodes[j].task_id == task->task_id) {
                dag_node = &dag->nodes[j];
                break;
            }
        }
        
        if (!dag_node) {
            continue;
        }
        
        // Calculate priority score based on:
        // 1. Critical path membership (highest priority)
        // 2. Low slack time (earlier scheduling needed)
        // 3. Task priority level
        // 4. Topological level (earlier dependencies)
        
        float priority_score = 0.0f;
        
        if (dag_node->in_critical_path) {
            priority_score += 100.0f; // Critical path gets highest priority
        }
        
        // Inverse slack time (lower slack = higher priority)
        priority_score += (10000.0f - dag_node->slack_time) / 100.0f;
        
        // Task priority
        switch (task->priority) {
            case PRIORITY_EMERGENCY: priority_score += 50.0f; break;
            case PRIORITY_CRITICAL: priority_score += 40.0f; break;
            case PRIORITY_HIGH: priority_score += 30.0f; break;
            case PRIORITY_NORMAL: priority_score += 20.0f; break;
            case PRIORITY_LOW: priority_score += 10.0f; break;
            case PRIORITY_BACKGROUND: priority_score += 5.0f; break;
        }
        
        // Prefer earlier levels (foundational tasks)
        priority_score += (10.0f - (float)dag_node->level);
        
        if (priority_score > best_priority_score) {
            best_priority_score = priority_score;
            best_task = task;
        }
    }
    
    return best_task;
}

static int execute_task(workflow_task_t* task) {
    printf("Orchestrator: Executing task '%s' (Action: %s)\n", task->name, task->action);
    
    task->state = TASK_STATE_RUNNING;
    atomic_store(&task->metrics.start_time_ns, get_timestamp_ns());
    
    // Here we would delegate to the actual agent
    // For simulation, vary execution time based on task type
    uint32_t execution_time_ms = 1000;  // Default 1 second
    
    switch (task->type) {
        case TASK_TYPE_ANALYSIS:
            execution_time_ms = 2000 + (rand() % 3000);  // 2-5 seconds
            break;
        case TASK_TYPE_BUILD:
            execution_time_ms = 5000 + (rand() % 10000); // 5-15 seconds
            break;
        case TASK_TYPE_TEST:
            execution_time_ms = 3000 + (rand() % 7000);  // 3-10 seconds
            break;
        case TASK_TYPE_DEPLOY:
            execution_time_ms = 4000 + (rand() % 6000);  // 4-10 seconds
            break;
        case TASK_TYPE_SECURITY:
            execution_time_ms = 6000 + (rand() % 9000);  // 6-15 seconds
            break;
        case TASK_TYPE_DOCUMENTATION:
            execution_time_ms = 1500 + (rand() % 2500);  // 1.5-4 seconds
            break;
        default:
            execution_time_ms = 1000 + (rand() % 2000);  // 1-3 seconds
            break;
    }
    
    // Simulate execution
    usleep(execution_time_ms * 1000);
    
    // Simulate success/failure based on priority (higher priority = higher success rate)
    int success_rate = 95;  // Default 95%
    switch (task->priority) {
        case PRIORITY_EMERGENCY:
        case PRIORITY_CRITICAL:
            success_rate = 98;
            break;
        case PRIORITY_HIGH:
            success_rate = 96;
            break;
        case PRIORITY_NORMAL:
            success_rate = 94;
            break;
        case PRIORITY_LOW:
            success_rate = 92;
            break;
        case PRIORITY_BACKGROUND:
            success_rate = 90;
            break;
    }
    
    bool success = (rand() % 100) < success_rate;
    
    atomic_store(&task->metrics.end_time_ns, get_timestamp_ns());
    atomic_store(&task->metrics.execution_time_ms, execution_time_ms);
    
    // Simulate resource usage
    atomic_store(&task->metrics.cpu_time_ms, execution_time_ms * (80 + rand() % 20) / 100);
    atomic_store(&task->metrics.memory_peak_mb, 64 + (rand() % 192));  // 64-256 MB
    
    if (success) {
        task->state = TASK_STATE_COMPLETED;
        task->exit_code = 0;
        task->metrics.efficiency_score = 0.8f + (float)(rand() % 20) / 100.0f;  // 0.8-1.0
        task->metrics.quality_score = 0.85f + (float)(rand() % 15) / 100.0f;   // 0.85-1.0
        
        snprintf(task->result_data, sizeof(task->result_data), 
                "Task completed successfully in %ums", execution_time_ms);
    } else {
        task->state = TASK_STATE_FAILED;
        task->exit_code = 1;
        task->metrics.efficiency_score = 0.3f + (float)(rand() % 40) / 100.0f;  // 0.3-0.7
        task->metrics.quality_score = 0.2f + (float)(rand() % 30) / 100.0f;    // 0.2-0.5
        
        strcpy(task->error_message, "Simulated task execution failure");
    }
    
    atomic_fetch_add(&g_orchestrator->stats.tasks_executed, 1);
    if (!success) {
        atomic_fetch_add(&g_orchestrator->stats.tasks_failed, 1);
    }
    
    return success ? 0 : -1;
}

static void* workflow_executor_thread(void* arg) {
    executor_thread_t* executor = (executor_thread_t*)arg;
    
    // Set CPU affinity
    cpu_set_t cpuset;
    CPU_ZERO(&cpuset);
    CPU_SET(executor->cpu_id, &cpuset);
    sched_setaffinity(0, sizeof(cpu_set_t), &cpuset);
    
    char thread_name[16];
    snprintf(thread_name, sizeof(thread_name), "wf_exec_%d", executor->thread_id);
    pthread_setname_np(pthread_self(), thread_name);
    
    // Local DAG cache for workflows
    workflow_dag_t* workflow_dags = calloc(MAX_WORKFLOWS, sizeof(workflow_dag_t));
    if (!workflow_dags) {
        printf("Orchestrator: Failed to allocate DAG cache for executor %d\n", executor->thread_id);
        return NULL;
    }
    
    while (executor->running && g_orchestrator->running) {
        bool found_work = false;
        
        pthread_rwlock_rdlock(&g_orchestrator->workflows_lock);
        
        // Look for running workflows with ready tasks
        for (uint32_t i = 0; i < MAX_WORKFLOWS && executor->running; i++) {
            workflow_context_t* workflow = &g_orchestrator->workflows[i];
            
            if (workflow->workflow_id == 0 || workflow->state != WORKFLOW_STATE_RUNNING) {
                continue;
            }
            
            pthread_mutex_lock(&workflow->lock);
            
            // Build/update DAG for this workflow if needed
            workflow_dag_t* dag = &workflow_dags[i];
            if (dag->node_count == 0 || dag->node_count != workflow->task_count) {
                printf("Orchestrator: Building DAG for workflow '%s'\n", workflow->name);
                
                if (build_workflow_dag(workflow, dag) == 0 &&
                    validate_dag_acyclic(dag) == 0 &&
                    calculate_topological_levels(dag) == 0 &&
                    calculate_critical_path(workflow, dag) == 0) {
                    
                    printf("Orchestrator: DAG analysis complete - Critical path: %u tasks, Est. time: %.1fs\n",
                           dag->critical_path_length, dag->total_estimated_time / 1000.0f);
                } else {
                    printf("Orchestrator: Failed to build DAG, falling back to simple scheduling\n");
                    dag->node_count = 0; // Mark as invalid
                }
            }
            
            // Select next task using DAG-based priority scheduling
            workflow_task_t* selected_task = NULL;
            
            if (dag->node_count > 0 && dag->is_acyclic) {
                // Use advanced DAG-based scheduling
                selected_task = select_next_task_dag_priority(workflow, dag);
            } else {
                // Fall back to simple dependency-based scheduling
                for (uint32_t j = 0; j < workflow->task_count; j++) {
                    workflow_task_t* task = &workflow->tasks[j];
                    
                    if (task->state == TASK_STATE_PENDING &&
                        are_task_dependencies_satisfied(workflow, task)) {
                        selected_task = task;
                        break;
                    }
                }
            }
            
            if (selected_task) {
                // Check parallel execution limits
                if (workflow->strategy == STRATEGY_PARALLEL_LIMITED &&
                    workflow->tasks_running >= workflow->max_parallel_tasks) {
                    selected_task = NULL;
                }
                
                if (workflow->strategy == STRATEGY_SEQUENTIAL &&
                    workflow->tasks_running > 0) {
                    selected_task = NULL;
                }
            }
            
            if (selected_task) {
                // Assign and execute task
                selected_task->state = TASK_STATE_QUEUED;
                selected_task->assigned_agent_id = executor->thread_id;
                workflow->tasks_pending--;
                workflow->tasks_running++;
                found_work = true;
                
                atomic_fetch_add(&g_orchestrator->stats.active_tasks, 1);
                
                // Find corresponding DAG node for metrics
                dag_node_t* dag_node = NULL;
                if (dag->node_count > 0) {
                    for (uint32_t k = 0; k < dag->node_count; k++) {
                        if (dag->nodes[k].task_id == selected_task->task_id) {
                            dag_node = &dag->nodes[k];
                            break;
                        }
                    }
                }
                
                if (dag_node && dag_node->in_critical_path) {
                    printf("Orchestrator: Executing CRITICAL PATH task '%s' (Level %u, Slack: %.1fs)\n",
                           selected_task->name, dag_node->level, dag_node->slack_time / 1000.0f);
                } else {
                    printf("Orchestrator: Executing task '%s'\n", selected_task->name);
                }
                
                // Execute task
                uint64_t task_start_time = get_timestamp_ns();
                int result = execute_task(selected_task);
                uint64_t task_execution_time = get_timestamp_ns() - task_start_time;
                
                // Update workflow state
                workflow->tasks_running--;
                if (result == 0) {
                    workflow->tasks_completed++;
                    
                    // Update DAG timing if available
                    if (dag_node) {
                        float actual_duration = task_execution_time / 1000000.0f; // Convert to ms
                        printf("Orchestrator: Task completed in %.1fms (estimated: %ums)\n",
                               actual_duration, selected_task->timeout_ms);
                    }
                } else {
                    workflow->tasks_failed++;
                    
                    // Retry logic
                    uint32_t retry_count = atomic_load(&selected_task->metrics.retry_count);
                    if (retry_count < selected_task->max_retries) {
                        atomic_fetch_add(&selected_task->metrics.retry_count, 1);
                        atomic_fetch_add(&g_orchestrator->stats.tasks_retried, 1);
                        selected_task->state = TASK_STATE_PENDING;
                        workflow->tasks_failed--;
                        workflow->tasks_pending++;
                        printf("Orchestrator: Retrying task '%s' (attempt %u/%u)\n",
                               selected_task->name, retry_count + 2, selected_task->max_retries + 1);
                    } else if (dag_node && dag_node->in_critical_path) {
                        printf("Orchestrator: WARNING - Critical path task '%s' failed permanently\n",
                               selected_task->name);
                    }
                }
                
                atomic_fetch_sub(&g_orchestrator->stats.active_tasks, 1);
                
                // Update workflow progress
                workflow->progress_percentage = calculate_workflow_progress(workflow);
                
                // Update estimated completion time based on DAG
                if (dag->node_count > 0 && dag->total_estimated_time > 0) {
                    float remaining_work = (float)(workflow->task_count - workflow->tasks_completed) / workflow->task_count;
                    workflow->estimated_completion_ms = (uint32_t)(dag->total_estimated_time * remaining_work);
                }
                
                // Check if workflow is complete
                if (workflow->tasks_completed + workflow->tasks_failed >= workflow->task_count) {
                    bool has_failed_tasks = false;
                    uint32_t failed_critical_tasks = 0;
                    
                    for (uint32_t k = 0; k < workflow->task_count; k++) {
                        if (workflow->tasks[k].state == TASK_STATE_FAILED) {
                            has_failed_tasks = true;
                            
                            // Check if failed task was on critical path
                            if (dag->node_count > 0) {
                                for (uint32_t l = 0; l < dag->node_count; l++) {
                                    if (dag->nodes[l].task_id == workflow->tasks[k].task_id &&
                                        dag->nodes[l].in_critical_path) {
                                        failed_critical_tasks++;
                                        break;
                                    }
                                }
                            }
                        }
                    }
                    
                    if (has_failed_tasks) {
                        workflow->state = WORKFLOW_STATE_FAILED;
                        atomic_fetch_add(&g_orchestrator->stats.workflows_failed, 1);
                        
                        if (failed_critical_tasks > 0) {
                            printf("Orchestrator: Workflow '%s' FAILED - %u critical path tasks failed\n",
                                   workflow->name, failed_critical_tasks);
                        }
                    } else {
                        workflow->state = WORKFLOW_STATE_COMPLETED;
                        atomic_fetch_add(&g_orchestrator->stats.workflows_completed, 1);
                    }
                    
                    workflow->end_time_ns = get_timestamp_ns();
                    float actual_duration = (workflow->end_time_ns - workflow->start_time_ns) / 1000000000.0f;
                    float estimated_duration = dag->total_estimated_time / 1000.0f;
                    
                    atomic_fetch_sub(&g_orchestrator->stats.active_workflows, 1);
                    
                    pthread_cond_broadcast(&workflow->state_changed);
                    
                    printf("Orchestrator: Workflow '%s' %s (%.1f%% complete, %.1fs actual vs %.1fs estimated)\n",
                           workflow->name,
                           workflow->state == WORKFLOW_STATE_COMPLETED ? "COMPLETED" : "FAILED",
                           workflow->progress_percentage, actual_duration, estimated_duration);
                }
            }
            
            pthread_mutex_unlock(&workflow->lock);
            
            if (found_work) break;  // Found work, check other workflows next iteration
        }
        
        pthread_rwlock_unlock(&g_orchestrator->workflows_lock);
        
        if (!found_work) {
            usleep(50000);  // Sleep 50ms if no work found
        } else {
            atomic_fetch_add(&executor->tasks_processed, 1);
            atomic_fetch_add(&executor->processing_time_ns, get_timestamp_ns() - (executor->processing_time_ns / 1000000ULL));
        }
    }
    
    free(workflow_dags);
    return NULL;
}

int start_workflow_execution(uint32_t workflow_id) {
    if (!g_orchestrator) {
        return -EINVAL;
    }
    
    // Find workflow
    workflow_context_t* workflow = NULL;
    pthread_rwlock_rdlock(&g_orchestrator->workflows_lock);
    
    for (uint32_t i = 0; i < MAX_WORKFLOWS; i++) {
        if (g_orchestrator->workflows[i].workflow_id == workflow_id) {
            workflow = &g_orchestrator->workflows[i];
            break;
        }
    }
    
    if (!workflow) {
        pthread_rwlock_unlock(&g_orchestrator->workflows_lock);
        return -ENOENT;
    }
    
    pthread_mutex_lock(&workflow->lock);
    
    if (workflow->state != WORKFLOW_STATE_CREATED && workflow->state != WORKFLOW_STATE_PLANNED) {
        pthread_mutex_unlock(&workflow->lock);
        pthread_rwlock_unlock(&g_orchestrator->workflows_lock);
        return -EINVAL;  // Workflow already started or completed
    }
    
    workflow->state = WORKFLOW_STATE_RUNNING;
    workflow->start_time_ns = get_timestamp_ns();
    atomic_fetch_add(&g_orchestrator->stats.active_workflows, 1);
    
    pthread_mutex_unlock(&workflow->lock);
    pthread_rwlock_unlock(&g_orchestrator->workflows_lock);
    
    printf("Orchestrator: Started execution of workflow '%s' (ID: %u)\n", 
           workflow->name, workflow_id);
    
    return 0;
}

int start_orchestrator_threads() {
    if (!g_orchestrator) {
        return -EINVAL;
    }
    
    // Start executor threads
    for (uint32_t i = 0; i < g_orchestrator->executor_count; i++) {
        int ret = pthread_create(&g_orchestrator->executors[i].thread, NULL,
                               workflow_executor_thread, &g_orchestrator->executors[i]);
        if (ret != 0) {
            printf("Orchestrator: Failed to start executor thread %u: %s\n", i, strerror(ret));
            return ret;
        }
    }
    
    printf("Orchestrator: Started %u execution threads\n", g_orchestrator->executor_count);
    return 0;
}

// ============================================================================
// STATISTICS AND MONITORING
// ============================================================================

void print_orchestrator_statistics() {
    if (!g_orchestrator) {
        printf("Project Orchestrator service not initialized\n");
        return;
    }
    
    printf("\n=== Project Orchestrator Service Statistics ===\n");
    printf("Projects created: %lu\n", atomic_load(&g_orchestrator->stats.projects_created));
    printf("Workflows created: %lu\n", atomic_load(&g_orchestrator->stats.workflows_created));
    printf("Workflows completed: %lu\n", atomic_load(&g_orchestrator->stats.workflows_completed));
    printf("Workflows failed: %lu\n", atomic_load(&g_orchestrator->stats.workflows_failed));
    printf("Tasks executed: %lu\n", atomic_load(&g_orchestrator->stats.tasks_executed));
    printf("Tasks failed: %lu\n", atomic_load(&g_orchestrator->stats.tasks_failed));
    printf("Tasks retried: %lu\n", atomic_load(&g_orchestrator->stats.tasks_retried));
    printf("Active workflows: %u\n", atomic_load(&g_orchestrator->stats.active_workflows));
    printf("Active tasks: %u\n", atomic_load(&g_orchestrator->stats.active_tasks));
    
    // Project summary
    printf("\nProjects:\n");
    printf("%-8s %-25s %-12s %-10s %-12s\n",
           "ID", "Name", "State", "Workflows", "Success Rate");
    printf("%-8s %-25s %-12s %-10s %-12s\n",
           "--------", "-------------------------", "------------",
           "----------", "------------");
    
    pthread_rwlock_rdlock(&g_orchestrator->projects_lock);
    
    for (uint32_t i = 0; i < MAX_PROJECTS; i++) {
        project_context_t* project = &g_orchestrator->projects[i];
        
        if (project->project_id == 0) continue;
        
        const char* state_str = "UNKNOWN";
        switch (project->state) {
            case PROJECT_STATE_INITIALIZING: state_str = "INIT"; break;
            case PROJECT_STATE_ACTIVE: state_str = "ACTIVE"; break;
            case PROJECT_STATE_PAUSED: state_str = "PAUSED"; break;
            case PROJECT_STATE_COMPLETED: state_str = "COMPLETED"; break;
            case PROJECT_STATE_ARCHIVED: state_str = "ARCHIVED"; break;
            case PROJECT_STATE_FAILED: state_str = "FAILED"; break;
        }
        
        printf("%-8u %-25s %-12s %-10u %-11.1f%%\n",
               project->project_id, project->name, state_str, 
               project->workflow_count, project->overall_success_rate * 100.0f);
    }
    
    pthread_rwlock_unlock(&g_orchestrator->projects_lock);
    
    // Workflow summary
    printf("\nActive Workflows:\n");
    printf("%-8s %-25s %-12s %-8s %-8s %-10s\n",
           "ID", "Name", "State", "Tasks", "Progress", "Strategy");
    printf("%-8s %-25s %-12s %-8s %-8s %-10s\n",
           "--------", "-------------------------", "------------",
           "--------", "--------", "----------");
    
    pthread_rwlock_rdlock(&g_orchestrator->workflows_lock);
    
    for (uint32_t i = 0; i < MAX_WORKFLOWS; i++) {
        workflow_context_t* workflow = &g_orchestrator->workflows[i];
        
        if (workflow->workflow_id == 0) continue;
        
        const char* state_str = "UNKNOWN";
        switch (workflow->state) {
            case WORKFLOW_STATE_CREATED: state_str = "CREATED"; break;
            case WORKFLOW_STATE_PLANNED: state_str = "PLANNED"; break;
            case WORKFLOW_STATE_RUNNING: state_str = "RUNNING"; break;
            case WORKFLOW_STATE_PAUSED: state_str = "PAUSED"; break;
            case WORKFLOW_STATE_COMPLETED: state_str = "COMPLETED"; break;
            case WORKFLOW_STATE_FAILED: state_str = "FAILED"; break;
            case WORKFLOW_STATE_CANCELLED: state_str = "CANCELLED"; break;
            case WORKFLOW_STATE_RECOVERING: state_str = "RECOVERY"; break;
        }
        
        const char* strategy_str = "UNKNOWN";
        switch (workflow->strategy) {
            case STRATEGY_SEQUENTIAL: strategy_str = "SEQUENTIAL"; break;
            case STRATEGY_PARALLEL_UNLIMITED: strategy_str = "PARALLEL"; break;
            case STRATEGY_PARALLEL_LIMITED: strategy_str = "PAR_LIM"; break;
            case STRATEGY_PIPELINE: strategy_str = "PIPELINE"; break;
            case STRATEGY_ADAPTIVE: strategy_str = "ADAPTIVE"; break;
        }
        
        printf("%-8u %-25s %-12s %-8u %-7.1f%% %-10s\n",
               workflow->workflow_id, workflow->name, state_str,
               workflow->task_count, workflow->progress_percentage, strategy_str);
    }
    
    pthread_rwlock_unlock(&g_orchestrator->workflows_lock);
    
    // Executor thread performance
    printf("\nExecutor Threads:\n");
    printf("%-8s %-8s %-12s %-15s\n", "ID", "CPU", "Tasks Proc", "Avg Time (μs)");
    printf("%-8s %-8s %-12s %-15s\n", "--------", "--------", "------------", "---------------");
    
    for (uint32_t i = 0; i < g_orchestrator->executor_count; i++) {
        executor_thread_t* executor = &g_orchestrator->executors[i];
        
        uint64_t tasks_processed = atomic_load(&executor->tasks_processed);
        uint64_t processing_time = atomic_load(&executor->processing_time_ns);
        uint64_t avg_time_us = tasks_processed > 0 ? processing_time / (tasks_processed * 1000) : 0;
        
        printf("%-8d %-8d %-12lu %-15lu\n",
               executor->thread_id, executor->cpu_id, tasks_processed, avg_time_us);
    }
    
    printf("\n");
}

// ============================================================================
// EXAMPLE USAGE AND TESTING
// ============================================================================

#ifdef ORCHESTRATOR_TEST_MODE

int main() {
    printf("Project Orchestrator Agent Test\n");
    printf("===============================\n");
    
    // Initialize orchestrator service
    if (orchestrator_service_init() != 0) {
        printf("Failed to initialize orchestrator service\n");
        return 1;
    }
    
    // Create test project
    uint32_t project_id = create_project("Web Application Development",
                                        "Complete full-stack web application development project",
                                        4);
    if (project_id == 0) {
        printf("Failed to create project\n");
        return 1;
    }
    
    // Activate project
    if (activate_project(project_id) != 0) {
        printf("Failed to activate project\n");
        return 1;
    }
    
    // Create comprehensive workflow
    uint32_t workflow_id = create_workflow(project_id, "Full Development Pipeline",
                                         "Complete CI/CD pipeline with testing and deployment",
                                         STRATEGY_PARALLEL_LIMITED, 6);
    if (workflow_id == 0) {
        printf("Failed to create workflow\n");
        return 1;
    }
    
    // Add workflow tasks
    uint32_t task1 = add_workflow_task(workflow_id, "Code Analysis", 
                                      "Static code analysis and security scan",
                                      TASK_TYPE_ANALYSIS, PRIORITY_HIGH,
                                      3, "static_analysis", "analyze_codebase", 
                                      "target=src/ depth=full", 30000);
                                      
    uint32_t task2 = add_workflow_task(workflow_id, "Unit Tests",
                                      "Run comprehensive unit test suite", 
                                      TASK_TYPE_TEST, PRIORITY_CRITICAL,
                                      5, "unit_testing", "run_tests",
                                      "suite=unit coverage=90", 60000);
                                      
    uint32_t task3 = add_workflow_task(workflow_id, "Build Frontend",
                                      "Build and optimize frontend assets",
                                      TASK_TYPE_BUILD, PRIORITY_HIGH,
                                      7, "frontend_build", "build_assets", 
                                      "mode=production optimize=true", 45000);
                                      
    uint32_t task4 = add_workflow_task(workflow_id, "Build Backend",
                                      "Compile and package backend services",
                                      TASK_TYPE_BUILD, PRIORITY_HIGH,
                                      8, "backend_build", "compile_services",
                                      "target=release optimization=O3", 90000);
                                      
    uint32_t task5 = add_workflow_task(workflow_id, "Integration Tests", 
                                      "End-to-end integration testing",
                                      TASK_TYPE_TEST, PRIORITY_HIGH,
                                      5, "integration_testing", "run_e2e_tests",
                                      "environment=staging timeout=300", 180000);
                                      
    uint32_t task6 = add_workflow_task(workflow_id, "Security Scan",
                                      "Comprehensive security vulnerability scan",
                                      TASK_TYPE_SECURITY, PRIORITY_CRITICAL,
                                      3, "security_scan", "scan_vulnerabilities",
                                      "depth=full include_deps=true", 120000);
                                      
    uint32_t task7 = add_workflow_task(workflow_id, "Performance Tests",
                                      "Load and performance testing",
                                      TASK_TYPE_TEST, PRIORITY_NORMAL,
                                      5, "performance_testing", "run_load_tests",
                                      "users=1000 duration=300", 300000);
                                      
    uint32_t task8 = add_workflow_task(workflow_id, "Documentation",
                                      "Generate API and user documentation", 
                                      TASK_TYPE_DOCUMENTATION, PRIORITY_NORMAL,
                                      16, "doc_generation", "generate_docs",
                                      "format=html include_api=true", 60000);
                                      
    uint32_t task9 = add_workflow_task(workflow_id, "Deploy Staging",
                                      "Deploy to staging environment",
                                      TASK_TYPE_DEPLOY, PRIORITY_HIGH,
                                      26, "deployment", "deploy_application",
                                      "target=staging health_check=true", 120000);
                                      
    uint32_t task10 = add_workflow_task(workflow_id, "Deploy Production",
                                       "Deploy to production environment", 
                                       TASK_TYPE_DEPLOY, PRIORITY_CRITICAL,
                                       26, "deployment", "deploy_application", 
                                       "target=production rollback=enabled", 180000);
    
    // Add task dependencies
    add_task_dependency(workflow_id, task2, task1);    // Unit tests after analysis
    add_task_dependency(workflow_id, task3, task2);    // Frontend build after tests  
    add_task_dependency(workflow_id, task4, task2);    // Backend build after tests
    add_task_dependency(workflow_id, task5, task3);    // Integration tests after frontend
    add_task_dependency(workflow_id, task5, task4);    // Integration tests after backend
    add_task_dependency(workflow_id, task6, task4);    // Security scan after backend
    add_task_dependency(workflow_id, task7, task5);    // Performance tests after integration
    add_task_dependency(workflow_id, task8, task5);    // Documentation after integration
    add_task_dependency(workflow_id, task9, task6);    // Staging after security scan
    add_task_dependency(workflow_id, task9, task7);    // Staging after performance tests
    add_task_dependency(workflow_id, task10, task9);   // Production after staging
    
    printf("Created workflow with %u tasks and dependencies\n", 10);
    
    // Start executor threads
    if (start_orchestrator_threads() != 0) {
        printf("Failed to start orchestrator threads\n");
        return 1;
    }
    
    // Start workflow execution
    if (start_workflow_execution(workflow_id) != 0) {
        printf("Failed to start workflow execution\n");
        return 1;
    }
    
    // Monitor execution
    printf("\nMonitoring workflow execution...\n");
    
    for (int i = 0; i < 60; i++) {  // Monitor for 60 seconds
        sleep(1);
        
        if (i % 10 == 0) {  // Print stats every 10 seconds
            print_orchestrator_statistics();
        }
        
        // Check if workflow completed
        pthread_rwlock_rdlock(&g_orchestrator->workflows_lock);
        bool workflow_done = false;
        for (uint32_t j = 0; j < MAX_WORKFLOWS; j++) {
            if (g_orchestrator->workflows[j].workflow_id == workflow_id) {
                workflow_state_t state = g_orchestrator->workflows[j].state;
                workflow_done = (state == WORKFLOW_STATE_COMPLETED || 
                               state == WORKFLOW_STATE_FAILED);
                break;
            }
        }
        pthread_rwlock_unlock(&g_orchestrator->workflows_lock);
        
        if (workflow_done) {
            printf("Workflow execution completed!\n");
            break;
        }
    }
    
    // Final statistics
    print_orchestrator_statistics();
    
    // Cleanup
    orchestrator_service_cleanup();
    
    return 0;
}

#endif