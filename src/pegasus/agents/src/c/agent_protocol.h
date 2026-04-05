/*
 * ULTRA-FAST BINARY PROTOCOL - Header File
 * Public API for the high-performance agent communication protocol
 */

#ifndef ULTRA_FAST_PROTOCOL_H
#define ULTRA_FAST_PROTOCOL_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

// Protocol version
#define UFP_VERSION_MAJOR 3
#define UFP_VERSION_MINOR 0
#define UFP_VERSION_PATCH 0

// Configuration constants
#define UFP_MAX_AGENTS 65535
#define UFP_MAX_PAYLOAD_SIZE (16 * 1024 * 1024)
#define UFP_MAX_TARGETS 256
#define UFP_AGENT_NAME_SIZE 64

// Message types
typedef enum {
    UFP_MSG_REQUEST = 0x01,
    UFP_MSG_RESPONSE = 0x02,
    UFP_MSG_BROADCAST = 0x03,
    UFP_MSG_HEARTBEAT = 0x04,
    UFP_MSG_ACK = 0x05,
    UFP_MSG_ERROR = 0x06,
    UFP_MSG_VETO = 0x07,
    UFP_MSG_TASK = 0x08,
    UFP_MSG_RESULT = 0x09,
    UFP_MSG_STATE_SYNC = 0x0A,
    UFP_MSG_RESOURCE_REQ = 0x0B,
    UFP_MSG_RESOURCE_RESP = 0x0C,
    UFP_MSG_DISCOVERY = 0x0D,
    UFP_MSG_SHUTDOWN = 0x0E,
    UFP_MSG_EMERGENCY = 0x0F
} ufp_msg_type_t;

// Priority levels
typedef enum {
    UFP_PRIORITY_CRITICAL = 0x00,
    UFP_PRIORITY_HIGH = 0x01,
    UFP_PRIORITY_MEDIUM = 0x02,
    UFP_PRIORITY_LOW = 0x03,
    UFP_PRIORITY_BACKGROUND = 0x04
} ufp_priority_t;

// Error codes
typedef enum {
    UFP_SUCCESS = 0,
    UFP_ERROR_INVALID_PARAM = -1,
    UFP_ERROR_BUFFER_TOO_SMALL = -2,
    UFP_ERROR_CHECKSUM_MISMATCH = -3,
    UFP_ERROR_PROTOCOL_VERSION = -4,
    UFP_ERROR_OUT_OF_MEMORY = -5,
    UFP_ERROR_QUEUE_FULL = -6,
    UFP_ERROR_QUEUE_EMPTY = -7,
    UFP_ERROR_TIMEOUT = -8,
    UFP_ERROR_NOT_INITIALIZED = -9,
    UFP_ERROR_ALREADY_INITIALIZED = -10
} ufp_error_t;

// Forward declarations
typedef struct ufp_context ufp_context_t;
typedef struct ufp_message ufp_message_t;
typedef struct ufp_ring_buffer ufp_ring_buffer_t;
typedef struct ufp_message_pool ufp_message_pool_t;

// Message structure
struct ufp_message {
    uint32_t msg_id;
    ufp_msg_type_t msg_type;
    ufp_priority_t priority;
    char source[UFP_AGENT_NAME_SIZE];
    char targets[UFP_MAX_TARGETS][UFP_AGENT_NAME_SIZE];
    uint8_t target_count;
    void* payload;
    size_t payload_size;
    uint32_t timestamp;
    uint32_t correlation_id;
    uint8_t flags;
};

// Statistics structure
typedef struct {
    uint64_t messages_sent;
    uint64_t messages_received;
    uint64_t bytes_sent;
    uint64_t bytes_received;
    uint64_t errors;
    uint64_t checksum_failures;
    double avg_latency_ns;
    double max_latency_ns;
    double throughput_mbps;
} ufp_stats_t;

// Callback function types
typedef void (*ufp_message_callback_t)(const ufp_message_t* message, void* user_data);
typedef void (*ufp_error_callback_t)(ufp_error_t error, const char* message, void* user_data);

// ============================================================================
// Core API Functions
// ============================================================================

/**
 * Initialize the ultra-fast protocol library
 * @return UFP_SUCCESS on success, error code otherwise
 */
ufp_error_t ufp_init(void);

/**
 * Cleanup the protocol library
 */
void ufp_cleanup(void);

/**
 * Create a new protocol context for an agent
 * @param agent_name Name of the agent
 * @return Context pointer or NULL on error
 */
ufp_context_t* ufp_create_context(const char* agent_name);

/**
 * Destroy a protocol context
 * @param ctx Context to destroy
 */
void ufp_destroy_context(ufp_context_t* ctx);

// ============================================================================
// Message Operations
// ============================================================================

/**
 * Create a new message
 * @return Message pointer or NULL on error
 */
ufp_message_t* ufp_message_create(void);

/**
 * Destroy a message
 * @param msg Message to destroy
 */
void ufp_message_destroy(ufp_message_t* msg);

/**
 * Pack a message into binary format
 * @param msg Message to pack
 * @param buffer Output buffer
 * @param buffer_size Size of output buffer
 * @return Packed size or negative error code
 */
ssize_t ufp_pack_message(const ufp_message_t* msg, uint8_t* buffer, size_t buffer_size);

/**
 * Unpack a message from binary format
 * @param buffer Input buffer
 * @param buffer_size Size of input buffer
 * @param msg Output message structure
 * @return UFP_SUCCESS or error code
 */
ufp_error_t ufp_unpack_message(const uint8_t* buffer, size_t buffer_size, ufp_message_t* msg);

// ============================================================================
// Communication Functions
// ============================================================================

/**
 * Send a message
 * @param ctx Context
 * @param msg Message to send
 * @return UFP_SUCCESS or error code
 */
ufp_error_t ufp_send(ufp_context_t* ctx, const ufp_message_t* msg);

/**
 * Send a message asynchronously
 * @param ctx Context
 * @param msg Message to send
 * @param callback Completion callback
 * @param user_data User data for callback
 * @return UFP_SUCCESS or error code
 */
ufp_error_t ufp_send_async(ufp_context_t* ctx, const ufp_message_t* msg,
                           void (*callback)(ufp_error_t, void*), void* user_data);

/**
 * Receive a message
 * @param ctx Context
 * @param msg Output message
 * @param timeout_ms Timeout in milliseconds (0 for non-blocking, -1 for infinite)
 * @return UFP_SUCCESS, UFP_ERROR_TIMEOUT, or error code
 */
ufp_error_t ufp_receive(ufp_context_t* ctx, ufp_message_t* msg, int timeout_ms);

/**
 * Register a callback for incoming messages
 * @param ctx Context
 * @param callback Message callback
 * @param user_data User data for callback
 * @return UFP_SUCCESS or error code
 */
ufp_error_t ufp_register_callback(ufp_context_t* ctx, 
                                  ufp_message_callback_t callback,
                                  void* user_data);

// ============================================================================
// Ring Buffer Operations (Lock-free IPC)
// ============================================================================

/**
 * Create a lock-free ring buffer for IPC
 * @param size Buffer size (will be rounded up to power of 2)
 * @return Ring buffer pointer or NULL on error
 */
ufp_ring_buffer_t* ufp_ring_buffer_create(size_t size);

/**
 * Destroy a ring buffer
 * @param rb Ring buffer to destroy
 */
void ufp_ring_buffer_destroy(ufp_ring_buffer_t* rb);

/**
 * Write to ring buffer (lock-free, wait-free for single producer)
 * @param rb Ring buffer
 * @param data Data to write
 * @param len Length of data
 * @return true on success, false if buffer full
 */
bool ufp_ring_buffer_write(ufp_ring_buffer_t* rb, const void* data, size_t len);

/**
 * Read from ring buffer (lock-free, wait-free for single consumer)
 * @param rb Ring buffer
 * @param data Output buffer
 * @param max_len Maximum bytes to read
 * @return Number of bytes read, 0 if empty
 */
size_t ufp_ring_buffer_read(ufp_ring_buffer_t* rb, void* data, size_t max_len);

// ============================================================================
// Message Pool Operations (Zero allocation)
// ============================================================================

/**
 * Create a message pool for zero-allocation messaging
 * @param message_size Size of each message
 * @param pool_size Number of messages in pool
 * @return Message pool pointer or NULL on error
 */
ufp_message_pool_t* ufp_pool_create(size_t message_size, size_t pool_size);

/**
 * Destroy a message pool
 * @param pool Pool to destroy
 */
void ufp_pool_destroy(ufp_message_pool_t* pool);

/**
 * Allocate a message from pool (lock-free)
 * @param pool Message pool
 * @return Message pointer or NULL if pool exhausted
 */
void* ufp_pool_alloc(ufp_message_pool_t* pool);

/**
 * Return message to pool (lock-free)
 * @param pool Message pool
 * @param msg Message to return
 */
void ufp_pool_free(ufp_message_pool_t* pool, void* msg);

// ============================================================================
// Utility Functions
// ============================================================================

/**
 * Register an agent name to ID mapping
 * @param name Agent name
 * @return Agent ID (1-65535)
 */
uint16_t ufp_register_agent(const char* name);

/**
 * Get agent name from ID
 * @param id Agent ID
 * @return Agent name or "UNKNOWN"
 */
const char* ufp_get_agent_name(uint16_t id);

/**
 * Calculate CRC32C checksum (hardware accelerated if available)
 * @param data Data to checksum
 * @param len Length of data
 * @return CRC32C checksum
 */
uint32_t ufp_crc32c(const void* data, size_t len);

/**
 * Get library version string
 * @return Version string
 */
const char* ufp_version(void);

/**
 * Get performance statistics
 * @param stats Output statistics structure
 */
void ufp_get_stats(ufp_stats_t* stats);

/**
 * Reset performance statistics
 */
void ufp_reset_stats(void);

// ============================================================================
// Batch Operations
// ============================================================================

/**
 * Send multiple messages in a batch (more efficient)
 * @param ctx Context
 * @param messages Array of messages
 * @param count Number of messages
 * @return Number of messages sent successfully
 */
size_t ufp_send_batch(ufp_context_t* ctx, const ufp_message_t** messages, size_t count);

/**
 * Receive multiple messages in a batch
 * @param ctx Context
 * @param messages Array to store messages
 * @param max_count Maximum messages to receive
 * @param timeout_ms Timeout in milliseconds
 * @return Number of messages received
 */
size_t ufp_receive_batch(ufp_context_t* ctx, ufp_message_t* messages, 
                         size_t max_count, int timeout_ms);

// ============================================================================
// Advanced Features
// ============================================================================

/**
 * Enable compression for large messages
 * @param ctx Context
 * @param enable true to enable, false to disable
 * @param min_size Minimum message size to compress
 */
void ufp_set_compression(ufp_context_t* ctx, bool enable, size_t min_size);

/**
 * Set CPU affinity for protocol threads
 * @param ctx Context
 * @param cpu_mask CPU affinity mask
 */
void ufp_set_cpu_affinity(ufp_context_t* ctx, uint64_t cpu_mask);

/**
 * Enable/disable NUMA optimization
 * @param ctx Context
 * @param enable true to enable NUMA optimization
 */
void ufp_set_numa_optimization(ufp_context_t* ctx, bool enable);

#ifdef __cplusplus
}
#endif

#endif // ULTRA_FAST_PROTOCOL_H