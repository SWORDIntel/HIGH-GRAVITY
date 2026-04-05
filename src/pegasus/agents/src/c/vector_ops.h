/*
 * VECTORIZED OPERATIONS HEADER
 * 
 * High-performance vectorized operations with AVX-512/AVX2/SSE2 fallback support
 * - Runtime detection (not CPUID) with signal-based testing
 * - Automatic fallback chain: AVX-512 → AVX2 → SSE2 → scalar
 * - Intel Meteor Lake P-core/E-core awareness
 * - Performance-critical checksum, memcpy, hashing operations
 * 
 * Author: CONSTRUCTOR Agent
 * Version: 1.0 Enhanced
 */

#ifndef VECTOR_OPS_H
#define VECTOR_OPS_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#include <signal.h>
#include <setjmp.h>
#include <immintrin.h>
#include <string.h>

// ============================================================================
// CPU FEATURE DETECTION AND RUNTIME TESTING
// ============================================================================

// CPU capabilities structure
typedef struct {
    bool has_avx512;
    bool has_avx2;
    bool has_sse42;
    bool has_crc32;
    bool is_pcore;       // Intel Meteor Lake P-core (0-11)
    bool is_ecore;       // Intel Meteor Lake E-core (12-21)
    int cpu_id;
    int numa_node;
    bool tested;
} cpu_capabilities_t;

// Vector operation modes
typedef enum {
    VECTOR_MODE_AUTO = 0,
    VECTOR_MODE_AVX512 = 1,
    VECTOR_MODE_AVX2 = 2,
    VECTOR_MODE_SSE2 = 3,
    VECTOR_MODE_SCALAR = 4
} vector_mode_t;

// Global capability cache
extern __thread cpu_capabilities_t g_cpu_caps;
extern __thread bool g_caps_initialized;
extern __thread jmp_buf g_sigill_jmpbuf;
extern __thread volatile bool g_in_test;

// ============================================================================
// RUNTIME CAPABILITY DETECTION WITH SIGNAL HANDLING
// ============================================================================

// Signal handler for illegal instruction detection
void sigill_handler(int sig);

// Safe instruction testing with signal handling
bool test_avx512_safe(void);
bool test_avx2_safe(void);
bool test_sse42_safe(void);

// Initialize CPU capabilities for current thread/core
void init_cpu_capabilities(void);

// Get current CPU capabilities (initializes if needed)
static inline const cpu_capabilities_t* get_cpu_capabilities(void) {
    if (!g_caps_initialized) {
        init_cpu_capabilities();
    }
    return &g_cpu_caps;
}

// Check if current core supports AVX-512 (P-cores only on Meteor Lake)
static inline bool can_use_avx512(void) {
    const cpu_capabilities_t* caps = get_cpu_capabilities();
    return caps->has_avx512 && caps->is_pcore;
}

// Check if current core supports AVX2 (all cores on Meteor Lake)
static inline bool can_use_avx2(void) {
    const cpu_capabilities_t* caps = get_cpu_capabilities();
    return caps->has_avx2;
}

// ============================================================================
// VECTORIZED CHECKSUM OPERATIONS
// ============================================================================

// CRC32C checksum with vectorized fallback
uint32_t vector_crc32c_avx512(const void* data, size_t len, uint32_t initial);
uint32_t vector_crc32c_avx2(const void* data, size_t len, uint32_t initial);
uint32_t vector_crc32c_sse42(const void* data, size_t len, uint32_t initial);
uint32_t vector_crc32c_scalar(const void* data, size_t len, uint32_t initial);

// Auto-selecting CRC32C implementation
static inline uint32_t vector_calculate_checksum(const void* data, size_t len) {
    const cpu_capabilities_t* caps = get_cpu_capabilities();
    
    if (caps->has_avx512 && caps->is_pcore && len >= 64) {
        return vector_crc32c_avx512(data, len, 0xFFFFFFFF);
    } else if (caps->has_avx2 && len >= 32) {
        return vector_crc32c_avx2(data, len, 0xFFFFFFFF);
    } else if (caps->has_sse42 && caps->has_crc32) {
        return vector_crc32c_sse42(data, len, 0xFFFFFFFF);
    } else {
        return vector_crc32c_scalar(data, len, 0xFFFFFFFF);
    }
}

// ============================================================================
// VECTORIZED MEMORY OPERATIONS
// ============================================================================

// High-performance vectorized memcpy variants
void* vector_memcpy_avx512(void* restrict dst, const void* restrict src, size_t n);
void* vector_memcpy_avx2(void* restrict dst, const void* restrict src, size_t n);
void* vector_memcpy_sse2(void* restrict dst, const void* restrict src, size_t n);

// Auto-selecting memcpy implementation
static inline void* vector_memcpy(void* restrict dst, const void* restrict src, size_t n) {
    const cpu_capabilities_t* caps = get_cpu_capabilities();
    
    // Use vectorized copy for larger buffers only
    if (n < 64) {
        return memcpy(dst, src, n);
    }
    
    if (caps->has_avx512 && caps->is_pcore && n >= 512) {
        return vector_memcpy_avx512(dst, src, n);
    } else if (caps->has_avx2 && n >= 256) {
        return vector_memcpy_avx2(dst, src, n);
    } else if (caps->has_sse42 && n >= 128) {
        return vector_memcpy_sse2(dst, src, n);
    } else {
        return memcpy(dst, src, n);
    }
}

// Vectorized memory comparison
int vector_memcmp_avx512(const void* s1, const void* s2, size_t n);
int vector_memcmp_avx2(const void* s1, const void* s2, size_t n);

static inline int vector_memcmp(const void* s1, const void* s2, size_t n) {
    const cpu_capabilities_t* caps = get_cpu_capabilities();
    
    if (n < 32) {
        return memcmp(s1, s2, n);
    }
    
    if (caps->has_avx512 && caps->is_pcore && n >= 64) {
        return vector_memcmp_avx512(s1, s2, n);
    } else if (caps->has_avx2 && n >= 32) {
        return vector_memcmp_avx2(s1, s2, n);
    } else {
        return memcmp(s1, s2, n);
    }
}

// ============================================================================
// VECTORIZED HASHING OPERATIONS
// ============================================================================

// Fast hash computation for topic routing
uint32_t vector_hash_avx512(const void* data, size_t len);
uint32_t vector_hash_avx2(const void* data, size_t len);
uint32_t vector_hash_scalar(const void* data, size_t len);

// Auto-selecting hash function
static inline uint32_t vector_fast_hash(const void* data, size_t len) {
    const cpu_capabilities_t* caps = get_cpu_capabilities();
    
    if (caps->has_avx512 && caps->is_pcore && len >= 64) {
        return vector_hash_avx512(data, len);
    } else if (caps->has_avx2 && len >= 32) {
        return vector_hash_avx2(data, len);
    } else {
        return vector_hash_scalar(data, len);
    }
}

// ============================================================================
// BATCH PROCESSING OPERATIONS
// ============================================================================

// Batch message processing structure
typedef struct {
    void** messages;
    void** payloads;
    uint32_t* sizes;
    uint32_t count;
    uint32_t capacity;
} message_batch_t;

// Vectorized batch checksum computation
void vector_batch_checksums_avx512(message_batch_t* batch, uint32_t* checksums);
void vector_batch_checksums_avx2(message_batch_t* batch, uint32_t* checksums);
void vector_batch_checksums_scalar(message_batch_t* batch, uint32_t* checksums);

// Auto-selecting batch checksum
static inline void vector_batch_checksums(message_batch_t* batch, uint32_t* checksums) {
    const cpu_capabilities_t* caps = get_cpu_capabilities();
    
    if (caps->has_avx512 && caps->is_pcore && batch->count >= 8) {
        vector_batch_checksums_avx512(batch, checksums);
    } else if (caps->has_avx2 && batch->count >= 4) {
        vector_batch_checksums_avx2(batch, checksums);
    } else {
        vector_batch_checksums_scalar(batch, checksums);
    }
}

// Batch message copying with vectorization
void vector_batch_copy_avx512(message_batch_t* src_batch, message_batch_t* dst_batch);
void vector_batch_copy_avx2(message_batch_t* src_batch, message_batch_t* dst_batch);

static inline void vector_batch_copy(message_batch_t* src_batch, message_batch_t* dst_batch) {
    const cpu_capabilities_t* caps = get_cpu_capabilities();
    
    if (caps->has_avx512 && caps->is_pcore) {
        vector_batch_copy_avx512(src_batch, dst_batch);
    } else if (caps->has_avx2) {
        vector_batch_copy_avx2(src_batch, dst_batch);
    } else {
        // Fallback to scalar batch copy
        for (uint32_t i = 0; i < src_batch->count && i < dst_batch->capacity; i++) {
            dst_batch->messages[i] = vector_memcpy(
                dst_batch->messages[i], 
                src_batch->messages[i], 
                src_batch->sizes[i]
            );
            dst_batch->sizes[i] = src_batch->sizes[i];
        }
        dst_batch->count = (src_batch->count < dst_batch->capacity) ? 
                          src_batch->count : dst_batch->capacity;
    }
}

// ============================================================================
// PERFORMANCE MONITORING
// ============================================================================

// Vector operation statistics
typedef struct {
    uint64_t avx512_ops;
    uint64_t avx2_ops;
    uint64_t sse42_ops;
    uint64_t scalar_ops;
    uint64_t total_bytes;
    uint64_t total_time_ns;
    uint32_t mode_switches;
} vector_stats_t;

extern __thread vector_stats_t g_vector_stats;

// Statistics functions
void vector_stats_init(void);
void vector_stats_record_op(vector_mode_t mode, size_t bytes, uint64_t time_ns);
const vector_stats_t* vector_get_stats(void);
void vector_print_stats(void);

// ============================================================================
// UTILITY MACROS
// ============================================================================

// Alignment macros for vectorized operations
#define VECTOR_ALIGN_64 __attribute__((aligned(64)))
#define VECTOR_ALIGN_32 __attribute__((aligned(32)))
#define VECTOR_ALIGN_16 __attribute__((aligned(16)))

// Check if pointer is aligned for vectorized operations
#define IS_ALIGNED(ptr, bytes) (((uintptr_t)(ptr) & ((bytes)-1)) == 0)

// Get optimal vector size for current CPU
static inline size_t get_optimal_vector_size(void) {
    const cpu_capabilities_t* caps = get_cpu_capabilities();
    
    if (caps->has_avx512 && caps->is_pcore) {
        return 64;  // 512 bits
    } else if (caps->has_avx2) {
        return 32;  // 256 bits
    } else {
        return 16;  // 128 bits (SSE)
    }
}

// Prefetch hints for vectorized operations
static inline void vector_prefetch(const void* addr, int rw, int locality) {
    __builtin_prefetch(addr, rw, locality);
}

#endif /* VECTOR_OPS_H */