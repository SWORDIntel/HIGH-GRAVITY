/*
 * AI-ENHANCED ROUTING SYSTEM HEADER
 * 
 * Header file for AI-enhanced routing with NPU integration
 * for the Claude Agent Communication System
 * 
 * Author: ML-OPS Agent
 * Version: 1.0 Production
 */

#ifndef AI_ENHANCED_ROUTER_H
#define AI_ENHANCED_ROUTER_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

// ============================================================================
// INCLUDES AND FORWARD DECLARATIONS
// ============================================================================

// Include main protocol header and compatibility layer
#include "compatibility_layer.h"
#include "agent_protocol.h"

// ============================================================================
// AI ROUTING TYPES
// ============================================================================

// AI routing strategies
typedef enum {
    ROUTE_STRATEGY_MANUAL = 0,
    ROUTE_STRATEGY_LOAD_BALANCED = 1,
    ROUTE_STRATEGY_LATENCY_OPTIMAL = 2,
    ROUTE_STRATEGY_SEMANTIC_SIMILARITY = 3,
    ROUTE_STRATEGY_ML_PREDICTED = 4,
    ROUTE_STRATEGY_ADAPTIVE = 5
} ai_routing_strategy_t;

// Model types for different routing decisions
typedef enum {
    MODEL_TYPE_LOAD_PREDICTOR = 1,
    MODEL_TYPE_LATENCY_ESTIMATOR = 2,
    MODEL_TYPE_ANOMALY_DETECTOR = 3,
    MODEL_TYPE_SEMANTIC_ROUTER = 4,
    MODEL_TYPE_PATTERN_CLASSIFIER = 5,
    MODEL_TYPE_CAPACITY_PLANNER = 6
} ai_model_type_t;

// Hardware accelerator types
typedef enum {
    ACCEL_TYPE_CPU = 0,
    ACCEL_TYPE_NPU = 1,
    ACCEL_TYPE_GNA = 2,
    ACCEL_TYPE_GPU = 3,
    ACCEL_TYPE_VECTOR_DB = 4
} accelerator_type_t;

// Routing decision from AI models
typedef struct {
    uint32_t recommended_target;
    float confidence_score;
    ai_routing_strategy_t strategy_used;
    accelerator_type_t accelerator_used;
    
    // Prediction metadata
    float expected_latency_ms;
    float expected_success_rate;
    float load_impact_score;
    bool anomaly_detected;
    
    uint64_t decision_time_ns;
    uint32_t model_version;
} ai_routing_decision_t;

// Performance prediction for adaptive scaling
typedef struct {
    uint64_t timestamp_ns;
    float predicted_load;
    float predicted_latency;
    uint32_t recommended_replicas;
    float confidence;
    
    // Resource recommendations
    bool scale_up_npu;
    bool scale_up_gpu;
    uint32_t additional_threads;
} performance_prediction_t;

// ============================================================================
// CORE API FUNCTIONS
// ============================================================================

/**
 * Initialize the AI-enhanced routing service
 * @return 0 on success, negative error code on failure
 */
int ai_router_service_init(void);

/**
 * Cleanup the AI-enhanced routing service
 */
void ai_router_service_cleanup(void);

/**
 * Route a message using AI-enhanced routing
 * @param msg Message header
 * @param payload Message payload (optional)
 * @return Recommended target agent ID
 */
uint32_t ai_route_message(const enhanced_msg_header_t* msg, const void* payload);

/**
 * Get detailed routing decision with metadata
 * @param msg Message header
 * @param payload Message payload (optional)
 * @return Full routing decision with confidence and metadata
 */
ai_routing_decision_t ai_get_routing_decision(const enhanced_msg_header_t* msg, const void* payload);

/**
 * Get performance prediction for system scaling
 * @param horizon_ms Prediction horizon in milliseconds
 * @return Performance prediction with scaling recommendations
 */
performance_prediction_t ai_get_performance_prediction(uint64_t horizon_ms);

/**
 * Load a routing model for AI-assisted decisions
 * @param model_path Path to model file (ONNX, OpenVINO IR, etc.)
 * @param model_type Type of routing model
 * @return 0 on success, negative error code on failure
 */
int ai_load_routing_model(const char* model_path, ai_model_type_t model_type);

/**
 * Get routing statistics
 * @param total_decisions Output: total routing decisions made
 * @param ai_decisions Output: AI-assisted decisions made
 * @param anomalies Output: number of anomalies detected
 * @param avg_latency_ns Output: average decision latency in nanoseconds
 */
void ai_get_routing_stats(uint64_t* total_decisions, 
                         uint64_t* ai_decisions, 
                         uint64_t* anomalies, 
                         uint64_t* avg_latency_ns);

/**
 * Print comprehensive routing statistics
 */
void ai_print_routing_stats(void);

// ============================================================================
// ADVANCED FEATURES
// ============================================================================

/**
 * Update routing model with new training data
 * @param model_type Type of model to update
 * @param training_data Training data buffer
 * @param data_size Size of training data
 * @return 0 on success, negative error code on failure
 */
int ai_update_model_online(ai_model_type_t model_type, 
                          const void* training_data, 
                          size_t data_size);

/**
 * Set anomaly detection threshold
 * @param threshold Anomaly detection threshold (0.0 - 1.0)
 * @return 0 on success, negative error code on failure
 */
int ai_set_anomaly_threshold(float threshold);

/**
 * Set prediction confidence threshold
 * @param threshold Minimum confidence for AI-assisted routing (0.0 - 1.0)
 * @return 0 on success, negative error code on failure
 */
int ai_set_confidence_threshold(float threshold);

/**
 * Enable/disable hardware accelerator
 * @param accel_type Accelerator type
 * @param enable True to enable, false to disable
 * @return 0 on success, negative error code on failure
 */
int ai_set_accelerator_enabled(accelerator_type_t accel_type, bool enable);

/**
 * Get accelerator utilization
 * @param accel_type Accelerator type
 * @return Utilization percentage (0.0 - 1.0), or negative on error
 */
float ai_get_accelerator_utilization(accelerator_type_t accel_type);

/**
 * Perform accelerator health check
 * @param accel_type Accelerator type
 * @return True if healthy, false otherwise
 */
bool ai_check_accelerator_health(accelerator_type_t accel_type);

// ============================================================================
// VECTOR DATABASE API
// ============================================================================

/**
 * Add message pattern to vector database
 * @param message_id Message identifier
 * @param features Feature vector
 * @param dimensions Number of dimensions
 * @return 0 on success, negative error code on failure
 */
int ai_vector_db_add_pattern(uint32_t message_id, 
                            const float* features, 
                            size_t dimensions);

/**
 * Find similar messages in vector database
 * @param query_features Query feature vector
 * @param dimensions Number of dimensions
 * @param max_results Maximum number of results to return
 * @param results Output array for similar message IDs
 * @param similarities Output array for similarity scores
 * @return Number of results found
 */
size_t ai_vector_db_find_similar(const float* query_features,
                                size_t dimensions,
                                size_t max_results,
                                uint32_t* results,
                                float* similarities);

/**
 * Clear vector database
 * @return 0 on success, negative error code on failure
 */
int ai_vector_db_clear(void);

// ============================================================================
// BATCH PROCESSING API
// ============================================================================

/**
 * Process batch of messages for routing decisions
 * @param messages Array of message headers
 * @param payloads Array of message payloads (can be NULL)
 * @param count Number of messages in batch
 * @param decisions Output array for routing decisions
 * @return Number of messages successfully processed
 */
size_t ai_route_message_batch(const enhanced_msg_header_t** messages,
                             const void** payloads,
                             size_t count,
                             ai_routing_decision_t* decisions);

/**
 * Process batch with specific accelerator
 * @param messages Array of message headers
 * @param payloads Array of message payloads (can be NULL)
 * @param count Number of messages in batch
 * @param accel_type Preferred accelerator type
 * @param decisions Output array for routing decisions
 * @return Number of messages successfully processed
 */
size_t ai_route_batch_with_accelerator(const enhanced_msg_header_t** messages,
                                      const void** payloads,
                                      size_t count,
                                      accelerator_type_t accel_type,
                                      ai_routing_decision_t* decisions);

// ============================================================================
// MONITORING AND ALERTS
// ============================================================================

/**
 * Callback for routing alerts
 * @param alert_type Type of alert
 * @param message Alert message
 * @param data Additional alert data
 * @param user_data User-provided context
 */
typedef void (*ai_routing_alert_callback_t)(int alert_type,
                                           const char* message,
                                           const void* data,
                                           void* user_data);

/**
 * Register callback for routing alerts
 * @param callback Callback function
 * @param user_data User data for callback
 * @return 0 on success, negative error code on failure
 */
int ai_register_alert_callback(ai_routing_alert_callback_t callback, void* user_data);

/**
 * Set performance monitoring thresholds
 * @param max_latency_ns Maximum acceptable decision latency
 * @param min_confidence Minimum acceptable confidence score
 * @param max_anomaly_rate Maximum acceptable anomaly rate
 * @return 0 on success, negative error code on failure
 */
int ai_set_monitoring_thresholds(uint64_t max_latency_ns,
                                float min_confidence,
                                float max_anomaly_rate);

// ============================================================================
// CONFIGURATION AND TUNING
// ============================================================================

/**
 * Set routing configuration parameters
 * @param param_name Parameter name
 * @param value Parameter value
 * @return 0 on success, negative error code on failure
 */
int ai_set_config_parameter(const char* param_name, const void* value);

/**
 * Get routing configuration parameter
 * @param param_name Parameter name
 * @param value Output buffer for parameter value
 * @param value_size Size of output buffer
 * @return 0 on success, negative error code on failure
 */
int ai_get_config_parameter(const char* param_name, void* value, size_t value_size);

/**
 * Load configuration from file
 * @param config_file Path to configuration file
 * @return 0 on success, negative error code on failure
 */
int ai_load_config_file(const char* config_file);

/**
 * Save current configuration to file
 * @param config_file Path to configuration file
 * @return 0 on success, negative error code on failure
 */
int ai_save_config_file(const char* config_file);

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

/**
 * Convert routing strategy to string
 * @param strategy Routing strategy
 * @return String representation
 */
const char* ai_routing_strategy_string(ai_routing_strategy_t strategy);

/**
 * Convert model type to string
 * @param model_type Model type
 * @return String representation
 */
const char* ai_model_type_string(ai_model_type_t model_type);

/**
 * Convert accelerator type to string
 * @param accel_type Accelerator type
 * @return String representation
 */
const char* ai_accelerator_type_string(accelerator_type_t accel_type);

/**
 * Get AI router version
 * @param major Output: major version
 * @param minor Output: minor version
 * @param patch Output: patch version
 */
void ai_get_version(int* major, int* minor, int* patch);

/**
 * Check if AI router is initialized
 * @return True if initialized, false otherwise
 */
bool ai_is_initialized(void);

/**
 * Get current timestamp in nanoseconds
 * @return Current timestamp
 */
uint64_t ai_get_timestamp_ns(void);

// ============================================================================
// INTEGRATION SERVICE API (from ai_router_integration.c)
// ============================================================================

// For integration with existing transport layer
typedef uint32_t raft_node_id_t;

/**
 * Initialize AI integration service
 * @param local_node_id Local node identifier for distributed coordination
 * @return 0 on success, negative error code on failure
 */
int ai_integration_service_init(raft_node_id_t local_node_id);

/**
 * Cleanup AI integration service
 */
void ai_integration_service_cleanup(void);

/**
 * Enable/disable AI routing in integration layer
 * @param enabled True to enable, false to disable
 * @return 0 on success, negative error code on failure
 */
int ai_integration_set_ai_routing_enabled(bool enabled);

/**
 * Set fallback routing function
 * @param route_func Original routing function for fallback
 * @return 0 on success, negative error code on failure
 */
int ai_integration_set_fallback_router(uint32_t (*route_func)(const enhanced_msg_header_t*, const void*));

/**
 * Get integrated routing function
 * @return Function pointer for integrated routing
 */
uint32_t (*ai_integration_get_router(void))(const enhanced_msg_header_t*, const void*);

/**
 * Get integration statistics
 * @param total_messages Output: total messages processed
 * @param ai_routed Output: messages routed by AI
 * @param traditional_routed Output: messages routed traditionally
 * @param current_load Output: current system load
 * @param ai_confidence Output: current AI confidence level
 */
void ai_integration_get_stats(uint64_t* total_messages,
                             uint64_t* ai_routed,
                             uint64_t* traditional_routed,
                             float* current_load,
                             float* ai_confidence);

/**
 * Print integration statistics
 */
void ai_integration_print_stats(void);

/**
 * Get current adaptive thresholds
 * @param confidence_threshold Output: confidence threshold
 * @param load_threshold Output: load threshold
 * @param latency_threshold_ns Output: latency threshold in nanoseconds
 */
void ai_integration_get_thresholds(float* confidence_threshold,
                                  float* load_threshold,
                                  uint64_t* latency_threshold_ns);

/**
 * Update adaptive thresholds
 * @param confidence_threshold New confidence threshold
 * @param load_threshold New load threshold
 * @param latency_threshold_ns New latency threshold
 * @return 0 on success, negative error code on failure
 */
int ai_integration_update_thresholds(float confidence_threshold,
                                    float load_threshold,
                                    uint64_t latency_threshold_ns);

// ============================================================================
// ERROR CODES
// ============================================================================

#define AI_ROUTER_SUCCESS           0
#define AI_ROUTER_ERROR_INVALID     -1
#define AI_ROUTER_ERROR_MEMORY      -2
#define AI_ROUTER_ERROR_NOT_INIT    -3
#define AI_ROUTER_ERROR_NOT_FOUND   -4
#define AI_ROUTER_ERROR_CAPACITY    -5
#define AI_ROUTER_ERROR_HARDWARE    -6
#define AI_ROUTER_ERROR_MODEL       -7
#define AI_ROUTER_ERROR_CONFIG      -8
#define AI_ROUTER_ERROR_IO          -9
#define AI_ROUTER_ERROR_TIMEOUT     -10

// Additional error codes
#define EALREADY                    114  // Operation already in progress
#define ENOSPC                      28   // No space left on device
#define EINVAL                      22   // Invalid argument
#define ENOMEM                      12   // Out of memory

#ifdef __cplusplus
}
#endif

#endif // AI_ENHANCED_ROUTER_H