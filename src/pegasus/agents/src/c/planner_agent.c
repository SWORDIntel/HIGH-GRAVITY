/*
 * DIRECTOR AGENT (Strategic Command) v1.0
 *
 * The apex decision-making and strategic oversight component of the ARCHITECT
 * system. This agent translates high-level, abstract directives into concrete,
 * actionable strategies. It leverages the Knowledge Graph for long-term state
 * and contextual understanding, orchestrates subordinate agents like the Planner
 * and Security specialists, and ensures all system actions align with overarching
 * mission goals.
 *
 * CORE MISSION:
 * 1. INTERPRET abstract user directives and strategic objectives.
 * 2. MODEL long-term goals and their dependencies within the Knowledge Graph.
 * 3. CONDUCT feasibility and risk analysis by querying specialist agents.
 * 4. FORMULATE high-level project plans and delegate execution to the Planner.
 * 5. PROVIDE continuous strategic oversight and adapt to changing conditions.
 * 6. MAINTAIN system-wide operational integrity and alignment with objectives.
 *
 * HARDWARE OPTIMIZATION (METEOR LAKE):
 * - Strategist Thread (Compute-intensive analysis, KG traversal): Affinity set to P-Cores.
 * - Operations/Monitor Threads (I/O, IPC, status checks): Affinity set to E-Cores.
 * - High-contention command queues utilize meteor_lake_spinlock_t.
 * - Strategic goal and system state structures use NUMA-aware, page-aligned memory.
 *
 * Author: ARCHITECT System Genesis
 * Version: 1.0.0 Production
 */

#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <stdbool.h>
#include <stdatomic.h>
#include <pthread.h>
#include <unistd.h>
#include <errno.h>
#include <sched.h>
#include <time.h>

// Stubs for inter-agent communication and hardware optimizations
#include "agent_protocol.h"
#include "compatibility_layer.h"
#include "meteor_lake_optimizations.h"

// ============================================================================
// CONSTANTS, ENUMS, AND CONFIGURATION
// ============================================================================

#define DIRECTOR_AGENT_ID 0
#define MAX_STRATEGIC_GOALS 64
#define MAX_RISKS_PER_GOAL 32
#define MAX_DIRECTIVES_QUEUE 128
#define MAX_SUB_PROJECTS 16
#define CACHE_LINE_SIZE 64
#define PAGE_SIZE 4096

// The state of a long-term strategic goal
typedef enum {
    GOAL_STATUS_UNINITIALIZED,
    GOAL_STATUS_DEFINED,
    GOAL_STATUS_ANALYZING_FEASIBILITY,
    GOAL_STATUS_RISK_ASSESSMENT,
    GOAL_STATUS_PENDING_APPROVAL,
    GOAL_STATUS_DELEGATED_TO_PLANNER,
    GOAL_STATUS_IN_EXECUTION,
    GOAL_STATUS_COMPLETED,
    GOAL_STATUS_FAILED,
    GOAL_STATUS_ARCHIVED
} goal_status_t;

// The type of strategic operation to be performed
typedef enum {
    STRATEGIC_OP_NEW_GOAL,
    STRATEGIC_OP_CANCEL_GOAL,
    STRATEGIC_OP_SYSTEM_HEALTH_CHECK,
    STRATEGIC_OP_KG_SYNCHRONIZE
} strategic_op_t;

// Risk level as determined by the Security Agent
typedef enum {
    RISK_LEVEL_NONE,
    RISK_LEVEL_LOW,
    RISK_LEVEL_MEDIUM,
    RISK_LEVEL_HIGH,
    RISK_LEVEL_CRITICAL
} risk_level_t;

// ============================================================================
// DATA STRUCTURES
// ============================================================================

// Represents a risk identified during analysis
typedef struct {
    char description[512];
    risk_level_t level;
    char mitigation_plan[1024];
    bool accepted;
} risk_assessment_t;

// Represents a sub-project delegated to the Planner Agent
typedef struct {
    uint32_t planner_project_id;
    char project_name[256];
    _Atomic bool is_complete;
} sub_project_t;

// Represents a high-level strategic goal (Page-aligned for performance)
typedef struct __attribute__((aligned(PAGE_SIZE))) {
    uint32_t goal_id;
    char directive[2048]; // The original high-level command
    _Atomic goal_status_t status;
    pthread_mutex_t lock;

    // Analysis Artifacts
    char feasibility_report[4096];
    risk_assessment_t risks[MAX_RISKS_PER_GOAL];
    uint32_t risk_count;
    float projected_resource_cost;
    float success_probability;

    // Execution Artifacts
    sub_project_t sub_projects[MAX_SUB_PROJECTS];
    uint32_t sub_project_count;

    // Timestamps
    uint64_t created_ns;
    uint64_t completed_ns;
} strategic_goal_t;

// A command submitted to the Director's internal queue
typedef struct {
    uint32_t directive_id;
    strategic_op_t operation;
    char payload[2048]; // Can be a new directive string, goal ID to cancel, etc.
} director_directive_t;


// System-wide metrics aggregated by the Director
typedef struct __attribute__((aligned(CACHE_LINE_SIZE))) {
    _Atomic uint32_t active_goals;
    _Atomic uint32_t total_projects_managed;
    _Atomic uint32_t critical_risks_accepted;
    _Atomic float overall_system_load;
    _Atomic float operational_readiness_score; // 0.0 - 1.0
} system_overview_metrics_t;


// Main Director Agent Service
typedef struct {
    uint32_t agent_id;
    char name[64];
    volatile bool running;

    // Strategic Goal Management
    strategic_goal_t* active_goals[MAX_STRATEGIC_GOALS];
    uint32_t goal_count;
    pthread_rwlock_t goals_lock;

    // Internal Command Queue
    director_directive_t directive_queue[MAX_DIRECTIVES_QUEUE];
    uint32_t directive_queue_head;
    uint32_t directive_queue_tail;
    meteor_lake_spinlock_t directive_queue_lock;
    pthread_cond_t directive_available_cond;

    // Worker Threads
    pthread_t strategist_thread; // P-Core: Analysis, Planning
    pthread_t operations_thread; // E-Core: Inter-agent communication
    pthread_t monitor_thread;    // E-Core: Health checks, metrics

    // System-wide view
    system_overview_metrics_t metrics;

} director_agent_t;

// Global agent instance
static director_agent_t* g_director_agent = NULL;

// ============================================================================
// FORWARD DECLARATIONS
// ============================================================================

// Service Lifecycle
int director_service_init();
void director_service_cleanup();
void print_director_statistics();

// External Interface
int submit_directive_to_director(const char* directive);

// Worker Thread Functions
void* director_strategist_thread(void* arg);
void* director_operations_thread(void* arg);
void* director_monitor_thread(void* arg);

// Core Logic
static strategic_goal_t* create_new_goal(const char* directive);
static void process_new_goal(strategic_goal_t* goal);
static void analyze_feasibility(strategic_goal_t* goal);
static void perform_risk_assessment(strategic_goal_t* goal);
static void delegate_goal_to_planner(strategic_goal_t* goal);
static void update_knowledge_graph_with_goal(const strategic_goal_t* goal, const char* event);
static const char* goal_status_to_string(goal_status_t status);

// Utility
static uint32_t generate_id();
static uint64_t get_timestamp_ns();


// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

static uint32_t generate_id() {
    static _Atomic uint32_t id_counter = 1;
    return atomic_fetch_add(&id_counter, 1);
}

static uint64_t get_timestamp_ns() {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (uint64_t)ts.tv_sec * 1000000000ULL + ts.tv_nsec;
}

// ============================================================================
// SERVICE INITIALIZATION & CLEANUP
// ============================================================================

int director_service_init() {
    fprintf(stderr, "Director Agent: Initializing Strategic Command...\n");
    if (g_director_agent) {
        fprintf(stderr, "Director Agent: Already initialized.\n");
        return -EALREADY;
    }

    // Allocate the main agent struct with NUMA awareness and page alignment
    g_director_agent = (director_agent_t*)meteor_lake_aligned_alloc(sizeof(director_agent_t), true);
    if (!g_director_agent) {
        perror("Director Agent: Failed to allocate memory");
        return -ENOMEM;
    }
    memset(g_director_agent, 0, sizeof(director_agent_t));

    // --- Initialize Agent State ---
    g_director_agent->agent_id = DIRECTOR_AGENT_ID;
    strncpy(g_director_agent->name, "Director_v1.0", sizeof(g_director_agent->name) - 1);
    g_director_agent->running = true;

    // --- Initialize Synchronization Primitives ---
    pthread_rwlock_init(&g_director_agent->goals_lock, NULL);
    meteor_lake_spinlock_init(&g_director_agent->directive_queue_lock);
    pthread_cond_init(&g_director_agent->directive_available_cond, NULL);

    // --- Initialize Metrics ---
    atomic_init(&g_director_agent->metrics.operational_readiness_score, 1.0f);

    // --- Start Worker Threads ---
    if (pthread_create(&g_director_agent->strategist_thread, NULL, director_strategist_thread, NULL) != 0 ||
        pthread_create(&g_director_agent->operations_thread, NULL, director_operations_thread, NULL) != 0 ||
        pthread_create(&g_director_agent->monitor_thread, NULL, director_monitor_thread, NULL) != 0) {
        
        fprintf(stderr, "Director Agent: Failed to create one or more worker threads. Aborting.\n");
        // A real implementation would have more robust teardown here
        free(g_director_agent);
        g_director_agent = NULL;
        return -EAGAIN;
    }

    fprintf(stderr, "Director Agent: Initialized with 3 worker threads.\n");
    if (is_meteor_lake_cpu()) {
        fprintf(stderr, "  Hardware: Meteor Lake CPU detected. Applying P/E-Core affinity optimizations.\n");
    }
    fprintf(stderr, "Director Agent: Strategic Command is online.\n");
    return 0;
}

void director_service_cleanup() {
    if (!g_director_agent) return;

    fprintf(stderr, "Director Agent: Shutting down Strategic Command...\n");
    g_director_agent->running = false;

    // Wake up and join all threads
    pthread_cond_broadcast(&g_director_agent->directive_available_cond);
    pthread_join(g_director_agent->strategist_thread, NULL);
    pthread_join(g_director_agent->operations_thread, NULL);
    pthread_join(g_director_agent->monitor_thread, NULL);

    // Destroy sync primitives
    pthread_rwlock_destroy(&g_director_agent->goals_lock);
    pthread_cond_destroy(&g_director_agent->directive_available_cond);

    // Free all allocated strategic goals
    pthread_rwlock_wrlock(&g_director_agent->goals_lock);
    for (uint32_t i = 0; i < g_director_agent->goal_count; i++) {
        pthread_mutex_destroy(&g_director_agent->active_goals[i]->lock);
        free(g_director_agent->active_goals[i]);
    }
    g_director_agent->goal_count = 0;
    pthread_rwlock_unlock(&g_director_agent->goals_lock);

    // Free the main agent struct
    free(g_director_agent);
    g_director_agent = NULL;

    fprintf(stderr, "Director Agent: Strategic Command is offline.\n");
}


// ============================================================================
// EXTERNAL COMMAND INTERFACE
// ============================================================================

/**
 * @brief Submits a new high-level directive to the Director Agent for processing.
 * This is the primary entry point for external commands.
 * @param directive A string describing the desired outcome.
 * @return 0 on success, negative error code on failure.
 */
int submit_directive_to_director(const char* directive) {
    if (!g_director_agent || !g_director_agent->running) {
        return -ESRCH; // Service not running
    }
    if (!directive || strlen(directive) == 0) {
        return -EINVAL; // Invalid argument
    }

    meteor_lake_spinlock_lock(&g_director_agent->directive_queue_lock);

    uint32_t next_tail = (g_director_agent->directive_queue_tail + 1) % MAX_DIRECTIVES_QUEUE;
    if (next_tail == g_director_agent->directive_queue_head) {
        meteor_lake_spinlock_unlock(&g_director_agent->directive_queue_lock);
        fprintf(stderr, "Director Agent: Directive queue is full. Command rejected.\n");
        return -EBUSY;
    }

    // Populate the new directive
    director_directive_t* new_cmd = &g_director_agent->directive_queue[g_director_agent->directive_queue_tail];
    new_cmd->directive_id = generate_id();
    new_cmd->operation = STRATEGIC_OP_NEW_GOAL;
    strncpy(new_cmd->payload, directive, sizeof(new_cmd->payload) - 1);
    new_cmd->payload[sizeof(new_cmd->payload) - 1] = '\0';

    // Advance the tail and signal the operations thread
    g_director_agent->directive_queue_tail = next_tail;
    
    pthread_cond_signal(&g_director_agent->directive_available_cond);
    meteor_lake_spinlock_unlock(&g_director_agent->directive_queue_lock);

    fprintf(stderr, "[Director] Directive received and queued (ID: %u).\n", new_cmd->directive_id);
    return 0;
}


// ============================================================================
// WORKER THREADS
// ============================================================================

/**
 * @brief P-Core Thread: Handles compute-intensive strategic analysis.
 * This thread is responsible for feasibility studies, KG traversals, and
 * complex problem decomposition.
 */
void* director_strategist_thread(void* arg) {
    // Pin this compute-heavy thread to Performance-Cores
    set_core_type_affinity(CORE_TYPE_P);
    pthread_setname_np(pthread_self(), "director_strategy");

    fprintf(stderr, "[Strategist Thread] Online. Affinity set to P-Cores.\n");

    while (g_director_agent->running) {
        bool work_done = false;
        pthread_rwlock_rdlock(&g_director_agent->goals_lock);

        for (uint32_t i = 0; i < g_director_agent->goal_count; ++i) {
            strategic_goal_t* goal = g_director_agent->active_goals[i];
            goal_status_t current_status = atomic_load(&goal->status);

            if (current_status == GOAL_STATUS_DEFINED ||
                current_status == GOAL_STATUS_ANALYZING_FEASIBILITY ||
                current_status == GOAL_STATUS_RISK_ASSESSMENT) {
                
                // Take ownership of the goal for processing
                pthread_mutex_lock(&goal->lock);
                // Re-check status after acquiring lock
                if (atomic_load(&goal->status) == current_status) {
                    process_new_goal(goal);
                    work_done = true;
                }
                pthread_mutex_unlock(&goal->lock);
            }
        }

        pthread_rwlock_unlock(&g_director_agent->goals_lock);

        if (!work_done) {
            // Sleep if there's no analysis to perform
            sleep(1);
        }
    }
    fprintf(stderr, "[Strategist Thread] Offline.\n");
    return NULL;
}

/**
 * @brief E-Core Thread: Handles command intake and inter-agent communication.
 * This thread dequeues new directives and dispatches tasks to other agents.
 * It is I/O-bound and suitable for Efficiency-Cores.
 */
void* director_operations_thread(void* arg) {
    // Pin this I/O-bound thread to Efficiency-Cores
    set_core_type_affinity(CORE_TYPE_E);
    pthread_setname_np(pthread_self(), "director_ops");

    fprintf(stderr, "[Operations Thread] Online. Affinity set to E-Cores.\n");

    while (g_director_agent->running) {
        meteor_lake_spinlock_lock(&g_director_agent->directive_queue_lock);

        // Wait for a new directive to become available
        while (g_director_agent->directive_queue_head == g_director_agent->directive_queue_tail && g_director_agent->running) {
            pthread_cond_wait(&g_director_agent->directive_available_cond, (pthread_mutex_t*)&g_director_agent->directive_queue_lock.lock);
        }

        if (!g_director_agent->running) {
            meteor_lake_spinlock_unlock(&g_director_agent->directive_queue_lock);
            break;
        }

        // Dequeue the next directive
        director_directive_t cmd = g_director_agent->directive_queue[g_director_agent->directive_queue_head];
        g_director_agent->directive_queue_head = (g_director_agent->directive_queue_head + 1) % MAX_DIRECTIVES_QUEUE;
        meteor_lake_spinlock_unlock(&g_director_agent->directive_queue_lock);

        // Process the directive
        switch (cmd.operation) {
            case STRATEGIC_OP_NEW_GOAL: {
                fprintf(stderr, "[Operations] Processing new goal directive: \"%s\"\n", cmd.payload);
                strategic_goal_t* new_goal = create_new_goal(cmd.payload);
                if (new_goal) {
                    pthread_rwlock_wrlock(&g_director_agent->goals_lock);
                    if (g_director_agent->goal_count < MAX_STRATEGIC_GOALS) {
                        g_director_agent->active_goals[g_director_agent->goal_count++] = new_goal;
                        atomic_fetch_add(&g_director_agent->metrics.active_goals, 1);
                    } else {
                        fprintf(stderr, "[Operations] Error: Max strategic goals reached. Cannot create new goal.\n");
                        free(new_goal);
                    }
                    pthread_rwlock_unlock(&g_director_agent->goals_lock);
                }
                break;
            }
            case STRATEGIC_OP_CANCEL_GOAL:
                // Implementation for cancelling a goal would go here
                break;
            default:
                fprintf(stderr, "[Operations] Warning: Unhandled directive operation type %d.\n", cmd.operation);
                break;
        }
    }
    fprintf(stderr, "[Operations Thread] Offline.\n");
    return NULL;
}


/**
 * @brief E-Core Thread: Handles background monitoring of system health and goal progress.
 * This thread is suitable for Efficiency-Cores as it performs periodic, low-intensity tasks.
 */
void* director_monitor_thread(void* arg) {
    set_core_type_affinity(CORE_TYPE_E);
    pthread_setname_np(pthread_self(), "director_monitor");
    
    fprintf(stderr, "[Monitor Thread] Online. Affinity set to E-Cores.\n");

    while(g_director_agent->running) {
        pthread_rwlock_rdlock(&g_director_agent->goals_lock);
        
        for (uint32_t i = 0; i < g_director_agent->goal_count; ++i) {
            strategic_goal_t* goal = g_director_agent->active_goals[i];
            if (atomic_load(&goal->status) == GOAL_STATUS_IN_EXECUTION) {
                // Simulate checking progress with the Planner agent
                // In a real system, this would involve IPC (e.g., check_planner_project_status)
                bool all_subprojects_done = true;
                if(goal->sub_project_count == 0) all_subprojects_done = false;

                for (uint32_t j = 0; j < goal->sub_project_count; ++j) {
                    if (!atomic_load(&goal->sub_projects[j].is_complete)) {
                        // Simulate a sub-project completing
                        if ((rand() % 100) > 80) {
                             atomic_store(&goal->sub_projects[j].is_complete, true);
                             fprintf(stderr, "[Monitor] Sub-project '%s' for Goal %u has completed.\n", goal->sub_projects[j].project_name, goal->goal_id);
                        } else {
                            all_subprojects_done = false;
                        }
                    }
                }
                
                if (all_subprojects_done) {
                    fprintf(stderr, "[Monitor] All sub-projects for Goal %u are complete. Finalizing goal.\n", goal->goal_id);
                    atomic_store(&goal->status, GOAL_STATUS_COMPLETED);
                    atomic_fetch_sub(&g_director_agent->metrics.active_goals, 1);
                    update_knowledge_graph_with_goal(goal, "GoalCompleted");
                }
            }
        }
        
        pthread_rwlock_unlock(&g_director_agent->goals_lock);
        
        // Wait for the next monitoring cycle
        sleep(5);
    }
    fprintf(stderr, "[Monitor Thread] Offline.\n");
    return NULL;
}


// ============================================================================
// CORE LOGIC IMPLEMENTATION
// ============================================================================

/**
 * @brief Allocates and initializes a new strategic_goal_t structure.
 * @param directive The directive string for the new goal.
 * @return A pointer to the newly created goal, or NULL on failure.
 */
static strategic_goal_t* create_new_goal(const char* directive) {
    // Allocate page-aligned memory for the goal structure
    strategic_goal_t* goal = (strategic_goal_t*)meteor_lake_aligned_alloc(sizeof(strategic_goal_t), true);
    if (!goal) {
        perror("Director Agent: Failed to allocate memory for new goal");
        return NULL;
    }
    memset(goal, 0, sizeof(strategic_goal_t));

    goal->goal_id = generate_id();
    strncpy(goal->directive, directive, sizeof(goal->directive) - 1);
    atomic_init(&goal->status, GOAL_STATUS_DEFINED);
    pthread_mutex_init(&goal->lock, NULL);
    goal->created_ns = get_timestamp_ns();
    
    fprintf(stderr, "[Director Logic] New goal created (ID: %u). Status: DEFINED.\n", goal->goal_id);
    update_knowledge_graph_with_goal(goal, "GoalCreated");
    
    return goal;
}

/**
 * @brief State machine for processing a goal through its analysis phases.
 * This function is called by the Strategist thread.
 * @param goal The strategic goal to process.
 */
static void process_new_goal(strategic_goal_t* goal) {
    goal_status_t status = atomic_load(&goal->status);
    
    fprintf(stderr, "[Strategist] Processing Goal %u (Current Status: %s)\n", goal->goal_id, goal_status_to_string(status));
    
    switch(status) {
        case GOAL_STATUS_DEFINED:
            atomic_store(&goal->status, GOAL_STATUS_ANALYZING_FEASIBILITY);
            // Fall-through to start analysis immediately
        
        case GOAL_STATUS_ANALYZING_FEASIBILITY:
            analyze_feasibility(goal);
            // Transition to the next state
            atomic_store(&goal->status, GOAL_STATUS_RISK_ASSESSMENT);
            break;

        case GOAL_STATUS_RISK_ASSESSMENT:
            perform_risk_assessment(goal);
            // Transition to the next state for final review/approval
            atomic_store(&goal->status, GOAL_STATUS_PENDING_APPROVAL);
            break;

        default:
            // This function should not be called for goals in other states.
            break;
    }
    fprintf(stderr, "[Strategist] Finished processing pass for Goal %u. New status: %s\n", goal->goal_id, goal_status_to_string(atomic_load(&goal->status)));
}

/**
 * @brief Simulates analyzing the feasibility of a goal.
 * In a real system, this would involve complex KG queries and heuristics.
 * @param goal The goal to analyze.
 */
static void analyze_feasibility(strategic_goal_t* goal) {
    fprintf(stderr, "[Strategist] Analyzing feasibility for Goal %u...\n", goal->goal_id);
    update_knowledge_graph_with_goal(goal, "FeasibilityAnalysisStarted");

    // Simulate compute-intensive analysis
    usleep(500 * 1000); // 500ms

    // Simulate results
    goal->success_probability = 0.85f + ((rand() % 15) / 100.0f); // 85-100%
    goal->projected_resource_cost = 50.0f + (rand() % 100);

    snprintf(goal->feasibility_report, sizeof(goal->feasibility_report),
        "Feasibility analysis complete for directive: '%s'.\n"
        "Projected success probability: %.2f%%.\n"
        "Estimated resource cost: %.1f units.\n"
        "Recommendation: Proceed to risk assessment.",
        goal->directive, goal->success_probability * 100.0, goal->projected_resource_cost);
    
    update_knowledge_graph_with_goal(goal, "FeasibilityAnalysisComplete");
    fprintf(stderr, "[Strategist] Feasibility analysis complete for Goal %u.\n", goal->goal_id);
}

/**
 * @brief Simulates performing a risk assessment for the goal.
 * This would involve an IPC call to the Security Agent.
 * @param goal The goal to assess.
 */
static void perform_risk_assessment(strategic_goal_t* goal) {
    fprintf(stderr, "[Strategist] Performing risk assessment for Goal %u...\n", goal->goal_id);
    
    // Simulate IPC call to Security Agent
    // security_agent_assess_risks(goal->goal_id, goal->directive);
    usleep(300 * 1000); // 300ms

    // Simulate receiving a response from the Security Agent
    goal->risk_count = 0;
    if ((rand() % 10) > 6) { // 30% chance of finding a high risk
        risk_assessment_t* risk = &goal->risks[goal->risk_count++];
        risk->level = RISK_LEVEL_HIGH;
        strncpy(risk->description, "Execution may expose a critical internal API.", sizeof(risk->description)-1);
        strncpy(risk->mitigation_plan, "Implement additional authentication layer and rate limiting before execution.", sizeof(risk->mitigation_plan)-1);
        risk->accepted = false; // High risks require explicit approval
        atomic_fetch_add(&g_director_agent->metrics.critical_risks_accepted, 1);
    }
    if ((rand() % 10) > 3) { // 60% chance of a medium risk
        risk_assessment_t* risk = &goal->risks[goal->risk_count++];
        risk->level = RISK_LEVEL_MEDIUM;
        strncpy(risk->description, "Increased load on database cluster may impact performance of other services.", sizeof(risk->description)-1);
        strncpy(risk->mitigation_plan, "Schedule execution during off-peak hours and pre-scale database replicas.", sizeof(risk->mitigation_plan)-1);
        risk->accepted = true; // Medium risks can be auto-accepted with mitigation
    }

    update_knowledge_graph_with_goal(goal, "RiskAssessmentComplete");
    fprintf(stderr, "[Strategist] Risk assessment complete for Goal %u. Found %u risks.\n", goal->goal_id, goal->risk_count);
}

/**
 * @brief Simulates delegating an approved goal to the Planner Agent.
 * This would involve an IPC call to the Planner Agent.
 * @param goal The goal to delegate.
 */
static void delegate_goal_to_planner(strategic_goal_t* goal) {
    fprintf(stderr, "[Director Logic] Delegating Goal %u to Planner Agent...\n", goal->goal_id);
    
    // Simple decomposition for simulation
    sub_project_t* p1 = &goal->sub_projects[goal->sub_project_count++];
    snprintf(p1->project_name, sizeof(p1->project_name), "Phase 1: Build & Test for Goal %u", goal->goal_id);
    // planner_agent_create_plan(p1->project_name);
    
    sub_project_t* p2 = &goal->sub_projects[goal->sub_project_count++];
    snprintf(p2->project_name, sizeof(p2->project_name), "Phase 2: Deploy & Verify for Goal %u", goal->goal_id);
    // planner_agent_create_plan(p2->project_name);
    
    atomic_store(&goal->status, GOAL_STATUS_IN_EXECUTION);
    atomic_fetch_add(&g_director_agent->metrics.total_projects_managed, (unsigned int)goal->sub_project_count);
    
    update_knowledge_graph_with_goal(goal, "DelegatedToPlanner");
    fprintf(stderr, "[Director Logic] Delegation of Goal %u complete. Status: IN_EXECUTION\n", goal->goal_id);
}


/**
 * @brief Simulates writing goal status updates to the Knowledge Graph.
 * @param goal The goal being updated.
 * @param event A description of the event.
 */
static void update_knowledge_graph_with_goal(const strategic_goal_t* goal, const char* event) {
    // In a real system, this would serialize the goal's state and send it
    // to the KG service.
    // kg_client_update_node(goal->goal_id, "StrategicGoal", goal->status, event);
    // For simulation, we just log it.
    fprintf(stderr, "  [KG Stub] Updating Node ID %u with event: %s\n", goal->goal_id, event);
}


/**
 * @brief Converts a goal status enum to a human-readable string.
 */
static const char* goal_status_to_string(goal_status_t status) {
    switch (status) {
        case GOAL_STATUS_UNINITIALIZED: return "UNINITIALIZED";
        case GOAL_STATUS_DEFINED: return "DEFINED";
        case GOAL_STATUS_ANALYZING_FEASIBILITY: return "ANALYZING_FEASIBILITY";
        case GOAL_STATUS_RISK_ASSESSMENT: return "RISK_ASSESSMENT";
        case GOAL_STATUS_PENDING_APPROVAL: return "PENDING_APPROVAL";
        case GOAL_STATUS_DELEGATED_TO_PLANNER: return "DELEGATED_TO_PLANNER";
        case GOAL_STATUS_IN_EXECUTION: return "IN_EXECUTION";
        case GOAL_STATUS_COMPLETED: return "COMPLETED";
        case GOAL_STATUS_FAILED: return "FAILED";
        case GOAL_STATUS_ARCHIVED: return "ARCHIVED";
        default: return "UNKNOWN";
    }
}


// ============================================================================
// STATISTICS AND MONITORING
// ============================================================================

void print_director_statistics() {
    if (!g_director_agent) {
        printf("Director Agent not initialized.\n");
        return;
    }

    printf("\n\n--- Director Agent v1.0 Strategic Overview ---\n");
    if (is_meteor_lake_cpu()) {
        printf("Hardware Status: [CPU Temp: %d°C | Thermal Throttling: %s]\n",
            get_package_temperature(), is_thermal_throttling() ? "YES" : "NO");
    }

    system_overview_metrics_t* m = &g_director_agent->metrics;
    printf("System Metrics: [Active Goals: %u | Total Projects: %u | Critical Risks: %u | Readiness: %.1f%%]\n",
        atomic_load(&m->active_goals),
        atomic_load(&m->total_projects_managed),
        atomic_load(&m->critical_risks_accepted),
        atomic_load(&m->operational_readiness_score) * 100.0f);
    
    printf("----------------------------------------------\n");
    printf("%-8s | %-60s | %-25s\n", "Goal ID", "Directive", "Status");
    printf("---------|--------------------------------------------------------------|--------------------------\n");

    pthread_rwlock_rdlock(&g_director_agent->goals_lock);
    if (g_director_agent->goal_count == 0) {
        printf("No active strategic goals.\n");
    }
    for (uint32_t i = 0; i < g_director_agent->goal_count; i++) {
        strategic_goal_t* goal = g_director_agent->active_goals[i];
        char truncated_directive[61];
        strncpy(truncated_directive, goal->directive, 60);
        if (strlen(goal->directive) > 60) {
            strcpy(truncated_directive + 57, "...");
        } else {
            truncated_directive[strlen(goal->directive)] = '\0';
        }
        
        printf("%-8u | %-60s | %-25s\n",
               goal->goal_id,
               truncated_directive,
               goal_status_to_string(atomic_load(&goal->status)));
    }
    pthread_rwlock_unlock(&g_director_agent->goals_lock);
    printf("----------------------------------------------\n\n");
}


// ============================================================================
// EXAMPLE USAGE AND TESTING
// ============================================================================

#ifdef DIRECTOR_TEST_MODE

int main() {
    srand(time(NULL));
    printf("Director Agent Test Mode\n");
    printf("========================\n");

    if (director_service_init() != 0) {
        fprintf(stderr, "Fatal: Failed to initialize Director service.\n");
        return 1;
    }

    printf("\n--- Test Scenario Initiated ---\n");
    submit_directive_to_director("Develop and deploy a real-time anomaly detection system for network traffic.");
    submit_directive_to_director("Refactor the entire authentication service to use quantum-resistant cryptography.");
    
    // Let the agent process the initial stages
    sleep(3);
    print_director_statistics();

    // Manually approve a goal to move it forward
    pthread_rwlock_rdlock(&g_director_agent->goals_lock);
    strategic_goal_t* goal_to_approve = NULL;
    for(uint32_t i=0; i < g_director_agent->goal_count; ++i) {
        if(atomic_load(&g_director_agent->active_goals[i]->status) == GOAL_STATUS_PENDING_APPROVAL) {
            goal_to_approve = g_director_agent->active_goals[i];
            break;
        }
    }
    pthread_rwlock_unlock(&g_director_agent->goals_lock);
    
    if (goal_to_approve) {
        printf("\n--- Manually Approving Goal %u ---\n", goal_to_approve->goal_id);
        delegate_goal_to_planner(goal_to_approve);
    } else {
        printf("\n--- No goals pending approval at this time ---\n");
    }

    printf("\nAgent running. Monitoring execution for 15 seconds...\n");
    for (int i = 0; i < 3; i++) {
        sleep(5);
        print_director_statistics();
    }

    director_service_cleanup();
    printf("\n--- Test Scenario Complete ---\n");
    return 0;
}

#endif