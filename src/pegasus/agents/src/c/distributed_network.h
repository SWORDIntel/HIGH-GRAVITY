/*
 * DISTRIBUTED NETWORKING AND CONSENSUS LAYER
 * 
 * Production-grade distributed networking system for the Claude Agent Communication System
 * - Raft consensus algorithm for distributed coordination
 * - Multi-node service discovery with failure detection
 * - Network partition handling and split-brain prevention
 * - Load balancing across distributed agent instances
 * - Failover and recovery mechanisms with automatic healing
 * - Mutual TLS security with certificate rotation
 * - High-throughput networking (4.2M+ msg/sec target)
 * - NUMA-aware, CPU-optimized implementation
 * 
 * Author: Agent Communication System
 * Version: 1.0 Distributed
 */

#ifndef DISTRIBUTED_NETWORK_H
#define DISTRIBUTED_NETWORK_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#include <pthread.h>
#include <netinet/in.h>
#include <openssl/ssl.h>
#include <openssl/x509.h>

#ifdef __cplusplus
extern "C" {
#endif

// ============================================================================
// SYSTEM CONSTANTS AND LIMITS
// ============================================================================

#define DIST_NET_VERSION_MAJOR 1
#define DIST_NET_VERSION_MINOR 0
#define DIST_NET_VERSION_PATCH 0

// Network configuration
#define MAX_CLUSTER_NODES 64
#define MAX_NODE_NAME 64
#define MAX_ENDPOINTS_PER_NODE 8
#define MAX_CERTIFICATES 16
#define MAX_TLS_SESSIONS 1024

// Raft consensus parameters
#define RAFT_ELECTION_TIMEOUT_MIN_MS 150
#define RAFT_ELECTION_TIMEOUT_MAX_MS 300
#define RAFT_HEARTBEAT_INTERVAL_MS 50
#define RAFT_COMMIT_BATCH_SIZE 256
#define RAFT_LOG_COMPACTION_THRESHOLD 10000

// Performance targets
#define TARGET_THROUGHPUT_MSG_SEC 4200000
#define TARGET_LATENCY_P99_NS 250000
#define TARGET_BANDWIDTH_GBPS 100
#define CACHE_LINE_SIZE 64
#define PAGE_SIZE 4096

// Message limits
#define MAX_DISTRIBUTED_MSG_SIZE (64 * 1024 * 1024)
#define MAX_BATCH_SIZE 1024
#define MAX_PIPELINE_DEPTH 128

// ============================================================================
// NETWORK NODE TYPES
// ============================================================================

typedef enum {
    NODE_ROLE_LEADER = 1,
    NODE_ROLE_FOLLOWER = 2,
    NODE_ROLE_CANDIDATE = 3,
    NODE_ROLE_OBSERVER = 4,      // Read-only, doesn't participate in elections
    NODE_ROLE_LEARNER = 5        // Catching up to cluster state
} node_role_t;

typedef enum {
    NODE_STATE_INITIALIZING = 0,
    NODE_STATE_DISCOVERING = 1,
    NODE_STATE_JOINING = 2,
    NODE_STATE_ACTIVE = 3,
    NODE_STATE_DEGRADED = 4,
    NODE_STATE_PARTITIONED = 5,
    NODE_STATE_LEAVING = 6,
    NODE_STATE_FAILED = 7
} node_state_t;

typedef enum {
    ENDPOINT_TYPE_TCP = 1,
    ENDPOINT_TYPE_UDP = 2,
    ENDPOINT_TYPE_RDMA = 3,
    ENDPOINT_TYPE_SHARED_MEM = 4,
    ENDPOINT_TYPE_UNIX_SOCKET = 5
} endpoint_type_t;

// ============================================================================
// RAFT CONSENSUS TYPES
// ============================================================================

typedef uint64_t raft_term_t;
typedef uint64_t raft_index_t;
typedef uint32_t raft_node_id_t;

typedef enum {
    RAFT_MSG_VOTE_REQUEST = 1,
    RAFT_MSG_VOTE_RESPONSE = 2,
    RAFT_MSG_APPEND_ENTRIES = 3,
    RAFT_MSG_APPEND_ENTRIES_RESP = 4,
    RAFT_MSG_CLIENT_REQUEST = 5,
    RAFT_MSG_CLIENT_RESPONSE = 6,
    RAFT_MSG_HEARTBEAT = 7,
    RAFT_MSG_SNAPSHOT = 8,
    RAFT_MSG_INSTALL_SNAPSHOT = 9
} raft_msg_type_t;

typedef enum {
    RAFT_ENTRY_CONFIG = 1,      // Cluster configuration change
    RAFT_ENTRY_APPLICATION = 2, // Application data
    RAFT_ENTRY_NOOP = 3        // No-op for leader initialization
} raft_entry_type_t;

// ============================================================================
// DATA STRUCTURES
// ============================================================================

// Network endpoint descriptor
typedef struct {
    endpoint_type_t type;
    char address[128];          // IP address or path
    uint16_t port;
    uint32_t flags;
    uint64_t bandwidth_bps;     // Available bandwidth
    uint32_t latency_us;        // Average latency
    bool secure;                // TLS enabled
} network_endpoint_t;

// Node descriptor
typedef struct __attribute__((aligned(CACHE_LINE_SIZE))) {
    raft_node_id_t node_id;
    char name[MAX_NODE_NAME];
    node_role_t role;
    node_state_t state;
    
    // Network endpoints
    uint32_t endpoint_count;
    network_endpoint_t endpoints[MAX_ENDPOINTS_PER_NODE];
    
    // Health metrics
    uint64_t last_heartbeat_ns;
    uint64_t last_contact_ns;
    uint32_t consecutive_failures;
    float load_factor;          // 0.0 - 1.0
    uint64_t messages_processed;
    uint64_t bytes_processed;
    
    // Raft state
    raft_term_t current_term;
    raft_index_t commit_index;
    raft_index_t last_applied;
    
    // Security
    X509* certificate;          // Node certificate
    time_t cert_expiry;
    
    bool voting;                // Can participate in elections
    bool active;
} cluster_node_t;

// Raft log entry
typedef struct __attribute__((packed)) {
    raft_index_t index;
    raft_term_t term;
    raft_entry_type_t type;
    uint64_t timestamp_ns;
    uint32_t data_size;
    uint32_t checksum;
    uint8_t data[];             // Variable length data
} raft_log_entry_t;

// Raft vote request
typedef struct __attribute__((packed)) {
    raft_msg_type_t msg_type;   // RAFT_MSG_VOTE_REQUEST
    raft_term_t term;
    raft_node_id_t candidate_id;
    raft_index_t last_log_index;
    raft_term_t last_log_term;
    uint32_t checksum;
} raft_vote_request_t;

// Raft vote response
typedef struct __attribute__((packed)) {
    raft_msg_type_t msg_type;   // RAFT_MSG_VOTE_RESPONSE
    raft_term_t term;
    bool vote_granted;
    raft_node_id_t voter_id;
    uint32_t checksum;
} raft_vote_response_t;

// Raft append entries request
typedef struct __attribute__((packed)) {
    raft_msg_type_t msg_type;   // RAFT_MSG_APPEND_ENTRIES
    raft_term_t term;
    raft_node_id_t leader_id;
    raft_index_t prev_log_index;
    raft_term_t prev_log_term;
    raft_index_t leader_commit;
    uint32_t entry_count;
    uint32_t total_size;
    uint32_t checksum;
    uint8_t entries[];          // Variable length entries
} raft_append_entries_t;

// Raft append entries response
typedef struct __attribute__((packed)) {
    raft_msg_type_t msg_type;   // RAFT_MSG_APPEND_ENTRIES_RESP
    raft_term_t term;
    raft_node_id_t node_id;
    bool success;
    raft_index_t match_index;   // For leader to update next_index
    uint32_t checksum;
} raft_append_entries_resp_t;

// Network message envelope
typedef struct __attribute__((packed, aligned(64))) {
    uint32_t magic;             // 0x444E4554 ("DNET")
    uint32_t version;
    uint64_t message_id;
    uint64_t timestamp_ns;
    
    raft_node_id_t source_node;
    raft_node_id_t dest_node;
    
    uint32_t message_type;      // raft_msg_type_t or application type
    uint32_t priority;          // 0 = highest
    uint32_t flags;
    
    uint32_t payload_size;
    uint32_t batch_size;        // Number of messages in batch
    uint32_t sequence_number;
    
    uint32_t checksum_header;   // Header checksum
    uint32_t checksum_payload;  // Payload checksum
    
    uint8_t padding[12];        // Pad to 64 bytes
    uint8_t payload[];          // Variable length payload
} dist_network_msg_t;

// TLS session context
typedef struct {
    SSL* ssl;
    SSL_CTX* ssl_ctx;
    X509* peer_cert;
    raft_node_id_t peer_node_id;
    uint64_t session_start_ns;
    uint64_t bytes_encrypted;
    uint64_t bytes_decrypted;
    bool handshake_complete;
    uint32_t cipher_suite;
} tls_session_t;

// Load balancer state
typedef struct __attribute__((aligned(CACHE_LINE_SIZE))) {
    uint32_t node_count;
    raft_node_id_t nodes[MAX_CLUSTER_NODES];
    
    // Load balancing algorithms
    _Atomic uint32_t round_robin_counter;
    uint64_t node_loads[MAX_CLUSTER_NODES];    // Messages processed
    uint64_t node_response_times[MAX_CLUSTER_NODES]; // Average response time ns
    
    // Connection pooling
    int tcp_connections[MAX_CLUSTER_NODES];    // Socket FDs
    tls_session_t* tls_sessions[MAX_CLUSTER_NODES];
    
    pthread_rwlock_t lock;
} load_balancer_t;

// Network statistics
typedef struct __attribute__((aligned(CACHE_LINE_SIZE))) {
    _Atomic uint64_t messages_sent;
    _Atomic uint64_t messages_received;
    _Atomic uint64_t bytes_sent;
    _Atomic uint64_t bytes_received;
    
    _Atomic uint64_t raft_votes_requested;
    _Atomic uint64_t raft_votes_granted;
    _Atomic uint64_t raft_appends_sent;
    _Atomic uint64_t raft_appends_successful;
    
    _Atomic uint64_t network_errors;
    _Atomic uint64_t tls_handshake_failures;
    _Atomic uint64_t partition_events;
    _Atomic uint64_t split_brain_detections;
    
    _Atomic uint64_t leader_elections;
    _Atomic uint64_t failover_events;
    
    // Performance metrics
    _Atomic uint64_t min_latency_ns;
    _Atomic uint64_t max_latency_ns;
    _Atomic uint64_t total_latency_ns;
    _Atomic uint64_t latency_samples;
    
    _Atomic uint32_t current_throughput_msg_sec;
    _Atomic uint32_t peak_throughput_msg_sec;
} network_stats_t;

// Raft state machine
typedef struct __attribute__((aligned(PAGE_SIZE))) {
    // Persistent state (must survive reboots)
    raft_term_t current_term;
    raft_node_id_t voted_for;
    
    // Log state
    raft_log_entry_t** log;     // Dynamic array of log entries
    raft_index_t log_size;
    raft_index_t log_capacity;
    
    // Volatile state (all servers)
    raft_index_t commit_index;
    raft_index_t last_applied;
    
    // Volatile state (leaders only)
    raft_index_t* next_index;   // For each follower
    raft_index_t* match_index;  // For each follower
    
    // Election state
    uint64_t election_deadline_ns;
    uint64_t last_heartbeat_ns;
    uint32_t votes_received;
    bool* voted_for_us;         // Which nodes voted for us
    
    // Configuration
    raft_node_id_t node_id;
    node_role_t role;
    raft_node_id_t leader_id;
    
    pthread_rwlock_t lock;
} raft_state_t;

// Main distributed network service
typedef struct __attribute__((aligned(PAGE_SIZE))) {
    // Cluster topology
    uint32_t cluster_size;
    cluster_node_t nodes[MAX_CLUSTER_NODES];
    raft_node_id_t local_node_id;
    
    // Raft consensus
    raft_state_t* raft_state;
    
    // Load balancing
    load_balancer_t* load_balancer;
    
    // Security
    SSL_CTX* ssl_server_ctx;
    SSL_CTX* ssl_client_ctx;
    X509* local_certificate;
    EVP_PKEY* local_private_key;
    
    // Network I/O
    int epoll_fd;               // Main epoll instance
    int server_socket;          // Listening socket
    pthread_t* network_threads; // Network I/O threads
    uint32_t thread_count;
    
    // Statistics and monitoring
    network_stats_t stats;
    
    // Control
    volatile bool running;
    volatile bool is_leader;
    volatile bool cluster_stable;
    
    // Configuration
    uint32_t max_throughput_msg_sec;
    uint32_t heartbeat_interval_ms;
    uint32_t election_timeout_ms;
    
    pthread_mutex_t service_lock;
} distributed_network_service_t;

// ============================================================================
// ERROR CODES
// ============================================================================

typedef enum {
    DIST_NET_SUCCESS = 0,
    DIST_NET_ERROR_INVALID_PARAM = -1,
    DIST_NET_ERROR_OUT_OF_MEMORY = -2,
    DIST_NET_ERROR_NETWORK = -3,
    DIST_NET_ERROR_TLS = -4,
    DIST_NET_ERROR_TIMEOUT = -5,
    DIST_NET_ERROR_NOT_LEADER = -6,
    DIST_NET_ERROR_SPLIT_BRAIN = -7,
    DIST_NET_ERROR_PARTITION = -8,
    DIST_NET_ERROR_ELECTION_IN_PROGRESS = -9,
    DIST_NET_ERROR_NODE_NOT_FOUND = -10,
    DIST_NET_ERROR_CLUSTER_UNSTABLE = -11,
    DIST_NET_ERROR_CAPACITY_EXCEEDED = -12,
    DIST_NET_ERROR_NOT_INITIALIZED = -13
} dist_net_error_t;

// ============================================================================
// CORE SERVICE FUNCTIONS
// ============================================================================

/**
 * Initialize the distributed networking system
 * @param local_node_id This node's unique identifier
 * @param cluster_config_file Path to cluster configuration file
 * @param cert_file Path to TLS certificate file
 * @param key_file Path to TLS private key file
 * @return DIST_NET_SUCCESS on success, error code otherwise
 */
dist_net_error_t dist_net_init(raft_node_id_t local_node_id,
                               const char* cluster_config_file,
                               const char* cert_file,
                               const char* key_file);

/**
 * Cleanup the distributed networking system
 */
void dist_net_cleanup(void);

/**
 * Start the network service (begins discovery and consensus)
 * @param bind_address Address to bind server socket
 * @param bind_port Port to bind server socket
 * @return DIST_NET_SUCCESS on success, error code otherwise
 */
dist_net_error_t dist_net_start(const char* bind_address, uint16_t bind_port);

/**
 * Stop the network service
 */
void dist_net_stop(void);

/**
 * Get service status
 * @return true if service is running and stable
 */
bool dist_net_is_stable(void);

/**
 * Get current cluster leader
 * @return Leader node ID, or 0 if no leader
 */
raft_node_id_t dist_net_get_leader(void);

// ============================================================================
// NODE MANAGEMENT
// ============================================================================

/**
 * Add a node to the cluster configuration
 * @param node_id Node identifier
 * @param name Node name
 * @param endpoints Array of network endpoints
 * @param endpoint_count Number of endpoints
 * @param voting Whether node can participate in elections
 * @return DIST_NET_SUCCESS on success, error code otherwise
 */
dist_net_error_t dist_net_add_node(raft_node_id_t node_id,
                                   const char* name,
                                   const network_endpoint_t* endpoints,
                                   uint32_t endpoint_count,
                                   bool voting);

/**
 * Remove a node from the cluster
 * @param node_id Node to remove
 * @return DIST_NET_SUCCESS on success, error code otherwise
 */
dist_net_error_t dist_net_remove_node(raft_node_id_t node_id);

/**
 * Get node information
 * @param node_id Node to query
 * @param node Output node information
 * @return DIST_NET_SUCCESS on success, error code otherwise
 */
dist_net_error_t dist_net_get_node_info(raft_node_id_t node_id, cluster_node_t* node);

/**
 * Get all active nodes
 * @param nodes Output array of nodes
 * @param max_nodes Maximum number of nodes to return
 * @return Number of active nodes
 */
uint32_t dist_net_get_active_nodes(cluster_node_t* nodes, uint32_t max_nodes);

/**
 * Update node health metrics
 * @param node_id Node to update
 * @param load_factor Current load factor (0.0 - 1.0)
 * @param messages_processed Total messages processed
 * @param bytes_processed Total bytes processed
 * @return DIST_NET_SUCCESS on success, error code otherwise
 */
dist_net_error_t dist_net_update_node_health(raft_node_id_t node_id,
                                             float load_factor,
                                             uint64_t messages_processed,
                                             uint64_t bytes_processed);

// ============================================================================
// MESSAGE PASSING
// ============================================================================

/**
 * Send a message to a specific node
 * @param dest_node_id Destination node
 * @param message_type Application-specific message type
 * @param payload Message payload
 * @param payload_size Size of payload
 * @param priority Message priority (0 = highest)
 * @return DIST_NET_SUCCESS on success, error code otherwise
 */
dist_net_error_t dist_net_send_message(raft_node_id_t dest_node_id,
                                       uint32_t message_type,
                                       const void* payload,
                                       size_t payload_size,
                                       uint32_t priority);

/**
 * Send a message to multiple nodes
 * @param dest_nodes Array of destination nodes
 * @param dest_count Number of destinations
 * @param message_type Application-specific message type
 * @param payload Message payload
 * @param payload_size Size of payload
 * @param priority Message priority (0 = highest)
 * @return Number of nodes successfully sent to
 */
uint32_t dist_net_multicast_message(const raft_node_id_t* dest_nodes,
                                    uint32_t dest_count,
                                    uint32_t message_type,
                                    const void* payload,
                                    size_t payload_size,
                                    uint32_t priority);

/**
 * Broadcast a message to all active nodes
 * @param message_type Application-specific message type
 * @param payload Message payload
 * @param payload_size Size of payload
 * @param priority Message priority (0 = highest)
 * @return Number of nodes successfully sent to
 */
uint32_t dist_net_broadcast_message(uint32_t message_type,
                                   const void* payload,
                                   size_t payload_size,
                                   uint32_t priority);

/**
 * Send a batch of messages for improved efficiency
 * @param messages Array of messages
 * @param message_count Number of messages
 * @return Number of messages successfully sent
 */
uint32_t dist_net_send_batch(const dist_network_msg_t** messages, uint32_t message_count);

// ============================================================================
// LOAD BALANCING
// ============================================================================

/**
 * Select the best node for a workload based on current load
 * @param exclude_nodes Array of nodes to exclude (optional)
 * @param exclude_count Number of excluded nodes
 * @return Selected node ID, or 0 if no suitable node found
 */
raft_node_id_t dist_net_select_node_by_load(const raft_node_id_t* exclude_nodes,
                                            uint32_t exclude_count);

/**
 * Select the best node for a workload based on latency
 * @param exclude_nodes Array of nodes to exclude (optional)
 * @param exclude_count Number of excluded nodes
 * @return Selected node ID, or 0 if no suitable node found
 */
raft_node_id_t dist_net_select_node_by_latency(const raft_node_id_t* exclude_nodes,
                                               uint32_t exclude_count);

/**
 * Get round-robin next node
 * @return Next node ID in round-robin order
 */
raft_node_id_t dist_net_select_node_round_robin(void);

// ============================================================================
// CONSENSUS OPERATIONS
// ============================================================================

/**
 * Propose a change to the distributed state (only valid on leader)
 * @param data Data to append to the distributed log
 * @param data_size Size of data
 * @param timeout_ms Maximum time to wait for consensus
 * @return DIST_NET_SUCCESS if committed, error code otherwise
 */
dist_net_error_t dist_net_propose(const void* data, size_t data_size, uint32_t timeout_ms);

/**
 * Read the current committed state
 * @param buffer Buffer to store committed data
 * @param buffer_size Size of buffer
 * @param data_size Output: actual size of committed data
 * @return DIST_NET_SUCCESS on success, error code otherwise
 */
dist_net_error_t dist_net_read_state(void* buffer, size_t buffer_size, size_t* data_size);

/**
 * Force a leader election (emergency use only)
 * @return DIST_NET_SUCCESS on success, error code otherwise
 */
dist_net_error_t dist_net_force_election(void);

/**
 * Transfer leadership to another node
 * @param new_leader_id Node to transfer leadership to
 * @return DIST_NET_SUCCESS on success, error code otherwise
 */
dist_net_error_t dist_net_transfer_leadership(raft_node_id_t new_leader_id);

// ============================================================================
// PARTITION AND FAILOVER HANDLING
// ============================================================================

/**
 * Check if the cluster is experiencing a network partition
 * @return true if partition detected
 */
bool dist_net_is_partitioned(void);

/**
 * Check if split-brain condition exists
 * @return true if split-brain detected
 */
bool dist_net_has_split_brain(void);

/**
 * Set the minimum cluster size for split-brain prevention
 * @param min_size Minimum number of nodes to consider cluster viable
 * @return DIST_NET_SUCCESS on success, error code otherwise
 */
dist_net_error_t dist_net_set_min_cluster_size(uint32_t min_size);

/**
 * Manually trigger failover procedures
 * @param failed_node_id Node that has failed
 * @return DIST_NET_SUCCESS on success, error code otherwise
 */
dist_net_error_t dist_net_trigger_failover(raft_node_id_t failed_node_id);

// ============================================================================
// SECURITY FUNCTIONS
// ============================================================================

/**
 * Rotate TLS certificates for all nodes
 * @param new_cert_file Path to new certificate file
 * @param new_key_file Path to new private key file
 * @return DIST_NET_SUCCESS on success, error code otherwise
 */
dist_net_error_t dist_net_rotate_certificates(const char* new_cert_file,
                                              const char* new_key_file);

/**
 * Verify a node's certificate
 * @param node_id Node to verify
 * @param cert Certificate to verify
 * @return true if certificate is valid and trusted
 */
bool dist_net_verify_node_certificate(raft_node_id_t node_id, X509* cert);

/**
 * Enable/disable mutual TLS authentication
 * @param enable true to enable mTLS, false to disable
 * @return DIST_NET_SUCCESS on success, error code otherwise
 */
dist_net_error_t dist_net_set_mutual_tls(bool enable);

// ============================================================================
// MONITORING AND STATISTICS
// ============================================================================

/**
 * Get comprehensive network statistics
 * @param stats Output statistics structure
 * @return DIST_NET_SUCCESS on success, error code otherwise
 */
dist_net_error_t dist_net_get_stats(network_stats_t* stats);

/**
 * Reset all statistics counters
 */
void dist_net_reset_stats(void);

/**
 * Print detailed network status and statistics
 */
void dist_net_print_status(void);

/**
 * Enable/disable performance monitoring
 * @param enable true to enable detailed monitoring
 * @return DIST_NET_SUCCESS on success, error code otherwise
 */
dist_net_error_t dist_net_enable_monitoring(bool enable);

/**
 * Set performance alert thresholds
 * @param max_latency_ns Maximum acceptable latency in nanoseconds
 * @param min_throughput_msg_sec Minimum acceptable throughput
 * @return DIST_NET_SUCCESS on success, error code otherwise
 */
dist_net_error_t dist_net_set_performance_thresholds(uint64_t max_latency_ns,
                                                     uint32_t min_throughput_msg_sec);

// ============================================================================
// CALLBACK TYPES
// ============================================================================

/**
 * Message received callback
 * @param source_node_id Source node
 * @param message_type Application message type
 * @param payload Message payload
 * @param payload_size Size of payload
 * @param user_data User-provided data
 */
typedef void (*dist_net_message_callback_t)(raft_node_id_t source_node_id,
                                            uint32_t message_type,
                                            const void* payload,
                                            size_t payload_size,
                                            void* user_data);

/**
 * Cluster state change callback
 * @param event_type Type of cluster event
 * @param node_id Affected node (if applicable)
 * @param user_data User-provided data
 */
typedef void (*dist_net_cluster_callback_t)(int event_type,
                                            raft_node_id_t node_id,
                                            void* user_data);

/**
 * Performance alert callback
 * @param alert_type Type of performance alert
 * @param current_value Current measured value
 * @param threshold_value Threshold that was exceeded
 * @param user_data User-provided data
 */
typedef void (*dist_net_perf_callback_t)(int alert_type,
                                         uint64_t current_value,
                                         uint64_t threshold_value,
                                         void* user_data);

/**
 * Register message received callback
 * @param callback Callback function
 * @param user_data User data for callback
 * @return DIST_NET_SUCCESS on success, error code otherwise
 */
dist_net_error_t dist_net_register_message_callback(dist_net_message_callback_t callback,
                                                    void* user_data);

/**
 * Register cluster state change callback
 * @param callback Callback function
 * @param user_data User data for callback
 * @return DIST_NET_SUCCESS on success, error code otherwise
 */
dist_net_error_t dist_net_register_cluster_callback(dist_net_cluster_callback_t callback,
                                                    void* user_data);

/**
 * Register performance alert callback
 * @param callback Callback function
 * @param user_data User data for callback
 * @return DIST_NET_SUCCESS on success, error code otherwise
 */
dist_net_error_t dist_net_register_perf_callback(dist_net_perf_callback_t callback,
                                                 void* user_data);

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

/**
 * Convert error code to human-readable string
 * @param error Error code
 * @return Error description string
 */
const char* dist_net_error_string(dist_net_error_t error);

/**
 * Convert node role to string
 * @param role Node role
 * @return Role name string
 */
const char* dist_net_role_string(node_role_t role);

/**
 * Convert node state to string
 * @param state Node state
 * @return State name string
 */
const char* dist_net_state_string(node_state_t state);

/**
 * Get current timestamp in nanoseconds (monotonic)
 * @return Current timestamp
 */
uint64_t dist_net_get_timestamp_ns(void);

/**
 * Generate unique message ID
 * @return Unique message identifier
 */
uint64_t dist_net_generate_message_id(void);

/**
 * Calculate network latency to a node
 * @param node_id Target node
 * @param latency_ns Output latency in nanoseconds
 * @return DIST_NET_SUCCESS on success, error code otherwise
 */
dist_net_error_t dist_net_measure_latency(raft_node_id_t node_id, uint64_t* latency_ns);

/**
 * Estimate bandwidth to a node
 * @param node_id Target node
 * @param bandwidth_bps Output bandwidth in bytes per second
 * @return DIST_NET_SUCCESS on success, error code otherwise
 */
dist_net_error_t dist_net_measure_bandwidth(raft_node_id_t node_id, uint64_t* bandwidth_bps);

#ifdef __cplusplus
}
#endif

#endif // DISTRIBUTED_NETWORK_H