/*
 * CONSTRUCTOR AGENT - Communication System Integration
 * Version 2.0 - Production-ready implementation
 */
#include "agent_protocol.h"
#include "agent_system.h"
#include "compatibility_layer.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdatomic.h>
#include <pthread.h>
#include <signal.h>
#include <errno.h>
#include <syslog.h>
#include <sys/mman.h>
#include <unistd.h>

#define AGENT_NAME_MAX          64
#define RECV_TIMEOUT_MS         100
#define MAX_RETRY_COUNT         3
#define CONSTRUCTOR_VERSION     "2.0.0"
#define MAX_BUILD_QUEUE         100
#define MAX_TEMPLATE_SIZE       (1024 * 1024)  // 1MB
#define BUILD_CACHE_SIZE        50

// Error codes
typedef enum {
    CONSTRUCTOR_SUCCESS = 0,
    CONSTRUCTOR_ERR_INIT = -1,
    CONSTRUCTOR_ERR_COMM = -2,
    CONSTRUCTOR_ERR_MEMORY = -3,
    CONSTRUCTOR_ERR_INVALID_PARAM = -4,
    CONSTRUCTOR_ERR_REGISTRATION = -5,
    CONSTRUCTOR_ERR_BUILD_FAILED = -6,
    CONSTRUCTOR_ERR_TEMPLATE_INVALID = -7,
    CONSTRUCTOR_ERR_QUEUE_FULL = -8
} constructor_error_t;

// Build request types
typedef enum {
    BUILD_TYPE_FUNCTION = 1,
    BUILD_TYPE_CLASS,
    BUILD_TYPE_MODULE,
    BUILD_TYPE_TEMPLATE,
    BUILD_TYPE_SCAFFOLD,
    BUILD_TYPE_TEST,
    BUILD_TYPE_DOCUMENTATION
} build_type_t;

// Build request structure
typedef struct {
    uint32_t request_id;
    build_type_t type;
    char* template_name;
    char* parameters;
    size_t param_size;
    uint32_t flags;
    uint64_t timestamp;
} build_request_t;

// Build result structure
typedef struct {
    uint32_t request_id;
    constructor_error_t status;
    char* generated_code;
    size_t code_size;
    uint32_t line_count;
    char* metadata;
    uint64_t build_time_us;
} build_result_t;

// Template cache entry
typedef struct {
    char name[128];
    char* template_data;
    size_t template_size;
    uint32_t usage_count;
    uint64_t last_used;
} template_cache_entry_t;

// Build queue node
typedef struct build_queue_node {
    build_request_t request;
    struct build_queue_node* next;
} build_queue_node_t;

// Agent definition with enhanced fields
typedef struct {
    ufp_context_t* comm_context;
    char name[AGENT_NAME_MAX];
    uint32_t agent_id;
    atomic_int state;
    pthread_mutex_t lock;
    pthread_cond_t queue_cond;
    
    // Build queue
    build_queue_node_t* queue_head;
    build_queue_node_t* queue_tail;
    atomic_uint queue_size;
    
    // Worker threads
    pthread_t* worker_threads;
    uint32_t worker_count;
    
    // Template cache
    template_cache_entry_t* template_cache;
    uint32_t cache_size;
    pthread_rwlock_t cache_lock;
    
    // Statistics
    atomic_uint builds_completed;
    atomic_uint builds_failed;
    atomic_uint templates_loaded;
    atomic_ullong total_lines_generated;
    atomic_ullong total_build_time_us;
    
    // Configuration
    char* template_dir;
    uint32_t max_build_size;
    uint32_t timeout_seconds;
} constructor_agent_t;

// Global agent instance for signal handling
static constructor_agent_t* g_agent = NULL;

// Signal handler for graceful shutdown
static void signal_handler(int sig) {
    if (g_agent) {
        syslog(LOG_INFO, "Constructor agent received signal %d, shutting down", sig);
        atomic_store(&g_agent->state, AGENT_STATE_SHUTDOWN);
        pthread_cond_broadcast(&g_agent->queue_cond);
    }
}

// Load template from disk with caching
static char* load_template(constructor_agent_t* agent, const char* template_name) {
    pthread_rwlock_rdlock(&agent->cache_lock);
    
    // Check cache first
    for (uint32_t i = 0; i < agent->cache_size; i++) {
        if (agent->template_cache[i].template_data &&
            strcmp(agent->template_cache[i].name, template_name) == 0) {
            agent->template_cache[i].usage_count++;
            agent->template_cache[i].last_used = time(NULL);
            char* cached = strdup(agent->template_cache[i].template_data);
            pthread_rwlock_unlock(&agent->cache_lock);
            return cached;
        }
    }
    pthread_rwlock_unlock(&agent->cache_lock);
    
    // Load from disk
    char filepath[512];
    snprintf(filepath, sizeof(filepath), "%s/%s.template", 
             agent->template_dir ? agent->template_dir : "/etc/constructor/templates",
             template_name);
    
    FILE* file = fopen(filepath, "r");
    if (!file) {
        syslog(LOG_WARNING, "Failed to open template: %s", filepath);
        return NULL;
    }
    
    // Get file size
    fseek(file, 0, SEEK_END);
    size_t size = ftell(file);
    fseek(file, 0, SEEK_SET);
    
    if (size > MAX_TEMPLATE_SIZE) {
        fclose(file);
        syslog(LOG_ERR, "Template too large: %zu bytes", size);
        return NULL;
    }
    
    char* template = malloc(size + 1);
    if (!template) {
        fclose(file);
        return NULL;
    }
    
    size_t read = fread(template, 1, size, file);
    fclose(file);
    
    if (read != size) {
        free(template);
        return NULL;
    }
    
    template[size] = '\0';
    
    // Add to cache
    pthread_rwlock_wrlock(&agent->cache_lock);
    
    // Find LRU entry or empty slot
    uint32_t cache_idx = 0;
    uint64_t oldest_time = UINT64_MAX;
    
    for (uint32_t i = 0; i < agent->cache_size; i++) {
        if (!agent->template_cache[i].template_data) {
            cache_idx = i;
            break;
        }
        if (agent->template_cache[i].last_used < oldest_time) {
            oldest_time = agent->template_cache[i].last_used;
            cache_idx = i;
        }
    }
    
    // Free old entry if replacing
    if (agent->template_cache[cache_idx].template_data) {
        free(agent->template_cache[cache_idx].template_data);
    }
    
    // Store new entry
    strncpy(agent->template_cache[cache_idx].name, template_name, 127);
    agent->template_cache[cache_idx].template_data = strdup(template);
    agent->template_cache[cache_idx].template_size = size;
    agent->template_cache[cache_idx].usage_count = 1;
    agent->template_cache[cache_idx].last_used = time(NULL);
    
    pthread_rwlock_unlock(&agent->cache_lock);
    
    atomic_fetch_add(&agent->templates_loaded, 1);
    return template;
}

// Generate code based on template and parameters
static build_result_t* generate_code(constructor_agent_t* agent, build_request_t* request) {
    build_result_t* result = calloc(1, sizeof(build_result_t));
    if (!result) {
        return NULL;
    }
    
    result->request_id = request->request_id;
    uint64_t start_time = clock();
    
    // Load appropriate template
    char* template = load_template(agent, request->template_name);
    if (!template) {
        result->status = CONSTRUCTOR_ERR_TEMPLATE_INVALID;
        return result;
    }
    
    // Parse parameters (simplified JSON-like format)
    char* generated = malloc(agent->max_build_size);
    if (!generated) {
        free(template);
        result->status = CONSTRUCTOR_ERR_MEMORY;
        return result;
    }
    
    // Template substitution engine
    char* output_ptr = generated;
    char* template_ptr = template;
    size_t output_size = 0;
    uint32_t line_count = 1;
    
    while (*template_ptr && output_size < agent->max_build_size - 1) {
        if (strncmp(template_ptr, "{{", 2) == 0) {
            // Find end of variable
            char* end = strstr(template_ptr + 2, "}}");
            if (end) {
                char var_name[128];
                size_t var_len = end - template_ptr - 2;
                if (var_len < sizeof(var_name)) {
                    strncpy(var_name, template_ptr + 2, var_len);
                    var_name[var_len] = '\0';
                    
                    // Look up variable in parameters
                    char* value = strstr(request->parameters, var_name);
                    if (value) {
                        value = strchr(value, ':');
                        if (value) {
                            value += 2; // Skip ": "
                            char* value_end = strchr(value, ',');
                            if (!value_end) value_end = strchr(value, '}');
                            
                            if (value_end) {
                                size_t copy_len = value_end - value;
                                if (output_size + copy_len < agent->max_build_size - 1) {
                                    // Remove quotes if present
                                    if (*value == '"') {
                                        value++;
                                        copy_len -= 2;
                                    }
                                    memcpy(output_ptr, value, copy_len);
                                    output_ptr += copy_len;
                                    output_size += copy_len;
                                }
                            }
                        }
                    }
                }
                template_ptr = end + 2;
                continue;
            }
        }
        
        if (*template_ptr == '\n') {
            line_count++;
        }
        
        *output_ptr++ = *template_ptr++;
        output_size++;
    }
    
    *output_ptr = '\0';
    free(template);
    
    // Store result
    result->generated_code = generated;
    result->code_size = output_size;
    result->line_count = line_count;
    result->status = CONSTRUCTOR_SUCCESS;
    result->build_time_us = clock() - start_time;
    
    // Generate metadata
    char metadata[256];
    snprintf(metadata, sizeof(metadata), 
             "Type: %d, Lines: %u, Size: %zu, Time: %lu us",
             request->type, line_count, output_size, result->build_time_us);
    result->metadata = strdup(metadata);
    
    // Update statistics
    atomic_fetch_add(&agent->builds_completed, 1);
    atomic_fetch_add(&agent->total_lines_generated, line_count);
    atomic_fetch_add(&agent->total_build_time_us, result->build_time_us);
    
    return result;
}

// Worker thread function
static void* worker_thread(void* arg) {
    constructor_agent_t* agent = (constructor_agent_t*)arg;
    
    syslog(LOG_INFO, "Constructor worker thread started");
    
    while (atomic_load(&agent->state) == AGENT_STATE_ACTIVE) {
        pthread_mutex_lock(&agent->lock);
        
        // Wait for work
        while (agent->queue_head == NULL && 
               atomic_load(&agent->state) == AGENT_STATE_ACTIVE) {
            pthread_cond_wait(&agent->queue_cond, &agent->lock);
        }
        
        if (atomic_load(&agent->state) != AGENT_STATE_ACTIVE) {
            pthread_mutex_unlock(&agent->lock);
            break;
        }
        
        // Get request from queue
        build_queue_node_t* node = agent->queue_head;
        if (node) {
            agent->queue_head = node->next;
            if (!agent->queue_head) {
                agent->queue_tail = NULL;
            }
            atomic_fetch_sub(&agent->queue_size, 1);
        }
        
        pthread_mutex_unlock(&agent->lock);
        
        if (node) {
            // Process build request
            build_result_t* result = generate_code(agent, &node->request);
            
            if (result) {
                // Send result back
                ufp_message_t* response = ufp_message_create();
                if (response) {
                    strncpy(response->source, agent->name, UFP_NAME_MAX - 1);
                    // Target would come from original request
                    response->target_count = 1;
                    response->msg_type = UFP_MSG_BUILD_RESULT;
                    
                    // Serialize result
                    response->payload_size = sizeof(build_result_t) + result->code_size;
                    response->payload = malloc(response->payload_size);
                    
                    if (response->payload) {
                        memcpy(response->payload, result, sizeof(build_result_t));
                        memcpy(response->payload + sizeof(build_result_t), 
                               result->generated_code, result->code_size);
                        
                        ufp_send(agent->comm_context, response);
                    }
                    
                    ufp_message_destroy(response);
                }
                
                // Cleanup
                free(result->generated_code);
                free(result->metadata);
                free(result);
            }
            
            // Cleanup request
            free(node->request.template_name);
            free(node->request.parameters);
            free(node);
        }
    }
    
    syslog(LOG_INFO, "Constructor worker thread exiting");
    return NULL;
}

// Initialize agent with full error handling
constructor_error_t constructor_init(constructor_agent_t* agent, const char* config_path) {
    if (!agent) {
        return CONSTRUCTOR_ERR_INVALID_PARAM;
    }
    
    memset(agent, 0, sizeof(constructor_agent_t));
    
    // Initialize synchronization primitives
    if (pthread_mutex_init(&agent->lock, NULL) != 0) {
        syslog(LOG_ERR, "Failed to initialize mutex: %s", strerror(errno));
        return CONSTRUCTOR_ERR_INIT;
    }
    
    if (pthread_cond_init(&agent->queue_cond, NULL) != 0) {
        pthread_mutex_destroy(&agent->lock);
        return CONSTRUCTOR_ERR_INIT;
    }
    
    if (pthread_rwlock_init(&agent->cache_lock, NULL) != 0) {
        pthread_mutex_destroy(&agent->lock);
        pthread_cond_destroy(&agent->queue_cond);
        return CONSTRUCTOR_ERR_INIT;
    }
    
    // Initialize communication context with retry logic
    int retry_count = 0;
    while (retry_count < MAX_RETRY_COUNT) {
        agent->comm_context = ufp_create_context("constructor");
        if (agent->comm_context) {
            break;
        }
        retry_count++;
        usleep(100000); // 100ms backoff
    }
    
    if (!agent->comm_context) {
        pthread_mutex_destroy(&agent->lock);
        pthread_cond_destroy(&agent->queue_cond);
        pthread_rwlock_destroy(&agent->cache_lock);
        syslog(LOG_ERR, "Failed to create communication context after %d retries", MAX_RETRY_COUNT);
        return CONSTRUCTOR_ERR_COMM;
    }
    
    // Set agent properties
    strncpy(agent->name, "constructor", AGENT_NAME_MAX - 1);
    agent->name[AGENT_NAME_MAX - 1] = '\0';
    atomic_store(&agent->state, AGENT_STATE_ACTIVE);
    
    // Configuration
    agent->max_build_size = 1024 * 1024; // 1MB default
    agent->timeout_seconds = 30;
    agent->worker_count = sysconf(_SC_NPROCESSORS_ONLN);
    if (agent->worker_count < 2) agent->worker_count = 2;
    if (agent->worker_count > 8) agent->worker_count = 8;
    
    // Initialize template cache
    agent->cache_size = BUILD_CACHE_SIZE;
    agent->template_cache = calloc(agent->cache_size, sizeof(template_cache_entry_t));
    if (!agent->template_cache) {
        constructor_cleanup(agent);
        return CONSTRUCTOR_ERR_MEMORY;
    }
    
    // Load configuration if provided
    if (config_path) {
        agent->template_dir = strdup(config_path);
        if (!agent->template_dir) {
            constructor_cleanup(agent);
            return CONSTRUCTOR_ERR_MEMORY;
        }
    }
    
    // Start worker threads
    agent->worker_threads = calloc(agent->worker_count, sizeof(pthread_t));
    if (!agent->worker_threads) {
        constructor_cleanup(agent);
        return CONSTRUCTOR_ERR_MEMORY;
    }
    
    for (uint32_t i = 0; i < agent->worker_count; i++) {
        if (pthread_create(&agent->worker_threads[i], NULL, worker_thread, agent) != 0) {
            syslog(LOG_ERR, "Failed to create worker thread %u", i);
            agent->worker_count = i; // Adjust count for cleanup
            constructor_cleanup(agent);
            return CONSTRUCTOR_ERR_INIT;
        }
    }
    
    // Register with discovery service
    agent_metadata_t metadata = {
        .version = CONSTRUCTOR_VERSION,
        .capabilities = AGENT_CAP_BUILD | AGENT_CAP_TEMPLATE | AGENT_CAP_ASYNC,
        .max_concurrent = agent->worker_count * 10
    };
    
    if (agent_register("constructor", AGENT_TYPE_CONSTRUCTOR, &metadata, sizeof(metadata)) != 0) {
        constructor_cleanup(agent);
        return CONSTRUCTOR_ERR_REGISTRATION;
    }
    
    // Set up signal handlers
    g_agent = agent;
    signal(SIGINT, signal_handler);
    signal(SIGTERM, signal_handler);
    
    syslog(LOG_INFO, "Constructor agent initialized with %u workers", agent->worker_count);
    return CONSTRUCTOR_SUCCESS;
}

// Process incoming message
static constructor_error_t constructor_process_message(constructor_agent_t* agent, ufp_message_t* msg) {
    if (!agent || !msg) {
        return CONSTRUCTOR_ERR_INVALID_PARAM;
    }
    
    syslog(LOG_DEBUG, "Processing message from %s, type: %d", msg->source, msg->msg_type);
    
    switch (msg->msg_type) {
        case UFP_MSG_BUILD_REQUEST: {
            // Check queue size
            if (atomic_load(&agent->queue_size) >= MAX_BUILD_QUEUE) {
                // Send error response
                ufp_message_t* response = ufp_message_create();
                if (response) {
                    strncpy(response->source, agent->name, UFP_NAME_MAX - 1);
                    strncpy(response->targets[0], msg->source, UFP_NAME_MAX - 1);
                    response->target_count = 1;
                    response->msg_type = UFP_MSG_ERROR;
                    response->error_code = CONSTRUCTOR_ERR_QUEUE_FULL;
                    ufp_send(agent->comm_context, response);
                    ufp_message_destroy(response);
                }
                return CONSTRUCTOR_ERR_QUEUE_FULL;
            }
            
            // Parse build request from payload
            build_request_t* request = (build_request_t*)msg->payload;
            
            // Create queue node
            build_queue_node_t* node = calloc(1, sizeof(build_queue_node_t));
            if (!node) {
                return CONSTRUCTOR_ERR_MEMORY;
            }
            
            // Copy request data
            memcpy(&node->request, request, sizeof(build_request_t));
            node->request.template_name = strdup((char*)(msg->payload + sizeof(build_request_t)));
            node->request.parameters = strdup((char*)(msg->payload + sizeof(build_request_t) + 
                                                      strlen(node->request.template_name) + 1));
            
            // Add to queue
            pthread_mutex_lock(&agent->lock);
            
            if (agent->queue_tail) {
                agent->queue_tail->next = node;
                agent->queue_tail = node;
            } else {
                agent->queue_head = agent->queue_tail = node;
            }
            
            atomic_fetch_add(&agent->queue_size, 1);
            pthread_cond_signal(&agent->queue_cond);
            
            pthread_mutex_unlock(&agent->lock);
            
            syslog(LOG_INFO, "Queued build request %u, queue size: %u", 
                   request->request_id, atomic_load(&agent->queue_size));
            break;
        }
        
        case UFP_MSG_STATUS_REQUEST: {
            // Return agent status
            ufp_message_t* response = ufp_message_create();
            if (response) {
                strncpy(response->source, agent->name, UFP_NAME_MAX - 1);
                strncpy(response->targets[0], msg->source, UFP_NAME_MAX - 1);
                response->target_count = 1;
                response->msg_type = UFP_MSG_STATUS_RESPONSE;
                
                // Create detailed status
                char status_buffer[512];
                uint64_t avg_build_time = 0;
                uint32_t builds = atomic_load(&agent->builds_completed);
                if (builds > 0) {
                    avg_build_time = atomic_load(&agent->total_build_time_us) / builds;
                }
                
                snprintf(status_buffer, sizeof(status_buffer),
                        "State: %d, Workers: %u, Queue: %u/%d, "
                        "Builds: %u, Failed: %u, Lines: %llu, "
                        "Avg Time: %lu us, Templates: %u",
                        atomic_load(&agent->state),
                        agent->worker_count,
                        atomic_load(&agent->queue_size),
                        MAX_BUILD_QUEUE,
                        builds,
                        atomic_load(&agent->builds_failed),
                        atomic_load(&agent->total_lines_generated),
                        avg_build_time,
                        atomic_load(&agent->templates_loaded));
                
                response->payload = strdup(status_buffer);
                response->payload_size = strlen(status_buffer);
                
                ufp_send(agent->comm_context, response);
                ufp_message_destroy(response);
            }
            break;
        }
        
        default: {
            // Send acknowledgment
            ufp_message_t* response = ufp_message_create();
            if (response) {
                strncpy(response->source, agent->name, UFP_NAME_MAX - 1);
                strncpy(response->targets[0], msg->source, UFP_NAME_MAX - 1);
                response->target_count = 1;
                response->msg_type = UFP_MSG_ACK;
                ufp_send(agent->comm_context, response);
                ufp_message_destroy(response);
            }
            break;
        }
    }
    
    return CONSTRUCTOR_SUCCESS;
}

// Main agent loop
void constructor_run(constructor_agent_t* agent) {
    if (!agent) {
        return;
    }
    
    ufp_message_t msg;
    int consecutive_errors = 0;
    
    syslog(LOG_INFO, "Constructor agent entering main loop");
    
    while (atomic_load(&agent->state) == AGENT_STATE_ACTIVE) {
        int recv_result = ufp_receive(agent->comm_context, &msg, RECV_TIMEOUT_MS);
        
        if (recv_result == UFP_SUCCESS) {
            consecutive_errors = 0;
            
            if (constructor_process_message(agent, &msg) != CONSTRUCTOR_SUCCESS) {
                syslog(LOG_WARNING, "Failed to process message");
            }
            
            // Clean up message payload
            if (msg.payload && msg.payload_size > 0) {
                free(msg.payload);
            }
        } else if (recv_result != UFP_TIMEOUT) {
            consecutive_errors++;
            syslog(LOG_WARNING, "Receive error: %d, consecutive errors: %d", 
                   recv_result, consecutive_errors);
            
            // Circuit breaker
            if (consecutive_errors >= 10) {
                syslog(LOG_ERR, "Too many consecutive errors, shutting down");
                atomic_store(&agent->state, AGENT_STATE_ERROR);
                break;
            }
            
            // Exponential backoff
            usleep(consecutive_errors * 100000);
        }
    }
    
    syslog(LOG_INFO, "Constructor agent exiting main loop");
}

// Cleanup function
void constructor_cleanup(constructor_agent_t* agent) {
    if (!agent) {
        return;
    }
    
    syslog(LOG_INFO, "Cleaning up constructor agent");
    
    // Signal shutdown
    atomic_store(&agent->state, AGENT_STATE_SHUTDOWN);
    pthread_cond_broadcast(&agent->queue_cond);
    
    // Wait for worker threads
    if (agent->worker_threads) {
        for (uint32_t i = 0; i < agent->worker_count; i++) {
            pthread_join(agent->worker_threads[i], NULL);
        }
        free(agent->worker_threads);
    }
    
    // Clean up queue
    pthread_mutex_lock(&agent->lock);
    build_queue_node_t* node = agent->queue_head;
    while (node) {
        build_queue_node_t* next = node->next;
        free(node->request.template_name);
        free(node->request.parameters);
        free(node);
        node = next;
    }
    pthread_mutex_unlock(&agent->lock);
    
    // Clean up template cache
    if (agent->template_cache) {
        for (uint32_t i = 0; i < agent->cache_size; i++) {
            free(agent->template_cache[i].template_data);
        }
        free(agent->template_cache);
    }
    
    // Unregister from discovery service
    agent_unregister("constructor");
    
    // Destroy communication context
    if (agent->comm_context) {
        ufp_destroy_context(agent->comm_context);
    }
    
    // Free configuration
    free(agent->template_dir);
    
    // Destroy synchronization primitives
    pthread_mutex_destroy(&agent->lock);
    pthread_cond_destroy(&agent->queue_cond);
    pthread_rwlock_destroy(&agent->cache_lock);
    
    // Clear global reference
    if (g_agent == agent) {
        g_agent = NULL;
    }
    
    syslog(LOG_INFO, "Constructor agent cleanup complete");
}

// Get statistics
void constructor_get_stats(constructor_agent_t* agent, uint32_t* builds, uint32_t* failures, 
                          uint64_t* lines, uint64_t* avg_time_us) {
    if (!agent) {
        return;
    }
    
    uint32_t completed = atomic_load(&agent->builds_completed);
    
    if (builds) *builds = completed;
    if (failures) *failures = atomic_load(&agent->builds_failed);
    if (lines) *lines = atomic_load(&agent->total_lines_generated);
    if (avg_time_us && completed > 0) {
        *avg_time_us = atomic_load(&agent->total_build_time_us) / completed;
    }
}