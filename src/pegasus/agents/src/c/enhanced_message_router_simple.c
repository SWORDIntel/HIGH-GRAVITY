/*
 * SIMPLIFIED ENHANCED MESSAGE ROUTER
 * 
 * Simplified version that focuses on compatibility and basic vectorization
 * Uses hardware CRC32 when available, falls back to software implementation
 * 100% API compatible with message_router.c
 * 
 * Author: CONSTRUCTOR Agent  
 * Version: 1.0 Simplified Enhanced
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <stdbool.h>
#include <stdatomic.h>
#include <pthread.h>
#include <sys/time.h>
#include <unistd.h>
#include <errno.h>
#include <sched.h>
#include <x86intrin.h>

// Include our simplified vector operations
#include "vector_ops_simple.h"
#include "compatibility_layer.h"

// ============================================================================
// SIMPLIFIED CPU CAPABILITIES IMPLEMENTATION
// ============================================================================

__thread simple_cpu_caps_t g_simple_caps = {0};
__thread bool g_simple_caps_init = false;

void simple_init_caps(void) {
    if (g_simple_caps_init) {
        return;
    }
    
    memset(&g_simple_caps, 0, sizeof(g_simple_caps));
    
    // Get current CPU ID
    g_simple_caps.cpu_id = sched_getcpu();
    
    // Simple capability detection using compiler flags
#ifdef __AVX2__
    g_simple_caps.has_avx2 = true;
#endif

#ifdef __SSE4_2__
    g_simple_caps.has_sse42 = true;
    g_simple_caps.has_crc32 = true;
#endif
    
    g_simple_caps.tested = true;
    g_simple_caps_init = true;
    
    printf("Simple Enhanced Router: CPU %d - AVX2: %s, SSE4.2: %s, CRC32: %s\n",
           g_simple_caps.cpu_id,
           g_simple_caps.has_avx2 ? "YES" : "NO",
           g_simple_caps.has_sse42 ? "YES" : "NO",
           g_simple_caps.has_crc32 ? "YES" : "NO");
}

// ============================================================================
// MESSAGE ROUTER API COMPATIBILITY LAYER
// ============================================================================

// Import the essential types and constants from original router
#define MAX_TOPICS 1024
#define MAX_TOPIC_NAME 128
#define MAX_SUBSCRIBERS_PER_TOPIC 64
#define MAX_MESSAGE_SIZE (16 * 1024 * 1024)
#define MESSAGE_TTL_DEFAULT_MS 30000

typedef enum {
    MSG_TYPE_PUBLISH = 1,
    MSG_TYPE_SUBSCRIBE = 2,
    MSG_TYPE_REQUEST = 4,
    MSG_TYPE_RESPONSE = 5
} message_type_t;

typedef enum {
    PRIORITY_EMERGENCY = 0,
    PRIORITY_CRITICAL = 1,
    PRIORITY_HIGH = 2,
    PRIORITY_NORMAL = 3,
    PRIORITY_LOW = 4,
    PRIORITY_BACKGROUND = 5
} message_priority_t;

typedef struct __attribute__((packed, aligned(64))) {
    uint32_t magic;               // 0x524F5554 ("ROUT")
    uint32_t message_id;
    uint64_t timestamp_ns;
    uint32_t source_agent_id;
    uint32_t correlation_id;
    message_type_t msg_type;
    message_priority_t priority;
    uint16_t flags;
    uint32_t payload_size;
    uint32_t ttl_ms;
    char topic[MAX_TOPIC_NAME];
    uint32_t checksum;
    uint8_t padding[20];
} routing_message_t;

// Simple router service structure
typedef struct {
    volatile bool running;
    uint32_t next_message_id;
    uint32_t next_correlation_id;
    uint64_t messages_processed;
    uint64_t enhanced_operations;
} simple_router_service_t;

static simple_router_service_t* g_simple_router = NULL;

// ============================================================================
// ENHANCED UTILITY FUNCTIONS
// ============================================================================

static inline uint64_t get_timestamp_ns() {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (uint64_t)ts.tv_sec * 1000000000ULL + ts.tv_nsec;
}

static inline uint32_t next_message_id() {
    return __atomic_fetch_add(&g_simple_router->next_message_id, 1, __ATOMIC_RELAXED);
}

// ENHANCED: Topic hashing with optimized hash function
static inline uint32_t enhanced_hash_topic(const char* topic) {
    uint32_t hash = simple_fast_hash(topic, strlen(topic));
    __atomic_fetch_add(&g_simple_router->enhanced_operations, 1, __ATOMIC_RELAXED);
    return hash % MAX_TOPICS;
}

// ENHANCED: Checksum calculation with hardware acceleration
static uint32_t enhanced_calculate_checksum(const void* data, size_t len) {
    uint32_t checksum = simple_calculate_checksum(data, len);
    __atomic_fetch_add(&g_simple_router->enhanced_operations, 1, __ATOMIC_RELAXED);
    return ~checksum;
}

// ============================================================================
// ENHANCED MESSAGE ROUTER FUNCTIONS
// ============================================================================

int simple_router_service_init() {
    printf("Simple Enhanced Message Router - Initializing\n");
    
    // Initialize CPU capabilities
    simple_init_caps();
    
    // Allocate router service structure
    g_simple_router = calloc(1, sizeof(simple_router_service_t));
    if (!g_simple_router) {
        return -ENOMEM;
    }
    
    g_simple_router->running = true;
    g_simple_router->next_message_id = 1;
    g_simple_router->next_correlation_id = 1;
    g_simple_router->messages_processed = 0;
    g_simple_router->enhanced_operations = 0;
    
    printf("Simple Enhanced Router initialized with hardware acceleration: %s\n",
           g_simple_caps.has_crc32 ? "CRC32" : "Software only");
    
    return 0;
}

void simple_router_service_cleanup() {
    if (g_simple_router) {
        g_simple_router->running = false;
        
        printf("Simple Enhanced Router Statistics:\n");
        printf("  Messages processed: %lu\n", g_simple_router->messages_processed);
        printf("  Enhanced operations: %lu\n", g_simple_router->enhanced_operations);
        printf("  Hardware acceleration: %s\n", g_simple_caps.has_crc32 ? "YES" : "NO");
        
        free(g_simple_router);
        g_simple_router = NULL;
    }
    
    printf("Simple Enhanced Message Router - Cleaned up\n");
}

// ENHANCED: Publish function with vectorized operations
int enhanced_publish_to_topic_simple(const char* topic_name, uint32_t source_agent_id,
                                      const void* payload, size_t payload_size,
                                      message_priority_t priority) {
    if (!g_simple_router || !topic_name || !payload || payload_size > MAX_MESSAGE_SIZE) {
        return -EINVAL;
    }
    
    // Ensure capabilities are initialized
    if (!g_simple_caps_init) {
        simple_init_caps();
    }
    
    // Use enhanced hash function for topic lookup  
    uint32_t hash = enhanced_hash_topic(topic_name);
    
    // Create routing message
    routing_message_t msg = {0};
    msg.magic = 0x524F5554;  // "ROUT"
    msg.message_id = next_message_id();
    msg.timestamp_ns = get_timestamp_ns();
    msg.source_agent_id = source_agent_id;
    msg.msg_type = MSG_TYPE_PUBLISH;
    msg.priority = priority;
    msg.payload_size = payload_size;
    msg.ttl_ms = MESSAGE_TTL_DEFAULT_MS;
    strncpy(msg.topic, topic_name, MAX_TOPIC_NAME - 1);
    msg.topic[MAX_TOPIC_NAME - 1] = '\0';
    
    // ENHANCED: Use hardware-accelerated checksum calculation
    msg.checksum = enhanced_calculate_checksum(&msg, sizeof(msg) - sizeof(msg.checksum));
    
    // Update statistics
    __atomic_fetch_add(&g_simple_router->messages_processed, 1, __ATOMIC_RELAXED);
    
    printf("Simple Enhanced Router: Published message %u to topic '%s' (hash: %u, checksum: 0x%08x)\n", 
           msg.message_id, topic_name, hash, msg.checksum);
    
    printf("  Acceleration: %s, Payload: %zu bytes\n",
           g_simple_caps.has_crc32 ? "Hardware CRC32" : "Software CRC32",
           payload_size);
    
    return 1;  // Simulated delivery count
}

// ============================================================================
// PERFORMANCE TESTING AND DEMONSTRATION
// ============================================================================

void test_vectorized_operations() {
    printf("\n=== Simple Enhanced Router Vectorized Operations Test ===\n");
    
    // Test data of various sizes
    const size_t test_sizes[] = {16, 32, 64, 128, 256, 512, 1024};
    const size_t num_sizes = sizeof(test_sizes) / sizeof(test_sizes[0]);
    
    printf("Testing enhanced checksum calculation:\n");
    
    for (size_t i = 0; i < num_sizes; i++) {
        char* test_data = malloc(test_sizes[i]);
        if (!test_data) continue;
        
        // Fill with test pattern
        for (size_t j = 0; j < test_sizes[i]; j++) {
            test_data[j] = (j % 256);
        }
        
        // Test enhanced checksum
        struct timespec start, end;
        clock_gettime(CLOCK_MONOTONIC, &start);
        
        uint32_t checksum = enhanced_calculate_checksum(test_data, test_sizes[i]);
        
        clock_gettime(CLOCK_MONOTONIC, &end);
        
        uint64_t time_ns = (end.tv_sec - start.tv_sec) * 1000000000ULL + 
                          (end.tv_nsec - start.tv_nsec);
        
        printf("  Size %4zu bytes: Checksum 0x%08x, Time: %lu ns\n", 
               test_sizes[i], checksum, time_ns);
        
        free(test_data);
    }
    
    // Test hash function performance
    printf("\nTesting enhanced hash function:\n");
    const char* test_topics[] = {
        "system.alerts",
        "task.coordination", 
        "security.events",
        "performance.metrics",
        "network.status"
    };
    
    for (size_t i = 0; i < 5; i++) {
        uint32_t hash = enhanced_hash_topic(test_topics[i]);
        printf("  Topic '%s': Hash %u (mod %u = %u)\n",
               test_topics[i], hash, MAX_TOPICS, hash % MAX_TOPICS);
    }
}

// ============================================================================
// DEMONSTRATION MAIN FUNCTION
// ============================================================================

#ifdef SIMPLE_ENHANCED_ROUTER_TEST_MODE

int main() {
    printf("Simple Enhanced Message Router - Test Suite\n");
    printf("============================================\n");
    
    // Initialize enhanced router
    if (simple_router_service_init() != 0) {
        printf("Failed to initialize simple enhanced router service\n");
        return 1;
    }
    
    // Test enhanced message publishing
    printf("\nTesting enhanced message publishing:\n");
    
    const char* messages[] = {
        "System alert: CPU usage high",
        "Task coordination: Build started",
        "Security event: Login attempt",
        "Performance metric: Latency spike detected",
        "Network status: Connection established"
    };
    
    for (int i = 0; i < 5; i++) {
        enhanced_publish_to_topic_simple("test.enhanced", 100 + i, 
                                          messages[i], strlen(messages[i]), 
                                          PRIORITY_NORMAL + i);
    }
    
    // Test vectorized operations
    test_vectorized_operations();
    
    // Print final statistics
    printf("\n=== Final Statistics ===\n");
    printf("CPU Capabilities:\n");
    printf("  CPU ID: %d\n", g_simple_caps.cpu_id);
    printf("  AVX2: %s\n", g_simple_caps.has_avx2 ? "YES" : "NO");
    printf("  SSE4.2: %s\n", g_simple_caps.has_sse42 ? "YES" : "NO");
    printf("  Hardware CRC32: %s\n", g_simple_caps.has_crc32 ? "YES" : "NO");
    
    printf("\nRouter Performance:\n");
    printf("  Messages processed: %lu\n", g_simple_router->messages_processed);
    printf("  Enhanced operations: %lu\n", g_simple_router->enhanced_operations);
    
    // Cleanup
    simple_router_service_cleanup();
    
    return 0;
}

#endif /* SIMPLE_ENHANCED_ROUTER_TEST_MODE */