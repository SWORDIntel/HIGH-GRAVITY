#ifndef METEOR_LAKE_OPTIMIZATIONS_H
#define METEOR_LAKE_OPTIMIZATIONS_H

#include <immintrin.h>
#include <cpuid.h>
#include <sched.h>
#include <numa.h>

// Meteor Lake CPU identification
#define METEOR_LAKE_FAMILY 6
#define METEOR_LAKE_MODEL 0xAA  // Intel Core Ultra (Meteor Lake)

// Core type identification for Meteor Lake
typedef enum {
    CORE_TYPE_P = 0,      // Performance cores (0,2,4,6,8,10)
    CORE_TYPE_E = 1,      // Efficiency cores (12-19)
    CORE_TYPE_LP_E = 2    // Low Power E-cores (20-21)
} meteor_lake_core_type_t;

// P-core IDs for Meteor Lake
static const int METEOR_LAKE_P_CORES[] = {0, 2, 4, 6, 8, 10};
static const int METEOR_LAKE_E_CORES[] = {12, 13, 14, 15, 16, 17, 18, 19};
static const int METEOR_LAKE_LP_E_CORES[] = {20, 21};

// AVX-512 detection for hidden support
static inline int has_hidden_avx512(void) {
    unsigned int eax, ebx, ecx, edx;
    
    // Check CPUID leaf 7, subleaf 0
    __cpuid_count(7, 0, eax, ebx, ecx, edx);
    
    // Check for AVX-512 Foundation (bit 16 in EBX)
    // Even if disabled by microcode, hardware support may exist
    return (ebx & (1 << 16)) != 0;
}

// NPU detection for Meteor Lake
static inline int has_meteor_lake_npu(void) {
    unsigned int eax, ebx, ecx, edx;
    
    // Check extended CPUID for NPU presence
    __cpuid(0x80000000, eax, ebx, ecx, edx);
    if (eax >= 0x80000008) {
        __cpuid(0x80000008, eax, ebx, ecx, edx);
        // NPU capabilities in ECX bits (Intel-specific)
        return (ecx & (1 << 8)) != 0;
    }
    return 0;
}

// Set thread affinity to specific core type
static inline int set_core_affinity(meteor_lake_core_type_t core_type, int core_index) {
    cpu_set_t cpuset;
    CPU_ZERO(&cpuset);
    
    switch (core_type) {
        case CORE_TYPE_P:
            if (core_index < 6) {
                CPU_SET(METEOR_LAKE_P_CORES[core_index], &cpuset);
            }
            break;
        case CORE_TYPE_E:
            if (core_index < 8) {
                CPU_SET(METEOR_LAKE_E_CORES[core_index], &cpuset);
            }
            break;
        case CORE_TYPE_LP_E:
            if (core_index < 2) {
                CPU_SET(METEOR_LAKE_LP_E_CORES[core_index], &cpuset);
            }
            break;
    }
    
    return sched_setaffinity(0, sizeof(cpu_set_t), &cpuset);
}

// Memory allocation optimized for Meteor Lake NUMA
static inline void* meteor_lake_numa_alloc(size_t size, int prefer_p_cores) {
    if (numa_available() >= 0) {
        // Allocate on NUMA node closest to P-cores for performance
        int node = prefer_p_cores ? 0 : -1;
        return numa_alloc_onnode(size, node);
    }
    
    // Fallback to aligned allocation
    return aligned_alloc(64, (size + 63) & ~63);
}

// AVX-512 optimized memory copy (if hidden AVX-512 available)
static inline void meteor_lake_memcpy_avx512(void* dst, const void* src, size_t size) {
    if (has_hidden_avx512() && size >= 64) {
        const char* s = (const char*)src;
        char* d = (char*)dst;
        size_t chunks = size / 64;
        
        for (size_t i = 0; i < chunks; i++) {
            __m512i data = _mm512_load_si512((const __m512i*)(s + i * 64));
            _mm512_store_si512((__m512i*)(d + i * 64), data);
        }
        
        // Handle remainder
        size_t remainder = size % 64;
        if (remainder) {
            memcpy(d + chunks * 64, s + chunks * 64, remainder);
        }
    } else {
        memcpy(dst, src, size);
    }
}

// High-performance spinlock optimized for Meteor Lake
typedef struct {
    volatile int lock;
    int padding[15];  // Avoid false sharing (64-byte cacheline)
} meteor_lake_spinlock_t;

static inline void meteor_lake_spinlock_init(meteor_lake_spinlock_t* lock) {
    lock->lock = 0;
}

static inline void meteor_lake_spinlock_lock(meteor_lake_spinlock_t* lock) {
    while (__atomic_exchange_n(&lock->lock, 1, __ATOMIC_ACQUIRE)) {
        // Use PAUSE instruction to be friendly to SMT
        __builtin_ia32_pause();
    }
}

static inline void meteor_lake_spinlock_unlock(meteor_lake_spinlock_t* lock) {
    __atomic_store_n(&lock->lock, 0, __ATOMIC_RELEASE);
}

// Thermal monitoring for Meteor Lake
static inline int get_meteor_lake_thermal_status(void) {
    unsigned int eax, edx;
    
    // Read IA32_THERM_STATUS MSR (0x19C)
    // This requires elevated privileges
    __asm__ volatile ("rdmsr" : "=a"(eax), "=d"(edx) : "c"(0x19C));
    
    // Extract thermal status bits
    return (eax >> 16) & 0x7F;  // Temperature in Celsius offset
}

#endif // METEOR_LAKE_OPTIMIZATIONS_H
