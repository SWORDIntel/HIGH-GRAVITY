/*
 * ENHANCED VECTOR ROUTER C FFI HEADER
 * 
 * C header for integrating the enhanced Rust vector router with the 
 * Claude Agent Communication System binary protocol.
 * 
 * Features:
 * - Meteor Lake hardware optimization
 * - HNSW indexing for O(log N) search performance
 * - AVX-512/AVX2 SIMD acceleration
 * - Memory-mapped persistent storage
 * - Multiple similarity metrics
 * - Real-time performance metrics
 * 
 * Author: ML-OPS Agent (Enhanced FFI)
 * Version: 2.0 Production
 */

#ifndef VECTOR_ROUTER_H
#define VECTOR_ROUTER_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

// ============================================================================
// TYPE DEFINITIONS
// ============================================================================

/// Opaque handle to the vector router database
typedef struct VectorRouterHandle VectorRouterHandle;

/// C-compatible search result structure
typedef struct {
    uint8_t id[16];        // UUID as 16 bytes
    float similarity;      // Similarity score (0.0 - 1.0)
    const char* metadata;  // Optional metadata (can be NULL)
} CSearchResult;

/// C-compatible search results array
typedef struct {
    CSearchResult* results;  // Array of results
    size_t count;           // Number of results
    size_t capacity;        // Allocated capacity
} CSearchResults;

// ============================================================================
// CORE API FUNCTIONS
// ============================================================================

/**
 * Initialize the enhanced vector router system
 * 
 * @param storage_path Path to storage directory for persistent vectors
 * @param vector_dimension Dimension of vectors to store (e.g., 128, 384, 768)
 * @return Handle to vector router or NULL on failure
 */
VectorRouterHandle* vector_router_create(const char* storage_path, size_t vector_dimension);

/**
 * Insert a vector into the database
 * 
 * @param handle Vector router handle
 * @param vector_data Float array containing vector data
 * @param vector_dimension Number of dimensions in vector
 * @param metadata Optional metadata string (can be NULL)
 * @return true on success, false on failure
 */
bool vector_router_insert(
    VectorRouterHandle* handle,
    const float* vector_data,
    size_t vector_dimension,
    const char* metadata
);

/**
 * Search for k most similar vectors
 * 
 * Uses HNSW indexing with automatic P-core/E-core optimization
 * and AVX-512/AVX2 SIMD acceleration.
 * 
 * @param handle Vector router handle
 * @param query_vector Query vector to search for
 * @param vector_dimension Number of dimensions in query vector
 * @param k Number of results to return
 * @return Search results (must be freed with vector_router_free_results)
 */
CSearchResults vector_router_search(
    VectorRouterHandle* handle,
    const float* query_vector,
    size_t vector_dimension,
    size_t k
);

/**
 * Free memory allocated for search results
 * 
 * @param results Results returned from vector_router_search
 */
void vector_router_free_results(CSearchResults results);

// ============================================================================
// PERFORMANCE MONITORING
// ============================================================================

/**
 * Get performance metrics from the vector router
 * 
 * @param handle Vector router handle
 * @param searches_total Total number of searches performed (can be NULL)
 * @param searches_p_core Searches executed on P-cores (can be NULL)
 * @param searches_e_core Searches executed on E-cores (can be NULL)
 * @param avg_latency_us Average search latency in microseconds (can be NULL)
 * @return true on success, false on failure
 */
bool vector_router_get_metrics(
    VectorRouterHandle* handle,
    uint64_t* searches_total,
    uint64_t* searches_p_core,
    uint64_t* searches_e_core,
    uint64_t* avg_latency_us
);

// ============================================================================
// LIFECYCLE MANAGEMENT
// ============================================================================

/**
 * Shutdown and cleanup the vector router
 * 
 * @param handle Vector router handle to destroy
 */
void vector_router_destroy(VectorRouterHandle* handle);

/**
 * Get version information
 * 
 * @return Version string (static, do not free)
 */
const char* vector_router_version(void);

// ============================================================================
// INTEGRATION HELPER MACROS
// ============================================================================

/// Check if vector router is available at runtime
#define VECTOR_ROUTER_AVAILABLE() (vector_router_version() != NULL)

/// Default vector dimensions for common embedding models
#define VECTOR_DIM_OPENAI_ADA2    1536
#define VECTOR_DIM_SENTENCE_BERT  384
#define VECTOR_DIM_CLIP           512
#define VECTOR_DIM_CUSTOM_128     128

/// Performance targets for Meteor Lake hardware
#define EXPECTED_LATENCY_P_CORE_US  50   // P-core search latency target
#define EXPECTED_LATENCY_E_CORE_US  150  // E-core search latency target
#define EXPECTED_THROUGHPUT_QPS     2000 // Queries per second target

#ifdef __cplusplus
}
#endif

#endif // VECTOR_ROUTER_H