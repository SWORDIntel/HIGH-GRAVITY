/*
 * SIMPLIFIED VECTORIZED OPERATIONS HEADER
 * 
 * Simplified version for compatibility with systems without AVX-512
 * Focuses on AVX2/SSE2 fallback with runtime detection
 * 
 * Author: CONSTRUCTOR Agent
 * Version: 1.0 Simplified
 */

#ifndef VECTOR_OPS_SIMPLE_H
#define VECTOR_OPS_SIMPLE_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#include <immintrin.h>
#include <string.h>

// ============================================================================
// SIMPLIFIED CPU CAPABILITIES
// ============================================================================

typedef struct {
    bool has_avx2;
    bool has_sse42;
    bool has_crc32;
    int cpu_id;
    bool tested;
} simple_cpu_caps_t;

extern __thread simple_cpu_caps_t g_simple_caps;
extern __thread bool g_simple_caps_init;

// Initialize capabilities (simplified - no signal handling for now)
void simple_init_caps(void);

// ============================================================================
// SIMPLIFIED VECTORIZED OPERATIONS
// ============================================================================

// CRC32 with hardware acceleration when available
static inline uint32_t simple_crc32c(const void* data, size_t len, uint32_t crc) {
    if (!g_simple_caps_init) {
        simple_init_caps();
    }
    
    const uint8_t* bytes = (const uint8_t*)data;
    
#ifdef __SSE4_2__
    if (g_simple_caps.has_crc32) {
        // Use hardware CRC32
        for (size_t i = 0; i < len; i++) {
            crc = _mm_crc32_u8(crc, bytes[i]);
        }
        return crc;
    }
#endif
    
    // Software fallback
    for (size_t i = 0; i < len; i++) {
        crc ^= bytes[i];
        for (int j = 0; j < 8; j++) {
            crc = (crc >> 1) ^ ((crc & 1) ? 0x82F63B78 : 0);
        }
    }
    return crc;
}

// Enhanced checksum calculation
static inline uint32_t simple_calculate_checksum(const void* data, size_t len) {
    return simple_crc32c(data, len, 0xFFFFFFFF);
}

// Enhanced hash function (djb2)
static inline uint32_t simple_fast_hash(const void* data, size_t len) {
    const uint8_t* bytes = (const uint8_t*)data;
    uint32_t hash = 5381;
    
    for (size_t i = 0; i < len; i++) {
        hash = hash * 33 + bytes[i];
    }
    
    return hash;
}

// Enhanced memcpy (uses standard memcpy for now)
static inline void* simple_memcpy(void* restrict dst, const void* restrict src, size_t n) {
    return memcpy(dst, src, n);
}

#endif /* VECTOR_OPS_SIMPLE_H */