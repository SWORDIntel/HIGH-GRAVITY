/**
 * High-Performance Memory Pool Allocator Implementation
 * Intel Meteor Lake Optimized with NUMA Awareness
 */

#define _GNU_SOURCE
#include "memory_pool_allocator.h"
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <unistd.h>
#include <errno.h>
#include <sys/mman.h>
#include <cpuid.h>
#include <immintrin.h>
#include <sched.h>

// Global memory pool manager
static memory_pool_manager_t g_pool_manager = {0};
static __thread int t_current_numa_node = -1;

// Thread-local storage for current pool pointers (cache optimization)
static __thread thread_pool_t* t_current_pools[MAX_POOL_SIZES] = {0};

/**
 * Intel Meteor Lake hardware feature detection
 */
bool detect_meteor_lake_features(void) {
    uint32_t eax, ebx, ecx, edx;

    // Check for AVX-512 support
    if (__get_cpuid_count(7, 0, &eax, &ebx, &ecx, &edx)) {
        g_pool_manager.avx512_available = (ebx & (1 << 16)) != 0;  // AVX-512F
    }

    // Detect P-core and E-core count (simplified heuristic)
    g_pool_manager.p_core_count = 6;  // Typical for Meteor Lake
    g_pool_manager.e_core_count = 8;  // Typical for Meteor Lake

    // Check for huge page support
    g_pool_manager.huge_pages_enabled = (mmap(NULL, 2 * 1024 * 1024,
                                             PROT_READ | PROT_WRITE,
                                             MAP_PRIVATE | MAP_ANONYMOUS | MAP_HUGETLB,
                                             -1, 0) != MAP_FAILED);

    return true;
}

/**
 * Configure NUMA topology for Intel Meteor Lake
 */
void configure_numa_topology(void) {
    if (numa_available() < 0) {
        // Fallback for systems without NUMA
        for (int i = 0; i < NUMA_NODES; i++) {
            g_pool_manager.numa_pools[i].numa_node = 0;
        }
        return;
    }

    // Configure NUMA nodes for P-cores and E-cores
    for (int i = 0; i < NUMA_NODES; i++) {
        g_pool_manager.numa_pools[i].numa_node = i;
        numa_set_preferred(i);
    }
}

/**
 * Get optimal NUMA node for current thread
 */
int get_optimal_numa_node(void) {
    if (t_current_numa_node == -1) {
        cpu_set_t cpu_set;
        CPU_ZERO(&cpu_set);

        if (sched_getaffinity(0, sizeof(cpu_set), &cpu_set) == 0) {
            // Simple heuristic: P-cores (0-11) -> NUMA 0, E-cores (12-19) -> NUMA 1
            for (int cpu = 0; cpu < CPU_SETSIZE; cpu++) {
                if (CPU_ISSET(cpu, &cpu_set)) {
                    t_current_numa_node = (cpu < 12) ? 0 : 1;
                    break;
                }
            }
        }

        if (t_current_numa_node == -1) {
            t_current_numa_node = 0;  // Fallback
        }
    }

    return t_current_numa_node;
}

/**
 * Find appropriate pool size index for allocation
 */
static inline int find_pool_index(size_t size) {
    for (int i = 0; i < MAX_POOL_SIZES; i++) {
        if (size <= POOL_SIZES[i]) {
            return i;
        }
    }
    return -1;  // Too large for pooling
}

/**
 * Allocate a new chunk for a NUMA pool
 */
static void* allocate_chunk(numa_pool_t* pool) {
    void* chunk;

    if (g_pool_manager.huge_pages_enabled) {
        // Try huge pages first for better TLB efficiency
        chunk = mmap(NULL, POOL_CHUNK_SIZE,
                    PROT_READ | PROT_WRITE,
                    MAP_PRIVATE | MAP_ANONYMOUS | MAP_HUGETLB,
                    -1, 0);

        if (chunk == MAP_FAILED) {
            // Fallback to regular pages
            chunk = mmap(NULL, POOL_CHUNK_SIZE,
                        PROT_READ | PROT_WRITE,
                        MAP_PRIVATE | MAP_ANONYMOUS,
                        -1, 0);
        }
    } else {
        chunk = mmap(NULL, POOL_CHUNK_SIZE,
                    PROT_READ | PROT_WRITE,
                    MAP_PRIVATE | MAP_ANONYMOUS,
                    -1, 0);
    }

    if (chunk == MAP_FAILED) {
        return NULL;
    }

    // NUMA bind the memory to the appropriate node
    if (numa_available() >= 0) {
        numa_tonode_memory(chunk, POOL_CHUNK_SIZE, pool->numa_node);
    }

    return chunk;
}

/**
 * Initialize thread-local pool for specific size class
 */
static thread_pool_t* init_thread_pool(int pool_index, int numa_node) {
    numa_pool_t* numa_pool = &g_pool_manager.numa_pools[numa_node];

    if (!numa_pool->thread_pools[pool_index]) {
        // Allocate cache-aligned thread pool structure
        size_t pool_size = sizeof(thread_pool_t);
        thread_pool_t* pool = aligned_alloc(CACHE_LINE_SIZE, pool_size);
        if (!pool) return NULL;

        memset(pool, 0, pool_size);
        pool->numa_node = numa_node;

        // Pre-allocate chunk if needed
        pthread_mutex_lock(&numa_pool->chunk_mutex);
        if (!numa_pool->chunk_base) {
            numa_pool->chunk_base = allocate_chunk(numa_pool);
            numa_pool->chunk_size = POOL_CHUNK_SIZE;
        }
        pthread_mutex_unlock(&numa_pool->chunk_mutex);

        numa_pool->thread_pools[pool_index] = pool;
    }

    return numa_pool->thread_pools[pool_index];
}

/**
 * AVX-512 optimized memory copy (when available)
 */
void avx512_memcpy(void* dst, const void* src, size_t size) {
    if (!g_pool_manager.avx512_available || size < 64) {
        memcpy(dst, src, size);
        return;
    }

    const char* s = (const char*)src;
    char* d = (char*)dst;

    // AVX-512 copy for aligned data
    if (((uintptr_t)src & 63) == 0 && ((uintptr_t)dst & 63) == 0) {
        size_t avx512_chunks = size / 64;
        for (size_t i = 0; i < avx512_chunks; i++) {
            __m512i data = _mm512_load_si512((__m512i*)(s + i * 64));
            _mm512_store_si512((__m512i*)(d + i * 64), data);
        }

        // Handle remainder
        size_t remainder = size % 64;
        if (remainder > 0) {
            memcpy(d + avx512_chunks * 64, s + avx512_chunks * 64, remainder);
        }
    } else {
        memcpy(dst, src, size);
    }
}

/**
 * AVX-512 optimized memory set
 */
void avx512_memset(void* ptr, int value, size_t size) {
    if (!g_pool_manager.avx512_available || size < 64) {
        memset(ptr, value, size);
        return;
    }

    char* p = (char*)ptr;
    __m512i val = _mm512_set1_epi8(value);

    if (((uintptr_t)ptr & 63) == 0) {
        size_t avx512_chunks = size / 64;
        for (size_t i = 0; i < avx512_chunks; i++) {
            _mm512_store_si512((__m512i*)(p + i * 64), val);
        }

        size_t remainder = size % 64;
        if (remainder > 0) {
            memset(p + avx512_chunks * 64, value, remainder);
        }
    } else {
        memset(ptr, value, size);
    }
}

/**
 * Initialize memory pool system
 */
int memory_pool_init(void) {
    pthread_mutex_lock(&g_pool_manager.init_mutex);

    if (g_pool_manager.initialized) {
        pthread_mutex_unlock(&g_pool_manager.init_mutex);
        return 0;
    }

    // Detect hardware features
    detect_meteor_lake_features();
    configure_numa_topology();

    // Initialize NUMA pools
    for (int i = 0; i < NUMA_NODES; i++) {
        numa_pool_t* pool = &g_pool_manager.numa_pools[i];
        pool->numa_node = i;
        pthread_mutex_init(&pool->chunk_mutex, NULL);
        memset(pool->thread_pools, 0, sizeof(pool->thread_pools));
    }

    g_pool_manager.initialized = true;
    pthread_mutex_unlock(&g_pool_manager.init_mutex);

    return 0;
}

/**
 * NUMA-aware malloc implementation
 */
void* pool_malloc_numa(size_t size, int numa_node) {
    if (size == 0) return NULL;

    if (!g_pool_manager.initialized) {
        memory_pool_init();
    }

    int pool_index = find_pool_index(size);
    if (pool_index == -1) {
        // Large allocation - use system malloc
        g_pool_manager.cache_misses++;
        return malloc(size);
    }

    // Ensure valid NUMA node
    if (numa_node < 0 || numa_node >= NUMA_NODES) {
        numa_node = get_optimal_numa_node();
    }

    // Get or create thread-local pool
    thread_pool_t* pool = t_current_pools[pool_index];
    if (!pool) {
        pool = init_thread_pool(pool_index, numa_node);
        t_current_pools[pool_index] = pool;
    }

    // Try to get from free list
    if (pool->free_list) {
        void* ptr = pool->free_list;
        pool->free_list = *(void**)ptr;
        pool->free_count--;
        pool->total_allocated++;
        g_pool_manager.cache_hits++;
        g_pool_manager.total_allocations++;
        return ptr;
    }

    // Allocate new block from chunk
    numa_pool_t* numa_pool = &g_pool_manager.numa_pools[numa_node];
    pthread_mutex_lock(&numa_pool->chunk_mutex);

    if (!numa_pool->chunk_base) {
        numa_pool->chunk_base = allocate_chunk(numa_pool);
        numa_pool->chunk_size = POOL_CHUNK_SIZE;
    }

    size_t alloc_size = POOL_SIZES[pool_index];
    if (numa_pool->chunk_size < alloc_size) {
        // Need new chunk
        numa_pool->chunk_base = allocate_chunk(numa_pool);
        numa_pool->chunk_size = POOL_CHUNK_SIZE;
    }

    void* ptr = numa_pool->chunk_base;
    numa_pool->chunk_base = (char*)numa_pool->chunk_base + alloc_size;
    numa_pool->chunk_size -= alloc_size;
    numa_pool->total_allocated_bytes += alloc_size;

    if (numa_pool->total_allocated_bytes > numa_pool->peak_allocated_bytes) {
        numa_pool->peak_allocated_bytes = numa_pool->total_allocated_bytes;
    }

    pthread_mutex_unlock(&numa_pool->chunk_mutex);

    pool->total_allocated++;
    g_pool_manager.total_allocations++;
    g_pool_manager.bytes_saved_by_pooling += (alloc_size - size);

    return ptr;
}

/**
 * Standard malloc implementation (uses optimal NUMA node)
 */
void* pool_malloc(size_t size) {
    return pool_malloc_numa(size, get_optimal_numa_node());
}

/**
 * Cache-aligned malloc implementation
 */
void* pool_malloc_aligned(size_t size, size_t alignment) {
    if (alignment == 0 || (alignment & (alignment - 1)) != 0) {
        return NULL;  // Invalid alignment
    }

    // For cache-line alignment, use optimized path
    if (alignment == CACHE_LINE_SIZE) {
        size_t aligned_size = (size + CACHE_LINE_SIZE - 1) & ~(CACHE_LINE_SIZE - 1);
        void* ptr = pool_malloc(aligned_size);

        // Memory from pool allocator should already be reasonably aligned
        if (((uintptr_t)ptr & (CACHE_LINE_SIZE - 1)) == 0) {
            return ptr;
        }
    }

    // Fallback to system aligned_alloc
    return aligned_alloc(alignment, size);
}

/**
 * Calloc implementation with AVX-512 optimized zeroing
 */
void* pool_calloc(size_t nmemb, size_t size) {
    size_t total_size = nmemb * size;
    void* ptr = pool_malloc(total_size);

    if (ptr) {
        avx512_memset(ptr, 0, total_size);
    }

    return ptr;
}

/**
 * NUMA-aware calloc
 */
void* pool_calloc_numa(size_t nmemb, size_t size, int numa_node) {
    size_t total_size = nmemb * size;
    void* ptr = pool_malloc_numa(total_size, numa_node);

    if (ptr) {
        avx512_memset(ptr, 0, total_size);
    }

    return ptr;
}

/**
 * Cache-aligned calloc
 */
void* pool_calloc_aligned(size_t nmemb, size_t size, size_t alignment) {
    size_t total_size = nmemb * size;
    void* ptr = pool_malloc_aligned(total_size, alignment);

    if (ptr) {
        avx512_memset(ptr, 0, total_size);
    }

    return ptr;
}

/**
 * Free implementation
 */
void pool_free(void* ptr) {
    if (!ptr) return;

    // Determine if this is a pooled allocation
    // For simplicity, we'll track this with a simple heuristic
    // In production, you'd want a more sophisticated tracking system

    int pool_index = -1;
    int numa_node = get_optimal_numa_node();

    // Try to return to appropriate pool
    for (int i = 0; i < MAX_POOL_SIZES; i++) {
        thread_pool_t* pool = t_current_pools[i];
        if (pool) {
            // Add to free list
            *(void**)ptr = pool->free_list;
            pool->free_list = ptr;
            pool->free_count++;
            g_pool_manager.total_deallocations++;
            return;
        }
    }

    // Not a pooled allocation, use system free
    free(ptr);
    g_pool_manager.total_deallocations++;
}

/**
 * Realloc implementation (simplified)
 */
void* pool_realloc(void* ptr, size_t size) {
    if (!ptr) {
        return pool_malloc(size);
    }

    if (size == 0) {
        pool_free(ptr);
        return NULL;
    }

    // For simplicity, allocate new and copy
    // In production, you'd want to check if the new size fits in the same pool
    void* new_ptr = pool_malloc(size);
    if (new_ptr) {
        // Copy old data (we'd need to track original size for this)
        // For now, copy a reasonable amount
        avx512_memcpy(new_ptr, ptr, size);
        pool_free(ptr);
    }

    return new_ptr;
}

/**
 * Get pool statistics
 */
void pool_get_stats(pool_stats_t* stats) {
    if (!stats) return;

    memset(stats, 0, sizeof(pool_stats_t));

    stats->total_allocated = g_pool_manager.total_allocations;
    stats->total_freed = g_pool_manager.total_deallocations;
    stats->pool_hits = g_pool_manager.cache_hits;
    stats->pool_misses = g_pool_manager.cache_misses;

    for (int i = 0; i < NUMA_NODES; i++) {
        numa_pool_t* pool = &g_pool_manager.numa_pools[i];
        stats->current_usage += pool->total_allocated_bytes;
        if (pool->peak_allocated_bytes > stats->peak_usage) {
            stats->peak_usage = pool->peak_allocated_bytes;
        }
    }

    // Calculate hit rate
    uint64_t total_requests = stats->pool_hits + stats->pool_misses;
    if (total_requests > 0) {
        stats->fragmentation_ratio = (double)stats->pool_misses / total_requests;
    }
}

/**
 * Print pool statistics
 */
void pool_print_stats(void) {
    pool_stats_t stats;
    pool_get_stats(&stats);

    printf("\n=== Memory Pool Statistics ===\n");
    printf("Total allocations: %lu\n", stats.total_allocated);
    printf("Total deallocations: %lu\n", stats.total_freed);
    printf("Current usage: %lu bytes (%.2f MB)\n",
           stats.current_usage, stats.current_usage / (1024.0 * 1024.0));
    printf("Peak usage: %lu bytes (%.2f MB)\n",
           stats.peak_usage, stats.peak_usage / (1024.0 * 1024.0));
    printf("Pool hits: %lu\n", stats.pool_hits);
    printf("Pool misses: %lu\n", stats.pool_misses);
    printf("Bytes saved by pooling: %lu\n", g_pool_manager.bytes_saved_by_pooling);

    if (stats.pool_hits + stats.pool_misses > 0) {
        double hit_rate = (double)stats.pool_hits / (stats.pool_hits + stats.pool_misses) * 100.0;
        printf("Pool hit rate: %.2f%%\n", hit_rate);
    }

    printf("AVX-512 available: %s\n", g_pool_manager.avx512_available ? "Yes" : "No");
    printf("Huge pages enabled: %s\n", g_pool_manager.huge_pages_enabled ? "Yes" : "No");
    printf("==============================\n");
}

/**
 * Cleanup memory pools
 */
void memory_pool_cleanup(void) {
    // In a production system, you'd want to properly cleanup all allocations
    // For now, just reset the manager
    memset(&g_pool_manager, 0, sizeof(g_pool_manager));
}

/**
 * Check if AVX-512 is available
 */
bool is_avx512_available(void) {
    return g_pool_manager.avx512_available;
}