/*
 * RING BUFFER ADAPTER - Implementation
 * 
 * Smart integration using the adapter pattern with vtables.
 * This is how professional C projects handle multiple implementations.
 */

#include <stdlib.h>
#include <string.h>
#include <numa.h>
#include "ring_buffer_adapter.h"

// ============================================================================
// COMPATIBILITY LAYER ADAPTER
// ============================================================================

// Wrapper functions that adapt the compatibility layer interface
static int compat_write_wrapper(void* impl, int priority, 
                               enhanced_msg_header_t* msg, uint8_t* payload) {
    return ring_buffer_write_priority((ring_buffer_t*)impl, priority, msg, payload);
}

static int compat_read_wrapper(void* impl, int priority,
                              enhanced_msg_header_t* msg, uint8_t* payload) {
    return ring_buffer_read_priority(impl, priority, msg, payload);
}

static void compat_destroy_wrapper(void* impl) {
    ring_buffer_destroy((ring_buffer_t*)impl);
}

static size_t compat_get_stats_wrapper(void* impl, int stat_type) {
    // The compatibility layer doesn't expose stats, return 0
    return 0;
}

// Vtable for compatibility layer operations
static const ring_buffer_ops_t compat_ops = {
    .write = compat_write_wrapper,
    .read = compat_read_wrapper,
    .destroy = compat_destroy_wrapper,
    .get_stats = compat_get_stats_wrapper
};

// Factory function for compatibility layer adapter
ring_buffer_adapter_t* create_compat_ring_buffer_adapter(size_t size) {
    ring_buffer_adapter_t* adapter = calloc(1, sizeof(ring_buffer_adapter_t));
    if (!adapter) return NULL;
    
    adapter->impl = ring_buffer_create(size / 4);  // Divide by 4 priority levels
    if (!adapter->impl) {
        free(adapter);
        return NULL;
    }
    
    adapter->ops = &compat_ops;
    return adapter;
}

// ============================================================================
// HYBRID RING BUFFER ADAPTER
// ============================================================================

typedef struct {
    void* compat_rb;           // Compatibility layer ring buffer
    void* stats;               // Statistics structure
    int numa_node;             // NUMA node affinity
    size_t total_messages;     // Total messages processed
    size_t total_bytes;        // Total bytes processed
} hybrid_impl_t;

static int hybrid_write_wrapper(void* impl, int priority,
                               enhanced_msg_header_t* msg, uint8_t* payload) {
    hybrid_impl_t* hybrid = (hybrid_impl_t*)impl;
    
    // Use compatibility layer for actual storage
    int result = ring_buffer_write_priority((ring_buffer_t*)hybrid->compat_rb, 
                                           priority, msg, payload);
    
    // Update statistics
    if (result == 0) {
        __atomic_fetch_add(&hybrid->total_messages, 1, __ATOMIC_RELAXED);
        __atomic_fetch_add(&hybrid->total_bytes, sizeof(*msg) + msg->payload_size, 
                          __ATOMIC_RELAXED);
    }
    
    return result;
}

static int hybrid_read_wrapper(void* impl, int priority,
                              enhanced_msg_header_t* msg, uint8_t* payload) {
    hybrid_impl_t* hybrid = (hybrid_impl_t*)impl;
    return ring_buffer_read_priority(hybrid->compat_rb, priority, msg, payload);
}

static void hybrid_destroy_wrapper(void* impl) {
    hybrid_impl_t* hybrid = (hybrid_impl_t*)impl;
    if (hybrid) {
        if (hybrid->compat_rb) {
            ring_buffer_destroy((ring_buffer_t*)hybrid->compat_rb);
        }
        if (hybrid->stats) {
            numa_free(hybrid->stats, sizeof(void*));
        }
        free(hybrid);
    }
}

static size_t hybrid_get_stats_wrapper(void* impl, int stat_type) {
    hybrid_impl_t* hybrid = (hybrid_impl_t*)impl;
    switch (stat_type) {
        case 0: return hybrid->total_messages;
        case 1: return hybrid->total_bytes;
        case 2: return hybrid->numa_node;
        default: return 0;
    }
}

// Vtable for hybrid operations
static const ring_buffer_ops_t hybrid_ops = {
    .write = hybrid_write_wrapper,
    .read = hybrid_read_wrapper,
    .destroy = hybrid_destroy_wrapper,
    .get_stats = hybrid_get_stats_wrapper
};

// Factory function for hybrid adapter
ring_buffer_adapter_t* create_hybrid_ring_buffer_adapter(size_t size, int numa_node) {
    ring_buffer_adapter_t* adapter = calloc(1, sizeof(ring_buffer_adapter_t));
    if (!adapter) return NULL;
    
    hybrid_impl_t* hybrid = calloc(1, sizeof(hybrid_impl_t));
    if (!hybrid) {
        free(adapter);
        return NULL;
    }
    
    // Create compatibility layer ring buffer
    hybrid->compat_rb = ring_buffer_create(size / 4);
    if (!hybrid->compat_rb) {
        free(hybrid);
        free(adapter);
        return NULL;
    }
    
    // Set NUMA node
    hybrid->numa_node = numa_node;
    
    // Allocate stats on the specified NUMA node if available
    if (numa_available() >= 0 && numa_node >= 0) {
        hybrid->stats = numa_alloc_onnode(sizeof(void*), numa_node);
    }
    
    adapter->impl = hybrid;
    adapter->ops = &hybrid_ops;
    return adapter;
}

// ============================================================================
// DPDK RING BUFFER ADAPTER (Stub for future implementation)
// ============================================================================

ring_buffer_adapter_t* create_dpdk_ring_buffer_adapter(size_t size) {
    // For now, fall back to compatibility layer
    return create_compat_ring_buffer_adapter(size);
}