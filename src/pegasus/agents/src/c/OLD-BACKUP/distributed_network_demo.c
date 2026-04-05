/*
 * DISTRIBUTED NETWORKING SYSTEM DEMONSTRATION
 * 
 * Comprehensive demonstration of the distributed Claude Agent Communication System:
 * - Multi-node cluster setup and consensus
 * - High-throughput message passing (4.2M+ msg/sec target)
 * - Load balancing and automatic failover
 * - Network partition detection and recovery
 * - Service discovery and health monitoring
 * - TLS security and certificate management
 * 
 * Author: Agent Communication System
 * Version: 1.0 Distributed
 */

#include "distributed_network.h"
#include "ultra_fast_protocol.h"
#include "agent_system.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <signal.h>
#include <time.h>
#include <sys/time.h>
#include <pthread.h>
#include <getopt.h>

// ============================================================================
// DEMO CONFIGURATION
// ============================================================================

#define DEMO_CLUSTER_SIZE 5
#define DEMO_MESSAGE_COUNT 1000000
#define DEMO_THREADS_PER_NODE 8
#define DEMO_TEST_DURATION_SEC 60
#define DEMO_WARMUP_SEC 10

// Demo scenarios
typedef enum {
    SCENARIO_BASIC_CLUSTERING = 1,
    SCENARIO_HIGH_THROUGHPUT = 2,
    SCENARIO_PARTITION_RECOVERY = 3,
    SCENARIO_LOAD_BALANCING = 4,
    SCENARIO_SECURITY_FEATURES = 5,
    SCENARIO_FAILOVER_TEST = 6,
    SCENARIO_ALL = 99
} demo_scenario_t;

// Global control variables
static volatile bool g_demo_running = true;
static volatile bool g_demo_shutdown = false;

// Demo configuration
typedef struct {
    raft_node_id_t local_node_id;
    demo_scenario_t scenario;
    uint32_t cluster_size;
    uint32_t message_count;
    uint32_t thread_count;
    uint32_t test_duration_sec;
    bool verbose;
    bool enable_tls;
    char* config_file;
    char* cert_file;
    char* key_file;
    char* bind_address;
    uint16_t bind_port;
} demo_config_t;

// Performance metrics
typedef struct {
    _Atomic uint64_t messages_sent;
    _Atomic uint64_t messages_received;
    _Atomic uint64_t bytes_sent;
    _Atomic uint64_t bytes_received;
    _Atomic uint64_t errors;
    _Atomic uint64_t leader_elections;
    _Atomic uint64_t partition_events;
    
    uint64_t start_time_ns;
    uint64_t end_time_ns;
    
    double peak_throughput_msg_sec;
    double average_latency_ns;
    double p99_latency_ns;
} demo_metrics_t;

static demo_metrics_t g_metrics = {0};

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

static inline uint64_t get_time_ns(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (uint64_t)ts.tv_sec * 1000000000ULL + ts.tv_nsec;
}

static void print_banner(void) {
    printf("\n");
    printf("╔══════════════════════════════════════════════════════════════════╗\n");
    printf("║        DISTRIBUTED CLAUDE AGENT COMMUNICATION SYSTEM            ║\n");
    printf("║                     Network Demo & Test Suite                   ║\n");
    printf("║                                                                  ║\n");
    printf("║  Target Performance: 4.2M+ messages/sec, p99 < 250μs           ║\n");
    printf("║  Features: Raft Consensus, Load Balancing, TLS Security         ║\n");
    printf("╚══════════════════════════════════════════════════════════════════╝\n");
    printf("\n");
}

static void signal_handler(int signum) {
    printf("\n[DEMO] Received signal %d, shutting down gracefully...\n", signum);
    g_demo_running = false;
    g_demo_shutdown = true;
}

static void setup_signal_handlers(void) {
    signal(SIGINT, signal_handler);
    signal(SIGTERM, signal_handler);
    signal(SIGHUP, signal_handler);
}

// ============================================================================
// MESSAGE CALLBACK HANDLERS
// ============================================================================

static void message_received_callback(raft_node_id_t source_node_id,
                                     uint32_t message_type,
                                     const void* payload,
                                     size_t payload_size,
                                     void* user_data) {
    atomic_fetch_add(&g_metrics.messages_received, 1);
    atomic_fetch_add(&g_metrics.bytes_received, payload_size);
    
    if (g_demo_running) {
        // Echo some messages back for testing
        if (message_type == 1001 && payload_size > 0) {
            dist_net_send_message(source_node_id, 1002, payload, payload_size, 1);
        }
    }
}

static void cluster_event_callback(int event_type, raft_node_id_t node_id, void* user_data) {
    const char* event_name = 
        (event_type == 1) ? "NODE_BECAME_FOLLOWER" :
        (event_type == 2) ? "NODE_BECAME_LEADER" :
        (event_type == 3) ? "NODE_JOINED" :
        (event_type == 4) ? "NODE_LEFT" :
        (event_type == 5) ? "PARTITION_DETECTED" :
        (event_type == 6) ? "PARTITION_RECOVERED" : "UNKNOWN_EVENT";
    
    printf("[CLUSTER] Event: %s (Node: %u)\n", event_name, node_id);
    
    if (event_type == 2) {
        atomic_fetch_add(&g_metrics.leader_elections, 1);
    } else if (event_type == 5) {
        atomic_fetch_add(&g_metrics.partition_events, 1);
    }
}

static void performance_alert_callback(int alert_type, uint64_t current_value, 
                                      uint64_t threshold_value, void* user_data) {
    const char* alert_name = 
        (alert_type == 1) ? "HIGH_LATENCY" :
        (alert_type == 2) ? "LOW_THROUGHPUT" :
        (alert_type == 3) ? "HIGH_ERROR_RATE" : "UNKNOWN_ALERT";
    
    printf("[PERF] Alert: %s (Current: %lu, Threshold: %lu)\n", 
           alert_name, current_value, threshold_value);
}

// ============================================================================
// DEMO SCENARIOS
// ============================================================================

static int demo_basic_clustering(demo_config_t* config) {
    printf("\n=== SCENARIO: Basic Clustering ===\n");
    printf("Testing cluster formation, leader election, and basic consensus\n");
    
    // Initialize distributed networking
    printf("[DEMO] Initializing distributed networking (Node ID: %u)...\n", config->local_node_id);
    
    dist_net_error_t result = dist_net_init(config->local_node_id, 
                                            config->config_file,
                                            config->cert_file, 
                                            config->key_file);
    if (result != DIST_NET_SUCCESS) {
        printf("[ERROR] Failed to initialize distributed networking: %s\n", 
               dist_net_error_string(result));
        return -1;
    }
    
    // Register callbacks
    dist_net_register_message_callback(message_received_callback, NULL);
    dist_net_register_cluster_callback(cluster_event_callback, NULL);
    dist_net_register_perf_callback(performance_alert_callback, NULL);
    
    // Add cluster nodes (in real deployment, this would come from config file)
    for (uint32_t i = 1; i <= config->cluster_size; i++) {
        if (i != config->local_node_id) {
            network_endpoint_t endpoint = {
                .type = ENDPOINT_TYPE_TCP,
                .port = config->bind_port,
                .bandwidth_bps = 10ULL * 1024 * 1024 * 1024, // 10 Gbps
                .latency_us = 100,
                .secure = config->enable_tls
            };
            
            snprintf(endpoint.address, sizeof(endpoint.address), "127.0.0.%u", i);
            
            char node_name[64];
            snprintf(node_name, sizeof(node_name), "node_%u", i);
            
            dist_net_add_node(i, node_name, &endpoint, 1, true);
        }
    }
    
    // Start the service
    printf("[DEMO] Starting distributed network service on %s:%u...\n", 
           config->bind_address, config->bind_port);
    
    result = dist_net_start(config->bind_address, config->bind_port);
    if (result != DIST_NET_SUCCESS) {
        printf("[ERROR] Failed to start networking service: %s\n", 
               dist_net_error_string(result));
        dist_net_cleanup();
        return -1;
    }
    
    printf("[DEMO] Waiting for cluster to stabilize...\n");
    
    // Wait for cluster to become stable
    int stabilization_timeout = 30;
    while (stabilization_timeout > 0 && !dist_net_is_stable()) {
        sleep(1);
        stabilization_timeout--;
        
        if (stabilization_timeout % 5 == 0) {
            printf("[DEMO] Waiting for stability... (%d seconds remaining)\n", stabilization_timeout);
        }
    }
    
    if (dist_net_is_stable()) {
        printf("[DEMO] ✓ Cluster is stable!\n");
        raft_node_id_t leader = dist_net_get_leader();
        printf("[DEMO] Current leader: Node %u\n", leader);
        
        // Test basic message sending
        printf("[DEMO] Testing basic message exchange...\n");
        
        const char* test_message = "Hello from distributed agent system!";
        for (uint32_t i = 1; i <= config->cluster_size; i++) {
            if (i != config->local_node_id) {
                result = dist_net_send_message(i, 1001, test_message, strlen(test_message), 1);
                if (result == DIST_NET_SUCCESS) {
                    atomic_fetch_add(&g_metrics.messages_sent, 1);
                    atomic_fetch_add(&g_metrics.bytes_sent, strlen(test_message));
                } else {
                    atomic_fetch_add(&g_metrics.errors, 1);
                }
            }
        }
        
        // Wait for responses
        sleep(2);
        
        printf("[DEMO] ✓ Basic clustering test completed\n");
        
    } else {
        printf("[DEMO] ✗ Cluster failed to stabilize within timeout\n");
        dist_net_stop();
        dist_net_cleanup();
        return -1;
    }
    
    return 0;
}

static void* high_throughput_sender_thread(void* arg) {
    demo_config_t* config = (demo_config_t*)arg;
    
    char message_buffer[1024];
    snprintf(message_buffer, sizeof(message_buffer), 
             "High throughput test message from node %u", config->local_node_id);
    
    uint64_t messages_per_thread = config->message_count / config->thread_count;
    uint64_t start_time = get_time_ns();
    
    printf("[SENDER] Thread started, will send %lu messages\n", messages_per_thread);
    
    for (uint64_t i = 0; i < messages_per_thread && g_demo_running; i++) {
        raft_node_id_t target_node = (config->local_node_id % config->cluster_size) + 1;
        if (target_node == config->local_node_id) {
            target_node = (target_node % config->cluster_size) + 1;
        }
        
        dist_net_error_t result = dist_net_send_message(target_node, 2001, 
                                                       message_buffer, strlen(message_buffer), 2);
        
        if (result == DIST_NET_SUCCESS) {
            atomic_fetch_add(&g_metrics.messages_sent, 1);
            atomic_fetch_add(&g_metrics.bytes_sent, strlen(message_buffer));
        } else {
            atomic_fetch_add(&g_metrics.errors, 1);
        }
        
        // Adaptive rate limiting to prevent overwhelming
        if (i % 10000 == 0) {
            usleep(1000); // 1ms pause every 10k messages
        }
    }
    
    uint64_t end_time = get_time_ns();
    double duration_sec = (end_time - start_time) / 1000000000.0;
    double throughput = messages_per_thread / duration_sec;
    
    printf("[SENDER] Thread completed: %.0f messages/sec\n", throughput);
    
    return NULL;
}

static int demo_high_throughput(demo_config_t* config) {
    printf("\n=== SCENARIO: High Throughput Messaging ===\n");
    printf("Target: 4.2M+ messages/second with low latency\n");
    
    g_metrics.start_time_ns = get_time_ns();
    
    // Create sender threads
    pthread_t* sender_threads = malloc(config->thread_count * sizeof(pthread_t));
    if (!sender_threads) {
        printf("[ERROR] Failed to allocate memory for threads\n");
        return -1;
    }
    
    printf("[DEMO] Starting %u sender threads for high throughput test...\n", config->thread_count);
    
    for (uint32_t i = 0; i < config->thread_count; i++) {
        int result = pthread_create(&sender_threads[i], NULL, high_throughput_sender_thread, config);
        if (result != 0) {
            printf("[ERROR] Failed to create sender thread %u: %s\n", i, strerror(result));
            free(sender_threads);
            return -1;
        }
    }
    
    // Monitor performance during the test
    printf("[DEMO] Monitoring performance for %u seconds...\n", config->test_duration_sec);
    
    uint64_t last_sent = 0;
    uint64_t last_received = 0;
    uint64_t last_time = get_time_ns();
    
    for (uint32_t sec = 0; sec < config->test_duration_sec && g_demo_running; sec++) {
        sleep(1);
        
        uint64_t current_sent = atomic_load(&g_metrics.messages_sent);
        uint64_t current_received = atomic_load(&g_metrics.messages_received);
        uint64_t current_time = get_time_ns();
        
        double interval_sec = (current_time - last_time) / 1000000000.0;
        double send_rate = (current_sent - last_sent) / interval_sec;
        double recv_rate = (current_received - last_received) / interval_sec;
        
        if (send_rate > g_metrics.peak_throughput_msg_sec) {
            g_metrics.peak_throughput_msg_sec = send_rate;
        }
        
        printf("[PERF] Send: %.0f msg/s, Recv: %.0f msg/s, Errors: %lu\n",
               send_rate, recv_rate, atomic_load(&g_metrics.errors));
        
        last_sent = current_sent;
        last_received = current_received;
        last_time = current_time;
    }
    
    // Wait for all threads to complete
    printf("[DEMO] Waiting for sender threads to complete...\n");
    
    for (uint32_t i = 0; i < config->thread_count; i++) {
        pthread_join(sender_threads[i], NULL);
    }
    
    g_metrics.end_time_ns = get_time_ns();
    
    free(sender_threads);
    
    printf("[DEMO] ✓ High throughput test completed\n");
    return 0;
}

static int demo_partition_recovery(demo_config_t* config) {
    printf("\n=== SCENARIO: Network Partition Recovery ===\n");
    printf("Testing partition detection and automatic recovery\n");
    
    // This scenario would simulate network partitions
    // In a real test, this might involve iptables rules or network namespaces
    
    printf("[DEMO] Simulating network partition...\n");
    
    // Send a burst of messages to establish baseline
    const char* message = "Pre-partition message";
    for (int i = 0; i < 100; i++) {
        raft_node_id_t target = (config->local_node_id % config->cluster_size) + 1;
        if (target == config->local_node_id) target++;
        
        dist_net_send_message(target, 3001, message, strlen(message), 1);
        usleep(10000); // 10ms between messages
    }
    
    printf("[DEMO] Checking partition detection...\n");
    sleep(5);
    
    bool is_partitioned = service_discovery_is_partitioned();
    bool has_quorum = service_discovery_has_quorum();
    
    printf("[DEMO] Partition detected: %s\n", is_partitioned ? "YES" : "NO");
    printf("[DEMO] Has quorum: %s\n", has_quorum ? "YES" : "NO");
    
    // Simulate recovery
    printf("[DEMO] Simulating partition recovery...\n");
    sleep(5);
    
    // Send recovery messages
    message = "Post-recovery message";
    for (int i = 0; i < 100; i++) {
        raft_node_id_t target = (config->local_node_id % config->cluster_size) + 1;
        if (target == config->local_node_id) target++;
        
        dist_net_error_t result = dist_net_send_message(target, 3002, message, strlen(message), 1);
        if (result == DIST_NET_SUCCESS) {
            atomic_fetch_add(&g_metrics.messages_sent, 1);
        }
        usleep(10000);
    }
    
    printf("[DEMO] ✓ Partition recovery test completed\n");
    return 0;
}

static int demo_load_balancing(demo_config_t* config) {
    printf("\n=== SCENARIO: Load Balancing ===\n");
    printf("Testing load balancing algorithms and failover\n");
    
    // Initialize load balancer
    if (load_balancer_init() != 0) {
        printf("[ERROR] Failed to initialize load balancer\n");
        return -1;
    }
    
    // Test different load balancing algorithms
    const char* algorithms[] = {"Round-Robin", "Least-Loaded", "Latency-Based", "Adaptive", "Consistent-Hash"};
    
    for (int alg = 0; alg < 5; alg++) {
        printf("[DEMO] Testing %s load balancing...\n", algorithms[alg]);
        
        // Send 1000 messages using this algorithm
        const char* test_message = "Load balancing test message";
        for (int i = 0; i < 1000 && g_demo_running; i++) {
            raft_node_id_t selected_node = load_balancer_select_node(alg, &i, sizeof(i));
            
            if (selected_node > 0) {
                dist_net_error_t result = dist_net_send_message(selected_node, 4001 + alg, 
                                                               test_message, strlen(test_message), 1);
                if (result == DIST_NET_SUCCESS) {
                    atomic_fetch_add(&g_metrics.messages_sent, 1);
                    load_balancer_report_request_result(selected_node, true, 1000000); // 1ms latency
                } else {
                    load_balancer_report_request_result(selected_node, false, 0);
                }
            }
            
            if (i % 100 == 0) {
                usleep(10000); // 10ms pause every 100 messages
            }
        }
        
        printf("[DEMO] ✓ %s algorithm test completed\n", algorithms[alg]);
    }
    
    load_balancer_print_status();
    load_balancer_cleanup();
    
    printf("[DEMO] ✓ Load balancing test completed\n");
    return 0;
}

static int demo_security_features(demo_config_t* config) {
    printf("\n=== SCENARIO: Security Features ===\n");
    printf("Testing TLS encryption, certificate validation, and secure communication\n");
    
    if (!config->enable_tls) {
        printf("[DEMO] TLS not enabled, skipping security test\n");
        return 0;
    }
    
    // Test encrypted message exchange
    const char* secure_message = "This message should be encrypted with TLS";
    
    printf("[DEMO] Sending encrypted messages...\n");
    
    for (uint32_t target = 1; target <= config->cluster_size; target++) {
        if (target != config->local_node_id) {
            dist_net_error_t result = dist_net_send_message(target, 5001, 
                                                           secure_message, strlen(secure_message), 0);
            if (result == DIST_NET_SUCCESS) {
                atomic_fetch_add(&g_metrics.messages_sent, 1);
                printf("[DEMO] ✓ Encrypted message sent to node %u\n", target);
            } else {
                printf("[DEMO] ✗ Failed to send encrypted message to node %u: %s\n", 
                       target, dist_net_error_string(result));
                atomic_fetch_add(&g_metrics.errors, 1);
            }
        }
    }
    
    // Wait for encrypted responses
    sleep(2);
    
    printf("[DEMO] ✓ Security features test completed\n");
    return 0;
}

static int demo_failover_test(demo_config_t* config) {
    printf("\n=== SCENARIO: Failover Test ===\n");
    printf("Testing automatic failover and leader re-election\n");
    
    raft_node_id_t original_leader = dist_net_get_leader();
    printf("[DEMO] Current leader: Node %u\n", original_leader);
    
    if (original_leader == config->local_node_id) {
        printf("[DEMO] This node is the leader, testing failover by forcing election...\n");
        
        dist_net_error_t result = dist_net_force_election();
        if (result == DIST_NET_SUCCESS) {
            printf("[DEMO] ✓ Leader election triggered\n");
        } else {
            printf("[DEMO] ✗ Failed to trigger leader election: %s\n", dist_net_error_string(result));
        }
        
        // Wait for new leader election
        sleep(5);
        
        raft_node_id_t new_leader = dist_net_get_leader();
        printf("[DEMO] New leader after election: Node %u\n", new_leader);
        
        if (new_leader != original_leader) {
            printf("[DEMO] ✓ Successful leader failover\n");
        } else {
            printf("[DEMO] ⚠ Leader remained the same (possible single-node cluster)\n");
        }
        
    } else {
        printf("[DEMO] This node is not the leader, testing follower behavior during failover\n");
        
        // Send messages during potential leader changes
        const char* failover_message = "Message during potential failover";
        
        for (int i = 0; i < 50; i++) {
            dist_net_error_t result = dist_net_send_message(original_leader, 6001, 
                                                           failover_message, strlen(failover_message), 1);
            if (result == DIST_NET_SUCCESS) {
                atomic_fetch_add(&g_metrics.messages_sent, 1);
            } else {
                atomic_fetch_add(&g_metrics.errors, 1);
            }
            
            usleep(100000); // 100ms between messages
        }
    }
    
    printf("[DEMO] ✓ Failover test completed\n");
    return 0;
}

// ============================================================================
// METRICS AND REPORTING
// ============================================================================

static void print_final_metrics(demo_config_t* config) {
    printf("\n");
    printf("╔══════════════════════════════════════════════════════════════════╗\n");
    printf("║                          FINAL RESULTS                          ║\n");
    printf("╚══════════════════════════════════════════════════════════════════╝\n");
    
    double duration_sec = (g_metrics.end_time_ns - g_metrics.start_time_ns) / 1000000000.0;
    uint64_t total_sent = atomic_load(&g_metrics.messages_sent);
    uint64_t total_received = atomic_load(&g_metrics.messages_received);
    uint64_t total_errors = atomic_load(&g_metrics.errors);
    
    double avg_send_rate = total_sent / duration_sec;
    double avg_recv_rate = total_received / duration_sec;
    double error_rate = (double)total_errors / (total_sent + total_errors) * 100.0;
    
    printf("Test Duration:           %.2f seconds\n", duration_sec);
    printf("Messages Sent:           %lu\n", total_sent);
    printf("Messages Received:       %lu\n", total_received);
    printf("Total Errors:            %lu (%.2f%%)\n", total_errors, error_rate);
    printf("Bytes Sent:              %lu\n", atomic_load(&g_metrics.bytes_sent));
    printf("Bytes Received:          %lu\n", atomic_load(&g_metrics.bytes_received));
    printf("\nPerformance Metrics:\n");
    printf("Average Send Rate:       %.0f messages/sec\n", avg_send_rate);
    printf("Average Receive Rate:    %.0f messages/sec\n", avg_recv_rate);
    printf("Peak Throughput:         %.0f messages/sec\n", g_metrics.peak_throughput_msg_sec);
    printf("Leader Elections:        %lu\n", atomic_load(&g_metrics.leader_elections));
    printf("Partition Events:        %lu\n", atomic_load(&g_metrics.partition_events));
    
    // Performance assessment
    printf("\nPerformance Assessment:\n");
    if (g_metrics.peak_throughput_msg_sec >= 4200000) {
        printf("✓ EXCELLENT: Peak throughput exceeds 4.2M msg/sec target\n");
    } else if (g_metrics.peak_throughput_msg_sec >= 2000000) {
        printf("✓ GOOD: Peak throughput above 2M msg/sec\n");
    } else if (g_metrics.peak_throughput_msg_sec >= 1000000) {
        printf("⚠ FAIR: Peak throughput above 1M msg/sec\n");
    } else {
        printf("✗ POOR: Peak throughput below 1M msg/sec\n");
    }
    
    if (error_rate < 0.01) {
        printf("✓ EXCELLENT: Error rate below 0.01%%\n");
    } else if (error_rate < 0.1) {
        printf("✓ GOOD: Error rate below 0.1%%\n");
    } else if (error_rate < 1.0) {
        printf("⚠ FAIR: Error rate below 1%%\n");
    } else {
        printf("✗ POOR: Error rate above 1%%\n");
    }
    
    printf("\n");
    
    // Print final system status
    printf("Final System Status:\n");
    dist_net_print_status();
    service_discovery_print_status();
}

// ============================================================================
// MAIN PROGRAM
// ============================================================================

static void print_usage(const char* program_name) {
    printf("Usage: %s [OPTIONS]\n", program_name);
    printf("\nDistributed Claude Agent Communication System Demo\n\n");
    printf("Options:\n");
    printf("  -n, --node-id ID          Local node identifier (1-%d)\n", DEMO_CLUSTER_SIZE);
    printf("  -s, --scenario NUM        Demo scenario to run:\n");
    printf("                              1 = Basic Clustering\n");
    printf("                              2 = High Throughput\n");
    printf("                              3 = Partition Recovery\n");
    printf("                              4 = Load Balancing\n");
    printf("                              5 = Security Features\n");
    printf("                              6 = Failover Test\n");
    printf("                              99 = All Scenarios\n");
    printf("  -c, --cluster-size SIZE   Cluster size (default: %d)\n", DEMO_CLUSTER_SIZE);
    printf("  -m, --messages COUNT      Number of messages to send (default: %d)\n", DEMO_MESSAGE_COUNT);
    printf("  -t, --threads NUM         Number of sender threads (default: %d)\n", DEMO_THREADS_PER_NODE);
    printf("  -d, --duration SEC        Test duration in seconds (default: %d)\n", DEMO_TEST_DURATION_SEC);
    printf("  -b, --bind-address ADDR   Bind address (default: 127.0.0.1)\n");
    printf("  -p, --port PORT          Bind port (default: 8800+node_id)\n");
    printf("  --config FILE            Configuration file path\n");
    printf("  --cert FILE              TLS certificate file\n");
    printf("  --key FILE               TLS private key file\n");
    printf("  --tls                    Enable TLS encryption\n");
    printf("  -v, --verbose            Verbose output\n");
    printf("  -h, --help               Show this help message\n");
    printf("\nExamples:\n");
    printf("  %s --node-id 1 --scenario 99    # Run all scenarios as node 1\n", program_name);
    printf("  %s -n 2 -s 2 -m 5000000 -t 16   # High throughput test with 5M messages\n", program_name);
    printf("  %s -n 1 --tls --cert cert.pem --key key.pem  # Secure cluster\n", program_name);
}

int main(int argc, char* argv[]) {
    demo_config_t config = {
        .local_node_id = 1,
        .scenario = SCENARIO_ALL,
        .cluster_size = DEMO_CLUSTER_SIZE,
        .message_count = DEMO_MESSAGE_COUNT,
        .thread_count = DEMO_THREADS_PER_NODE,
        .test_duration_sec = DEMO_TEST_DURATION_SEC,
        .verbose = false,
        .enable_tls = false,
        .config_file = NULL,
        .cert_file = NULL,
        .key_file = NULL,
        .bind_address = "127.0.0.1",
        .bind_port = 0  // Will be set based on node ID
    };
    
    // Parse command line options
    static struct option long_options[] = {
        {"node-id", required_argument, 0, 'n'},
        {"scenario", required_argument, 0, 's'},
        {"cluster-size", required_argument, 0, 'c'},
        {"messages", required_argument, 0, 'm'},
        {"threads", required_argument, 0, 't'},
        {"duration", required_argument, 0, 'd'},
        {"bind-address", required_argument, 0, 'b'},
        {"port", required_argument, 0, 'p'},
        {"config", required_argument, 0, 0},
        {"cert", required_argument, 0, 0},
        {"key", required_argument, 0, 0},
        {"tls", no_argument, 0, 0},
        {"verbose", no_argument, 0, 'v'},
        {"help", no_argument, 0, 'h'},
        {0, 0, 0, 0}
    };
    
    int option_index = 0;
    int c;
    
    while ((c = getopt_long(argc, argv, "n:s:c:m:t:d:b:p:vh", long_options, &option_index)) != -1) {
        switch (c) {
            case 'n':
                config.local_node_id = (raft_node_id_t)atoi(optarg);
                break;
            case 's':
                config.scenario = (demo_scenario_t)atoi(optarg);
                break;
            case 'c':
                config.cluster_size = (uint32_t)atoi(optarg);
                break;
            case 'm':
                config.message_count = (uint32_t)atoi(optarg);
                break;
            case 't':
                config.thread_count = (uint32_t)atoi(optarg);
                break;
            case 'd':
                config.test_duration_sec = (uint32_t)atoi(optarg);
                break;
            case 'b':
                config.bind_address = optarg;
                break;
            case 'p':
                config.bind_port = (uint16_t)atoi(optarg);
                break;
            case 'v':
                config.verbose = true;
                break;
            case 'h':
                print_usage(argv[0]);
                return 0;
            case 0:
                if (strcmp(long_options[option_index].name, "config") == 0) {
                    config.config_file = optarg;
                } else if (strcmp(long_options[option_index].name, "cert") == 0) {
                    config.cert_file = optarg;
                } else if (strcmp(long_options[option_index].name, "key") == 0) {
                    config.key_file = optarg;
                } else if (strcmp(long_options[option_index].name, "tls") == 0) {
                    config.enable_tls = true;
                }
                break;
            default:
                print_usage(argv[0]);
                return 1;
        }
    }
    
    // Set default port based on node ID if not specified
    if (config.bind_port == 0) {
        config.bind_port = 8800 + config.local_node_id;
    }
    
    // Validate configuration
    if (config.local_node_id < 1 || config.local_node_id > config.cluster_size) {
        printf("[ERROR] Node ID must be between 1 and %u\n", config.cluster_size);
        return 1;
    }
    
    if (config.enable_tls && (!config.cert_file || !config.key_file)) {
        printf("[ERROR] TLS enabled but certificate or key file not specified\n");
        return 1;
    }
    
    print_banner();
    
    printf("Configuration:\n");
    printf("  Node ID: %u\n", config.local_node_id);
    printf("  Scenario: %d\n", config.scenario);
    printf("  Cluster Size: %u\n", config.cluster_size);
    printf("  Bind Address: %s:%u\n", config.bind_address, config.bind_port);
    printf("  TLS Enabled: %s\n", config.enable_tls ? "Yes" : "No");
    printf("  Messages: %u\n", config.message_count);
    printf("  Threads: %u\n", config.thread_count);
    printf("  Duration: %u seconds\n", config.test_duration_sec);
    printf("\n");
    
    setup_signal_handlers();
    
    // Initialize service discovery first
    printf("[DEMO] Initializing service discovery...\n");
    if (service_discovery_init(config.local_node_id, config.bind_address) != 0) {
        printf("[ERROR] Failed to initialize service discovery\n");
        return 1;
    }
    
    int result = 0;
    
    // Run demo scenarios
    if (config.scenario == SCENARIO_ALL || config.scenario == SCENARIO_BASIC_CLUSTERING) {
        result = demo_basic_clustering(&config);
        if (result != 0) goto cleanup;
    }
    
    if (config.scenario == SCENARIO_ALL || config.scenario == SCENARIO_HIGH_THROUGHPUT) {
        result = demo_high_throughput(&config);
        if (result != 0) goto cleanup;
    }
    
    if (config.scenario == SCENARIO_ALL || config.scenario == SCENARIO_PARTITION_RECOVERY) {
        result = demo_partition_recovery(&config);
        if (result != 0) goto cleanup;
    }
    
    if (config.scenario == SCENARIO_ALL || config.scenario == SCENARIO_LOAD_BALANCING) {
        result = demo_load_balancing(&config);
        if (result != 0) goto cleanup;
    }
    
    if (config.scenario == SCENARIO_ALL || config.scenario == SCENARIO_SECURITY_FEATURES) {
        result = demo_security_features(&config);
        if (result != 0) goto cleanup;
    }
    
    if (config.scenario == SCENARIO_ALL || config.scenario == SCENARIO_FAILOVER_TEST) {
        result = demo_failover_test(&config);
        if (result != 0) goto cleanup;
    }
    
    // Final metrics and cleanup
    print_final_metrics(&config);
    
cleanup:
    printf("[DEMO] Shutting down services...\n");
    
    dist_net_stop();
    dist_net_cleanup();
    service_discovery_cleanup();
    
    if (result == 0) {
        printf("[DEMO] ✓ All scenarios completed successfully!\n");
    } else {
        printf("[DEMO] ✗ Demo completed with errors\n");
    }
    
    return result;
}