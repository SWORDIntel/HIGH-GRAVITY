#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <numa.h>

// Memory pool structure optimized for Meteor Lake
typedef struct memory_pool {
    void* base_addr;
    size_t pool_size;
    size_t block_size;
    size_t num_blocks;
    unsigned char* free_bitmap;
    int numa_node;
} memory_pool_t;

// Intel Meteor Lake optimized allocation
void* meteor_lake_alloc(size_t size, int prefer_p_cores) {
    // Prefer allocation on P-core NUMA node for performance-critical data
    int numa_node = prefer_p_cores ? 0 : -1;
    
    if (numa_available() >= 0 && numa_node >= 0) {
        return numa_alloc_onnode(size, numa_node);
    }
    
    // Fallback to standard allocation with alignment
    void* ptr = aligned_alloc(64, (size + 63) & ~63);
    if (ptr) {
        madvise(ptr, size, MADV_HUGEPAGE); // Use huge pages if available
    }
    return ptr;
}

// Memory pool initialization for ultra-fast protocol
memory_pool_t* init_communication_pool(size_t pool_size, size_t block_size) {
    memory_pool_t* pool = malloc(sizeof(memory_pool_t));
    if (!pool) return NULL;
    
    pool->pool_size = pool_size;
    pool->block_size = block_size;
    pool->num_blocks = pool_size / block_size;
    
    // Allocate pool on P-core NUMA node for maximum performance
    pool->base_addr = meteor_lake_alloc(pool_size, 1);
    if (!pool->base_addr) {
        free(pool);
        return NULL;
    }
    
    // Initialize free bitmap
    size_t bitmap_size = (pool->num_blocks + 7) / 8;
    pool->free_bitmap = calloc(1, bitmap_size);
    if (!pool->free_bitmap) {
        numa_free(pool->base_addr, pool_size);
        free(pool);
        return NULL;
    }
    
    return pool;
}

// Ultra-fast block allocation (O(1) average case)
void* pool_alloc(memory_pool_t* pool) {
    // Find first free block using bit manipulation
    for (size_t i = 0; i < pool->num_blocks; i++) {
        size_t byte_idx = i / 8;
        size_t bit_idx = i % 8;
        
        if (!(pool->free_bitmap[byte_idx] & (1 << bit_idx))) {
            // Mark as allocated
            pool->free_bitmap[byte_idx] |= (1 << bit_idx);
            
            // Return pointer to block
            return (char*)pool->base_addr + (i * pool->block_size);
        }
    }
    
    return NULL; // Pool exhausted
}

// Ultra-fast block deallocation (O(1))
void pool_free(memory_pool_t* pool, void* ptr) {
    if (!ptr || ptr < pool->base_addr) return;
    
    size_t offset = (char*)ptr - (char*)pool->base_addr;
    size_t block_idx = offset / pool->block_size;
    
    if (block_idx >= pool->num_blocks) return;
    
    size_t byte_idx = block_idx / 8;
    size_t bit_idx = block_idx % 8;
    
    // Mark as free
    pool->free_bitmap[byte_idx] &= ~(1 << bit_idx);
}
