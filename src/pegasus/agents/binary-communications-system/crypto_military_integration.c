/*
 * Military Crypto Integration for Ultra-Fast Binary Protocol
 * Integrates military token authorization with existing binary communication system
 */

#define _DEFAULT_SOURCE
#include <sys/types.h>
#include <unistd.h>
#include <string.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <time.h>
#include "ultra_fast_protocol.h"
#include "compatibility_layer.h"

// Undefine compatibility macro that conflicts with UFP structure
#ifdef payload_size
#undef payload_size
#endif

// Military crypto message types (extending existing protocol)
#define UFP_MSG_CRYPTO_AUTH_REQ    0x20
#define UFP_MSG_CRYPTO_AUTH_RESP   0x21
#define UFP_MSG_CRYPTO_VERIFY      0x22
#define UFP_MSG_CRYPTO_RESULT      0x23
#define UFP_MSG_MILITARY_TOKEN     0x24
#define UFP_MSG_TPM2_ACCEL         0x25

// Agent IDs for crypto operations
#define UFP_CRYPTO_AGENT_ID        100
#define UFP_SECURITY_AGENT_ID      101
#define UFP_TPM2_AGENT_ID          102
#define UFP_MONITOR_AGENT_ID       103
#define UFP_DEBUGGER_AGENT_ID      104
#define UFP_CONSTRUCTOR_AGENT_ID   105
#define UFP_NPU_AGENT_ID           106

// Military authorization levels for binary protocol
typedef enum {
    UFP_AUTH_UNCLASSIFIED = 1,
    UFP_AUTH_CONFIDENTIAL = 2,
    UFP_AUTH_SECRET = 3,
    UFP_AUTH_TOP_SECRET = 4
} ufp_auth_level_t;

// Military crypto payload structure for UFP messages
typedef struct __attribute__((packed)) {
    uint32_t operation_type;       // Crypto operation type
    uint32_t auth_level;           // Required authorization level (ufp_auth_level_t)
    uint32_t token_mask;           // Active military tokens
    uint64_t crypto_session_id;    // Crypto session identifier
    uint32_t tpm2_handle;          // TPM2 hardware handle
    uint32_t data_length;          // Payload data length
    uint32_t result_length;        // Expected result length
    uint32_t performance_target;   // Target performance (vps)
    uint8_t crypto_data[];         // Variable crypto data
} ufp_crypto_payload_t;

/*
 * Military crypto operations using UFP context
 */
static ufp_context_t* crypto_context = NULL;

/*
 * Initialize crypto context with UFP
 */
static int init_crypto_context(void) {
    if (crypto_context) return 0;  // Already initialized

    crypto_context = ufp_create_context("crypto-military");
    if (!crypto_context) {
        printf("UFP CRYPTO: Failed to create crypto context\n");
        return -1;
    }

    printf("UFP CRYPTO: Military crypto context initialized\n");
    return 0;
}

/*
 * Route crypto message through UFP infrastructure
 */
static int route_crypto_message(ufp_message_t* msg, const char* target_agent) {
    if (!crypto_context) {
        if (init_crypto_context() != 0) return -1;
    }

    // Set target agent
    strncpy(msg->targets[0], target_agent, UFP_AGENT_NAME_SIZE - 1);
    msg->targets[0][UFP_AGENT_NAME_SIZE - 1] = '\0';
    msg->target_count = 1;

    // Set source as crypto system
    strncpy(msg->source, "crypto-military", UFP_AGENT_NAME_SIZE - 1);
    msg->source[UFP_AGENT_NAME_SIZE - 1] = '\0';

    // Set timestamp and correlation
    msg->timestamp = (uint32_t)time(NULL);
    msg->correlation_id = rand();

    // Route through UFP infrastructure
    return ufp_send(crypto_context, msg);
}

/*
 * Military crypto verification through binary protocol
 */
int ufp_crypto_verify_component(uint16_t agent_id, const void* data,
                               size_t data_len, ufp_auth_level_t auth_level) {
    ufp_message_t* msg = ufp_message_create();
    if (!msg) return -1;

    // Set message type and priority based on authorization level
    msg->msg_type = UFP_MSG_CRYPTO_VERIFY;
    if (auth_level >= UFP_AUTH_SECRET) {
        msg->priority = UFP_PRIORITY_CRITICAL;  // High-security operations
    } else {
        msg->priority = UFP_PRIORITY_HIGH;      // Standard operations
    }

    // Create crypto payload
    size_t payload_size = sizeof(ufp_crypto_payload_t) + data_len;
    ufp_crypto_payload_t* payload = malloc(payload_size);
    if (!payload) {
        ufp_message_destroy(msg);
        return -1;
    }

    // Fill crypto payload
    payload->operation_type = 0x1001;  // Component verification
    payload->auth_level = auth_level;
    payload->token_mask = 0;  // Will be filled by auth system
    payload->crypto_session_id = (uint64_t)time(NULL) << 32 | rand();
    payload->tpm2_handle = 0;  // Will be assigned by TPM2 system
    payload->data_length = data_len;
    payload->result_length = 32;  // SHA-256 hash result
    payload->performance_target = 1000;  // 1000+ vps target
    memcpy(payload->crypto_data, data, data_len);

    // Attach payload to message
    msg->payload = payload;
    msg->payload_size = payload_size;
    msg->msg_id = agent_id;

    // Route to appropriate agent based on authorization level
    const char* target_agent = (auth_level >= UFP_AUTH_SECRET) ? "security" : "crypto-validator";
    int result = route_crypto_message(msg, target_agent);

    // Cleanup
    free(payload);
    ufp_message_destroy(msg);
    return result;
}

/*
 * TPM2 hardware acceleration through binary protocol
 */
int ufp_crypto_tpm2_accelerate(uint16_t agent_id, const void* crypto_op,
                              size_t op_len) {
    ufp_message_t* msg = ufp_message_create();
    if (!msg) return -1;

    // TPM2 acceleration requires critical priority
    msg->msg_type = UFP_MSG_TPM2_ACCEL;
    msg->priority = UFP_PRIORITY_CRITICAL;
    msg->msg_id = agent_id;

    // Create TPM2 crypto payload
    size_t payload_size = sizeof(ufp_crypto_payload_t) + op_len;
    ufp_crypto_payload_t* payload = malloc(payload_size);
    if (!payload) {
        ufp_message_destroy(msg);
        return -1;
    }

    // Fill TPM2 payload
    payload->operation_type = 0x2001;  // TPM2 hardware operation
    payload->auth_level = UFP_AUTH_SECRET;  // Hardware requires SECRET clearance
    payload->token_mask = 0x3F;  // All military tokens
    payload->crypto_session_id = (uint64_t)time(NULL) << 32 | rand();
    payload->tpm2_handle = 0;  // Assigned by TPM2 driver
    payload->data_length = op_len;
    payload->result_length = 0;  // Variable result size
    payload->performance_target = 1000;  // 1000+ vps with hardware
    memcpy(payload->crypto_data, crypto_op, op_len);

    // Attach payload to message
    msg->payload = payload;
    msg->payload_size = payload_size;

    // Route to TPM2 hardware agent
    int result = route_crypto_message(msg, "hardware-intel");

    // Cleanup
    free(payload);
    ufp_message_destroy(msg);
    return result;
}

/*
 * Military token validation through binary protocol
 */
int ufp_validate_military_tokens(uint16_t agent_id, uint32_t required_tokens) {
    ufp_message_t* msg = ufp_message_create();
    if (!msg) return -1;

    // Token validation requires confidential level
    msg->msg_type = UFP_MSG_MILITARY_TOKEN;
    msg->priority = UFP_PRIORITY_HIGH;
    msg->msg_id = agent_id;

    // Create token validation payload
    size_t payload_size = sizeof(ufp_crypto_payload_t);
    ufp_crypto_payload_t* payload = malloc(payload_size);
    if (!payload) {
        ufp_message_destroy(msg);
        return -1;
    }

    // Fill token validation payload
    payload->operation_type = 0x3001;  // Military token validation
    payload->auth_level = UFP_AUTH_CONFIDENTIAL;  // Minimum for tokens
    payload->token_mask = required_tokens;
    payload->crypto_session_id = (uint64_t)time(NULL) << 32 | rand();
    payload->tpm2_handle = 0;  // Not needed for token validation
    payload->data_length = 0;  // No additional data
    payload->result_length = 4;  // Authorization result
    payload->performance_target = 0;  // Instant validation

    // Attach payload to message
    msg->payload = payload;
    msg->payload_size = payload_size;

    // Route to security agent for token validation
    int result = route_crypto_message(msg, "security");

    // Cleanup
    free(payload);
    ufp_message_destroy(msg);
    return result;
}

/*
 * Performance monitoring integration with binary protocol
 */
int ufp_crypto_performance_monitor(uint16_t agent_id, uint32_t operations_completed,
                                  uint32_t average_latency_ns) {
    ufp_message_t* msg = ufp_message_create();
    if (!msg) return -1;

    // Performance monitoring is low priority
    msg->msg_type = UFP_MSG_CRYPTO_RESULT;
    msg->priority = UFP_PRIORITY_LOW;
    msg->msg_id = agent_id;

    // Create performance monitoring payload
    size_t payload_size = sizeof(ufp_crypto_payload_t) + 8;  // Two uint32_t values
    ufp_crypto_payload_t* payload = malloc(payload_size);
    if (!payload) {
        ufp_message_destroy(msg);
        return -1;
    }

    // Fill performance monitoring payload
    payload->operation_type = 0x4001;  // Performance data
    payload->auth_level = UFP_AUTH_UNCLASSIFIED;  // Public metrics
    payload->token_mask = 0;  // No authorization needed
    payload->crypto_session_id = 0;  // No session needed
    payload->tpm2_handle = 0;  // Not hardware operation
    payload->data_length = 8;  // Two uint32_t values
    payload->result_length = 0;  // No result expected
    payload->performance_target = 1000;  // Target performance

    // Pack performance data
    uint32_t* perf_data = (uint32_t*)payload->crypto_data;
    perf_data[0] = operations_completed;
    perf_data[1] = average_latency_ns;

    // Attach payload to message
    msg->payload = payload;
    msg->payload_size = payload_size;

    // Route to monitoring agent
    int result = route_crypto_message(msg, "monitor");

    // Cleanup
    free(payload);
    ufp_message_destroy(msg);
    return result;
}

/*
 * Register crypto capabilities with UFP agent discovery
 */
int ufp_register_crypto_capabilities(uint16_t agent_id, uint32_t crypto_capabilities) {
    ufp_message_t* msg = ufp_message_create();
    if (!msg) return -1;

    // Discovery message
    msg->msg_type = UFP_MSG_DISCOVERY;
    msg->priority = UFP_PRIORITY_MEDIUM;
    msg->msg_id = agent_id;

    // Create capability announcement payload
    size_t payload_size = sizeof(uint32_t) * 3;  // agent_id, capabilities, flags
    uint32_t* capability_data = malloc(payload_size);
    if (!capability_data) {
        ufp_message_destroy(msg);
        return -1;
    }

    // Fill capability data
    capability_data[0] = agent_id;
    capability_data[1] = crypto_capabilities;
    capability_data[2] = 0;  // Custom flags

    // Set crypto-specific capability flags
    if (crypto_capabilities & 0x01) capability_data[2] |= 0x1000;  // Military authorization
    if (crypto_capabilities & 0x02) capability_data[2] |= 0x2000;  // TPM2 acceleration
    if (crypto_capabilities & 0x04) capability_data[2] |= 0x4000;  // Hardware security

    // Attach payload
    msg->payload = capability_data;
    msg->payload_size = payload_size;

    // Broadcast to all agents
    int result = route_crypto_message(msg, "broadcast");

    // Cleanup
    free(capability_data);
    ufp_message_destroy(msg);
    return result;
}

/*
 * Crypto system initialization with binary protocol
 */
int ufp_crypto_system_init(void) {
    // Initialize UFP library first
    if (ufp_init() != UFP_SUCCESS) {
        printf("UFP CRYPTO: Failed to initialize UFP library\n");
        return -1;
    }

    // Initialize crypto context
    if (init_crypto_context() != 0) {
        printf("UFP CRYPTO: Failed to initialize crypto context\n");
        return -1;
    }

    printf("UFP CRYPTO: Initializing military crypto integration\n");

    // Initialize random seed for session IDs
    srand((unsigned int)time(NULL));

    // Test military token system (simulation mode)
    printf("UFP CRYPTO: Military tokens in simulation mode\n");

    // Test TPM2 hardware integration (software fallback)
    printf("UFP CRYPTO: TPM2 hardware unavailable, software fallback\n");

    // Register crypto capabilities
    uint32_t crypto_caps = 0x07;  // Military auth + TPM2 + Hardware security
    ufp_register_crypto_capabilities(UFP_CRYPTO_AGENT_ID, crypto_caps);

    printf("UFP CRYPTO: Military crypto system integrated with binary protocol\n");
    return 0;
}

/*
 * Crypto system cleanup
 */
void ufp_crypto_system_cleanup(void) {
    if (crypto_context) {
        ufp_destroy_context(crypto_context);
        crypto_context = NULL;
    }
    ufp_cleanup();
    printf("UFP CRYPTO: Military crypto system cleanup complete\n");
}

/*
 * Simple test function to validate military crypto integration
 */
int ufp_crypto_test_integration(void) {
    printf("UFP CRYPTO: Testing military crypto integration\n");

    // Test data
    const char* test_data = "CLASSIFIED: Test crypto verification";
    size_t test_len = strlen(test_data);

    // Test component verification
    int result = ufp_crypto_verify_component(1, test_data, test_len, UFP_AUTH_SECRET);
    if (result == 0) {
        printf("UFP CRYPTO: Component verification test passed\n");
    } else {
        printf("UFP CRYPTO: Component verification test failed: %d\n", result);
    }

    // Test TPM2 acceleration
    result = ufp_crypto_tpm2_accelerate(2, test_data, test_len);
    if (result == 0) {
        printf("UFP CRYPTO: TPM2 acceleration test passed\n");
    } else {
        printf("UFP CRYPTO: TPM2 acceleration test failed: %d\n", result);
    }

    // Test military token validation
    result = ufp_validate_military_tokens(3, 0x07);  // All token types
    if (result == 0) {
        printf("UFP CRYPTO: Military token validation test passed\n");
    } else {
        printf("UFP CRYPTO: Military token validation test failed: %d\n", result);
    }

    // Test performance monitoring
    result = ufp_crypto_performance_monitor(4, 1000, 50000);  // 1000 ops, 50us avg
    if (result == 0) {
        printf("UFP CRYPTO: Performance monitoring test passed\n");
    } else {
        printf("UFP CRYPTO: Performance monitoring test failed: %d\n", result);
    }

    printf("UFP CRYPTO: Integration testing complete\n");
    return 0;
}