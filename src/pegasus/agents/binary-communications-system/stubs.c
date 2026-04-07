/*
 * STUB IMPLEMENTATIONS for binary communication system
 * 
 * Provides minimal implementations of required functions for linking
 */

#include "compatibility_layer.h"
#include "ultra_fast_protocol.h"
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <stdio.h>

// Simple ring buffer structure for stub implementation
struct ring_buffer {
    uint8_t* buffer;
    size_t size;
    size_t read_pos;
    size_t write_pos;
    size_t capacity;
};

// Ring buffer stub implementations
ring_buffer_t* ring_buffer_create(uint32_t max_size) {
    fprintf(stdout, "[STUB] ring_buffer_create called (max_size=%u)\n", (unsigned int)max_size);
    ring_buffer_t* rb = malloc(sizeof(ring_buffer_t));
    if (!rb) return NULL;
    
    rb->buffer = malloc(max_size);
    if (!rb->buffer) {
        free(rb);
        return NULL;
    }
    
    rb->size = max_size;
    rb->read_pos = 0;
    rb->write_pos = 0;
    rb->capacity = max_size;
    
    return rb;
}

void ring_buffer_destroy(ring_buffer_t* rb) {
    fprintf(stdout, "[STUB] ring_buffer_destroy called\n");
    if (rb) {
        free(rb->buffer);
        free(rb);
    }
}

int ring_buffer_write_priority(ring_buffer_t* rb, int priority, 
                              enhanced_msg_header_t* msg, uint8_t* payload) {
    fprintf(stdout, "[STUB] ring_buffer_write_priority called\n");
    if (!rb || !msg) return -1;
    
    size_t msg_size = sizeof(enhanced_msg_header_t) + msg->payload_len;
    if (msg_size > rb->capacity - rb->size) return -1; // Buffer full
    
    // Simple implementation - just copy the message
    memcpy(rb->buffer + rb->write_pos, msg, sizeof(enhanced_msg_header_t));
    if (payload && msg->payload_len > 0) {
        memcpy(rb->buffer + rb->write_pos + sizeof(enhanced_msg_header_t), 
               payload, msg->payload_len);
    }
    
    rb->write_pos = (rb->write_pos + msg_size) % rb->capacity;
    rb->size += msg_size;
    
    return 0; // Success
}

int ring_buffer_read_priority(ring_buffer_t* rb, int priority, 
                             enhanced_msg_header_t* msg, uint8_t* payload) {
    fprintf(stdout, "[STUB] ring_buffer_read_priority called\n");
    if (!rb || !msg || rb->size == 0) return -1;
    
    // Simple implementation - read the next message
    memcpy(msg, rb->buffer + rb->read_pos, sizeof(enhanced_msg_header_t));
    
    if (payload && msg->payload_len > 0) {
        memcpy(payload, rb->buffer + rb->read_pos + sizeof(enhanced_msg_header_t), 
               msg->payload_len);
    }
    
    size_t msg_size = sizeof(enhanced_msg_header_t) + msg->payload_len;
    rb->read_pos = (rb->read_pos + msg_size) % rb->capacity;
    rb->size -= msg_size;
    
    return 0; // Success
}

// Message processing stub implementations
void process_message_pcore(enhanced_msg_header_t* msg, uint8_t* payload) {
    fprintf(stdout, "[STUB] process_message_pcore called\n");
    // Stub: Just increment a counter or do minimal processing
    if (msg) {
        msg->flags |= 0x1000; // Mark as processed by P-core
    }
}

void process_message_ecore(enhanced_msg_header_t* msg, uint8_t* payload) {
    fprintf(stdout, "[STUB] process_message_ecore called\n");
    // Stub: Just increment a counter or do minimal processing
    if (msg) {
        msg->flags |= 0x2000; // Mark as processed by E-core
    }
}

ufp_message_t* ufp_message_create(void) {
    fprintf(stdout, "[STUB] ufp_message_create called\n");
    ufp_message_t* msg = malloc(sizeof(ufp_message_t));
    if (!msg) return NULL;
    memset(msg, 0, sizeof(ufp_message_t));
    return msg;
}

void ufp_cleanup(void) {
    fprintf(stdout, "[STUB] ufp_cleanup called\n");
    // Stub
}

ufp_error_t ufp_send(ufp_context_t* ctx, const ufp_message_t* msg) {
    fprintf(stdout, "[STUB] ufp_send called\n");
    return UFP_SUCCESS;
}

ufp_context_t* ufp_create_context(const char* agent_name) {
    fprintf(stdout, "[STUB] ufp_create_context called\n");
    return NULL;
}

void ufp_destroy_context(ufp_context_t* ctx) {
    fprintf(stdout, "[STUB] ufp_destroy_context called\n");
    // Stub
}

ufp_error_t ufp_init(void) {
    fprintf(stdout, "[STUB] ufp_init called\n");
    return UFP_SUCCESS;
}

void ufp_message_destroy(ufp_message_t* msg) {
    fprintf(stdout, "[STUB] ufp_message_destroy called\n");
    if (msg) free(msg);
}

ssize_t ufp_pack_message(const ufp_message_t* msg, uint8_t* buffer, size_t buffer_size) {
    fprintf(stdout, "[STUB] ufp_pack_message called\n");
    return 0;
}

// I/O ring fallback implementations (already stubbed in compatibility_layer.h)
int io_uring_fallback_read(int fd, void *buf, size_t count, off_t offset) {
    fprintf(stdout, "[STUB] io_uring_fallback_read called\n");
    if (!buf) {
        fprintf(stderr, "[STUB Error] io_uring_fallback_read: buf is NULL\n");
        return -1;
    }
    // Simple fallback to pread
    return pread(fd, buf, count, offset);
}

int io_uring_fallback_write(int fd, const void *buf, size_t count, off_t offset) {
    fprintf(stdout, "[STUB] io_uring_fallback_write called\n");
    if (!buf) {
        fprintf(stderr, "[STUB Error] io_uring_fallback_write: buf is NULL\n");
        return -1;
    }
    // Simple fallback to pwrite  
    return pwrite(fd, buf, count, offset);
}
