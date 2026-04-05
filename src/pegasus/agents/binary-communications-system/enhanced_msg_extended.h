/*
 * EXTENDED MESSAGE HEADER - Full Feature Set
 * 
 * This extends the base enhanced_msg_header_t with all advanced features
 * while maintaining backward compatibility. This is the best practice approach.
 */

#ifndef ENHANCED_MSG_EXTENDED_H
#define ENHANCED_MSG_EXTENDED_H

#include "../src/c/compatibility_layer.h"

// Extended message header with ALL features
typedef struct {
    // Base fields (compatible with enhanced_msg_header_t)
    uint32_t magic;
    uint16_t version;
    uint16_t flags;
    uint32_t msg_type;
    uint32_t priority;
    uint64_t timestamp;
    uint32_t source_id;
    uint32_t target_id;
    uint32_t payload_size;
    uint32_t checksum;
    
    // Extended fields for advanced features
    float ai_confidence;           // NPU classification confidence
    uint16_t predicted_path[4];     // NPU predicted routing path
    float anomaly_score;            // GNA anomaly detection score
    uint32_t gpu_batch_id;          // GPU batch processing ID
    uint64_t io_uring_data;         // io_uring user data
    uint32_t numa_node;             // Preferred NUMA node
    uint32_t core_affinity;         // Preferred core type mask
    uint64_t hw_timestamp;          // Hardware timestamp if available
    
    // Performance metrics
    uint64_t enqueue_ns;            // Enqueue timestamp
    uint64_t dequeue_ns;            // Dequeue timestamp
    uint32_t retry_count;           // Number of retries
    uint32_t forward_count;         // Times forwarded
    
    // Reserved for future expansion
    uint64_t reserved[4];
} enhanced_msg_extended_t;

// Conversion functions for compatibility
static inline void msg_base_to_extended(const enhanced_msg_header_t* base, 
                                        enhanced_msg_extended_t* extended) {
    // Copy base fields
    extended->magic = base->magic;
    extended->version = base->version;
    extended->flags = base->flags;
    extended->msg_type = base->msg_type;
    extended->priority = base->priority;
    extended->timestamp = base->timestamp;
    extended->source_id = base->source_id;
    extended->target_id = base->target_id;
    extended->payload_size = base->payload_size;
    extended->checksum = base->checksum;
    
    // Initialize extended fields to defaults
    extended->ai_confidence = 0.0f;
    extended->anomaly_score = 0.0f;
    extended->gpu_batch_id = 0;
    extended->io_uring_data = 0;
    extended->numa_node = 0;
    extended->core_affinity = 0;
    extended->hw_timestamp = 0;
    extended->enqueue_ns = 0;
    extended->dequeue_ns = 0;
    extended->retry_count = 0;
    extended->forward_count = 0;
    
    for (int i = 0; i < 4; i++) {
        extended->predicted_path[i] = 0;
        extended->reserved[i] = 0;
    }
}

static inline void msg_extended_to_base(const enhanced_msg_extended_t* extended,
                                        enhanced_msg_header_t* base) {
    // Copy only base fields
    base->magic = extended->magic;
    base->version = extended->version;
    base->flags = extended->flags;
    base->msg_type = extended->msg_type;
    base->priority = extended->priority;
    base->timestamp = extended->timestamp;
    base->source_id = extended->source_id;
    base->target_id = extended->target_id;
    base->payload_size = extended->payload_size;
    base->checksum = extended->checksum;
}

// Check if a message has extended fields (by version or flags)
static inline bool msg_is_extended(const enhanced_msg_header_t* msg) {
    return (msg->version >= 2) || (msg->flags & 0x8000);  // High bit indicates extended
}

#endif // ENHANCED_MSG_EXTENDED_H