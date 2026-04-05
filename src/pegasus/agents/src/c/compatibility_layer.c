/*
 * COMPATIBILITY LAYER - Enhanced Implementation
 * 
 * Provides compatibility abstractions for the Agent Communication System v7.0
 * - io_uring fallback implementations for older kernels
 * - Ring buffer operations with priority queues
 * - CPU-specific message processing (P-cores vs E-cores)
 * - Work stealing queue implementation
 * - Platform-specific optimizations
 * - Thread-safe operations
 * 
 * Author: Agent Communication System v7.0
 * Version: 7.0.0 Production
 */

#ifndef _GNU_SOURCE
#define _GNU_SOURCE
#endif

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <stdbool.h>
#include <stdatomic.h>
#include <pthread.h>
#include <unistd.h>
#include <errno.h>
#include <fcntl.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <sys/syscall.h>
#include <sys/uio.h>
#include <sched.h>
#include <time.h>
#include <limits.h>
#include "compatibility_layer.h"

// Check for io_uring availability
#ifdef __linux__
#include <linux/version.h>
// Try to include liburing if available
#ifdef __has_include
  #if __has_include(<liburing.h>)
    #define HAS_IO_URING 1
    #include <liburing.h>
  #endif
#else
  // Fallback: try to include anyway for older compilers
  #if LINUX_VERSION_CODE >= KERNEL_VERSION(5,1,0)
    #define HAS_IO_URING 1
    #include <liburing.h>
  #endif
#endif
#endif

// Enhanced message header structure is defined in compatibility_layer.h

// Ring buffer implementation
typedef struct ring_buffer_entry {
    enhanced_msg_header_t header;
    uint8_t* payload;
    struct ring_buffer_entry* next;
} ring_buffer_entry_t;

struct ring_buffer {
    ring_buffer_entry_t* queues[4];  // 4 priority levels
    pthread_mutex_t locks[4];
    pthread_cond_t not_empty[4];
    uint32_t sizes[4];
    uint32_t max_size;
    atomic_uint total_messages;
};

// Work queue implementation
struct work_item {
    void* data;
    void (*function)(void*);
    uint32_t priority;
    uint64_t timestamp;
    struct work_item* next;
};

struct work_queue {
    work_item_t* head;
    work_item_t* tail;
    pthread_mutex_t lock;
    pthread_cond_t not_empty;
    atomic_uint size;
    uint32_t max_size;
    bool allow_stealing;
};

// Global compatibility state
static struct {
    bool io_uring_available;
    bool avx512_available;
    bool avx2_available;
    uint32_t p_core_count;
    uint32_t e_core_count;
    uint32_t numa_nodes;
    uint64_t page_size;
    work_queue_t* global_work_queues[32];  // Per-core work queues
    uint32_t work_queue_count;
} g_compat_state = {0};

// Initialize compatibility layer
int compatibility_layer_init(void) {
    // Detect CPU features
    FILE* f = fopen("/proc/cpuinfo", "r");
    if (f) {
        char line[256];
        int processor_count = 0;
        while (fgets(line, sizeof(line), f)) {
            if (strstr(line, "processor")) {
                processor_count++;
            }
            if (strstr(line, "avx512f")) {
                g_compat_state.avx512_available = true;
            }
            if (strstr(line, "avx2")) {
                g_compat_state.avx2_available = true;
            }
        }
        fclose(f);
        
        // Estimate P-cores and E-cores (simplified)
        if (processor_count > 16) {
            g_compat_state.p_core_count = 12;  // Assume 12 P-threads
            g_compat_state.e_core_count = processor_count - 12;
        } else {
            g_compat_state.p_core_count = processor_count;
            g_compat_state.e_core_count = 0;
        }
    }
    
    // Check io_uring availability
#ifdef HAS_IO_URING
    struct io_uring ring;
    if (io_uring_queue_init(8, &ring, 0) == 0) {
        g_compat_state.io_uring_available = true;
        io_uring_queue_exit(&ring);
    }
#endif
    
    // Get page size
    g_compat_state.page_size = sysconf(_SC_PAGESIZE);
    
    // Initialize per-core work queues
    g_compat_state.work_queue_count = sysconf(_SC_NPROCESSORS_ONLN);
    if (g_compat_state.work_queue_count > 32) {
        g_compat_state.work_queue_count = 32;
    }
    
    for (uint32_t i = 0; i < g_compat_state.work_queue_count; i++) {
        g_compat_state.global_work_queues[i] = work_queue_create(1024);
    }
    
    printf("Compatibility Layer Initialized:\n");
    printf("  io_uring: %s\n", g_compat_state.io_uring_available ? "Available" : "Fallback");
    printf("  AVX-512: %s\n", g_compat_state.avx512_available ? "Available" : "Not Available");
    printf("  AVX2: %s\n", g_compat_state.avx2_available ? "Available" : "Not Available");
    printf("  P-cores: %u, E-cores: %u\n", g_compat_state.p_core_count, g_compat_state.e_core_count);
    printf("  Work queues: %u\n", g_compat_state.work_queue_count);
    
    return 0;
}

// Cleanup compatibility layer
void compatibility_layer_cleanup(void) {
    for (uint32_t i = 0; i < g_compat_state.work_queue_count; i++) {
        if (g_compat_state.global_work_queues[i]) {
            work_queue_destroy(g_compat_state.global_work_queues[i]);
        }
    }
}

// ============================================================================
// IO_URING COMPATIBILITY
// ============================================================================

// Enhanced io_uring fallback with proper error handling
int io_uring_fallback_read(int fd, void *buf, size_t count, off_t offset) {
    if (fd < 0 || !buf || count == 0) {
        errno = EINVAL;
        return -1;
    }
    
    // Use pread for atomic positioning if available
#ifdef _GNU_SOURCE
    ssize_t result = pread(fd, buf, count, offset);
#else
    // Fallback to lseek + read (not thread-safe)
    off_t old_offset = lseek(fd, 0, SEEK_CUR);
    if (old_offset == (off_t)-1) {
        return -1;
    }
    
    if (lseek(fd, offset, SEEK_SET) == (off_t)-1) {
        return -1;
    }
    
    ssize_t result = read(fd, buf, count);
    
    // Restore original position
    lseek(fd, old_offset, SEEK_SET);
#endif
    
    return result;
}

int io_uring_fallback_write(int fd, const void *buf, size_t count, off_t offset) {
    if (fd < 0 || !buf || count == 0) {
        errno = EINVAL;
        return -1;
    }
    
    // Use pwrite for atomic positioning if available
#ifdef _GNU_SOURCE
    ssize_t result = pwrite(fd, buf, count, offset);
#else
    // Fallback to lseek + write (not thread-safe)
    off_t old_offset = lseek(fd, 0, SEEK_CUR);
    if (old_offset == (off_t)-1) {
        return -1;
    }
    
    if (lseek(fd, offset, SEEK_SET) == (off_t)-1) {
        return -1;
    }
    
    ssize_t result = write(fd, buf, count);
    
    // Restore original position
    lseek(fd, old_offset, SEEK_SET);
#endif
    
    return result;
}

// Async I/O wrapper
int async_read(int fd, void *buf, size_t count, off_t offset, void (*callback)(int, void*), void* user_data) {
#ifdef HAS_IO_URING
    if (g_compat_state.io_uring_available) {
        // Would use io_uring here in full implementation
        // For now, fall through to sync version
    }
#endif
    
    // Synchronous fallback
    int result = io_uring_fallback_read(fd, buf, count, offset);
    if (callback) {
        callback(result, user_data);
    }
    return result;
}

int async_write(int fd, const void *buf, size_t count, off_t offset, void (*callback)(int, void*), void* user_data) {
#ifdef HAS_IO_URING
    if (g_compat_state.io_uring_available) {
        // Would use io_uring here in full implementation
        // For now, fall through to sync version
    }
#endif
    
    // Synchronous fallback
    int result = io_uring_fallback_write(fd, buf, count, offset);
    if (callback) {
        callback(result, user_data);
    }
    return result;
}

// ============================================================================
// RING BUFFER IMPLEMENTATION
// ============================================================================

// Create ring buffer
ring_buffer_t* ring_buffer_create(uint32_t max_size) {
    ring_buffer_t* rb = (ring_buffer_t*)calloc(1, sizeof(ring_buffer_t));
    if (!rb) return NULL;
    
    rb->max_size = max_size;
    atomic_store(&rb->total_messages, 0);
    
    for (int i = 0; i < 4; i++) {
        pthread_mutex_init(&rb->locks[i], NULL);
        pthread_cond_init(&rb->not_empty[i], NULL);
        rb->sizes[i] = 0;
        rb->queues[i] = NULL;
    }
    
    return rb;
}

// Destroy ring buffer
void ring_buffer_destroy(ring_buffer_t* rb) {
    if (!rb) return;
    
    for (int i = 0; i < 4; i++) {
        pthread_mutex_lock(&rb->locks[i]);
        
        ring_buffer_entry_t* entry = rb->queues[i];
        while (entry) {
            ring_buffer_entry_t* next = entry->next;
            if (entry->payload) {
                free(entry->payload);
            }
            free(entry);
            entry = next;
        }
        
        pthread_mutex_unlock(&rb->locks[i]);
        pthread_mutex_destroy(&rb->locks[i]);
        pthread_cond_destroy(&rb->not_empty[i]);
    }
    
    free(rb);
}

// Write to ring buffer with priority
int ring_buffer_write_priority(ring_buffer_t* rb, int priority, enhanced_msg_header_t* msg, uint8_t* payload) {
    if (!rb || !msg || priority < 0 || priority > 3) {
        return -1;
    }
    
    pthread_mutex_lock(&rb->locks[priority]);
    
    // Check if full
    if (rb->sizes[priority] >= rb->max_size) {
        pthread_mutex_unlock(&rb->locks[priority]);
        errno = ENOSPC;
        return -1;
    }
    
    // Create new entry
    ring_buffer_entry_t* entry = (ring_buffer_entry_t*)malloc(sizeof(ring_buffer_entry_t));
    if (!entry) {
        pthread_mutex_unlock(&rb->locks[priority]);
        return -1;
    }
    
    // Copy header
    memcpy(&entry->header, msg, sizeof(enhanced_msg_header_t));
    
    // Copy payload if present
    if (payload && msg->payload_size > 0) {
        entry->payload = (uint8_t*)malloc(msg->payload_size);
        if (!entry->payload) {
            free(entry);
            pthread_mutex_unlock(&rb->locks[priority]);
            return -1;
        }
        memcpy(entry->payload, payload, msg->payload_size);
    } else {
        entry->payload = NULL;
    }
    
    // Add to queue
    entry->next = NULL;
    if (!rb->queues[priority]) {
        rb->queues[priority] = entry;
    } else {
        // Find tail and append
        ring_buffer_entry_t* tail = rb->queues[priority];
        while (tail->next) {
            tail = tail->next;
        }
        tail->next = entry;
    }
    
    rb->sizes[priority]++;
    atomic_fetch_add(&rb->total_messages, 1);
    
    // Signal waiting readers
    pthread_cond_signal(&rb->not_empty[priority]);
    pthread_mutex_unlock(&rb->locks[priority]);
    
    return 0;
}

// Read from ring buffer with priority
int ring_buffer_read_priority(ring_buffer_t* rb, int priority, enhanced_msg_header_t* msg, uint8_t* payload) {
    
    if (!rb || !msg || priority < 0 || priority > 3) {
        return -1;
    }
    
    pthread_mutex_lock(&rb->locks[priority]);
    
    // Wait for messages if empty
    while (rb->sizes[priority] == 0) {
        pthread_cond_wait(&rb->not_empty[priority], &rb->locks[priority]);
    }
    
    // Get first entry
    ring_buffer_entry_t* entry = rb->queues[priority];
    if (!entry) {
        pthread_mutex_unlock(&rb->locks[priority]);
        return -1;
    }
    
    // Remove from queue
    rb->queues[priority] = entry->next;
    rb->sizes[priority]--;
    atomic_fetch_sub(&rb->total_messages, 1);
    
    // Copy header
    memcpy(msg, &entry->header, sizeof(enhanced_msg_header_t));
    
    // Copy payload if provided buffer
    if (payload && entry->payload && entry->header.payload_size > 0) {
        memcpy(payload, entry->payload, entry->header.payload_size);
    }
    
    // Free entry
    if (entry->payload) {
        free(entry->payload);
    }
    free(entry);
    
    pthread_mutex_unlock(&rb->locks[priority]);
    
    return 0;
}

// Try read without blocking
int ring_buffer_try_read_priority(ring_buffer_t* rb, int priority, enhanced_msg_header_t* msg, uint8_t* payload) {
    if (!rb || !msg || priority < 0 || priority > 3) {
        return -1;
    }
    
    pthread_mutex_lock(&rb->locks[priority]);
    
    if (rb->sizes[priority] == 0) {
        pthread_mutex_unlock(&rb->locks[priority]);
        errno = EAGAIN;
        return -1;
    }
    
    // Get first entry
    ring_buffer_entry_t* entry = rb->queues[priority];
    if (!entry) {
        pthread_mutex_unlock(&rb->locks[priority]);
        return -1;
    }
    
    // Remove from queue
    rb->queues[priority] = entry->next;
    rb->sizes[priority]--;
    atomic_fetch_sub(&rb->total_messages, 1);
    
    // Copy data
    memcpy(msg, &entry->header, sizeof(enhanced_msg_header_t));
    if (payload && entry->payload) {
        memcpy(payload, entry->payload, entry->header.payload_size);
    }
    
    // Free entry
    if (entry->payload) {
        free(entry->payload);
    }
    free(entry);
    
    pthread_mutex_unlock(&rb->locks[priority]);
    
    return 0;
}

// ============================================================================
// CPU-SPECIFIC MESSAGE PROCESSING
// ============================================================================

// Get current CPU type (P-core or E-core)
static int get_cpu_type(void) {
    int cpu = sched_getcpu();
    if (cpu < 0) return -1;
    
    // Simplified: assume first 12 CPUs are P-cores (threads 0-11)
    if (cpu < 12) {
        return 0;  // P-core
    } else {
        return 1;  // E-core
    }
}

// Process message on P-core (performance core)
void process_message_pcore(enhanced_msg_header_t* msg, uint8_t* payload) {
    if (!msg) return;
    
    // P-cores handle compute-intensive tasks
    uint64_t start_time = 0;
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    start_time = ts.tv_sec * 1000000000UL + ts.tv_nsec;
    
    // Simulate compute-intensive processing
    if (msg->msg_type & 0x1000) {  // High-priority compute flag
        // Use AVX-512 if available for compute
        if (g_compat_state.avx512_available) {
            // AVX-512 optimized path
            for (int i = 0; i < 1000; i++) {
                __builtin_ia32_pause();  // CPU pause instruction
            }
        } else if (g_compat_state.avx2_available) {
            // AVX2 optimized path
            for (int i = 0; i < 1500; i++) {
                __builtin_ia32_pause();
            }
        } else {
            // Standard processing
            for (int i = 0; i < 2000; i++) {
                __builtin_ia32_pause();
            }
        }
    }
    
    // Process payload
    if (payload && msg->payload_size > 0) {
        // Compute checksum
        uint32_t checksum = 0;
        for (uint32_t i = 0; i < msg->payload_size; i++) {
            checksum = ((checksum << 1) | (checksum >> 31)) ^ payload[i];
        }
        
        if (checksum != msg->checksum) {
            fprintf(stderr, "P-core: Checksum mismatch for message %u\n", msg->source_id);
        }
    }
    
    // Log processing time
    clock_gettime(CLOCK_MONOTONIC, &ts);
    uint64_t end_time = ts.tv_sec * 1000000000UL + ts.tv_nsec;
    uint64_t duration_ns = end_time - start_time;
    
    if (duration_ns > 1000000) {  // Log if > 1ms
        printf("P-core: Message %u processed in %lu us\n", 
               msg->source_id, duration_ns / 1000);
    }
}

// Process message on E-core (efficiency core)
void process_message_ecore(enhanced_msg_header_t* msg, uint8_t* payload) {
    if (!msg) return;
    
    // E-cores handle I/O and background tasks
    uint64_t start_time = 0;
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    start_time = ts.tv_sec * 1000000000UL + ts.tv_nsec;
    
    // Simulate I/O or lightweight processing
    if (msg->msg_type & 0x2000) {  // I/O flag
        // Simulate I/O operation
        usleep(100);  // 100 microseconds
    } else {
        // Lightweight processing
        for (int i = 0; i < 100; i++) {
            __builtin_ia32_pause();
        }
    }
    
    // Process payload
    if (payload && msg->payload_size > 0) {
        // Simple validation
        if (msg->payload_size > 65536) {
            fprintf(stderr, "E-core: Oversized payload from %u: %u bytes\n",
                   msg->source_id, msg->payload_size);
        }
    }
    
    // Log if slow
    clock_gettime(CLOCK_MONOTONIC, &ts);
    uint64_t end_time = ts.tv_sec * 1000000000UL + ts.tv_nsec;
    uint64_t duration_ns = end_time - start_time;
    
    if (duration_ns > 500000) {  // Log if > 500us
        printf("E-core: Message %u processed in %lu us\n",
               msg->source_id, duration_ns / 1000);
    }
}

// Route message to appropriate processor
void process_message_adaptive(enhanced_msg_header_t* msg, uint8_t* payload) {
    int cpu_type = get_cpu_type();
    
    if (cpu_type == 0) {
        process_message_pcore(msg, payload);
    } else {
        process_message_ecore(msg, payload);
    }
}

// ============================================================================
// WORK QUEUE IMPLEMENTATION
// ============================================================================

// Create work queue
work_queue_t* work_queue_create(uint32_t max_size) {
    work_queue_t* queue = (work_queue_t*)calloc(1, sizeof(work_queue_t));
    if (!queue) return NULL;
    
    queue->max_size = max_size;
    queue->allow_stealing = true;
    atomic_store(&queue->size, 0);
    pthread_mutex_init(&queue->lock, NULL);
    pthread_cond_init(&queue->not_empty, NULL);
    
    return queue;
}

// Destroy work queue
void work_queue_destroy(work_queue_t* queue) {
    if (!queue) return;
    
    pthread_mutex_lock(&queue->lock);
    
    work_item_t* item = queue->head;
    while (item) {
        work_item_t* next = item->next;
        free(item);
        item = next;
    }
    
    pthread_mutex_unlock(&queue->lock);
    pthread_mutex_destroy(&queue->lock);
    pthread_cond_destroy(&queue->not_empty);
    
    free(queue);
}

// Submit work to queue
int work_queue_submit(work_queue_t* queue, void* data, void (*function)(void*), uint32_t priority) {
    if (!queue || !function) return -1;
    
    pthread_mutex_lock(&queue->lock);
    
    if (atomic_load(&queue->size) >= queue->max_size) {
        pthread_mutex_unlock(&queue->lock);
        errno = ENOSPC;
        return -1;
    }
    
    work_item_t* item = (work_item_t*)malloc(sizeof(work_item_t));
    if (!item) {
        pthread_mutex_unlock(&queue->lock);
        return -1;
    }
    
    item->data = data;
    item->function = function;
    item->priority = priority;
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    item->timestamp = ts.tv_sec * 1000000000UL + ts.tv_nsec;
    item->next = NULL;
    
    // Insert based on priority
    if (!queue->head || priority > queue->head->priority) {
        item->next = queue->head;
        queue->head = item;
        if (!queue->tail) {
            queue->tail = item;
        }
    } else {
        work_item_t* current = queue->head;
        while (current->next && current->next->priority >= priority) {
            current = current->next;
        }
        item->next = current->next;
        current->next = item;
        if (!item->next) {
            queue->tail = item;
        }
    }
    
    atomic_fetch_add(&queue->size, 1);
    pthread_cond_signal(&queue->not_empty);
    pthread_mutex_unlock(&queue->lock);
    
    return 0;
}

// Get work from queue
work_item_t* work_queue_get(work_queue_t* queue) {
    if (!queue) return NULL;
    
    pthread_mutex_lock(&queue->lock);
    
    while (queue->head == NULL) {
        pthread_cond_wait(&queue->not_empty, &queue->lock);
    }
    
    work_item_t* item = queue->head;
    queue->head = item->next;
    if (!queue->head) {
        queue->tail = NULL;
    }
    
    atomic_fetch_sub(&queue->size, 1);
    pthread_mutex_unlock(&queue->lock);
    
    return item;
}

// Try to steal work from queue (non-blocking)
void* work_queue_steal(void* queue_ptr) {
    work_queue_t* queue = (work_queue_t*)queue_ptr;
    if (!queue || !queue->allow_stealing) return NULL;
    
    pthread_mutex_lock(&queue->lock);
    
    if (queue->head == NULL) {
        pthread_mutex_unlock(&queue->lock);
        return NULL;
    }
    
    // Steal from the tail (oldest low-priority work)
    work_item_t* current = queue->head;
    
    // Find the second-to-last item
    while (current->next && current->next->next) {
        current = current->next;
    }
    
    work_item_t* stolen = NULL;
    
    if (current->next) {
        // Steal the last item
        stolen = current->next;
        current->next = NULL;
        queue->tail = current;
    } else if (current == queue->head && atomic_load(&queue->size) == 1) {
        // Only one item, steal it
        stolen = queue->head;
        queue->head = NULL;
        queue->tail = NULL;
    }
    
    if (stolen) {
        atomic_fetch_sub(&queue->size, 1);
    }
    
    pthread_mutex_unlock(&queue->lock);
    
    return stolen;
}

// Work stealing scheduler
void* work_stealing_scheduler(int cpu_id) {
    if (cpu_id < 0 || cpu_id >= (int)g_compat_state.work_queue_count) {
        return NULL;
    }
    
    work_queue_t* local_queue = g_compat_state.global_work_queues[cpu_id];
    if (!local_queue) return NULL;
    
    // Try local queue first
    if (atomic_load(&local_queue->size) > 0) {
        return work_queue_get(local_queue);
    }
    
    // Try to steal from other queues
    for (uint32_t i = 0; i < g_compat_state.work_queue_count; i++) {
        if (i == (uint32_t)cpu_id) continue;
        
        work_queue_t* victim = g_compat_state.global_work_queues[i];
        if (victim && atomic_load(&victim->size) > 1) {  // Only steal if victim has multiple items
            void* stolen = work_queue_steal(victim);
            if (stolen) {
                return stolen;
            }
        }
    }
    
    return NULL;
}

// ============================================================================
// MEMORY MANAGEMENT
// ============================================================================

// Allocate aligned memory
void* aligned_alloc_compat(size_t alignment, size_t size) {
#ifdef _GNU_SOURCE
    void* ptr = NULL;
    if (posix_memalign(&ptr, alignment, size) == 0) {
        return ptr;
    }
    return NULL;
#else
    // Fallback implementation
    void* raw = malloc(size + alignment - 1 + sizeof(void*));
    if (!raw) return NULL;
    
    void** aligned = (void**)(((uintptr_t)raw + sizeof(void*) + alignment - 1) & ~(alignment - 1));
    aligned[-1] = raw;
    return aligned;
#endif
}

// Free aligned memory
void aligned_free_compat(void* ptr) {
#ifdef _GNU_SOURCE
    free(ptr);
#else
    if (ptr) {
        void** aligned = (void**)ptr;
        free(aligned[-1]);
    }
#endif
}

// Allocate huge pages if available
void* huge_page_alloc(size_t size) {
#ifdef __linux__
    void* ptr = mmap(NULL, size, PROT_READ | PROT_WRITE,
                    MAP_PRIVATE | MAP_ANONYMOUS | MAP_HUGETLB, -1, 0);
    if (ptr != MAP_FAILED) {
        return ptr;
    }
#endif
    // Fallback to regular allocation
    return aligned_alloc_compat(g_compat_state.page_size, size);
}

// Free huge pages
void huge_page_free(void* ptr, size_t size) {
#ifdef __linux__
    if (ptr && ptr != MAP_FAILED) {
        munmap(ptr, size);
        return;
    }
#endif
    aligned_free_compat(ptr);
}

// ============================================================================
// CPU AFFINITY AND NUMA
// ============================================================================

// Set thread CPU affinity
int set_cpu_affinity(pthread_t thread, int cpu_id) {
#ifdef __linux__
    cpu_set_t cpuset;
    CPU_ZERO(&cpuset);
    CPU_SET(cpu_id, &cpuset);
    return pthread_setaffinity_np(thread, sizeof(cpu_set_t), &cpuset);
#else
    (void)thread;
    (void)cpu_id;
    return -1;
#endif
}

// Set thread to P-cores only
int set_thread_pcore_affinity(pthread_t thread) {
#ifdef __linux__
    cpu_set_t cpuset;
    CPU_ZERO(&cpuset);
    for (uint32_t i = 0; i < g_compat_state.p_core_count && i < 12; i++) {
        CPU_SET(i, &cpuset);
    }
    return pthread_setaffinity_np(thread, sizeof(cpu_set_t), &cpuset);
#else
    (void)thread;
    return -1;
#endif
}

// Set thread to E-cores only
int set_thread_ecore_affinity(pthread_t thread) {
#ifdef __linux__
    cpu_set_t cpuset;
    CPU_ZERO(&cpuset);
    for (uint32_t i = 12; i < 12 + g_compat_state.e_core_count && i < 32; i++) {
        CPU_SET(i, &cpuset);
    }
    return pthread_setaffinity_np(thread, sizeof(cpu_set_t), &cpuset);
#else
    (void)thread;
    return -1;
#endif
}

// Get current CPU
int get_current_cpu(void) {
#ifdef __linux__
    return sched_getcpu();
#else
    return -1;
#endif
}

// ============================================================================
// ATOMIC OPERATIONS COMPATIBILITY
// ============================================================================

// Atomic compare and swap
bool atomic_cas(volatile uint64_t* ptr, uint64_t expected, uint64_t desired) {
    return __atomic_compare_exchange_n(ptr, &expected, desired, false,
                                       __ATOMIC_SEQ_CST, __ATOMIC_SEQ_CST);
}

// Atomic fetch and add
uint64_t atomic_fetch_add_compat(volatile uint64_t* ptr, uint64_t value) {
    return __atomic_fetch_add(ptr, value, __ATOMIC_SEQ_CST);
}

// Memory fence
void memory_fence(void) {
    __atomic_thread_fence(__ATOMIC_SEQ_CST);
}

// ============================================================================
// HIGH-RESOLUTION TIMING
// ============================================================================

// Get high-resolution timestamp
uint64_t get_timestamp_ns(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec * 1000000000UL + ts.tv_nsec;
}

// Get CPU timestamp counter
uint64_t get_tsc(void) {
#ifdef __x86_64__
    uint32_t lo, hi;
    __asm__ __volatile__ ("rdtsc" : "=a" (lo), "=d" (hi));
    return ((uint64_t)hi << 32) | lo;
#else
    return get_timestamp_ns();
#endif
}

// High-resolution sleep
void nanosleep_compat(uint64_t nanoseconds) {
    struct timespec ts;
    ts.tv_sec = nanoseconds / 1000000000;
    ts.tv_nsec = nanoseconds % 1000000000;
    nanosleep(&ts, NULL);
}

// ============================================================================
// SIMD OPERATIONS
// ============================================================================

// Check SIMD capabilities
bool has_avx512(void) {
    return g_compat_state.avx512_available;
}

bool has_avx2(void) {
    return g_compat_state.avx2_available;
}

// Memory copy optimized for architecture
void* memcpy_optimized(void* dest, const void* src, size_t n) {
    if (g_compat_state.avx512_available && n >= 64) {
        // AVX-512 optimized copy for large blocks
        // Would use AVX-512 intrinsics here
        return memcpy(dest, src, n);
    } else if (g_compat_state.avx2_available && n >= 32) {
        // AVX2 optimized copy
        // Would use AVX2 intrinsics here
        return memcpy(dest, src, n);
    } else {
        // Standard memcpy
        return memcpy(dest, src, n);
    }
}

// ============================================================================
// PLATFORM INFO
// ============================================================================

// Get system info structure
system_info_t get_system_info(void) {
    system_info_t info = {0};
    
    info.cpu_count = sysconf(_SC_NPROCESSORS_ONLN);
    info.p_core_count = g_compat_state.p_core_count;
    info.e_core_count = g_compat_state.e_core_count;
    info.page_size = g_compat_state.page_size;
    info.cache_line_size = 64;  // Standard x86_64
    info.has_avx512 = g_compat_state.avx512_available;
    info.has_avx2 = g_compat_state.avx2_available;
    info.has_io_uring = g_compat_state.io_uring_available;
    
    // Get memory info
    long pages = sysconf(_SC_PHYS_PAGES);
    long page_size = sysconf(_SC_PAGE_SIZE);
    info.total_memory = pages * page_size;
    
    long avail_pages = sysconf(_SC_AVPHYS_PAGES);
    info.available_memory = avail_pages * page_size;
    
    return info;
}

// Get CPU temperature (simplified)
double get_cpu_temperature(void) {
    FILE* f = fopen("/sys/class/thermal/thermal_zone0/temp", "r");
    if (!f) return 50.0;  // Default
    
    int temp_millicelsius;
    if (fscanf(f, "%d", &temp_millicelsius) == 1) {
        fclose(f);
        return temp_millicelsius / 1000.0;
    }
    
    fclose(f);
    return 50.0;
}

// ============================================================================
// ERROR HANDLING
// ============================================================================

// Error string helper
const char* compat_error_string(int error) {
    switch (error) {
        case COMPAT_SUCCESS: return "Success";
        case COMPAT_ERROR_INVALID_PARAM: return "Invalid parameter";
        case COMPAT_ERROR_NO_MEMORY: return "Out of memory";
        case COMPAT_ERROR_TIMEOUT: return "Operation timed out";
        case COMPAT_ERROR_NOT_FOUND: return "Not found";
        case COMPAT_ERROR_BUSY: return "Resource busy";
        case COMPAT_ERROR_QUEUE_FULL: return "Queue full";
        case COMPAT_ERROR_IO: return "I/O error";
        case COMPAT_ERROR_NOT_SUPPORTED: return "Not supported";
        case COMPAT_ERROR_THERMAL: return "Thermal throttling";
        default: return "Unknown error";
    }
}