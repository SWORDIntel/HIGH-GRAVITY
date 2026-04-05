/**
 * High-Performance Memory Pool Allocator
 * Intel Meteor Lake Optimized with NUMA Awareness
 *
 * Features:
 * - Cache-line aligned allocations (64-byte alignment)
 * - NUMA-aware memory allocation for P-core/E-core hybrid
 * - Thread-local storage pools for zero-contention
 * - Memory pool recycling to reduce 271MB allocation overhead
 * - AVX-512 optimized memcpy operations for large transfers
 */

#ifndef MEMORY_POOL_ALLOCATOR_H
#define MEMORY_POOL_ALLOCATOR_H

#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>
#include <pthread.h>
#include <numa.h>
#include <sys/mman.h>

// Cache line size for Intel Meteor Lake
#define CACHE_LINE_SIZE 64
#define NUMA_NODES 2  // Typical for Meteor Lake
#define MAX_POOL_SIZES 16
#define POOL_CHUNK_SIZE (2 * 1024 * 1024)  // 2MB chunks for huge pages

// Memory pool size classes (optimized for observed allocation patterns)
static const size_t POOL_SIZES[MAX_POOL_SIZES] = {
    32, 64, 128, 256, 512, 1024, 2048, 4096,
    8192, 16384, 32768, 65536, 131072, 262144, 524288, 1048576
};

// Thread-local memory pool structure
typedef struct __attribute__((aligned(CACHE_LINE_SIZE))) {
    void* free_list;
    uint32_t free_count;
    uint32_t total_allocated;
    uint32_t numa_node;
    uint8_t padding[CACHE_LINE_SIZE - 16];
} thread_pool_t;

// NUMA-aware memory pool
typedef struct __attribute__((aligned(CACHE_LINE_SIZE))) {
    thread_pool_t* thread_pools[MAX_POOL_SIZES];
    void* chunk_base;
    size_t chunk_size;
    uint32_t numa_node;
    pthread_mutex_t chunk_mutex;
    uint64_t total_allocated_bytes;
    uint64_t peak_allocated_bytes;
    uint32_t allocation_count;
    uint8_t padding[CACHE_LINE_SIZE - 48];
} numa_pool_t;

// Global memory pool manager
typedef struct {
    numa_pool_t numa_pools[NUMA_NODES];
    bool initialized;
    pthread_mutex_t init_mutex;

    // Performance tracking
    uint64_t total_allocations;
    uint64_t total_deallocations;
    uint64_t bytes_saved_by_pooling;
    uint64_t cache_hits;
    uint64_t cache_misses;

    // Intel Meteor Lake specific optimizations
    bool avx512_available;
    bool huge_pages_enabled;
    uint32_t p_core_count;
    uint32_t e_core_count;
} memory_pool_manager_t;

// Function prototypes
int memory_pool_init(void);
void memory_pool_cleanup(void);
void* pool_malloc(size_t size);
void* pool_calloc(size_t nmemb, size_t size);
void* pool_realloc(void* ptr, size_t size);
void pool_free(void* ptr);

// NUMA-aware allocation
void* pool_malloc_numa(size_t size, int numa_node);
void* pool_calloc_numa(size_t nmemb, size_t size, int numa_node);

// Cache-aligned allocation for performance-critical structures
void* pool_malloc_aligned(size_t size, size_t alignment);
void* pool_calloc_aligned(size_t nmemb, size_t size, size_t alignment);

// Memory pool statistics and monitoring
typedef struct {
    uint64_t total_allocated;
    uint64_t total_freed;
    uint64_t current_usage;
    uint64_t peak_usage;
    uint64_t pool_hits;
    uint64_t pool_misses;
    uint64_t numa_local_allocations;
    uint64_t numa_remote_allocations;
    double fragmentation_ratio;
} pool_stats_t;

void pool_get_stats(pool_stats_t* stats);
void pool_print_stats(void);
void pool_reset_stats(void);

// Debugging and leak detection
#ifdef DEBUG_MEMORY_POOLS
typedef struct allocation_info {
    void* ptr;
    size_t size;
    const char* file;
    int line;
    uint64_t timestamp;
    struct allocation_info* next;
} allocation_info_t;

void pool_track_allocation(void* ptr, size_t size, const char* file, int line);
void pool_track_deallocation(void* ptr);
void pool_dump_leaks(void);

#define POOL_MALLOC(size) pool_malloc_debug(size, __FILE__, __LINE__)
#define POOL_CALLOC(nmemb, size) pool_calloc_debug(nmemb, size, __FILE__, __LINE__)
#define POOL_FREE(ptr) pool_free_debug(ptr, __FILE__, __LINE__)

void* pool_malloc_debug(size_t size, const char* file, int line);
void* pool_calloc_debug(size_t nmemb, size_t size, const char* file, int line);
void pool_free_debug(void* ptr, const char* file, int line);
#else
#define POOL_MALLOC(size) pool_malloc(size)
#define POOL_CALLOC(nmemb, size) pool_calloc(nmemb, size)
#define POOL_FREE(ptr) pool_free(ptr)
#endif

// Intel Meteor Lake hardware detection
bool detect_meteor_lake_features(void);
void configure_numa_topology(void);
int get_optimal_numa_node(void);

// AVX-512 optimized memory operations
void avx512_memcpy(void* dst, const void* src, size_t size);
void avx512_memset(void* ptr, int value, size_t size);
bool is_avx512_available(void);

#endif // MEMORY_POOL_ALLOCATOR_H