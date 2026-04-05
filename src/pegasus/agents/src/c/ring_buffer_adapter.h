/*
 * RING BUFFER ADAPTER - Smart Integration Layer
 * 
 * This adapter provides a clean interface between the ultra_hybrid system
 * and the compatibility layer using function pointers (vtable pattern).
 * This is a standard technique in C for creating polymorphic interfaces.
 */

#ifndef RING_BUFFER_ADAPTER_H
#define RING_BUFFER_ADAPTER_H

#include <stdint.h>
#include <stdbool.h>
#include "compatibility_layer.h"

// Forward declaration
typedef struct ring_buffer_adapter ring_buffer_adapter_t;

// Function pointer types for ring buffer operations
typedef int (*rb_write_fn)(void* impl, int priority, enhanced_msg_header_t* msg, uint8_t* payload);
typedef int (*rb_read_fn)(void* impl, int priority, enhanced_msg_header_t* msg, uint8_t* payload);
typedef void (*rb_destroy_fn)(void* impl);
typedef size_t (*rb_get_stats_fn)(void* impl, int stat_type);

// Vtable for ring buffer operations
typedef struct {
    rb_write_fn write;
    rb_read_fn read;
    rb_destroy_fn destroy;
    rb_get_stats_fn get_stats;
} ring_buffer_ops_t;

// Adapter structure that wraps any ring buffer implementation
struct ring_buffer_adapter {
    void* impl;                    // Pointer to actual implementation
    const ring_buffer_ops_t* ops;  // Operation vtable
    void* metadata;                // Optional metadata
};

// Factory functions for different implementations
ring_buffer_adapter_t* create_compat_ring_buffer_adapter(size_t size);
ring_buffer_adapter_t* create_hybrid_ring_buffer_adapter(size_t size, int numa_node);
ring_buffer_adapter_t* create_dpdk_ring_buffer_adapter(size_t size);

// Unified interface - these work with any adapter
static inline int ring_buffer_write(ring_buffer_adapter_t* adapter, int priority,
                                   enhanced_msg_header_t* msg, uint8_t* payload) {
    return adapter->ops->write(adapter->impl, priority, msg, payload);
}

static inline int ring_buffer_read(ring_buffer_adapter_t* adapter, int priority,
                                  enhanced_msg_header_t* msg, uint8_t* payload) {
    return adapter->ops->read(adapter->impl, priority, msg, payload);
}

static inline void ring_buffer_destroy_adapter(ring_buffer_adapter_t* adapter) {
    if (adapter) {
        if (adapter->ops && adapter->ops->destroy) {
            adapter->ops->destroy(adapter->impl);
        }
        free(adapter);
    }
}

#endif // RING_BUFFER_ADAPTER_H