/*
 * AGENT COORDINATION SYSTEM
 * 
 * Inter-agent communication and coordination protocols for the
 * Claude Agent Communication System v7.0
 * - Message routing and processing
 * - Agent discovery and registration
 * - Task delegation and response handling
 * - Load balancing and failover
 * - Performance monitoring and metrics
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
#include <sys/socket.h>
#include <sys/un.h>
#include <fcntl.h>
#include "compatibility_layer.h"
#include "agent_protocol.h"
#include <sched.h>
#include <signal.h>

// ============================================================================
// CONSTANTS AND CONFIGURATION
// ============================================================================

#define MAX_REGISTERED_AGENTS 256
#define MAX_PENDING_MESSAGES 1024
#define MAX_ACTIVE_DELEGATIONS 128
#define MESSAGE_BUFFER_SIZE 65536
#define COORDINATION_HEARTBEAT_MS 5000
#define DELEGATION_TIMEOUT_MS 30000
#define MAX_MESSAGE_RETRIES 3

// Agent states
typedef enum {
    AGENT_STATE_UNKNOWN = 0,
    AGENT_STATE_REGISTERED = 1,
    AGENT_STATE_ACTIVE = 2,
    AGENT_STATE_BUSY = 3,
    AGENT_STATE_UNAVAILABLE = 4,
    AGENT_STATE_FAILED = 5,
    AGENT_STATE_MAINTENANCE = 6
} agent_state_t;

// Task delegation states
typedef enum {
    DELEGATION_STATE_PENDING = 0,
    DELEGATION_STATE_SENT = 1,
    DELEGATION_STATE_ACKNOWLEDGED = 2,
    DELEGATION_STATE_IN_PROGRESS = 3,
    DELEGATION_STATE_COMPLETED = 4,
    DELEGATION_STATE_FAILED = 5,
    DELEGATION_STATE_TIMEOUT = 6,
    DELEGATION_STATE_CANCELLED = 7
} delegation_state_t;

// ============================================================================
// DATA STRUCTURES
// ============================================================================

// Agent registration info
typedef struct {
    uint32_t agent_id;
    uint32_t agent_type;
    char name[64];
    char capabilities[256];
    char endpoint_info[128];
    agent_state_t state;
    
    // Performance metrics
    uint32_t current_load_percent;
    uint32_t queue_depth;
    float avg_response_time_ms;
    float success_rate;
    
    // Coordination info
    uint64_t last_heartbeat_ns;
    uint64_t last_activity_ns;
    uint32_t active_delegations;
    uint32_t completed_tasks;
    uint32_t failed_tasks;
    
    pthread_mutex_t lock;
} agent_registry_entry_t;

// Task delegation record
typedef struct {
    uint32_t delegation_id;
    uint32_t source_agent_id;
    uint32_t target_agent_id;
    uint32_t target_agent_type;
    
    char task_description[512];
    char task_parameters[1024];
    char required_capability[64];
    
    delegation_state_t state;
    uint64_t creation_time_ns;
    uint64_t send_time_ns;
    uint64_t completion_time_ns;
    uint32_t timeout_ms;
    uint32_t retry_count;
    
    char result_data[2048];
    char error_message[256];
    int exit_code;
    
} task_delegation_t;

// Message processing context
typedef struct {
    enhanced_msg_header_t header;
    uint8_t payload[MAX_PAYLOAD_SIZE];
    size_t payload_size;
    uint64_t receive_time_ns;
    uint32_t processing_attempts;
    bool requires_response;
} message_context_t;

// Coordination statistics
typedef struct __attribute__((aligned(64))) {
    _Atomic uint64_t messages_sent;
    _Atomic uint64_t messages_received;
    _Atomic uint64_t messages_processed;
    _Atomic uint64_t messages_failed;
    _Atomic uint64_t delegations_created;
    _Atomic uint64_t delegations_completed;
    _Atomic uint64_t delegations_failed;
    _Atomic uint64_t agent_registrations;
    _Atomic uint32_t active_agents;
    double avg_message_processing_time_ms;
    double avg_delegation_completion_time_ms;
    double system_utilization_percent;
} coordination_stats_t;

// Main coordination service
typedef struct __attribute__((aligned(PAGE_SIZE))) {
    bool initialized;
    volatile bool running;
    
    // Agent registry
    agent_registry_entry_t agent_registry[MAX_REGISTERED_AGENTS];
    uint32_t registered_agent_count;
    pthread_rwlock_t registry_lock;
    
    // Task delegations
    task_delegation_t delegations[MAX_ACTIVE_DELEGATIONS];
    uint32_t active_delegation_count;
    pthread_rwlock_t delegations_lock;
    
    // Message queues
    message_context_t message_queue[MAX_PENDING_MESSAGES];
    uint32_t queue_head;
    uint32_t queue_tail;
    uint32_t queue_size;
    pthread_mutex_t queue_lock;
    pthread_cond_t queue_not_empty;
    
    // Worker threads
    pthread_t message_processor_thread;
    pthread_t delegation_monitor_thread;
    pthread_t heartbeat_thread;
    
    // Statistics
    coordination_stats_t stats;
    
    // Configuration
    uint32_t max_concurrent_delegations;
    uint32_t message_processing_threads;
    float load_balancing_threshold;
    bool failover_enabled;
    
} coordination_service_t;

// Global coordination service
static coordination_service_t* g_coordination = NULL;

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

static inline uint64_t get_timestamp_ns() {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (uint64_t)ts.tv_sec * 1000000000ULL + ts.tv_nsec;
}

static uint32_t generate_delegation_id() {
    static _Atomic uint32_t id_counter = 1;
    return atomic_fetch_add(&id_counter, 1);
}

static uint32_t generate_sequence_number() {
    static _Atomic uint32_t seq_counter = 1;
    return atomic_fetch_add(&seq_counter, 1);
}

// ============================================================================
// AGENT REGISTRY MANAGEMENT
// ============================================================================

int register_agent(uint32_t agent_id, uint32_t agent_type, const char* name,
                   const char* capabilities, const char* endpoint_info) {
    if (!g_coordination || !name) {
        return -EINVAL;
    }
    
    pthread_rwlock_wrlock(&g_coordination->registry_lock);
    
    // Check if agent is already registered
    for (uint32_t i = 0; i < g_coordination->registered_agent_count; i++) {
        if (g_coordination->agent_registry[i].agent_id == agent_id) {
            pthread_rwlock_unlock(&g_coordination->registry_lock);
            return -EEXIST;
        }
    }
    
    if (g_coordination->registered_agent_count >= MAX_REGISTERED_AGENTS) {
        pthread_rwlock_unlock(&g_coordination->registry_lock);
        return -ENOSPC;
    }
    
    // Find free slot
    agent_registry_entry_t* entry = NULL;
    for (uint32_t i = 0; i < MAX_REGISTERED_AGENTS; i++) {
        if (g_coordination->agent_registry[i].agent_id == 0) {
            entry = &g_coordination->agent_registry[i];
            break;
        }
    }
    
    if (!entry) {
        pthread_rwlock_unlock(&g_coordination->registry_lock);
        return -ENOSPC;
    }
    
    // Initialize entry
    pthread_mutex_lock(&entry->lock);
    
    entry->agent_id = agent_id;
    entry->agent_type = agent_type;
    strncpy(entry->name, name, sizeof(entry->name) - 1);
    entry->name[sizeof(entry->name) - 1] = '\0';
    
    if (capabilities) {
        strncpy(entry->capabilities, capabilities, sizeof(entry->capabilities) - 1);
        entry->capabilities[sizeof(entry->capabilities) - 1] = '\0';
    }
    
    if (endpoint_info) {
        strncpy(entry->endpoint_info, endpoint_info, sizeof(entry->endpoint_info) - 1);
        entry->endpoint_info[sizeof(entry->endpoint_info) - 1] = '\0';
    }
    
    entry->state = AGENT_STATE_REGISTERED;
    entry->current_load_percent = 0;
    entry->queue_depth = 0;
    entry->avg_response_time_ms = 0.0f;
    entry->success_rate = 1.0f;
    entry->last_heartbeat_ns = get_timestamp_ns();
    entry->last_activity_ns = entry->last_heartbeat_ns;
    entry->active_delegations = 0;
    entry->completed_tasks = 0;
    entry->failed_tasks = 0;
    
    g_coordination->registered_agent_count++;
    atomic_fetch_add(&g_coordination->stats.agent_registrations, 1);
    atomic_fetch_add(&g_coordination->stats.active_agents, 1);
    
    pthread_mutex_unlock(&entry->lock);
    pthread_rwlock_unlock(&g_coordination->registry_lock);
    
    printf("Coordination: Registered agent '%s' (ID: %u, Type: %u)\n", name, agent_id, agent_type);
    return 0;
}

int update_agent_status(uint32_t agent_id, agent_state_t state, 
                       uint32_t load_percent, uint32_t queue_depth) {
    if (!g_coordination) {
        return -EINVAL;
    }
    
    pthread_rwlock_rdlock(&g_coordination->registry_lock);
    
    agent_registry_entry_t* entry = NULL;
    for (uint32_t i = 0; i < g_coordination->registered_agent_count; i++) {
        if (g_coordination->agent_registry[i].agent_id == agent_id) {
            entry = &g_coordination->agent_registry[i];
            break;
        }
    }
    
    if (!entry) {
        pthread_rwlock_unlock(&g_coordination->registry_lock);
        return -ENOENT;
    }
    
    pthread_mutex_lock(&entry->lock);
    
    agent_state_t old_state = entry->state;
    entry->state = state;
    entry->current_load_percent = load_percent;
    entry->queue_depth = queue_depth;
    entry->last_heartbeat_ns = get_timestamp_ns();
    
    // Update active agent count
    if (old_state != AGENT_STATE_ACTIVE && state == AGENT_STATE_ACTIVE) {
        atomic_fetch_add(&g_coordination->stats.active_agents, 1);
    } else if (old_state == AGENT_STATE_ACTIVE && state != AGENT_STATE_ACTIVE) {
        atomic_fetch_sub(&g_coordination->stats.active_agents, 1);
    }
    
    pthread_mutex_unlock(&entry->lock);
    pthread_rwlock_unlock(&g_coordination->registry_lock);
    
    return 0;
}

agent_registry_entry_t* find_best_agent_for_task(uint32_t agent_type, 
                                                 const char* required_capability) {
    if (!g_coordination) {
        return NULL;
    }
    
    pthread_rwlock_rdlock(&g_coordination->registry_lock);
    
    agent_registry_entry_t* best_agent = NULL;
    float best_score = -1.0f;
    
    for (uint32_t i = 0; i < g_coordination->registered_agent_count; i++) {
        agent_registry_entry_t* entry = &g_coordination->agent_registry[i];
        
        pthread_mutex_lock(&entry->lock);
        
        // Check basic criteria
        if (entry->agent_type == agent_type && 
            entry->state == AGENT_STATE_ACTIVE &&
            entry->current_load_percent < 90) {
            
            // Check capability match if required
            bool capability_match = true;
            if (required_capability && strlen(required_capability) > 0) {
                capability_match = (strstr(entry->capabilities, required_capability) != NULL);
            }
            
            if (capability_match) {
                // Calculate selection score based on:
                // - Low load (40% weight)
                // - Low queue depth (30% weight) 
                // - High success rate (20% weight)
                // - Fast response time (10% weight)
                
                float load_score = (100.0f - entry->current_load_percent) / 100.0f;
                float queue_score = fmaxf(0.0f, (20.0f - entry->queue_depth) / 20.0f);
                float success_score = entry->success_rate;
                float response_score = fmaxf(0.0f, (1000.0f - entry->avg_response_time_ms) / 1000.0f);
                
                float total_score = (load_score * 0.4f) + (queue_score * 0.3f) + 
                                   (success_score * 0.2f) + (response_score * 0.1f);
                
                if (total_score > best_score) {
                    best_score = total_score;
                    best_agent = entry;
                }
            }
        }
        
        pthread_mutex_unlock(&entry->lock);
    }
    
    pthread_rwlock_unlock(&g_coordination->registry_lock);
    
    return best_agent;
}

// ============================================================================
// MESSAGE PROCESSING
// ============================================================================

int enqueue_message(const enhanced_msg_header_t* header, const uint8_t* payload) {
    if (!g_coordination || !header) {
        return -EINVAL;
    }
    
    pthread_mutex_lock(&g_coordination->queue_lock);
    
    if (g_coordination->queue_size >= MAX_PENDING_MESSAGES) {
        pthread_mutex_unlock(&g_coordination->queue_lock);
        return -ENOSPC;
    }
    
    message_context_t* msg = &g_coordination->message_queue[g_coordination->queue_tail];
    
    // Copy message data
    msg->header = *header;
    msg->payload_size = header->payload_len;
    
    if (payload && header->payload_len > 0) {
        size_t copy_size = (header->payload_len > MAX_PAYLOAD_SIZE) ? 
                          MAX_PAYLOAD_SIZE : header->payload_len;
        memcpy(msg->payload, payload, copy_size);
        msg->payload_size = copy_size;
    }
    
    msg->receive_time_ns = get_timestamp_ns();
    msg->processing_attempts = 0;
    msg->requires_response = (header->flags & MSG_FLAG_REQUIRES_ACK) != 0;
    
    g_coordination->queue_tail = (g_coordination->queue_tail + 1) % MAX_PENDING_MESSAGES;
    g_coordination->queue_size++;
    
    atomic_fetch_add(&g_coordination->stats.messages_received, 1);
    
    pthread_cond_signal(&g_coordination->queue_not_empty);
    pthread_mutex_unlock(&g_coordination->queue_lock);
    
    return 0;
}

static int process_message(message_context_t* msg) {
    if (!msg) {
        return -EINVAL;
    }
    
    uint64_t start_time = get_timestamp_ns();
    int result = 0;
    
    printf("Coordination: Processing message type %u from agent %u\n", 
           msg->header.msg_type, msg->header.source_agent);
    
    switch (msg->header.msg_type) {
        case MSG_TYPE_PING:
            // Handle ping - update agent heartbeat
            update_agent_status(msg->header.source_agent, AGENT_STATE_ACTIVE, 0, 0);
            
            if (msg->requires_response) {
                // Send pong response
                enhanced_msg_header_t response;
                init_message_header(&response, MSG_TYPE_PONG, 0, msg->header.source_agent);
                response.timestamp = get_timestamp_ns();
                response.sequence = generate_sequence_number();
                // In real implementation, would send via network/IPC
            }
            break;
            
        case MSG_TYPE_REQUEST:
            // Handle task request - delegate to appropriate agent
            {
                char* task_desc = (char*)msg->payload;
                uint32_t agent_type = msg->header.target_agents[0]; // Use first target as agent type
                
                agent_registry_entry_t* target_agent = find_best_agent_for_task(agent_type, NULL);
                if (target_agent) {
                    uint32_t delegation_id = delegate_task_to_agent(
                        msg->header.source_agent, target_agent->agent_id, 
                        task_desc, (char*)msg->payload, NULL, DELEGATION_TIMEOUT_MS);
                    
                    if (delegation_id == 0) {
                        result = -1;
                    }
                } else {
                    printf("Coordination: No suitable agent found for task request\n");
                    result = -ENOENT;
                }
            }
            break;
            
        case MSG_TYPE_RESPONSE:
            // Handle task response - update delegation status
            {
                // Extract delegation ID from payload (first 4 bytes)
                if (msg->payload_size >= 4) {
                    uint32_t delegation_id = *(uint32_t*)msg->payload;
                    complete_task_delegation(delegation_id, 0, (char*)(msg->payload + 4));
                }
            }
            break;
            
        case MSG_TYPE_NOTIFICATION:
            // Handle status notification
            {
                if (msg->payload_size >= 8) {
                    uint32_t load_percent = *(uint32_t*)msg->payload;
                    uint32_t queue_depth = *(uint32_t*)(msg->payload + 4);
                    update_agent_status(msg->header.source_agent, AGENT_STATE_ACTIVE, 
                                       load_percent, queue_depth);
                }
            }
            break;
            
        case MSG_TYPE_EMERGENCY:
            // Handle emergency message - high priority processing
            printf("Coordination: EMERGENCY message from agent %u: %s\n", 
                   msg->header.source_agent, (char*)msg->payload);
            
            // Update agent state and potentially trigger failover
            update_agent_status(msg->header.source_agent, AGENT_STATE_FAILED, 100, 0);
            break;
            
        default:
            printf("Coordination: Unknown message type %u\n", msg->header.msg_type);
            result = -EINVAL;
            break;
    }
    
    uint64_t processing_time = get_timestamp_ns() - start_time;
    double processing_time_ms = processing_time / 1000000.0;
    
    // Update statistics
    g_coordination->stats.avg_message_processing_time_ms = 
        (g_coordination->stats.avg_message_processing_time_ms * 0.9) + (processing_time_ms * 0.1);
    
    if (result == 0) {
        atomic_fetch_add(&g_coordination->stats.messages_processed, 1);
    } else {
        atomic_fetch_add(&g_coordination->stats.messages_failed, 1);
    }
    
    return result;
}

static void* message_processor_thread(void* arg) {
    (void)arg;
    
    pthread_setname_np(pthread_self(), "msg_processor");
    
    while (g_coordination && g_coordination->running) {
        pthread_mutex_lock(&g_coordination->queue_lock);
        
        while (g_coordination->queue_size == 0 && g_coordination->running) {
            pthread_cond_wait(&g_coordination->queue_not_empty, &g_coordination->queue_lock);
        }
        
        if (!g_coordination->running) {
            pthread_mutex_unlock(&g_coordination->queue_lock);
            break;
        }
        
        // Dequeue message
        message_context_t msg = g_coordination->message_queue[g_coordination->queue_head];
        g_coordination->queue_head = (g_coordination->queue_head + 1) % MAX_PENDING_MESSAGES;
        g_coordination->queue_size--;
        
        pthread_mutex_unlock(&g_coordination->queue_lock);
        
        // Process message
        msg.processing_attempts++;
        int result = process_message(&msg);
        
        if (result != 0 && msg.processing_attempts < MAX_MESSAGE_RETRIES) {
            // Re-queue for retry
            usleep(1000 * msg.processing_attempts); // Exponential backoff
            enqueue_message(&msg.header, msg.payload);
        }
    }
    
    return NULL;
}

// ============================================================================
// TASK DELEGATION SYSTEM
// ============================================================================

uint32_t delegate_task_to_agent(uint32_t source_agent_id, uint32_t target_agent_id,
                                const char* task_description, const char* parameters,
                                const char* required_capability, uint32_t timeout_ms) {
    if (!g_coordination || !task_description) {
        return 0;
    }
    
    pthread_rwlock_wrlock(&g_coordination->delegations_lock);
    
    if (g_coordination->active_delegation_count >= MAX_ACTIVE_DELEGATIONS) {
        pthread_rwlock_unlock(&g_coordination->delegations_lock);
        return 0;
    }
    
    // Find free delegation slot
    task_delegation_t* delegation = NULL;
    for (uint32_t i = 0; i < MAX_ACTIVE_DELEGATIONS; i++) {
        if (g_coordination->delegations[i].delegation_id == 0) {
            delegation = &g_coordination->delegations[i];
            break;
        }
    }
    
    if (!delegation) {
        pthread_rwlock_unlock(&g_coordination->delegations_lock);
        return 0;
    }
    
    // Initialize delegation
    delegation->delegation_id = generate_delegation_id();
    delegation->source_agent_id = source_agent_id;
    delegation->target_agent_id = target_agent_id;
    delegation->target_agent_type = 0; // Will be filled from registry
    
    strncpy(delegation->task_description, task_description, sizeof(delegation->task_description) - 1);
    delegation->task_description[sizeof(delegation->task_description) - 1] = '\0';
    
    if (parameters) {
        strncpy(delegation->task_parameters, parameters, sizeof(delegation->task_parameters) - 1);
        delegation->task_parameters[sizeof(delegation->task_parameters) - 1] = '\0';
    }
    
    if (required_capability) {
        strncpy(delegation->required_capability, required_capability, sizeof(delegation->required_capability) - 1);
        delegation->required_capability[sizeof(delegation->required_capability) - 1] = '\0';
    }
    
    delegation->state = DELEGATION_STATE_PENDING;
    delegation->creation_time_ns = get_timestamp_ns();
    delegation->timeout_ms = timeout_ms > 0 ? timeout_ms : DELEGATION_TIMEOUT_MS;
    delegation->retry_count = 0;
    delegation->exit_code = -1;
    
    g_coordination->active_delegation_count++;
    atomic_fetch_add(&g_coordination->stats.delegations_created, 1);
    
    uint32_t delegation_id = delegation->delegation_id;
    
    pthread_rwlock_unlock(&g_coordination->delegations_lock);
    
    // Send delegation message to target agent
    enhanced_msg_header_t msg_header;
    init_message_header(&msg_header, MSG_TYPE_REQUEST, source_agent_id, target_agent_id);
    msg_header.timestamp = get_timestamp_ns();
    msg_header.sequence = generate_sequence_number();
    msg_header.flags |= MSG_FLAG_REQUIRES_ACK;
    
    // Prepare payload (delegation_id + task_description + parameters)
    uint8_t payload[MAX_PAYLOAD_SIZE];
    size_t offset = 0;
    
    *(uint32_t*)payload = delegation_id;
    offset += 4;
    
    size_t desc_len = strlen(task_description) + 1;
    memcpy(payload + offset, task_description, desc_len);
    offset += desc_len;
    
    if (parameters) {
        size_t param_len = strlen(parameters) + 1;
        memcpy(payload + offset, parameters, param_len);
        offset += param_len;
    }
    
    msg_header.payload_len = offset;
    
    // In real implementation, would send via network/IPC
    // For simulation, mark as sent
    delegation->send_time_ns = get_timestamp_ns();
    delegation->state = DELEGATION_STATE_SENT;
    
    atomic_fetch_add(&g_coordination->stats.messages_sent, 1);
    
    printf("Coordination: Delegated task '%s' to agent %u (delegation ID: %u)\n",
           task_description, target_agent_id, delegation_id);
    
    return delegation_id;
}

int complete_task_delegation(uint32_t delegation_id, int exit_code, const char* result_data) {
    if (!g_coordination) {
        return -EINVAL;
    }
    
    pthread_rwlock_rdlock(&g_coordination->delegations_lock);
    
    task_delegation_t* delegation = NULL;
    for (uint32_t i = 0; i < MAX_ACTIVE_DELEGATIONS; i++) {
        if (g_coordination->delegations[i].delegation_id == delegation_id) {
            delegation = &g_coordination->delegations[i];
            break;
        }
    }
    
    if (!delegation) {
        pthread_rwlock_unlock(&g_coordination->delegations_lock);
        return -ENOENT;
    }
    
    delegation->completion_time_ns = get_timestamp_ns();
    delegation->exit_code = exit_code;
    
    if (result_data) {
        strncpy(delegation->result_data, result_data, sizeof(delegation->result_data) - 1);
        delegation->result_data[sizeof(delegation->result_data) - 1] = '\0';
    }
    
    if (exit_code == 0) {
        delegation->state = DELEGATION_STATE_COMPLETED;
        atomic_fetch_add(&g_coordination->stats.delegations_completed, 1);
    } else {
        delegation->state = DELEGATION_STATE_FAILED;
        atomic_fetch_add(&g_coordination->stats.delegations_failed, 1);
    }
    
    // Update target agent performance metrics
    pthread_rwlock_rdlock(&g_coordination->registry_lock);
    for (uint32_t i = 0; i < g_coordination->registered_agent_count; i++) {
        agent_registry_entry_t* entry = &g_coordination->agent_registry[i];
        
        if (entry->agent_id == delegation->target_agent_id) {
            pthread_mutex_lock(&entry->lock);
            
            if (exit_code == 0) {
                entry->completed_tasks++;
            } else {
                entry->failed_tasks++;
            }
            
            // Update success rate
            uint32_t total_tasks = entry->completed_tasks + entry->failed_tasks;
            entry->success_rate = (float)entry->completed_tasks / total_tasks;
            
            // Update average response time
            float completion_time_ms = (delegation->completion_time_ns - delegation->send_time_ns) / 1000000.0f;
            entry->avg_response_time_ms = (entry->avg_response_time_ms * 0.8f) + (completion_time_ms * 0.2f);
            
            entry->active_delegations--;
            
            pthread_mutex_unlock(&entry->lock);
            break;
        }
    }
    pthread_rwlock_unlock(&g_coordination->registry_lock);
    
    // Update delegation completion time statistics
    double completion_time_ms = (delegation->completion_time_ns - delegation->creation_time_ns) / 1000000.0;
    g_coordination->stats.avg_delegation_completion_time_ms = 
        (g_coordination->stats.avg_delegation_completion_time_ms * 0.9) + (completion_time_ms * 0.1);
    
    pthread_rwlock_unlock(&g_coordination->delegations_lock);
    
    printf("Coordination: Task delegation %u %s (%.1fms)\n", 
           delegation_id, exit_code == 0 ? "completed" : "failed", completion_time_ms);
    
    return 0;
}

// ============================================================================
// COORDINATION SERVICE MANAGEMENT
// ============================================================================

int coordination_service_init() {
    if (g_coordination) {
        return -EALREADY;
    }
    
    // Allocate coordination structure
    g_coordination = numa_alloc_onnode(sizeof(coordination_service_t), 0);
    if (!g_coordination) {
        return -ENOMEM;
    }
    
    memset(g_coordination, 0, sizeof(coordination_service_t));
    
    // Initialize basic properties
    g_coordination->running = true;
    g_coordination->registered_agent_count = 0;
    g_coordination->active_delegation_count = 0;
    g_coordination->queue_head = 0;
    g_coordination->queue_tail = 0;
    g_coordination->queue_size = 0;
    
    // Initialize locks
    pthread_rwlock_init(&g_coordination->registry_lock, NULL);
    pthread_rwlock_init(&g_coordination->delegations_lock, NULL);
    pthread_mutex_init(&g_coordination->queue_lock, NULL);
    pthread_cond_init(&g_coordination->queue_not_empty, NULL);
    
    for (int i = 0; i < MAX_REGISTERED_AGENTS; i++) {
        pthread_mutex_init(&g_coordination->agent_registry[i].lock, NULL);
    }
    
    // Configuration
    g_coordination->max_concurrent_delegations = MAX_ACTIVE_DELEGATIONS;
    g_coordination->message_processing_threads = 2;
    g_coordination->load_balancing_threshold = 0.8f;
    g_coordination->failover_enabled = true;
    
    g_coordination->initialized = true;
    
    printf("Coordination Service: Initialized\n");
    return 0;
}

void coordination_service_cleanup() {
    if (!g_coordination) {
        return;
    }
    
    g_coordination->running = false;
    
    // Stop threads
    if (g_coordination->message_processor_thread) {
        pthread_cond_broadcast(&g_coordination->queue_not_empty);
        pthread_join(g_coordination->message_processor_thread, NULL);
    }
    if (g_coordination->delegation_monitor_thread) {
        pthread_join(g_coordination->delegation_monitor_thread, NULL);
    }
    if (g_coordination->heartbeat_thread) {
        pthread_join(g_coordination->heartbeat_thread, NULL);
    }
    
    // Cleanup locks
    pthread_rwlock_destroy(&g_coordination->registry_lock);
    pthread_rwlock_destroy(&g_coordination->delegations_lock);
    pthread_mutex_destroy(&g_coordination->queue_lock);
    pthread_cond_destroy(&g_coordination->queue_not_empty);
    
    for (int i = 0; i < MAX_REGISTERED_AGENTS; i++) {
        pthread_mutex_destroy(&g_coordination->agent_registry[i].lock);
    }
    
    numa_free(g_coordination, sizeof(coordination_service_t));
    g_coordination = NULL;
    
    printf("Coordination Service: Cleaned up\n");
}

int start_coordination_threads() {
    if (!g_coordination) {
        return -EINVAL;
    }
    
    // Start message processor thread
    int ret = pthread_create(&g_coordination->message_processor_thread, NULL,
                           message_processor_thread, NULL);
    if (ret != 0) {
        printf("Coordination: Failed to start message processor thread: %s\n", strerror(ret));
        return ret;
    }
    
    printf("Coordination: Started message processing threads\n");
    return 0;
}

void print_coordination_statistics() {
    if (!g_coordination) {
        printf("Coordination service not initialized\n");
        return;
    }
    
    printf("\n=== Coordination Service Statistics ===\n");
    printf("Messages sent: %lu\n", atomic_load(&g_coordination->stats.messages_sent));
    printf("Messages received: %lu\n", atomic_load(&g_coordination->stats.messages_received));
    printf("Messages processed: %lu\n", atomic_load(&g_coordination->stats.messages_processed));
    printf("Messages failed: %lu\n", atomic_load(&g_coordination->stats.messages_failed));
    printf("Delegations created: %lu\n", atomic_load(&g_coordination->stats.delegations_created));
    printf("Delegations completed: %lu\n", atomic_load(&g_coordination->stats.delegations_completed));
    printf("Delegations failed: %lu\n", atomic_load(&g_coordination->stats.delegations_failed));
    printf("Active agents: %u\n", atomic_load(&g_coordination->stats.active_agents));
    printf("Avg message processing time: %.2fms\n", g_coordination->stats.avg_message_processing_time_ms);
    printf("Avg delegation completion time: %.2fms\n", g_coordination->stats.avg_delegation_completion_time_ms);
    
    // Agent registry summary
    printf("\nRegistered Agents:\n");
    printf("%-8s %-20s %-12s %-8s %-8s %-12s\n",
           "ID", "Name", "Type", "State", "Load", "Success Rate");
    printf("%-8s %-20s %-12s %-8s %-8s %-12s\n",
           "--------", "--------------------", "------------",
           "--------", "--------", "------------");
    
    pthread_rwlock_rdlock(&g_coordination->registry_lock);
    
    for (uint32_t i = 0; i < g_coordination->registered_agent_count; i++) {
        agent_registry_entry_t* entry = &g_coordination->agent_registry[i];
        
        if (entry->agent_id == 0) continue;
        
        const char* state_str = "UNKNOWN";
        switch (entry->state) {
            case AGENT_STATE_REGISTERED: state_str = "REG"; break;
            case AGENT_STATE_ACTIVE: state_str = "ACTIVE"; break;
            case AGENT_STATE_BUSY: state_str = "BUSY"; break;
            case AGENT_STATE_UNAVAILABLE: state_str = "UNAVAIL"; break;
            case AGENT_STATE_FAILED: state_str = "FAILED"; break;
            case AGENT_STATE_MAINTENANCE: state_str = "MAINT"; break;
            default: state_str = "UNKNOWN"; break;
        }
        
        printf("%-8u %-20s %-12u %-8s %-7u%% %-11.1f%%\n",
               entry->agent_id, entry->name, entry->agent_type, state_str,
               entry->current_load_percent, entry->success_rate * 100.0f);
    }
    
    pthread_rwlock_unlock(&g_coordination->registry_lock);
    
    printf("\n");
}