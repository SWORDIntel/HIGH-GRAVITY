/*
 * NON-BLOCKING RING BUFFER INTERFACE
 * 
 * Solves the blocking problem while preserving all features
 * Provides timeout-based reads and polling options
 */

#ifndef RING_BUFFER_NONBLOCKING_H
#define RING_BUFFER_NONBLOCKING_H

#include <errno.h>
#include <time.h>
#include "ring_buffer_adapter.h"
#include "compatibility_layer.h"

// Non-blocking wrapper for ring buffers
typedef struct {
    ring_buffer_adapter_t* adapter;
    int timeout_ms;
    bool use_polling;
    bool use_try_read;  // Use try_read functions when available
} nonblocking_rb_t;

// Create non-blocking wrapper
static inline nonblocking_rb_t* create_nonblocking_rb(ring_buffer_adapter_t* adapter,
                                                      int timeout_ms) {
    nonblocking_rb_t* nb = calloc(1, sizeof(nonblocking_rb_t));
    if (nb) {
        nb->adapter = adapter;
        nb->timeout_ms = timeout_ms;
        nb->use_polling = true;
        nb->use_try_read = true;
    }
    return nb;
}

// Non-blocking read with timeout
static inline int ring_buffer_read_nonblocking(nonblocking_rb_t* nb, int priority,
                                              enhanced_msg_header_t* msg, 
                                              uint8_t* payload) {
    if (!nb || !nb->adapter) return -EINVAL;
    
    // If we can use try_read, use it
    if (nb->use_try_read) {
        // First attempt - try non-blocking read
        int result = ring_buffer_try_read_priority((ring_buffer_t*)nb->adapter->impl,
                                                   priority, msg, payload);
        if (result == 0) return 0;  // Success
        if (result != -EAGAIN) return result;  // Real error
    }
    
    // Polling with timeout
    if (nb->use_polling && nb->timeout_ms > 0) {
        struct timespec start, now;
        clock_gettime(CLOCK_MONOTONIC, &start);
        
        int elapsed_ms = 0;
        while (elapsed_ms < nb->timeout_ms) {
            // Try read
            if (nb->use_try_read) {
                int result = ring_buffer_try_read_priority(
                    (ring_buffer_t*)nb->adapter->impl, priority, msg, payload);
                if (result == 0) return 0;  // Success
                if (result != -EAGAIN) return result;  // Real error
            }
            
            // Brief sleep to avoid CPU spinning
            usleep(1000);  // 1ms
            
            // Check timeout
            clock_gettime(CLOCK_MONOTONIC, &now);
            elapsed_ms = (now.tv_sec - start.tv_sec) * 1000 +
                        (now.tv_nsec - start.tv_nsec) / 1000000;
        }
        
        return -ETIMEDOUT;
    }
    
    // No timeout - single try
    if (nb->use_try_read) {
        return ring_buffer_try_read_priority((ring_buffer_t*)nb->adapter->impl,
                                            priority, msg, payload);
    }
    
    // Fallback to blocking read (not recommended)
    return ring_buffer_read(nb->adapter, priority, msg, payload);
}

// Non-blocking write (usually doesn't block anyway)
static inline int ring_buffer_write_nonblocking(nonblocking_rb_t* nb, int priority,
                                               enhanced_msg_header_t* msg,
                                               uint8_t* payload) {
    if (!nb || !nb->adapter) return -EINVAL;
    return ring_buffer_write(nb->adapter, priority, msg, payload);
}

// Destroy non-blocking wrapper
static inline void destroy_nonblocking_rb(nonblocking_rb_t* nb) {
    if (nb) {
        // Note: Does NOT destroy the underlying adapter
        free(nb);
    }
}

#endif // RING_BUFFER_NONBLOCKING_H