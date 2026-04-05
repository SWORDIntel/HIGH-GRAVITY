/*
 * AI ROUTER INTEGRATION MODULE
 * 
 * Integration layer between AI-enhanced routing system and existing
 * Claude Agent Communication System transport layer
 * 
 * This module provides seamless integration with:
 * - agent_bridge.c transport layer
 * - message_router.c routing service  
 * - distributed_network.c consensus layer
 * 
 * Features:
 * - Transparent AI routing injection
 * - Performance monitoring and feedback
 * - Adaptive threshold management
 * - Real-time model updates
 * - Distributed inference coordination
 * 
 * Author: ML-OPS Agent
 * Version: 1.0 Production
 */

#ifndef _GNU_SOURCE
#define _GNU_SOURCE
#endif
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <stdbool.h>
#include <stdatomic.h>
#include <pthread.h>
#include <unistd.h>
#include <errno.h>
#include <time.h>
#include <sys/mman.h>
#include <x86intrin.h>
#include <math.h>

// Include AI router header first (which includes agent_protocol.h)
#include "ai_enhanced_router.h"
// Include vector router integration
#include "vector_router.h"
// Then include other headers
#include "compatibility_layer.h"

// ============================================================================
// INTEGRATION CONFIGURATION
// ============================================================================

#define AI_INTEGRATION_VERSION_MAJOR 1
#define AI_INTEGRATION_VERSION_MINOR 0

// Performance thresholds for AI routing activation
#define AI_ACTIVATION_LOAD_THRESHOLD 0.6f
#define AI_ACTIVATION_LATENCY_THRESHOLD_NS 50000
#define AI_CONFIDENCE_MINIMUM 0.7f
#define AI_FALLBACK_TIMEOUT_NS 100000

// Statistics collection intervals
#define STATS_COLLECTION_INTERVAL_MS 1000
#define MODEL_UPDATE_INTERVAL_MS 60000
#define HEALTH_CHECK_INTERVAL_MS 5000

// Batch processing configuration
#define ADAPTIVE_BATCH_MIN_SIZE 8
#define ADAPTIVE_BATCH_MAX_SIZE 64
#define BATCH_TIMEOUT_NS 10000

// ============================================================================
// INTEGRATION DATA STRUCTURES
// ============================================================================

// Integration statistics
typedef struct __attribute__((aligned(64))) {
    _Atomic uint64_t total_messages_processed;
    _Atomic uint64_t ai_routing_enabled_count;
    _Atomic uint64_t ai_routing_disabled_count;
    _Atomic uint64_t fallback_routing_count;
    _Atomic uint64_t batch_processing_count;
    
    _Atomic uint64_t total_routing_time_ns;
    _Atomic uint64_t ai_routing_time_ns;
    _Atomic uint64_t traditional_routing_time_ns;
    
    _Atomic uint64_t accuracy_hits;
    _Atomic uint64_t accuracy_misses;
    _Atomic float current_system_load;
    _Atomic float current_ai_confidence;
    
    _Atomic uint64_t model_updates;
    _Atomic uint64_t threshold_adjustments;
    
    // Vector router performance metrics
    _Atomic uint64_t vector_searches_total;
    _Atomic uint64_t vector_searches_p_core;
    _Atomic uint64_t vector_searches_e_core;
    _Atomic uint64_t vector_avg_latency_us;
} integration_stats_t;

// Adaptive batch management
typedef struct {
    enhanced_msg_header_t* pending_messages[ADAPTIVE_BATCH_MAX_SIZE];
    void* pending_payloads[ADAPTIVE_BATCH_MAX_SIZE];
    ai_routing_decision_t* pending_decisions[ADAPTIVE_BATCH_MAX_SIZE];
    
    _Atomic size_t current_batch_size;
    _Atomic uint64_t batch_start_time;
    
    pthread_mutex_t batch_lock;
    pthread_cond_t batch_ready;
    
    bool batch_processing_active;
} adaptive_batch_manager_t;

// Performance feedback system
typedef struct {
    uint64_t routing_latencies[1024];  // Circular buffer
    float accuracy_scores[1024];       // Circular buffer
    uint32_t system_loads[1024];      // Circular buffer
    
    _Atomic size_t buffer_pos;
    
    // Adaptive thresholds
    float dynamic_confidence_threshold;
    float dynamic_load_threshold;
    uint64_t dynamic_latency_threshold_ns;
    
    pthread_rwlock_t feedback_lock;
    
    // Learning parameters
    float learning_rate;
    float momentum;
    
    uint64_t last_update_time;
} performance_feedback_t;

// Distributed coordination for multi-node AI routing
typedef struct {
    raft_node_id_t local_node_id;
    bool is_ai_coordinator;
    
    // Model synchronization
    uint64_t global_model_version;
    uint64_t local_model_version;
    
    // Load balancing across nodes
    float node_ai_loads[64];           // Per-node AI processing loads
    uint64_t node_last_seen[64];       // Last heartbeat timestamps
    
    pthread_mutex_t coordination_lock;
    
    // Inter-node communication
    void* model_sync_buffer;
    size_t model_sync_buffer_size;
} distributed_ai_coordinator_t;

// Main integration service
typedef struct __attribute__((aligned(4096))) {
    // Core components
    integration_stats_t stats;
    adaptive_batch_manager_t* batch_manager;
    performance_feedback_t* feedback_system;
    distributed_ai_coordinator_t* coordinator;
    
    // AI routing control
    volatile bool ai_routing_enabled;
    volatile bool auto_adaptation_enabled;
    volatile bool distributed_coordination_enabled;
    
    // Threading
    pthread_t stats_thread;
    pthread_t batch_processor_thread;
    pthread_t feedback_thread;
    pthread_t coordination_thread;
    
    // Original routing function pointers (for fallback)
    uint32_t (*original_route_function)(const enhanced_msg_header_t*, const void*);
    
    volatile bool running;
    pthread_mutex_t service_lock;
} ai_integration_service_t;

// Global service instance
static ai_integration_service_t* g_integration_service = NULL;

// Global vector router instance
static VectorRouterHandle* g_vector_router = NULL;

// Forward declarations for vector router functions
static void ai_router_populate_vector_database(void);

// ============================================================================
// PERFORMANCE FEEDBACK SYSTEM
// ============================================================================

static int init_performance_feedback(performance_feedback_t** feedback) {
    *feedback = aligned_alloc(64, sizeof(performance_feedback_t));
    if (!*feedback) return -ENOMEM;
    
    performance_feedback_t* pf = *feedback;
    memset(pf, 0, sizeof(performance_feedback_t));
    
    // Initialize adaptive thresholds
    pf->dynamic_confidence_threshold = AI_CONFIDENCE_MINIMUM;
    pf->dynamic_load_threshold = AI_ACTIVATION_LOAD_THRESHOLD;
    pf->dynamic_latency_threshold_ns = AI_ACTIVATION_LATENCY_THRESHOLD_NS;
    
    // Learning parameters
    pf->learning_rate = 0.01f;
    pf->momentum = 0.9f;
    
    atomic_store(&pf->buffer_pos, 0);
    pf->last_update_time = __builtin_ia32_rdtsc();
    
    pthread_rwlock_init(&pf->feedback_lock, NULL);
    
    printf("AI Integration: Performance feedback system initialized\n");
    return 0;
}

static void update_performance_feedback(performance_feedback_t* pf,
                                       uint64_t routing_latency_ns,
                                       float accuracy_score,
                                       uint32_t system_load) {
    if (!pf) return;
    
    size_t pos = atomic_fetch_add(&pf->buffer_pos, 1) % 1024;
    
    pthread_rwlock_wrlock(&pf->feedback_lock);
    
    // Store performance data
    pf->routing_latencies[pos] = routing_latency_ns;
    pf->accuracy_scores[pos] = accuracy_score;
    pf->system_loads[pos] = system_load;
    
    // Adaptive threshold adjustment using exponential moving average
    uint64_t current_time = __builtin_ia32_rdtsc();
    float time_delta = (current_time - pf->last_update_time) * 1e-9f; // Convert to seconds
    
    if (time_delta > 1.0f) { // Update every second
        // Calculate recent averages
        float avg_accuracy = 0.0f;
        float avg_latency = 0.0f;
        float avg_load = 0.0f;
        
        size_t samples = 0;
        for (size_t i = 0; i < 1024; i++) {
            if (pf->accuracy_scores[i] > 0.0f) {
                avg_accuracy += pf->accuracy_scores[i];
                avg_latency += pf->routing_latencies[i] * 1e-6f; // Convert to ms
                avg_load += pf->system_loads[i];
                samples++;
            }
        }
        
        if (samples > 0) {
            avg_accuracy /= samples;
            avg_latency /= samples;
            avg_load /= samples;
            
            // Adjust thresholds based on performance
            float alpha = pf->learning_rate;
            
            // If accuracy is high, we can lower confidence threshold
            if (avg_accuracy > 0.9f) {
                pf->dynamic_confidence_threshold = 
                    (1.0f - alpha) * pf->dynamic_confidence_threshold + 
                    alpha * (pf->dynamic_confidence_threshold * 0.95f);
            } else if (avg_accuracy < 0.8f) {
                pf->dynamic_confidence_threshold = 
                    (1.0f - alpha) * pf->dynamic_confidence_threshold + 
                    alpha * (pf->dynamic_confidence_threshold * 1.05f);
            }
            
            // Adjust load threshold based on latency performance
            if (avg_latency < 0.01f) { // Less than 10μs
                pf->dynamic_load_threshold = 
                    (1.0f - alpha) * pf->dynamic_load_threshold + 
                    alpha * (pf->dynamic_load_threshold * 0.98f);
            } else if (avg_latency > 0.05f) { // More than 50μs
                pf->dynamic_load_threshold = 
                    (1.0f - alpha) * pf->dynamic_load_threshold + 
                    alpha * (pf->dynamic_load_threshold * 1.02f);
            }
            
            // Clamp thresholds to reasonable ranges
            if (pf->dynamic_confidence_threshold < 0.5f) 
                pf->dynamic_confidence_threshold = 0.5f;
            if (pf->dynamic_confidence_threshold > 0.95f)
                pf->dynamic_confidence_threshold = 0.95f;
                
            if (pf->dynamic_load_threshold < 0.3f)
                pf->dynamic_load_threshold = 0.3f;
            if (pf->dynamic_load_threshold > 0.9f)
                pf->dynamic_load_threshold = 0.9f;
            
            pf->last_update_time = current_time;
        }
    }
    
    pthread_rwlock_unlock(&pf->feedback_lock);
}

// ============================================================================
// ADAPTIVE BATCH PROCESSING
// ============================================================================

static int init_adaptive_batch_manager(adaptive_batch_manager_t** manager) {
    *manager = aligned_alloc(64, sizeof(adaptive_batch_manager_t));
    if (!*manager) return -ENOMEM;
    
    adaptive_batch_manager_t* abm = *manager;
    memset(abm, 0, sizeof(adaptive_batch_manager_t));
    
    atomic_store(&abm->current_batch_size, 0);
    atomic_store(&abm->batch_start_time, 0);
    
    pthread_mutex_init(&abm->batch_lock, NULL);
    pthread_cond_init(&abm->batch_ready, NULL);
    
    abm->batch_processing_active = true;
    
    printf("AI Integration: Adaptive batch manager initialized\n");
    return 0;
}

static bool should_process_batch(adaptive_batch_manager_t* abm) {
    size_t current_size = atomic_load(&abm->current_batch_size);
    uint64_t current_time = __builtin_ia32_rdtsc();
    uint64_t batch_start = atomic_load(&abm->batch_start_time);
    
    // Process if batch is full or timeout exceeded
    return (current_size >= ADAPTIVE_BATCH_MAX_SIZE) ||
           (current_size >= ADAPTIVE_BATCH_MIN_SIZE && 
            (current_time - batch_start) > BATCH_TIMEOUT_NS * 3400); // Convert ns to cycles
}

static size_t process_batch(adaptive_batch_manager_t* abm) {
    pthread_mutex_lock(&abm->batch_lock);
    
    size_t batch_size = atomic_load(&abm->current_batch_size);
    if (batch_size == 0) {
        pthread_mutex_unlock(&abm->batch_lock);
        return 0;
    }
    
    // Collect batch messages
    enhanced_msg_header_t* messages[ADAPTIVE_BATCH_MAX_SIZE];
    const void* payloads[ADAPTIVE_BATCH_MAX_SIZE];
    ai_routing_decision_t decisions[ADAPTIVE_BATCH_MAX_SIZE];
    
    for (size_t i = 0; i < batch_size; i++) {
        messages[i] = abm->pending_messages[i];
        payloads[i] = abm->pending_payloads[i];
    }
    
    // Reset batch
    atomic_store(&abm->current_batch_size, 0);
    atomic_store(&abm->batch_start_time, __builtin_ia32_rdtsc());
    
    pthread_mutex_unlock(&abm->batch_lock);
    
    // Process batch using AI router
    size_t processed = ai_route_message_batch((const enhanced_msg_header_t**)messages,
                                             payloads, batch_size, decisions);
    
    // Store decisions back (simplified - would need proper synchronization)
    for (size_t i = 0; i < processed; i++) {
        if (abm->pending_decisions[i]) {
            *abm->pending_decisions[i] = decisions[i];
        }
    }
    
    return processed;
}

static void* batch_processor_worker(void* arg) {
    ai_integration_service_t* service = (ai_integration_service_t*)arg;
    adaptive_batch_manager_t* abm = service->batch_manager;
    
    while (service->running) {
        if (should_process_batch(abm)) {
            size_t processed = process_batch(abm);
            
            if (processed > 0) {
                atomic_fetch_add(&service->stats.batch_processing_count, processed);
            }
        }
        
        usleep(1000); // 1ms polling interval
    }
    
    return NULL;
}

// ============================================================================
// DISTRIBUTED AI COORDINATION
// ============================================================================

static int init_distributed_coordinator(distributed_ai_coordinator_t** coordinator,
                                       raft_node_id_t local_node_id) {
    *coordinator = aligned_alloc(64, sizeof(distributed_ai_coordinator_t));
    if (!*coordinator) return -ENOMEM;
    
    distributed_ai_coordinator_t* dc = *coordinator;
    memset(dc, 0, sizeof(distributed_ai_coordinator_t));
    
    dc->local_node_id = local_node_id;
    dc->is_ai_coordinator = false; // Will be determined by consensus
    dc->global_model_version = 0;
    dc->local_model_version = 0;
    
    // Initialize node tracking
    for (int i = 0; i < 64; i++) {
        dc->node_ai_loads[i] = 0.0f;
        dc->node_last_seen[i] = 0;
    }
    
    // Allocate model synchronization buffer
    dc->model_sync_buffer_size = 1024 * 1024; // 1MB
    dc->model_sync_buffer = aligned_alloc(4096, dc->model_sync_buffer_size);
    if (!dc->model_sync_buffer) {
        free(dc);
        return -ENOMEM;
    }
    
    pthread_mutex_init(&dc->coordination_lock, NULL);
    
    printf("AI Integration: Distributed coordinator initialized (node %u)\n", local_node_id);
    return 0;
}

static void update_node_ai_load(distributed_ai_coordinator_t* dc,
                               raft_node_id_t node_id,
                               float ai_load) {
    if (!dc || node_id >= 64) return;
    
    pthread_mutex_lock(&dc->coordination_lock);
    
    dc->node_ai_loads[node_id] = ai_load;
    dc->node_last_seen[node_id] = __builtin_ia32_rdtsc();
    
    pthread_mutex_unlock(&dc->coordination_lock);
}

static raft_node_id_t select_best_ai_node(distributed_ai_coordinator_t* dc) {
    if (!dc) return 0;
    
    pthread_mutex_lock(&dc->coordination_lock);
    
    raft_node_id_t best_node = dc->local_node_id;
    float best_load = 1.0f;
    uint64_t current_time = __builtin_ia32_rdtsc();
    
    // Find node with lowest AI load and recent heartbeat
    for (raft_node_id_t i = 0; i < 64; i++) {
        uint64_t time_delta = current_time - dc->node_last_seen[i];
        
        // Node must have been seen in last 5 seconds
        if (time_delta < (5000ULL * 3400ULL * 1000ULL) && // 5 seconds in cycles
            dc->node_ai_loads[i] < best_load) {
            best_load = dc->node_ai_loads[i];
            best_node = i;
        }
    }
    
    pthread_mutex_unlock(&dc->coordination_lock);
    
    return best_node;
}

// ============================================================================
// INTEGRATED ROUTING FUNCTION
// ============================================================================

static uint32_t integrated_route_message(const enhanced_msg_header_t* msg, const void* payload) {
    if (!g_integration_service || !g_integration_service->running) {
        // Fallback to original routing
        if (g_integration_service && g_integration_service->original_route_function) {
            return g_integration_service->original_route_function(msg, payload);
        }
        return msg->target_agents[0]; // Simple passthrough
    }
    
    uint64_t start_time = __builtin_ia32_rdtsc();
    ai_integration_service_t* service = g_integration_service;
    
    // Increment total message counter
    atomic_fetch_add(&service->stats.total_messages_processed, 1);
    
    // Check if AI routing should be used
    bool use_ai_routing = service->ai_routing_enabled;
    
    if (use_ai_routing && service->feedback_system) {
        pthread_rwlock_rdlock(&service->feedback_system->feedback_lock);
        
        float current_load = atomic_load_explicit(&service->stats.current_system_load, 
                                                 memory_order_relaxed);
        float load_threshold = service->feedback_system->dynamic_load_threshold;
        
        pthread_rwlock_unlock(&service->feedback_system->feedback_lock);
        
        // Disable AI routing if system load is too low (not worth the overhead)
        if (current_load < load_threshold) {
            use_ai_routing = false;
        }
    }
    
    uint32_t routing_result;
    float accuracy_score = 0.0f;
    
    if (use_ai_routing) {
        // Use AI-enhanced routing
        ai_routing_decision_t decision = ai_get_routing_decision(msg, payload);
        
        // Check confidence threshold
        float confidence_threshold = AI_CONFIDENCE_MINIMUM;
        if (service->feedback_system) {
            pthread_rwlock_rdlock(&service->feedback_system->feedback_lock);
            confidence_threshold = service->feedback_system->dynamic_confidence_threshold;
            pthread_rwlock_unlock(&service->feedback_system->feedback_lock);
        }
        
        if (decision.confidence_score >= confidence_threshold) {
            routing_result = decision.recommended_target;
            accuracy_score = decision.confidence_score;
            
            atomic_fetch_add(&service->stats.ai_routing_enabled_count, 1);
            
            uint64_t ai_time = __builtin_ia32_rdtsc() - start_time;
            atomic_fetch_add(&service->stats.ai_routing_time_ns, ai_time * 1000 / 3400);
            
        } else {
            // AI confidence too low, fallback to traditional routing
            if (service->original_route_function) {
                routing_result = service->original_route_function(msg, payload);
            } else {
                routing_result = msg->target_agents[0];
            }
            
            atomic_fetch_add(&service->stats.fallback_routing_count, 1);
        }
    } else {
        // Use traditional routing
        if (service->original_route_function) {
            routing_result = service->original_route_function(msg, payload);
        } else {
            routing_result = msg->target_agents[0];
        }
        
        atomic_fetch_add(&service->stats.ai_routing_disabled_count, 1);
        
        uint64_t traditional_time = __builtin_ia32_rdtsc() - start_time;
        atomic_fetch_add(&service->stats.traditional_routing_time_ns, 
                        traditional_time * 1000 / 3400);
    }
    
    // Update performance feedback
    if (service->feedback_system) {
        uint64_t total_time = (__builtin_ia32_rdtsc() - start_time) * 1000 / 3400;
        uint32_t system_load = (uint32_t)(atomic_load(&service->stats.current_system_load) * 1000);
        
        update_performance_feedback(service->feedback_system, total_time, 
                                   accuracy_score, system_load);
    }
    
    // Update total routing time
    uint64_t end_time = __builtin_ia32_rdtsc();
    atomic_fetch_add(&service->stats.total_routing_time_ns, 
                    (end_time - start_time) * 1000 / 3400);
    
    return routing_result;
}

// ============================================================================
// STATISTICS AND MONITORING
// ============================================================================

static void* stats_collector_worker(void* arg) {
    ai_integration_service_t* service = (ai_integration_service_t*)arg;
    
    while (service->running) {
        // Calculate current system metrics
        uint64_t total_messages = atomic_load(&service->stats.total_messages_processed);
        uint64_t ai_messages = atomic_load(&service->stats.ai_routing_enabled_count);
        uint64_t total_time = atomic_load(&service->stats.total_routing_time_ns);
        
        // Update derived metrics
        if (total_messages > 0) {
            float ai_usage_ratio = (float)ai_messages / total_messages;
            atomic_store(&service->stats.current_ai_confidence, ai_usage_ratio);
            
            float avg_latency = (float)total_time / total_messages;
            float load_estimate = avg_latency / 10000.0f; // Normalize to 0-1 range
            if (load_estimate > 1.0f) load_estimate = 1.0f;
            
            atomic_store(&service->stats.current_system_load, load_estimate);
        }
        
        // Update distributed coordinator if enabled
        if (service->coordinator && service->distributed_coordination_enabled) {
            float local_load = atomic_load(&service->stats.current_system_load);
            update_node_ai_load(service->coordinator, service->coordinator->local_node_id, 
                               local_load);
        }
        
        usleep(STATS_COLLECTION_INTERVAL_MS * 1000);
    }
    
    return NULL;
}

// ============================================================================
// SERVICE INITIALIZATION AND MANAGEMENT
// ============================================================================

int ai_integration_service_init(raft_node_id_t local_node_id) {
    if (g_integration_service) {
        return -EALREADY;
    }
    
    // Initialize AI router first
    if (ai_router_service_init() != 0) {
        printf("AI Integration: Failed to initialize AI router service\n");
        return -1;
    }
    
    // Allocate integration service
    g_integration_service = aligned_alloc(4096, sizeof(ai_integration_service_t));
    if (!g_integration_service) {
        ai_router_service_cleanup();
        return -ENOMEM;
    }
    
    memset(g_integration_service, 0, sizeof(ai_integration_service_t));
    ai_integration_service_t* service = g_integration_service;
    
    // Initialize components
    if (init_performance_feedback(&service->feedback_system) != 0) {
        printf("AI Integration: Failed to initialize performance feedback\n");
        free(service);
        g_integration_service = NULL;
        return -1;
    }
    
    if (init_adaptive_batch_manager(&service->batch_manager) != 0) {
        printf("AI Integration: Failed to initialize batch manager\n");
        free(service->feedback_system);
        free(service);
        g_integration_service = NULL;
        return -1;
    }
    
    if (init_distributed_coordinator(&service->coordinator, local_node_id) != 0) {
        printf("AI Integration: Failed to initialize distributed coordinator\n");
        free(service->batch_manager);
        free(service->feedback_system);
        free(service);
        g_integration_service = NULL;
        return -1;
    }
    
    // Initialize Enhanced Vector Router
    printf("AI Integration: Initializing enhanced vector router...\n");
    g_vector_router = vector_router_create("/tmp/claude_vectors", VECTOR_DIM_SENTENCE_BERT);
    if (!g_vector_router) {
        printf("AI Integration: Failed to initialize vector router (continuing without it)\n");
    } else {
        printf("AI Integration: Enhanced vector router initialized successfully\n");
        printf("AI Integration: Vector router version: %s\n", vector_router_version());
        
        // Pre-populate with known agent patterns for semantic routing
        ai_router_populate_vector_database();
    }
    
    // Initialize statistics
    memset(&service->stats, 0, sizeof(integration_stats_t));
    atomic_store(&service->stats.current_system_load, 0.0f);
    atomic_store(&service->stats.current_ai_confidence, 0.0f);
    
    // Set default configuration
    service->ai_routing_enabled = true;
    service->auto_adaptation_enabled = true;
    service->distributed_coordination_enabled = (local_node_id > 0);
    
    pthread_mutex_init(&service->service_lock, NULL);
    service->running = true;
    
    // Start worker threads
    pthread_create(&service->stats_thread, NULL, stats_collector_worker, service);
    pthread_create(&service->batch_processor_thread, NULL, batch_processor_worker, service);
    
    printf("AI Integration: Service initialized successfully\n");
    printf("AI Integration: - Local Node ID: %u\n", local_node_id);
    printf("AI Integration: - AI Routing: %s\n", service->ai_routing_enabled ? "enabled" : "disabled");
    printf("AI Integration: - Auto Adaptation: %s\n", service->auto_adaptation_enabled ? "enabled" : "disabled");
    printf("AI Integration: - Distributed Coordination: %s\n", service->distributed_coordination_enabled ? "enabled" : "disabled");
    
    return 0;
}

// ============================================================================
// VECTOR ROUTER INTEGRATION FUNCTIONS
// ============================================================================

// Generate a simple embedding for a message (placeholder - real implementation would use ML)
static void generate_message_embedding(const char* message, float* embedding, size_t dim) {
    if (!message || !embedding) return;
    
    // Simple hash-based embedding for demonstration
    // In production, this would use a real embedding model
    uint32_t hash = 5381;
    const char* p = message;
    while (*p) {
        hash = ((hash << 5) + hash) + *p++;
    }
    
    // Generate pseudo-random embedding based on hash
    for (size_t i = 0; i < dim; i++) {
        hash = hash * 1103515245 + 12345;
        embedding[i] = ((hash / 65536) % 32768) / 32768.0f;
    }
    
    // Normalize the embedding
    float norm = 0.0f;
    for (size_t i = 0; i < dim; i++) {
        norm += embedding[i] * embedding[i];
    }
    norm = sqrtf(norm);
    if (norm > 0.0f) {
        for (size_t i = 0; i < dim; i++) {
            embedding[i] /= norm;
        }
    }
}

// Populate vector database with known agent patterns
static void ai_router_populate_vector_database(void) {
    if (!g_vector_router) return;
    
    printf("AI Integration: Populating vector database with agent patterns...\n");
    
    // Define agent pattern embeddings
    struct {
        const char* pattern;
        const char* agent;
    } agent_patterns[] = {
        {"build compile make cmake", "constructor_agent"},
        {"debug trace breakpoint segfault", "debugger_agent"},
        {"security vulnerability CVE", "security_agent"},
        {"deploy kubernetes docker", "deployer_agent"},
        {"monitor metrics prometheus", "monitor_agent"},
        {"optimize performance speed", "optimizer_agent"},
        {"lint format style", "linter_agent"},
        {"test unit integration", "testbed_agent"},
        {"database sql query", "database_agent"},
        {"api rest graphql", "apidesigner_agent"},
        {"web react vue angular", "web_agent"},
        {"mobile ios android", "mobile_agent"},
        {"python tkinter streamlit", "pygui_agent"},
        {"terminal ncurses tui", "tui_agent"},
        {"machine learning model", "mlops_agent"},
        {"data analysis pandas", "datascience_agent"},
        {NULL, NULL}
    };
    
    float embedding[VECTOR_DIM_SENTENCE_BERT];
    int count = 0;
    
    for (int i = 0; agent_patterns[i].pattern != NULL; i++) {
        generate_message_embedding(agent_patterns[i].pattern, embedding, VECTOR_DIM_SENTENCE_BERT);
        
        if (vector_router_insert(g_vector_router, embedding, VECTOR_DIM_SENTENCE_BERT, 
                                agent_patterns[i].agent)) {
            count++;
        }
    }
    
    printf("AI Integration: Populated vector database with %d agent patterns\n", count);
}

// Route a message using semantic similarity
static const char* ai_router_semantic_route(const char* message) {
    if (!g_vector_router || !message) {
        return NULL;
    }
    
    float embedding[VECTOR_DIM_SENTENCE_BERT];
    generate_message_embedding(message, embedding, VECTOR_DIM_SENTENCE_BERT);
    
    // Search for most similar pattern
    CSearchResults results = vector_router_search(g_vector_router, embedding, 
                                                 VECTOR_DIM_SENTENCE_BERT, 3);
    
    const char* best_agent = NULL;
    if (results.count > 0 && results.results[0].similarity > 0.7f) {
        best_agent = results.results[0].metadata;
    }
    
    // Free results
    vector_router_free_results(results);
    
    return best_agent;
}

// Process a message with AI-enhanced routing
int ai_router_process_message(enhanced_msg_header_t* msg, uint8_t* payload) {
    if (!msg || !g_integration_service) {
        return -1;
    }
    
    // Try semantic routing if enabled
    if (g_integration_service->ai_routing_enabled && g_vector_router) {
        // Extract message content for semantic analysis
        char message_content[256] = {0};
        if (payload && msg->payload_len > 0) {
            size_t copy_len = msg->payload_len < 255 ? msg->payload_len : 255;
            memcpy(message_content, payload, copy_len);
            message_content[copy_len] = '\0';
        }
        
        // Get semantic routing suggestion
        const char* suggested_agent = ai_router_semantic_route(message_content);
        if (suggested_agent) {
            printf("AI Router: Semantic routing suggests agent: %s\n", suggested_agent);
            
            // Update message routing metadata
            msg->flags |= 0x8000; // Mark as AI-routed
            
            // Update metrics
            atomic_fetch_add(&g_integration_service->stats.ai_routing_enabled_count, 1);
        }
    }
    
    return 0;
}

// Get vector router performance metrics
void ai_router_get_vector_metrics(void) {
    if (!g_vector_router) return;
    
    uint64_t total_searches = 0;
    uint64_t p_core_searches = 0;
    uint64_t e_core_searches = 0;
    uint64_t avg_latency_us = 0;
    
    if (vector_router_get_metrics(g_vector_router, &total_searches, 
                                 &p_core_searches, &e_core_searches, 
                                 &avg_latency_us)) {
        printf("Vector Router Metrics:\n");
        printf("  Total Searches: %lu\n", total_searches);
        printf("  P-Core Searches: %lu\n", p_core_searches);
        printf("  E-Core Searches: %lu\n", e_core_searches);
        printf("  Avg Latency: %lu μs\n", avg_latency_us);
    }
}

void ai_integration_service_cleanup(void) {
    if (!g_integration_service) {
        return;
    }
    
    ai_integration_service_t* service = g_integration_service;
    service->running = false;
    
    // Stop worker threads
    pthread_join(service->stats_thread, NULL);
    pthread_join(service->batch_processor_thread, NULL);
    
    // Cleanup components
    if (service->feedback_system) {
        pthread_rwlock_destroy(&service->feedback_system->feedback_lock);
        free(service->feedback_system);
    }
    
    if (service->batch_manager) {
        pthread_mutex_destroy(&service->batch_manager->batch_lock);
        pthread_cond_destroy(&service->batch_manager->batch_ready);
        free(service->batch_manager);
    }
    
    if (service->coordinator) {
        pthread_mutex_destroy(&service->coordinator->coordination_lock);
        free(service->coordinator->model_sync_buffer);
        free(service->coordinator);
    }
    
    pthread_mutex_destroy(&service->service_lock);
    
    free(service);
    g_integration_service = NULL;
    
    // Cleanup Enhanced Vector Router
    if (g_vector_router) {
        printf("AI Integration: Shutting down enhanced vector router...\n");
        vector_router_destroy(g_vector_router);
        g_vector_router = NULL;
    }
    
    // Cleanup AI router
    ai_router_service_cleanup();
    
    printf("AI Integration: Service cleaned up\n");
}

// ============================================================================
// PUBLIC API FUNCTIONS
// ============================================================================

// Enable/disable AI routing
int ai_integration_set_ai_routing_enabled(bool enabled) {
    if (!g_integration_service) return -1;
    
    g_integration_service->ai_routing_enabled = enabled;
    
    printf("AI Integration: AI routing %s\n", enabled ? "enabled" : "disabled");
    return 0;
}

// Set original routing function for fallback
int ai_integration_set_fallback_router(uint32_t (*route_func)(const enhanced_msg_header_t*, const void*)) {
    if (!g_integration_service) return -1;
    
    g_integration_service->original_route_function = route_func;
    return 0;
}

// Get the integrated routing function
uint32_t (*ai_integration_get_router(void))(const enhanced_msg_header_t*, const void*) {
    return integrated_route_message;
}

// Get integration statistics
void ai_integration_get_stats(uint64_t* total_messages,
                             uint64_t* ai_routed,
                             uint64_t* traditional_routed,
                             float* current_load,
                             float* ai_confidence) {
    if (!g_integration_service) {
        if (total_messages) *total_messages = 0;
        if (ai_routed) *ai_routed = 0;
        if (traditional_routed) *traditional_routed = 0;
        if (current_load) *current_load = 0.0f;
        if (ai_confidence) *ai_confidence = 0.0f;
        return;
    }
    
    if (total_messages) {
        *total_messages = atomic_load(&g_integration_service->stats.total_messages_processed);
    }
    if (ai_routed) {
        *ai_routed = atomic_load(&g_integration_service->stats.ai_routing_enabled_count);
    }
    if (traditional_routed) {
        *traditional_routed = atomic_load(&g_integration_service->stats.ai_routing_disabled_count) +
                             atomic_load(&g_integration_service->stats.fallback_routing_count);
    }
    if (current_load) {
        *current_load = atomic_load(&g_integration_service->stats.current_system_load);
    }
    if (ai_confidence) {
        *ai_confidence = atomic_load(&g_integration_service->stats.current_ai_confidence);
    }
}

// Print comprehensive integration statistics
void ai_integration_print_stats(void) {
    if (!g_integration_service) {
        printf("AI Integration: Service not initialized\n");
        return;
    }
    
    ai_integration_service_t* service = g_integration_service;
    
    printf("\n=== AI Integration Statistics ===\n");
    printf("Total messages processed: %lu\n", 
           atomic_load(&service->stats.total_messages_processed));
    printf("AI routing enabled: %lu (%.1f%%)\n",
           atomic_load(&service->stats.ai_routing_enabled_count),
           100.0f * atomic_load(&service->stats.ai_routing_enabled_count) / 
           (atomic_load(&service->stats.total_messages_processed) + 1));
    printf("AI routing disabled: %lu (%.1f%%)\n",
           atomic_load(&service->stats.ai_routing_disabled_count),
           100.0f * atomic_load(&service->stats.ai_routing_disabled_count) / 
           (atomic_load(&service->stats.total_messages_processed) + 1));
    printf("Fallback routing: %lu (%.1f%%)\n",
           atomic_load(&service->stats.fallback_routing_count),
           100.0f * atomic_load(&service->stats.fallback_routing_count) / 
           (atomic_load(&service->stats.total_messages_processed) + 1));
    printf("Batch processing: %lu messages\n",
           atomic_load(&service->stats.batch_processing_count));
    
    // Performance metrics
    uint64_t total_time = atomic_load(&service->stats.total_routing_time_ns);
    uint64_t total_messages = atomic_load(&service->stats.total_messages_processed);
    
    if (total_messages > 0) {
        printf("Average routing latency: %.2f μs\n", 
               (float)total_time / total_messages / 1000.0f);
    }
    
    printf("Current system load: %.3f\n", 
           atomic_load(&service->stats.current_system_load));
    printf("Current AI confidence: %.3f\n", 
           atomic_load(&service->stats.current_ai_confidence));
    
    // Adaptive thresholds
    if (service->feedback_system) {
        pthread_rwlock_rdlock(&service->feedback_system->feedback_lock);
        printf("Dynamic confidence threshold: %.3f\n", 
               service->feedback_system->dynamic_confidence_threshold);
        printf("Dynamic load threshold: %.3f\n", 
               service->feedback_system->dynamic_load_threshold);
        pthread_rwlock_unlock(&service->feedback_system->feedback_lock);
    }
    
    printf("\n");
    
    // Print underlying AI router statistics
    ai_print_routing_stats();
}

// Get current adaptive thresholds
void ai_integration_get_thresholds(float* confidence_threshold,
                                  float* load_threshold,
                                  uint64_t* latency_threshold_ns) {
    if (!g_integration_service || !g_integration_service->feedback_system) {
        if (confidence_threshold) *confidence_threshold = AI_CONFIDENCE_MINIMUM;
        if (load_threshold) *load_threshold = AI_ACTIVATION_LOAD_THRESHOLD;
        if (latency_threshold_ns) *latency_threshold_ns = AI_ACTIVATION_LATENCY_THRESHOLD_NS;
        return;
    }
    
    performance_feedback_t* pf = g_integration_service->feedback_system;
    pthread_rwlock_rdlock(&pf->feedback_lock);
    
    if (confidence_threshold) {
        *confidence_threshold = pf->dynamic_confidence_threshold;
    }
    if (load_threshold) {
        *load_threshold = pf->dynamic_load_threshold;
    }
    if (latency_threshold_ns) {
        *latency_threshold_ns = pf->dynamic_latency_threshold_ns;
    }
    
    pthread_rwlock_unlock(&pf->feedback_lock);
}

// Force threshold update (for testing/debugging)
int ai_integration_update_thresholds(float confidence_threshold,
                                    float load_threshold,
                                    uint64_t latency_threshold_ns) {
    if (!g_integration_service || !g_integration_service->feedback_system) {
        return -1;
    }
    
    performance_feedback_t* pf = g_integration_service->feedback_system;
    pthread_rwlock_wrlock(&pf->feedback_lock);
    
    pf->dynamic_confidence_threshold = confidence_threshold;
    pf->dynamic_load_threshold = load_threshold;
    pf->dynamic_latency_threshold_ns = latency_threshold_ns;
    
    atomic_fetch_add(&g_integration_service->stats.threshold_adjustments, 1);
    
    pthread_rwlock_unlock(&pf->feedback_lock);
    
    printf("AI Integration: Thresholds updated - confidence=%.3f, load=%.3f, latency=%lu ns\n",
           confidence_threshold, load_threshold, latency_threshold_ns);
    
    return 0;
}