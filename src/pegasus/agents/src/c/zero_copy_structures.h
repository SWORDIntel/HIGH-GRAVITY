/**
 * Zero-Copy Data Structures for High-Performance Agent Communication
 * Intel Meteor Lake Optimized with NUMA Awareness
 *
 * Features:
 * - Shared memory regions with atomic operations
 * - Lock-free ring buffers with memory ordering
 * - Zero-copy message passing between agents
 * - Cache-line padding to prevent false sharing
 * - NUMA-aware memory mapping
 */

#ifndef ZERO_COPY_STRUCTURES_H
#define ZERO_COPY_STRUCTURES_H

#include <stdint.h>
#include <stdatomic.h>
#include <stdbool.h>
#include <sys/mman.h>

// Cache line size and alignment
#define CACHE_LINE_SIZE 64
#define ALIGN_CACHE_LINE __attribute__((aligned(CACHE_LINE_SIZE)))

// Zero-copy buffer sizes
#define ZC_RING_BUFFER_SIZE (4 * 1024 * 1024)  // 4MB ring buffers
#define ZC_MAX_MESSAGE_SIZE (64 * 1024)        // 64KB max message
#define ZC_NUM_BUFFERS 16                      // Number of ring buffers

/**
 * Zero-copy message header (cache-line aligned)
 */
typedef struct ALIGN_CACHE_LINE {
    atomic_uint64_t sequence;     // Message sequence number
    atomic_uint32_t size;         // Message payload size
    atomic_uint32_t source_id;    // Source agent ID
    atomic_uint32_t dest_id;      // Destination agent ID
    atomic_uint32_t message_type; // Message type identifier
    atomic_uint64_t timestamp;    // Timestamp (ns since epoch)
    atomic_uint32_t checksum;     // CRC32 checksum
    atomic_uint32_t flags;        // Message flags
    uint8_t padding[CACHE_LINE_SIZE - 40]; // Pad to cache line
} zc_message_header_t;

/**
 * Zero-copy ring buffer (lock-free, single producer/single consumer)
 */
typedef struct ALIGN_CACHE_LINE {
    // Producer cache line
    atomic_uint64_t producer_pos;
    uint8_t producer_padding[CACHE_LINE_SIZE - sizeof(atomic_uint64_t)];

    // Consumer cache line
    atomic_uint64_t consumer_pos;
    uint8_t consumer_padding[CACHE_LINE_SIZE - sizeof(atomic_uint64_t)];

    // Buffer metadata
    uint64_t buffer_size;
    uint64_t buffer_mask;    // size - 1 for fast modulo
    void* buffer_base;       // Shared memory base address
    uint32_t numa_node;      // NUMA node for this buffer
    uint32_t buffer_id;      // Unique buffer identifier

    // Statistics (cache-line aligned)
    atomic_uint64_t messages_sent;
    atomic_uint64_t messages_received;
    atomic_uint64_t bytes_transferred;
    atomic_uint64_t buffer_overruns;
    uint8_t stats_padding[CACHE_LINE_SIZE - 32];
} zc_ring_buffer_t;

/**
 * Zero-copy shared memory region
 */
typedef struct {
    void* base_addr;          // Base address of shared memory
    size_t total_size;        // Total size of shared region
    uint32_t numa_node;       // NUMA node for this region
    char region_name[64];     // Name for debugging

    // Ring buffers within this region
    zc_ring_buffer_t* ring_buffers;
    uint32_t num_ring_buffers;

    // Free block management
    atomic_uint64_t free_blocks_bitmap;  // Bitmap of free blocks
    uint32_t block_size;                 // Size of each block
    uint32_t num_blocks;                 // Total number of blocks
} zc_shared_region_t;

/**
 * Zero-copy message pool (for avoiding allocations)
 */
typedef struct ALIGN_CACHE_LINE {
    void* message_slots[1024];           // Pre-allocated message slots
    atomic_uint32_t free_bitmap[32];     // Bitmap of free slots (1024/32)
    uint32_t slot_size;                  // Size of each message slot
    uint32_t total_slots;                // Total number of slots
    uint32_t numa_node;                  // NUMA node for this pool

    // Pool statistics
    atomic_uint64_t allocations;
    atomic_uint64_t deallocations;
    atomic_uint64_t peak_usage;
    uint8_t stats_padding[CACHE_LINE_SIZE - 24];
} zc_message_pool_t;

/**
 * Zero-copy communication channel (bidirectional)
 */
typedef struct {
    zc_ring_buffer_t* send_buffer;     // Send ring buffer
    zc_ring_buffer_t* recv_buffer;     // Receive ring buffer
    zc_message_pool_t* message_pool;   // Message pool for this channel

    uint32_t local_agent_id;           // Local agent ID
    uint32_t remote_agent_id;          // Remote agent ID
    uint32_t channel_id;               // Unique channel ID

    // Channel statistics
    atomic_uint64_t messages_sent;
    atomic_uint64_t messages_received;
    atomic_uint64_t total_latency_ns;
    atomic_uint64_t min_latency_ns;
    atomic_uint64_t max_latency_ns;
} zc_channel_t;

/**
 * Zero-copy system manager
 */
typedef struct {
    zc_shared_region_t* regions[4];    // One region per NUMA node
    zc_channel_t* channels[256];       // Communication channels
    zc_message_pool_t* pools[4];       // Message pools per NUMA node

    uint32_t num_regions;
    uint32_t num_channels;
    uint32_t num_agents;

    // System-wide statistics
    atomic_uint64_t total_messages;
    atomic_uint64_t total_bytes;
    atomic_uint64_t zero_copy_hits;
    atomic_uint64_t fallback_allocations;

    bool initialized;
    pthread_mutex_t init_mutex;
} zc_system_t;

// Function prototypes

/**
 * System initialization and cleanup
 */
int zc_system_init(uint32_t num_agents);
void zc_system_cleanup(void);
zc_system_t* zc_get_system(void);

/**
 * Shared memory management
 */
zc_shared_region_t* zc_create_shared_region(const char* name, size_t size, uint32_t numa_node);
void zc_destroy_shared_region(zc_shared_region_t* region);
void* zc_alloc_from_region(zc_shared_region_t* region, size_t size);
void zc_free_to_region(zc_shared_region_t* region, void* ptr);

/**
 * Ring buffer operations
 */
zc_ring_buffer_t* zc_create_ring_buffer(size_t size, uint32_t numa_node);
void zc_destroy_ring_buffer(zc_ring_buffer_t* buffer);

// Zero-copy send (returns pointer to write directly into buffer)
void* zc_ring_reserve_send(zc_ring_buffer_t* buffer, uint32_t size);
int zc_ring_commit_send(zc_ring_buffer_t* buffer, uint32_t size);

// Zero-copy receive (returns pointer to read directly from buffer)
void* zc_ring_peek_receive(zc_ring_buffer_t* buffer, uint32_t* size);
int zc_ring_consume_receive(zc_ring_buffer_t* buffer, uint32_t size);

/**
 * Message pool operations
 */
zc_message_pool_t* zc_create_message_pool(uint32_t slot_size, uint32_t num_slots, uint32_t numa_node);
void zc_destroy_message_pool(zc_message_pool_t* pool);
void* zc_pool_alloc_message(zc_message_pool_t* pool);
void zc_pool_free_message(zc_message_pool_t* pool, void* message);

/**
 * Channel operations
 */
zc_channel_t* zc_create_channel(uint32_t local_id, uint32_t remote_id, uint32_t numa_node);
void zc_destroy_channel(zc_channel_t* channel);

// High-level zero-copy messaging
int zc_send_message(zc_channel_t* channel, const void* data, uint32_t size, uint32_t type);
int zc_receive_message(zc_channel_t* channel, void** data, uint32_t* size, uint32_t* type);
void zc_release_message(zc_channel_t* channel, void* data);

// Zero-copy batch operations
typedef struct {
    void* data;
    uint32_t size;
    uint32_t type;
} zc_message_batch_item_t;

int zc_send_batch(zc_channel_t* channel, zc_message_batch_item_t* messages, uint32_t count);
int zc_receive_batch(zc_channel_t* channel, zc_message_batch_item_t* messages, uint32_t max_count, uint32_t* received_count);

/**
 * Performance monitoring
 */
typedef struct {
    uint64_t total_messages;
    uint64_t total_bytes;
    uint64_t zero_copy_ratio;     // Percentage of zero-copy operations
    uint64_t avg_latency_ns;
    uint64_t min_latency_ns;
    uint64_t max_latency_ns;
    uint64_t throughput_mbps;
    uint64_t buffer_utilization;  // Percentage
} zc_performance_stats_t;

void zc_get_performance_stats(zc_performance_stats_t* stats);
void zc_reset_performance_stats(void);
void zc_print_performance_stats(void);

/**
 * NUMA optimization utilities
 */
int zc_get_optimal_numa_node_for_agents(uint32_t agent1, uint32_t agent2);
void zc_migrate_channel_to_numa_node(zc_channel_t* channel, uint32_t numa_node);
void zc_optimize_numa_placement(void);

/**
 * Memory ordering and synchronization utilities
 */
static inline void zc_memory_barrier(void) {
    atomic_thread_fence(memory_order_seq_cst);
}

static inline void zc_compiler_barrier(void) {
    asm volatile("" ::: "memory");
}

// Cache-friendly atomic operations
static inline uint64_t zc_atomic_load_relaxed_u64(const atomic_uint64_t* ptr) {
    return atomic_load_explicit(ptr, memory_order_relaxed);
}

static inline void zc_atomic_store_relaxed_u64(atomic_uint64_t* ptr, uint64_t value) {
    atomic_store_explicit(ptr, value, memory_order_relaxed);
}

static inline uint64_t zc_atomic_fetch_add_relaxed_u64(atomic_uint64_t* ptr, uint64_t value) {
    return atomic_fetch_add_explicit(ptr, value, memory_order_relaxed);
}

/**
 * Cache management utilities
 */
static inline void zc_prefetch_for_read(const void* addr) {
    __builtin_prefetch(addr, 0, 3);  // Prefetch for read, high temporal locality
}

static inline void zc_prefetch_for_write(const void* addr) {
    __builtin_prefetch(addr, 1, 3);  // Prefetch for write, high temporal locality
}

static inline void zc_flush_cache_line(const void* addr) {
    _mm_clflush(addr);
}

#endif // ZERO_COPY_STRUCTURES_H