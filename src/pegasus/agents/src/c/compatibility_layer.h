/* Auto-generated compatibility layer */
#ifndef COMPATIBILITY_LAYER_H
#define COMPATIBILITY_LAYER_H

#include <stdlib.h>
#include <unistd.h>
#include <sched.h>
#include <stdbool.h>

/* NUMA support - use real library if available */

/* io_uring compatibility - only define stubs if liburing not available */
/* These will only be used if liburing.h is not included */

// Forward declarations for missing protocol structures
#include <stdint.h>
// Always define the structure for compatibility
#ifndef ENHANCED_MSG_HEADER_T_DEFINED
typedef struct {
    uint32_t magic;
    uint16_t version;                  // Added for compatibility
    uint16_t flags;
    uint32_t msg_type;
    uint32_t priority;
    uint64_t timestamp;
    uint64_t sequence;
    uint32_t source_agent;
    uint32_t target_count;
    uint32_t target_agents[16];
    uint32_t payload_len;
    uint32_t crc32;
    
    // Extended fields for compatibility with other systems
    float ai_confidence;
    float anomaly_score;
    uint16_t predicted_path[4];
    uint64_t feature_hash;
    uint8_t gpu_batch_id;
    uint8_t padding2[31];
} enhanced_msg_header_t;

// Field compatibility macros - only for enhanced_msg_header_t usage
// These map old field names to new ones in enhanced_msg_header_t
#define source_id source_agent
#define target_id target_agents[0]
#define payload_size payload_len
#define checksum crc32
#define ENHANCED_MSG_HEADER_T_DEFINED
#endif /* ENHANCED_MSG_HEADER_T_DEFINED */

// System constants
#ifndef PAGE_SIZE
#define PAGE_SIZE 4096
#endif

// Error codes for compatibility layer
#define COMPAT_SUCCESS 0
#define COMPAT_ERROR_INVALID_PARAM -1
#define COMPAT_ERROR_NO_MEMORY -2
#define COMPAT_ERROR_TIMEOUT -3
#define COMPAT_ERROR_NOT_FOUND -4
#define COMPAT_ERROR_BUSY -5
#define COMPAT_ERROR_QUEUE_FULL -6
#define COMPAT_ERROR_IO -7
#define COMPAT_ERROR_NOT_SUPPORTED -8
#define COMPAT_ERROR_THERMAL -9

// System information structure
typedef struct {
    uint32_t cpu_count;
    uint32_t p_core_count;
    uint32_t e_core_count;
    size_t page_size;
    size_t cache_line_size;
    bool has_avx512;
    bool has_avx2;
    bool has_io_uring;
    size_t total_memory;
    size_t available_memory;
} system_info_t;

// Ring buffer type definition for compatibility
typedef struct ring_buffer ring_buffer_t;

// Work queue types for compatibility
typedef struct work_item work_item_t;
typedef struct work_queue work_queue_t;

// Function prototypes for missing functions
int io_uring_fallback_read(int fd, void *buf, size_t count, off_t offset);
int io_uring_fallback_write(int fd, const void *buf, size_t count, off_t offset);
int ring_buffer_read_priority(ring_buffer_t* rb, int priority, enhanced_msg_header_t* msg, uint8_t* payload);
int ring_buffer_write_priority(ring_buffer_t* rb, int priority, enhanced_msg_header_t* msg, uint8_t* payload);
void process_message_pcore(enhanced_msg_header_t* msg, uint8_t* payload);
void process_message_ecore(enhanced_msg_header_t* msg, uint8_t* payload);
void* work_queue_steal(void* queue);
ring_buffer_t* ring_buffer_create(uint32_t max_size);
void ring_buffer_destroy(ring_buffer_t* rb);

// Work queue functions
work_queue_t* work_queue_create(uint32_t max_size);
void work_queue_destroy(work_queue_t* queue);
int work_queue_submit(work_queue_t* queue, void* data, void (*function)(void*), uint32_t priority);
work_item_t* work_queue_get(work_queue_t* queue);

// Mock advanced feature stubs
static inline int streaming_pipeline_init(uint32_t partitions, const char* brokers, const char* topic) {
    (void)partitions; (void)brokers; (void)topic; return 0;
}
static inline void streaming_pipeline_shutdown(void) { }
static inline void streaming_pipeline_start(void) { }
static inline int nas_init(void) { return 0; }
static inline void nas_shutdown(void) { }
static inline void nas_get_stats(uint32_t* arch, double* fitness, uint32_t* gen) {
    if(arch) *arch = 100; 
    if(fitness) *fitness = 0.95; 
    if(gen) *gen = 10;
}
static inline int digital_twin_init(void) { return 0; }
static inline void* digital_twin_create(const char* name, int type) {
    (void)name; (void)type; return (void*)1;
}
static inline void digital_twin_shutdown(void) { }
static inline void digital_twin_get_stats(uint64_t* syncs, double* latency, uint64_t* pred, uint64_t* anom) {
    if(syncs) *syncs = 1000; 
    if(latency) *latency = 5.0; 
    if(pred) *pred = 500; 
    if(anom) *anom = 2;
}
static inline int multimodal_fusion_init(void) { return 0; }
static inline void* fusion_create_instance(int strategy) { (void)strategy; return (void*)1; }
static inline int fusion_process(void* fusion) { (void)fusion; return 0; }
static inline void multimodal_fusion_shutdown(void) { }

#endif /* COMPATIBILITY_LAYER_H */
