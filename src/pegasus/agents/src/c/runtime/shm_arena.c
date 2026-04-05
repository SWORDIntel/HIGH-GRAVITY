#define _GNU_SOURCE
#include <sys/mman.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>
#include <string.h>
#include <stdio.h>
#include <stdlib.h>
#include <errno.h>
#include <stdatomic.h>
#include "module_interface.h"

#define ARENA_SIZE (256 * 1024 * 1024)  // 256MB
#define RING_BUFFER_SIZE (16 * 1024 * 1024)  // 16MB per ring
#define MAX_RINGS 16
#define HUGE_PAGE_SIZE (2 * 1024 * 1024)  // 2MB

typedef struct {
    atomic_uint_fast64_t head;
    atomic_uint_fast64_t tail;
    uint32_t size;
    uint32_t mask;
    uint8_t padding[48];
} ring_header_t __attribute__((aligned(64)));

typedef struct {
    void* base_addr;
    size_t total_size;
    int shm_fd;
    
    // Ring buffer management
    ring_header_t* rings[MAX_RINGS];
    void* ring_data[MAX_RINGS];
    atomic_int ring_count;
    
    // Memory allocation
    atomic_size_t allocated;
    void* free_list_head;
    
    // Statistics
    atomic_uint_fast64_t messages_passed;
    atomic_uint_fast64_t bytes_transferred;
} shm_arena_t;

static shm_arena_t g_arena = {0};

int shm_arena_init(const char* name, size_t size) {
    if (size == 0) size = ARENA_SIZE;
    
    // Align to huge page boundary
    size = (size + HUGE_PAGE_SIZE - 1) & ~(HUGE_PAGE_SIZE - 1);
    
    // Create shared memory
    char shm_name[256];
    snprintf(shm_name, sizeof(shm_name), "/claude_arena_%s_%d", name, getpid());
    
    shm_unlink(shm_name);  // Clean up any previous instance
    
    g_arena.shm_fd = shm_open(shm_name, O_CREAT | O_EXCL | O_RDWR, 0600);
    if (g_arena.shm_fd < 0) {
        perror("shm_open");
        return -1;
    }
    
    if (ftruncate(g_arena.shm_fd, size) < 0) {
        perror("ftruncate");
        close(g_arena.shm_fd);
        shm_unlink(shm_name);
        return -1;
    }
    
    // Direct mapping without huge pages (microcode 0x24 restriction)
    g_arena.base_addr = mmap(NULL, size,
                             PROT_READ | PROT_WRITE,
                             MAP_SHARED | MAP_POPULATE,
                             g_arena.shm_fd, 0);
    
    if (g_arena.base_addr == MAP_FAILED) {
        perror("mmap");
        close(g_arena.shm_fd);
        shm_unlink(shm_name);
        return -1;
    }
    
    // Lock pages in memory
    if (mlock(g_arena.base_addr, size) < 0) {
        // Non-fatal, just a performance optimization
    }
    
    g_arena.total_size = size;
    atomic_store(&g_arena.allocated, 0);
    atomic_store(&g_arena.ring_count, 0);
    
    // Initialize first ring buffer
    shm_ring_create(0, RING_BUFFER_SIZE);
    
    return 0;
}

int shm_ring_create(uint32_t ring_id, size_t size) {
    if (ring_id >= MAX_RINGS) return -1;
    
    int current_count = atomic_load(&g_arena.ring_count);
    if (ring_id >= current_count) {
        atomic_store(&g_arena.ring_count, ring_id + 1);
    }
    
    // Allocate ring header and data
    size_t offset = atomic_fetch_add(&g_arena.allocated, sizeof(ring_header_t) + size);
    if (offset + sizeof(ring_header_t) + size > g_arena.total_size) {
        return -1;  // Out of arena space
    }
    
    ring_header_t* header = (ring_header_t*)((uint8_t*)g_arena.base_addr + offset);
    void* data = (uint8_t*)header + sizeof(ring_header_t);
    
    // Initialize ring
    atomic_store(&header->head, 0);
    atomic_store(&header->tail, 0);
    header->size = size;
    header->mask = size - 1;  // Assumes power of 2
    
    g_arena.rings[ring_id] = header;
    g_arena.ring_data[ring_id] = data;
    
    return 0;
}

int shm_ring_enqueue(uint32_t ring_id, const void* data, size_t len) {
    if (ring_id >= atomic_load(&g_arena.ring_count)) return -1;
    
    ring_header_t* ring = g_arena.rings[ring_id];
    if (!ring) return -1;
    
    // Fast path: try to reserve space
    uint64_t head = atomic_load_explicit(&ring->head, memory_order_acquire);
    uint64_t tail = atomic_load_explicit(&ring->tail, memory_order_relaxed);
    
    if (head - tail >= ring->size - len) {
        return -1;  // Ring full
    }
    
    // Reserve space atomically
    uint64_t write_pos = atomic_fetch_add_explicit(&ring->head, len, memory_order_acq_rel);
    
    // Copy data (may wrap around)
    uint8_t* ring_data = (uint8_t*)g_arena.ring_data[ring_id];
    uint32_t offset = write_pos & ring->mask;
    
    if (offset + len <= ring->size) {
        // No wrap
        memcpy(ring_data + offset, data, len);
    } else {
        // Handle wrap
        size_t first_part = ring->size - offset;
        memcpy(ring_data + offset, data, first_part);
        memcpy(ring_data, (uint8_t*)data + first_part, len - first_part);
    }
    
    // Update statistics
    atomic_fetch_add(&g_arena.messages_passed, 1);
    atomic_fetch_add(&g_arena.bytes_transferred, len);
    
    return 0;
}

int shm_ring_dequeue(uint32_t ring_id, void* data, size_t max_len, size_t* actual_len) {
    if (ring_id >= atomic_load(&g_arena.ring_count)) return -1;
    
    ring_header_t* ring = g_arena.rings[ring_id];
    if (!ring) return -1;
    
    uint64_t head = atomic_load_explicit(&ring->head, memory_order_relaxed);
    uint64_t tail = atomic_load_explicit(&ring->tail, memory_order_acquire);
    
    if (head == tail) {
        return -1;  // Ring empty
    }
    
    // Peek at message header to get actual size
    uint8_t* ring_data = (uint8_t*)g_arena.ring_data[ring_id];
    uint32_t offset = tail & ring->mask;
    
    shm_msg_header_t* msg = (shm_msg_header_t*)(ring_data + offset);
    size_t msg_size = sizeof(shm_msg_header_t) + msg->payload_len;
    
    if (msg_size > max_len) {
        *actual_len = msg_size;
        return -2;  // Buffer too small
    }
    
    // Copy message (may wrap around)
    if (offset + msg_size <= ring->size) {
        memcpy(data, ring_data + offset, msg_size);
    } else {
        size_t first_part = ring->size - offset;
        memcpy(data, ring_data + offset, first_part);
        memcpy((uint8_t*)data + first_part, ring_data, msg_size - first_part);
    }
    
    // Advance tail
    atomic_store_explicit(&ring->tail, tail + msg_size, memory_order_release);
    
    *actual_len = msg_size;
    return 0;
}

void shm_arena_stats(uint64_t* messages, uint64_t* bytes) {
    if (messages) *messages = atomic_load(&g_arena.messages_passed);
    if (bytes) *bytes = atomic_load(&g_arena.bytes_transferred);
}

void shm_arena_cleanup(void) {
    if (g_arena.base_addr && g_arena.base_addr != MAP_FAILED) {
        munmap(g_arena.base_addr, g_arena.total_size);
    }
    if (g_arena.shm_fd >= 0) {
        close(g_arena.shm_fd);
    }
    memset(&g_arena, 0, sizeof(g_arena));
}