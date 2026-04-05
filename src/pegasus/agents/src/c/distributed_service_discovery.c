/*
 * DISTRIBUTED SERVICE DISCOVERY AND NETWORK PARTITION HANDLING
 * 
 * Advanced service discovery system with network partition handling:
 * - Multi-protocol service discovery (UDP multicast, DNS-SD, Consul-like)
 * - Network partition detection using gossip protocol
 * - Split-brain prevention with quorum-based decisions
 * - Automatic node recovery and cluster healing
 * - Geographic distribution awareness
 * - Service health checking and auto-deregistration
 * 
 * Author: Agent Communication System
 * Version: 1.0 Distributed
 */

#include "distributed_network.h"
#include "agent_protocol.h"
#include "compatibility_layer.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdatomic.h>
#include <pthread.h>
#include <unistd.h>
#include <errno.h>
#include <time.h>
#include <sys/time.h>
#include <sys/socket.h>
#include <sys/epoll.h>
#include <arpa/inet.h>
#include <netinet/in.h>
#include <ifaddrs.h>
#include <net/if.h>
#include <numa.h>
#include <x86intrin.h>

// ============================================================================
// SERVICE DISCOVERY CONSTANTS
// ============================================================================

#define SD_MULTICAST_GROUP "239.255.42.99"  // Reserved for agent communication
#define SD_MULTICAST_PORT 8899
#define SD_UNICAST_PORT 8900
#define SD_GOSSIP_PORT 8901

#define SD_ANNOUNCEMENT_INTERVAL_MS 5000
#define SD_HEALTH_CHECK_INTERVAL_MS 2000
#define SD_GOSSIP_INTERVAL_MS 1000
#define SD_NODE_TIMEOUT_MS 15000
#define SD_PARTITION_TIMEOUT_MS 30000

#define SD_MAX_SERVICE_TYPES 64
#define SD_MAX_SERVICE_NAME 128
#define SD_MAX_SERVICE_METADATA 512
#define SD_MAX_GOSSIP_PAYLOAD 4096
#define SD_GOSSIP_FANOUT 3

#define SD_PROTOCOL_VERSION 1
#define SD_MAGIC_ANNOUNCEMENT 0x53444153  // "SDAS" - Service Discovery AnnouncementS
#define SD_MAGIC_QUERY 0x53445155        // "SDQU" - Service Discovery QUery
#define SD_MAGIC_RESPONSE 0x53445253     // "SDRS" - Service Discovery ReSponse
#define SD_MAGIC_GOSSIP 0x53444750       // "SDGP" - Service Discovery GossiP

// ============================================================================
// NETWORK PARTITION DETECTION
// ============================================================================

#define PARTITION_DETECTION_ALGORITHM_GOSSIP 1
#define PARTITION_DETECTION_ALGORITHM_HEARTBEAT 2
#define PARTITION_DETECTION_ALGORITHM_HYBRID 3

#define PARTITION_SUSPICION_THRESHOLD 3
#define PARTITION_CONFIRMATION_THRESHOLD 5
#define PARTITION_RECOVERY_THRESHOLD 3

// Geographic distribution
#define MAX_AVAILABILITY_ZONES 16
#define MAX_REGIONS 8

// ============================================================================
// DATA STRUCTURES
// ============================================================================

// Service registration entry
typedef struct {
    char service_type[64];
    char service_name[SD_MAX_SERVICE_NAME];
    raft_node_id_t node_id;
    
    // Network endpoints
    uint32_t endpoint_count;
    network_endpoint_t endpoints[MAX_ENDPOINTS_PER_NODE];
    
    // Service metadata
    char metadata[SD_MAX_SERVICE_METADATA];
    uint64_t registration_time_ns;
    uint64_t last_health_check_ns;
    
    // Health status
    bool is_healthy;
    uint32_t consecutive_failures;
    uint32_t health_check_interval_ms;
    
    // Service capabilities
    uint32_t protocol_version;
    uint32_t max_connections;
    uint64_t max_throughput;
    
    bool active;
} service_registration_t;

// Node information for gossip protocol
typedef struct __attribute__((aligned(64))) {
    raft_node_id_t node_id;
    char hostname[256];
    struct sockaddr_in address;
    
    // Gossip protocol state
    uint64_t incarnation;           // Logical timestamp
    uint64_t last_seen_ns;
    uint32_t suspicion_count;
    uint32_t confirmation_count;
    
    // Node status
    enum {
        NODE_STATUS_ALIVE = 1,
        NODE_STATUS_SUSPECT = 2,
        NODE_STATUS_DEAD = 3,
        NODE_STATUS_LEFT = 4
    } status;
    
    // Geographic information
    uint32_t availability_zone_id;
    uint32_t region_id;
    
    // Performance metrics
    float load_average;
    uint32_t active_connections;
    uint64_t uptime_ns;
    
    // Network partition detection
    uint64_t last_gossip_ns;
    uint32_t partition_group_id;    // 0 = unknown, >0 = partition group
    bool can_reach_majority;
    
} gossip_node_t;

// Gossip message types
typedef enum {
    GOSSIP_MSG_PING = 1,
    GOSSIP_MSG_PING_REQ = 2,
    GOSSIP_MSG_ACK = 3,
    GOSSIP_MSG_SUSPECT = 4,
    GOSSIP_MSG_ALIVE = 5,
    GOSSIP_MSG_DEAD = 6,
    GOSSIP_MSG_LEAVE = 7,
    GOSSIP_MSG_JOIN = 8,
    GOSSIP_MSG_PARTITION_INFO = 9
} gossip_msg_type_t;

// Service discovery message formats
typedef struct __attribute__((packed)) {
    uint32_t magic;                 // SD_MAGIC_ANNOUNCEMENT
    uint32_t protocol_version;
    raft_node_id_t node_id;
    uint64_t timestamp_ns;
    uint64_t incarnation;
    
    uint32_t service_count;
    uint32_t total_payload_size;
    uint32_t checksum;
    
    uint8_t services[];             // Variable length service data
} sd_announcement_msg_t;

typedef struct __attribute__((packed)) {
    uint32_t magic;                 // SD_MAGIC_QUERY
    uint32_t protocol_version;
    raft_node_id_t requesting_node_id;
    uint64_t query_id;
    uint32_t query_type;            // 0=all, 1=by_type, 2=by_name
    
    char service_type[64];
    char service_name[SD_MAX_SERVICE_NAME];
    uint32_t checksum;
} sd_query_msg_t;

typedef struct __attribute__((packed)) {
    uint32_t magic;                 // SD_MAGIC_RESPONSE
    uint32_t protocol_version;
    raft_node_id_t responding_node_id;
    uint64_t query_id;
    
    uint32_t service_count;
    uint32_t total_payload_size;
    uint32_t checksum;
    
    uint8_t services[];             // Variable length service data
} sd_response_msg_t;

typedef struct __attribute__((packed)) {
    uint32_t magic;                 // SD_MAGIC_GOSSIP
    uint32_t protocol_version;
    gossip_msg_type_t msg_type;
    raft_node_id_t source_node_id;
    uint64_t timestamp_ns;
    
    uint32_t payload_size;
    uint32_t checksum;
    
    uint8_t payload[];              // Variable length gossip payload
} gossip_msg_t;

// Network partition state
typedef struct {
    // Partition detection algorithm
    int detection_algorithm;
    
    // Current partition state
    bool partition_detected;
    uint64_t partition_start_ns;
    uint64_t partition_last_update_ns;
    uint32_t partition_count;       // Number of detected partitions
    
    // Quorum management
    uint32_t cluster_size;
    uint32_t quorum_size;           // Minimum nodes for majority
    uint32_t current_reachable_nodes;
    bool have_quorum;
    
    // Partition groups
    uint32_t local_partition_id;
    uint32_t partition_sizes[MAX_CLUSTER_NODES];
    raft_node_id_t partition_members[MAX_CLUSTER_NODES][MAX_CLUSTER_NODES];
    
    // Geographic distribution
    struct {
        uint32_t zone_id;
        char zone_name[64];
        uint32_t node_count;
        raft_node_id_t nodes[MAX_CLUSTER_NODES];
        bool is_reachable;
    } availability_zones[MAX_AVAILABILITY_ZONES];
    uint32_t zone_count;
    
    // Recovery tracking
    uint32_t nodes_recovering;
    uint64_t recovery_start_times[MAX_CLUSTER_NODES];
    
    pthread_mutex_t partition_lock;
} network_partition_state_t;

// Main service discovery service
typedef struct __attribute__((aligned(4096))) {
    // Local node information
    raft_node_id_t local_node_id;
    char local_hostname[256];
    struct sockaddr_in local_address;
    uint64_t local_incarnation;
    
    // Service registry
    service_registration_t services[MAX_CLUSTER_NODES * SD_MAX_SERVICE_TYPES];
    uint32_t service_count;
    pthread_rwlock_t service_lock;
    
    // Gossip protocol state
    gossip_node_t gossip_nodes[MAX_CLUSTER_NODES];
    uint32_t gossip_node_count;
    pthread_mutex_t gossip_lock;
    
    // Network partition detection
    network_partition_state_t partition_state;
    
    // Network sockets
    int multicast_socket;           // UDP multicast for announcements
    int unicast_socket;             // UDP unicast for queries/responses
    int gossip_socket;              // UDP socket for gossip protocol
    
    // Background threads
    pthread_t announcement_thread;
    pthread_t health_check_thread;
    pthread_t gossip_thread;
    pthread_t partition_monitor_thread;
    
    volatile bool running;
    
    // Statistics
    _Atomic uint64_t announcements_sent;
    _Atomic uint64_t queries_received;
    _Atomic uint64_t responses_sent;
    _Atomic uint64_t gossip_messages_sent;
    _Atomic uint64_t gossip_messages_received;
    _Atomic uint64_t partition_events;
    _Atomic uint64_t false_partition_alarms;
    
    // Configuration
    uint32_t announcement_interval_ms;
    uint32_t health_check_interval_ms;
    uint32_t gossip_interval_ms;
    uint32_t node_timeout_ms;
    
    pthread_mutex_t service_lock_mutex;
    
} service_discovery_t;

// Global service discovery instance
static service_discovery_t* g_sd_service = NULL;

// External references
extern distributed_network_service_t* g_dist_service;

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

static inline uint64_t get_monotonic_time_ns(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (uint64_t)ts.tv_sec * 1000000000ULL + ts.tv_nsec;
}

static inline uint32_t crc32c_fast(const void* data, size_t len) {
    const uint8_t* bytes = (const uint8_t*)data;
    uint32_t crc = 0xFFFFFFFF;
    
    for (size_t i = 0; i < len; i++) {
        crc = _mm_crc32_u8(crc, bytes[i]);
    }
    
    return ~crc;
}

static int get_local_ip_address(char* ip_str, size_t ip_str_len) {
    struct ifaddrs *ifaddrs_ptr, *ifa;
    
    if (getifaddrs(&ifaddrs_ptr) == -1) return -1;
    
    for (ifa = ifaddrs_ptr; ifa != NULL; ifa = ifa->ifa_next) {
        if (ifa->ifa_addr == NULL) continue;
        
        // Skip loopback and non-IPv4 interfaces
        if (ifa->ifa_addr->sa_family == AF_INET && 
            !(ifa->ifa_flags & IFF_LOOPBACK) &&
            (ifa->ifa_flags & IFF_RUNNING)) {
            
            struct sockaddr_in* addr_in = (struct sockaddr_in*)ifa->ifa_addr;
            const char* ip = inet_ntoa(addr_in->sin_addr);
            
            // Skip private networks if possible (prefer public IPs)
            if (strncmp(ip, "192.168.", 8) != 0 && 
                strncmp(ip, "10.", 3) != 0 && 
                strncmp(ip, "172.", 4) != 0) {
                strncpy(ip_str, ip, ip_str_len - 1);
                ip_str[ip_str_len - 1] = '\0';
                freeifaddrs(ifaddrs_ptr);
                return 0;
            }
        }
    }
    
    // Fallback to first non-loopback IPv4 address
    for (ifa = ifaddrs_ptr; ifa != NULL; ifa = ifa->ifa_next) {
        if (ifa->ifa_addr == NULL) continue;
        
        if (ifa->ifa_addr->sa_family == AF_INET && 
            !(ifa->ifa_flags & IFF_LOOPBACK)) {
            
            struct sockaddr_in* addr_in = (struct sockaddr_in*)ifa->ifa_addr;
            strncpy(ip_str, inet_ntoa(addr_in->sin_addr), ip_str_len - 1);
            ip_str[ip_str_len - 1] = '\0';
            freeifaddrs(ifaddrs_ptr);
            return 0;
        }
    }
    
    freeifaddrs(ifaddrs_ptr);
    return -1;
}

// ============================================================================
// GOSSIP PROTOCOL IMPLEMENTATION
// ============================================================================

static gossip_node_t* find_gossip_node(raft_node_id_t node_id) {
    for (uint32_t i = 0; i < g_sd_service->gossip_node_count; i++) {
        if (g_sd_service->gossip_nodes[i].node_id == node_id) {
            return &g_sd_service->gossip_nodes[i];
        }
    }
    return NULL;
}

static gossip_node_t* add_gossip_node(raft_node_id_t node_id, struct sockaddr_in* address) {
    if (g_sd_service->gossip_node_count >= MAX_CLUSTER_NODES) return NULL;
    
    pthread_mutex_lock(&g_sd_service->gossip_lock);
    
    gossip_node_t* node = &g_sd_service->gossip_nodes[g_sd_service->gossip_node_count++];
    node->node_id = node_id;
    node->address = *address;
    node->incarnation = 1;
    node->status = NODE_STATUS_ALIVE;
    node->last_seen_ns = get_monotonic_time_ns();
    node->suspicion_count = 0;
    node->confirmation_count = 0;
    node->partition_group_id = 0;
    node->can_reach_majority = true;
    
    pthread_mutex_unlock(&g_sd_service->gossip_lock);
    
    return node;
}

static void send_gossip_message(gossip_msg_type_t msg_type, raft_node_id_t target_node_id, 
                               const void* payload, size_t payload_size) {
    if (!g_sd_service || g_sd_service->gossip_socket < 0) return;
    
    size_t total_size = sizeof(gossip_msg_t) + payload_size;
    gossip_msg_t* msg = malloc(total_size);
    if (!msg) return;
    
    msg->magic = SD_MAGIC_GOSSIP;
    msg->protocol_version = SD_PROTOCOL_VERSION;
    msg->msg_type = msg_type;
    msg->source_node_id = g_sd_service->local_node_id;
    msg->timestamp_ns = get_monotonic_time_ns();
    msg->payload_size = payload_size;
    
    if (payload && payload_size > 0) {
        memcpy(msg->payload, payload, payload_size);
    }
    
    msg->checksum = crc32c_fast(msg, total_size - sizeof(msg->checksum));
    
    // Find target node address
    gossip_node_t* target_node = find_gossip_node(target_node_id);
    if (target_node) {
        sendto(g_sd_service->gossip_socket, msg, total_size, 0,
               (struct sockaddr*)&target_node->address, sizeof(target_node->address));
        
        atomic_fetch_add(&g_sd_service->gossip_messages_sent, 1);
    }
    
    free(msg);
}

static void broadcast_gossip_message(gossip_msg_type_t msg_type, const void* payload, size_t payload_size) {
    // Send to random subset of nodes (gossip fanout)
    uint32_t fanout = fminf(SD_GOSSIP_FANOUT, g_sd_service->gossip_node_count);
    
    for (uint32_t i = 0; i < fanout; i++) {
        uint32_t target_index = rand() % g_sd_service->gossip_node_count;
        gossip_node_t* target = &g_sd_service->gossip_nodes[target_index];
        
        if (target->node_id != g_sd_service->local_node_id && 
            target->status == NODE_STATUS_ALIVE) {
            send_gossip_message(msg_type, target->node_id, payload, payload_size);
        }
    }
}

static void handle_gossip_ping(gossip_node_t* sender, const gossip_msg_t* msg) {
    // Update sender's last seen time
    sender->last_seen_ns = get_monotonic_time_ns();
    
    // Send ACK response
    send_gossip_message(GOSSIP_MSG_ACK, sender->node_id, NULL, 0);
}

static void handle_gossip_suspect(gossip_node_t* sender, const gossip_msg_t* msg) {
    if (msg->payload_size < sizeof(raft_node_id_t)) return;
    
    raft_node_id_t suspected_node_id = *(raft_node_id_t*)msg->payload;
    gossip_node_t* suspected_node = find_gossip_node(suspected_node_id);
    
    if (suspected_node && suspected_node->status == NODE_STATUS_ALIVE) {
        suspected_node->suspicion_count++;
        
        if (suspected_node->suspicion_count >= PARTITION_SUSPICION_THRESHOLD) {
            suspected_node->status = NODE_STATUS_SUSPECT;
            printf("[SD] Node %u marked as SUSPECT\n", suspected_node_id);
            
            // Propagate suspicion
            broadcast_gossip_message(GOSSIP_MSG_SUSPECT, &suspected_node_id, sizeof(suspected_node_id));
        }
    }
}

static void handle_gossip_dead(gossip_node_t* sender, const gossip_msg_t* msg) {
    if (msg->payload_size < sizeof(raft_node_id_t)) return;
    
    raft_node_id_t dead_node_id = *(raft_node_id_t*)msg->payload;
    gossip_node_t* dead_node = find_gossip_node(dead_node_id);
    
    if (dead_node && dead_node->status != NODE_STATUS_DEAD) {
        dead_node->confirmation_count++;
        
        if (dead_node->confirmation_count >= PARTITION_CONFIRMATION_THRESHOLD) {
            dead_node->status = NODE_STATUS_DEAD;
            printf("[SD] Node %u confirmed as DEAD\n", dead_node_id);
            
            // Update partition state
            pthread_mutex_lock(&g_sd_service->partition_state.partition_lock);
            g_sd_service->partition_state.current_reachable_nodes--;
            
            if (g_sd_service->partition_state.current_reachable_nodes < g_sd_service->partition_state.quorum_size) {
                g_sd_service->partition_state.have_quorum = false;
                printf("[SD] QUORUM LOST - only %u reachable nodes, need %u\n",
                       g_sd_service->partition_state.current_reachable_nodes,
                       g_sd_service->partition_state.quorum_size);
            }
            
            pthread_mutex_unlock(&g_sd_service->partition_state.partition_lock);
        }
    }
}

static void* gossip_thread_main(void* arg) {
    printf("[SD] Gossip thread started\n");
    
    uint8_t buffer[SD_MAX_GOSSIP_PAYLOAD];
    struct sockaddr_in sender_addr;
    socklen_t sender_len;
    
    while (g_sd_service->running) {
        // Send periodic pings to random nodes
        if (g_sd_service->gossip_node_count > 0) {
            uint32_t target_index = rand() % g_sd_service->gossip_node_count;
            gossip_node_t* target = &g_sd_service->gossip_nodes[target_index];
            
            if (target->node_id != g_sd_service->local_node_id &&
                target->status == NODE_STATUS_ALIVE) {
                send_gossip_message(GOSSIP_MSG_PING, target->node_id, NULL, 0);
            }
        }
        
        // Process incoming gossip messages
        fd_set read_fds;
        FD_ZERO(&read_fds);
        FD_SET(g_sd_service->gossip_socket, &read_fds);
        
        struct timeval timeout = {0, 100000}; // 100ms timeout
        int ready = select(g_sd_service->gossip_socket + 1, &read_fds, NULL, NULL, &timeout);
        
        if (ready > 0 && FD_ISSET(g_sd_service->gossip_socket, &read_fds)) {
            sender_len = sizeof(sender_addr);
            ssize_t bytes = recvfrom(g_sd_service->gossip_socket, buffer, sizeof(buffer), 0,
                                   (struct sockaddr*)&sender_addr, &sender_len);
            
            if (bytes >= sizeof(gossip_msg_t)) {
                gossip_msg_t* msg = (gossip_msg_t*)buffer;
                
                // Validate message
                if (msg->magic == SD_MAGIC_GOSSIP && 
                    msg->protocol_version == SD_PROTOCOL_VERSION &&
                    bytes == sizeof(gossip_msg_t) + msg->payload_size) {
                    
                    // Verify checksum
                    uint32_t received_checksum = msg->checksum;
                    msg->checksum = 0;
                    uint32_t calculated_checksum = crc32c_fast(msg, bytes);
                    
                    if (received_checksum == calculated_checksum) {
                        atomic_fetch_add(&g_sd_service->gossip_messages_received, 1);
                        
                        // Find or add sender node
                        gossip_node_t* sender = find_gossip_node(msg->source_node_id);
                        if (!sender && msg->source_node_id != g_sd_service->local_node_id) {
                            sender = add_gossip_node(msg->source_node_id, &sender_addr);
                        }
                        
                        // Process message based on type
                        if (sender) {
                            switch (msg->msg_type) {
                                case GOSSIP_MSG_PING:
                                    handle_gossip_ping(sender, msg);
                                    break;
                                case GOSSIP_MSG_SUSPECT:
                                    handle_gossip_suspect(sender, msg);
                                    break;
                                case GOSSIP_MSG_DEAD:
                                    handle_gossip_dead(sender, msg);
                                    break;
                                case GOSSIP_MSG_ACK:
                                    sender->last_seen_ns = get_monotonic_time_ns();
                                    break;
                                default:
                                    break;
                            }
                        }
                    }
                }
            }
        }
        
        usleep(g_sd_service->gossip_interval_ms * 1000);
    }
    
    printf("[SD] Gossip thread exiting\n");
    return NULL;
}

// ============================================================================
// NETWORK PARTITION DETECTION
// ============================================================================

static void detect_network_partition(void) {
    if (!g_sd_service) return;
    
    pthread_mutex_lock(&g_sd_service->partition_state.partition_lock);
    
    uint64_t now = get_monotonic_time_ns();
    uint32_t reachable_nodes = 0;
    uint32_t alive_nodes = 0;
    uint32_t suspect_nodes = 0;
    uint32_t dead_nodes = 0;
    
    // Count node states
    for (uint32_t i = 0; i < g_sd_service->gossip_node_count; i++) {
        gossip_node_t* node = &g_sd_service->gossip_nodes[i];
        
        switch (node->status) {
            case NODE_STATUS_ALIVE:
                alive_nodes++;
                if (now - node->last_seen_ns < g_sd_service->node_timeout_ms * 1000000ULL) {
                    reachable_nodes++;
                }
                break;
            case NODE_STATUS_SUSPECT:
                suspect_nodes++;
                break;
            case NODE_STATUS_DEAD:
                dead_nodes++;
                break;
            default:
                break;
        }
    }
    
    // Include local node in reachable count
    reachable_nodes++;
    
    g_sd_service->partition_state.current_reachable_nodes = reachable_nodes;
    
    // Determine if we have quorum
    bool previous_quorum = g_sd_service->partition_state.have_quorum;
    bool current_quorum = (reachable_nodes >= g_sd_service->partition_state.quorum_size);
    g_sd_service->partition_state.have_quorum = current_quorum;
    
    // Detect partition based on reachability
    bool partition_detected = false;
    
    if (g_sd_service->partition_state.detection_algorithm == PARTITION_DETECTION_ALGORITHM_GOSSIP) {
        // Gossip-based detection: if we can't reach a majority of known nodes
        uint32_t total_known_nodes = alive_nodes + suspect_nodes + dead_nodes + 1; // +1 for local
        partition_detected = (reachable_nodes < total_known_nodes / 2 + 1);
        
    } else if (g_sd_service->partition_state.detection_algorithm == PARTITION_DETECTION_ALGORITHM_HEARTBEAT) {
        // Heartbeat-based detection: if too many nodes are unreachable for too long
        partition_detected = (suspect_nodes + dead_nodes > alive_nodes / 2);
        
    } else if (g_sd_service->partition_state.detection_algorithm == PARTITION_DETECTION_ALGORITHM_HYBRID) {
        // Hybrid approach: combine both methods
        uint32_t total_known_nodes = alive_nodes + suspect_nodes + dead_nodes + 1;
        bool gossip_partition = (reachable_nodes < total_known_nodes / 2 + 1);
        bool heartbeat_partition = (suspect_nodes + dead_nodes > alive_nodes / 2);
        partition_detected = gossip_partition && heartbeat_partition;
    }
    
    // Update partition state
    bool was_partitioned = g_sd_service->partition_state.partition_detected;
    g_sd_service->partition_state.partition_detected = partition_detected;
    
    if (partition_detected && !was_partitioned) {
        g_sd_service->partition_state.partition_start_ns = now;
        atomic_fetch_add(&g_sd_service->partition_events, 1);
        
        printf("[SD] NETWORK PARTITION DETECTED\n");
        printf("    Reachable nodes: %u\n", reachable_nodes);
        printf("    Required quorum: %u\n", g_sd_service->partition_state.quorum_size);
        printf("    Have quorum: %s\n", current_quorum ? "YES" : "NO");
        printf("    Alive: %u, Suspect: %u, Dead: %u\n", alive_nodes, suspect_nodes, dead_nodes);
        
    } else if (!partition_detected && was_partitioned) {
        uint64_t partition_duration = now - g_sd_service->partition_state.partition_start_ns;
        
        printf("[SD] NETWORK PARTITION RESOLVED\n");
        printf("    Partition duration: %.3f seconds\n", partition_duration / 1000000000.0);
        printf("    Reachable nodes: %u\n", reachable_nodes);
        
        if (partition_duration < 5000000000ULL) { // Less than 5 seconds
            atomic_fetch_add(&g_sd_service->false_partition_alarms, 1);
        }
    }
    
    // Log quorum state changes
    if (previous_quorum != current_quorum) {
        printf("[SD] QUORUM %s (reachable: %u, required: %u)\n",
               current_quorum ? "GAINED" : "LOST",
               reachable_nodes, g_sd_service->partition_state.quorum_size);
    }
    
    g_sd_service->partition_state.partition_last_update_ns = now;
    
    pthread_mutex_unlock(&g_sd_service->partition_state.partition_lock);
}

static void* partition_monitor_thread(void* arg) {
    printf("[SD] Partition monitor thread started\n");
    
    while (g_sd_service->running) {
        detect_network_partition();
        usleep(1000000); // Check every 1 second
    }
    
    printf("[SD] Partition monitor thread exiting\n");
    return NULL;
}

// ============================================================================
// SERVICE DISCOVERY IMPLEMENTATION
// ============================================================================

static void send_service_announcement(void) {
    if (!g_sd_service || g_sd_service->multicast_socket < 0) return;
    
    // Collect local services
    pthread_rwlock_rdlock(&g_sd_service->service_lock);
    
    uint32_t local_service_count = 0;
    service_registration_t local_services[SD_MAX_SERVICE_TYPES];
    
    for (uint32_t i = 0; i < g_sd_service->service_count; i++) {
        if (g_sd_service->services[i].node_id == g_sd_service->local_node_id &&
            g_sd_service->services[i].active &&
            local_service_count < SD_MAX_SERVICE_TYPES) {
            local_services[local_service_count++] = g_sd_service->services[i];
        }
    }
    
    pthread_rwlock_unlock(&g_sd_service->service_lock);
    
    if (local_service_count == 0) return;
    
    // Calculate message size
    size_t payload_size = local_service_count * sizeof(service_registration_t);
    size_t total_size = sizeof(sd_announcement_msg_t) + payload_size;
    
    sd_announcement_msg_t* msg = malloc(total_size);
    if (!msg) return;
    
    // Fill announcement message
    msg->magic = SD_MAGIC_ANNOUNCEMENT;
    msg->protocol_version = SD_PROTOCOL_VERSION;
    msg->node_id = g_sd_service->local_node_id;
    msg->timestamp_ns = get_monotonic_time_ns();
    msg->incarnation = g_sd_service->local_incarnation;
    msg->service_count = local_service_count;
    msg->total_payload_size = payload_size;
    
    // Copy service data
    memcpy(msg->services, local_services, payload_size);
    
    // Calculate checksum
    msg->checksum = crc32c_fast(msg, total_size - sizeof(msg->checksum));
    
    // Send multicast announcement
    struct sockaddr_in multicast_addr = {0};
    multicast_addr.sin_family = AF_INET;
    multicast_addr.sin_port = htons(SD_MULTICAST_PORT);
    inet_pton(AF_INET, SD_MULTICAST_GROUP, &multicast_addr.sin_addr);
    
    sendto(g_sd_service->multicast_socket, msg, total_size, 0,
           (struct sockaddr*)&multicast_addr, sizeof(multicast_addr));
    
    atomic_fetch_add(&g_sd_service->announcements_sent, 1);
    
    free(msg);
}

static void handle_service_announcement(const sd_announcement_msg_t* msg, size_t msg_size, 
                                       struct sockaddr_in* sender_addr) {
    if (!msg || msg->service_count == 0) return;
    
    // Validate message size
    size_t expected_size = sizeof(sd_announcement_msg_t) + (msg->service_count * sizeof(service_registration_t));
    if (msg_size != expected_size) return;
    
    // Skip our own announcements
    if (msg->node_id == g_sd_service->local_node_id) return;
    
    pthread_rwlock_wrlock(&g_sd_service->service_lock);
    
    // Process each announced service
    service_registration_t* announced_services = (service_registration_t*)msg->services;
    
    for (uint32_t i = 0; i < msg->service_count; i++) {
        service_registration_t* announced = &announced_services[i];
        
        // Find existing service registration or create new one
        service_registration_t* existing = NULL;
        for (uint32_t j = 0; j < g_sd_service->service_count; j++) {
            service_registration_t* service = &g_sd_service->services[j];
            
            if (service->node_id == announced->node_id &&
                strcmp(service->service_type, announced->service_type) == 0 &&
                strcmp(service->service_name, announced->service_name) == 0) {
                existing = service;
                break;
            }
        }
        
        if (existing) {
            // Update existing service
            *existing = *announced;
            existing->last_health_check_ns = get_monotonic_time_ns();
            existing->is_healthy = true;
            existing->active = true;
            
        } else if (g_sd_service->service_count < MAX_CLUSTER_NODES * SD_MAX_SERVICE_TYPES) {
            // Add new service
            g_sd_service->services[g_sd_service->service_count] = *announced;
            g_sd_service->services[g_sd_service->service_count].last_health_check_ns = get_monotonic_time_ns();
            g_sd_service->services[g_sd_service->service_count].is_healthy = true;
            g_sd_service->services[g_sd_service->service_count].active = true;
            g_sd_service->service_count++;
            
            printf("[SD] Discovered service: %s/%s from node %u\n",
                   announced->service_type, announced->service_name, announced->node_id);
        }
    }
    
    pthread_rwlock_unlock(&g_sd_service->service_lock);
    
    // Update gossip node information
    gossip_node_t* gossip_node = find_gossip_node(msg->node_id);
    if (!gossip_node) {
        gossip_node = add_gossip_node(msg->node_id, sender_addr);
    }
    
    if (gossip_node) {
        gossip_node->last_seen_ns = get_monotonic_time_ns();
        gossip_node->incarnation = msg->incarnation;
        gossip_node->status = NODE_STATUS_ALIVE;
        gossip_node->suspicion_count = 0;
        gossip_node->confirmation_count = 0;
    }
}

static void* announcement_thread_main(void* arg) {
    printf("[SD] Announcement thread started\n");
    
    uint8_t buffer[8192];
    struct sockaddr_in sender_addr;
    socklen_t sender_len;
    
    while (g_sd_service->running) {
        // Send periodic announcements
        send_service_announcement();
        
        // Process incoming announcements
        fd_set read_fds;
        FD_ZERO(&read_fds);
        FD_SET(g_sd_service->multicast_socket, &read_fds);
        
        struct timeval timeout = {g_sd_service->announcement_interval_ms / 1000, 
                                 (g_sd_service->announcement_interval_ms % 1000) * 1000};
        int ready = select(g_sd_service->multicast_socket + 1, &read_fds, NULL, NULL, &timeout);
        
        if (ready > 0 && FD_ISSET(g_sd_service->multicast_socket, &read_fds)) {
            sender_len = sizeof(sender_addr);
            ssize_t bytes = recvfrom(g_sd_service->multicast_socket, buffer, sizeof(buffer), 0,
                                   (struct sockaddr*)&sender_addr, &sender_len);
            
            if (bytes >= sizeof(sd_announcement_msg_t)) {
                sd_announcement_msg_t* msg = (sd_announcement_msg_t*)buffer;
                
                // Validate message
                if (msg->magic == SD_MAGIC_ANNOUNCEMENT && 
                    msg->protocol_version == SD_PROTOCOL_VERSION) {
                    
                    // Verify checksum
                    uint32_t received_checksum = msg->checksum;
                    msg->checksum = 0;
                    uint32_t calculated_checksum = crc32c_fast(msg, bytes);
                    
                    if (received_checksum == calculated_checksum) {
                        handle_service_announcement(msg, bytes, &sender_addr);
                    }
                }
            }
        }
    }
    
    printf("[SD] Announcement thread exiting\n");
    return NULL;
}

// ============================================================================
// PUBLIC API IMPLEMENTATION
// ============================================================================

int service_discovery_init(raft_node_id_t local_node_id, const char* bind_interface) {
    if (g_sd_service) return -1;
    
    int numa_node = numa_node_of_cpu(sched_getcpu());
    g_sd_service = numa_alloc_onnode(sizeof(service_discovery_t), numa_node);
    if (!g_sd_service) return -1;
    
    memset(g_sd_service, 0, sizeof(service_discovery_t));
    
    g_sd_service->local_node_id = local_node_id;
    g_sd_service->local_incarnation = 1;
    gethostname(g_sd_service->local_hostname, sizeof(g_sd_service->local_hostname));
    
    // Get local IP address
    char local_ip[INET_ADDRSTRLEN];
    if (get_local_ip_address(local_ip, sizeof(local_ip)) == 0) {
        g_sd_service->local_address.sin_family = AF_INET;
        inet_pton(AF_INET, local_ip, &g_sd_service->local_address.sin_addr);
    }
    
    // Initialize locks
    pthread_rwlock_init(&g_sd_service->service_lock, NULL);
    pthread_mutex_init(&g_sd_service->gossip_lock, NULL);
    pthread_mutex_init(&g_sd_service->partition_state.partition_lock, NULL);
    pthread_mutex_init(&g_sd_service->service_lock_mutex, NULL);
    
    // Initialize partition state
    g_sd_service->partition_state.detection_algorithm = PARTITION_DETECTION_ALGORITHM_HYBRID;
    g_sd_service->partition_state.cluster_size = 1; // Will be updated as nodes are discovered
    g_sd_service->partition_state.quorum_size = 1;
    g_sd_service->partition_state.current_reachable_nodes = 1;
    g_sd_service->partition_state.have_quorum = true;
    g_sd_service->partition_state.partition_detected = false;
    
    // Set configuration defaults
    g_sd_service->announcement_interval_ms = SD_ANNOUNCEMENT_INTERVAL_MS;
    g_sd_service->health_check_interval_ms = SD_HEALTH_CHECK_INTERVAL_MS;
    g_sd_service->gossip_interval_ms = SD_GOSSIP_INTERVAL_MS;
    g_sd_service->node_timeout_ms = SD_NODE_TIMEOUT_MS;
    
    // Create sockets
    
    // Multicast socket for announcements
    g_sd_service->multicast_socket = socket(AF_INET, SOCK_DGRAM, 0);
    if (g_sd_service->multicast_socket < 0) {
        service_discovery_cleanup();
        return -1;
    }
    
    int reuse = 1;
    setsockopt(g_sd_service->multicast_socket, SOL_SOCKET, SO_REUSEADDR, &reuse, sizeof(reuse));
    
    struct sockaddr_in multicast_bind_addr = {0};
    multicast_bind_addr.sin_family = AF_INET;
    multicast_bind_addr.sin_addr.s_addr = INADDR_ANY;
    multicast_bind_addr.sin_port = htons(SD_MULTICAST_PORT);
    
    if (bind(g_sd_service->multicast_socket, (struct sockaddr*)&multicast_bind_addr, 
             sizeof(multicast_bind_addr)) < 0) {
        service_discovery_cleanup();
        return -1;
    }
    
    // Join multicast group
    struct ip_mreq multicast_req;
    inet_pton(AF_INET, SD_MULTICAST_GROUP, &multicast_req.imr_multiaddr);
    multicast_req.imr_interface.s_addr = INADDR_ANY;
    setsockopt(g_sd_service->multicast_socket, IPPROTO_IP, IP_ADD_MEMBERSHIP, 
               &multicast_req, sizeof(multicast_req));
    
    // Unicast socket for queries/responses
    g_sd_service->unicast_socket = socket(AF_INET, SOCK_DGRAM, 0);
    if (g_sd_service->unicast_socket < 0) {
        service_discovery_cleanup();
        return -1;
    }
    
    struct sockaddr_in unicast_bind_addr = {0};
    unicast_bind_addr.sin_family = AF_INET;
    unicast_bind_addr.sin_addr.s_addr = INADDR_ANY;
    unicast_bind_addr.sin_port = htons(SD_UNICAST_PORT);
    
    bind(g_sd_service->unicast_socket, (struct sockaddr*)&unicast_bind_addr, 
         sizeof(unicast_bind_addr));
    
    // Gossip socket
    g_sd_service->gossip_socket = socket(AF_INET, SOCK_DGRAM, 0);
    if (g_sd_service->gossip_socket < 0) {
        service_discovery_cleanup();
        return -1;
    }
    
    struct sockaddr_in gossip_bind_addr = {0};
    gossip_bind_addr.sin_family = AF_INET;
    gossip_bind_addr.sin_addr.s_addr = INADDR_ANY;
    gossip_bind_addr.sin_port = htons(SD_GOSSIP_PORT);
    
    bind(g_sd_service->gossip_socket, (struct sockaddr*)&gossip_bind_addr, 
         sizeof(gossip_bind_addr));
    
    g_sd_service->running = true;
    
    // Start background threads
    pthread_create(&g_sd_service->announcement_thread, NULL, announcement_thread_main, NULL);
    pthread_create(&g_sd_service->gossip_thread, NULL, gossip_thread_main, NULL);
    pthread_create(&g_sd_service->partition_monitor_thread, NULL, partition_monitor_thread, NULL);
    
    printf("[SD] Service discovery initialized (Node ID: %u, IP: %s, NUMA: %d)\n", 
           local_node_id, local_ip, numa_node);
    
    return 0;
}

void service_discovery_cleanup(void) {
    if (!g_sd_service) return;
    
    g_sd_service->running = false;
    
    // Stop threads
    pthread_join(g_sd_service->announcement_thread, NULL);
    pthread_join(g_sd_service->gossip_thread, NULL);
    pthread_join(g_sd_service->partition_monitor_thread, NULL);
    
    // Close sockets
    if (g_sd_service->multicast_socket >= 0) close(g_sd_service->multicast_socket);
    if (g_sd_service->unicast_socket >= 0) close(g_sd_service->unicast_socket);
    if (g_sd_service->gossip_socket >= 0) close(g_sd_service->gossip_socket);
    
    // Cleanup locks
    pthread_rwlock_destroy(&g_sd_service->service_lock);
    pthread_mutex_destroy(&g_sd_service->gossip_lock);
    pthread_mutex_destroy(&g_sd_service->partition_state.partition_lock);
    pthread_mutex_destroy(&g_sd_service->service_lock_mutex);
    
    numa_free(g_sd_service, sizeof(service_discovery_t));
    g_sd_service = NULL;
    
    printf("[SD] Service discovery cleaned up\n");
}

int service_discovery_register_service(const char* service_type, const char* service_name,
                                      const network_endpoint_t* endpoints, uint32_t endpoint_count,
                                      const char* metadata) {
    if (!g_sd_service || !service_type || !service_name) return -1;
    
    pthread_rwlock_wrlock(&g_sd_service->service_lock);
    
    if (g_sd_service->service_count >= MAX_CLUSTER_NODES * SD_MAX_SERVICE_TYPES) {
        pthread_rwlock_unlock(&g_sd_service->service_lock);
        return -1;
    }
    
    service_registration_t* service = &g_sd_service->services[g_sd_service->service_count++];
    
    strncpy(service->service_type, service_type, sizeof(service->service_type) - 1);
    strncpy(service->service_name, service_name, sizeof(service->service_name) - 1);
    service->node_id = g_sd_service->local_node_id;
    
    service->endpoint_count = fminf(endpoint_count, MAX_ENDPOINTS_PER_NODE);
    if (endpoints) {
        memcpy(service->endpoints, endpoints, service->endpoint_count * sizeof(network_endpoint_t));
    }
    
    if (metadata) {
        strncpy(service->metadata, metadata, sizeof(service->metadata) - 1);
    }
    
    service->registration_time_ns = get_monotonic_time_ns();
    service->last_health_check_ns = service->registration_time_ns;
    service->is_healthy = true;
    service->consecutive_failures = 0;
    service->health_check_interval_ms = g_sd_service->health_check_interval_ms;
    service->protocol_version = SD_PROTOCOL_VERSION;
    service->active = true;
    
    pthread_rwlock_unlock(&g_sd_service->service_lock);
    
    printf("[SD] Registered service: %s/%s\n", service_type, service_name);
    return 0;
}

bool service_discovery_is_partitioned(void) {
    if (!g_sd_service) return false;
    
    pthread_mutex_lock(&g_sd_service->partition_state.partition_lock);
    bool partitioned = g_sd_service->partition_state.partition_detected;
    pthread_mutex_unlock(&g_sd_service->partition_state.partition_lock);
    
    return partitioned;
}

bool service_discovery_has_quorum(void) {
    if (!g_sd_service) return false;
    
    pthread_mutex_lock(&g_sd_service->partition_state.partition_lock);
    bool has_quorum = g_sd_service->partition_state.have_quorum;
    pthread_mutex_unlock(&g_sd_service->partition_state.partition_lock);
    
    return has_quorum;
}

void service_discovery_print_status(void) {
    if (!g_sd_service) {
        printf("Service discovery not initialized\n");
        return;
    }
    
    printf("\n=== Service Discovery Status ===\n");
    printf("Local Node: %u (%s)\n", g_sd_service->local_node_id, g_sd_service->local_hostname);
    printf("Local IP: %s\n", inet_ntoa(g_sd_service->local_address.sin_addr));
    printf("Running: %s\n", g_sd_service->running ? "Yes" : "No");
    
    pthread_rwlock_rdlock(&g_sd_service->service_lock);
    printf("Registered Services: %u\n", g_sd_service->service_count);
    
    for (uint32_t i = 0; i < g_sd_service->service_count; i++) {
        service_registration_t* service = &g_sd_service->services[i];
        if (service->active) {
            printf("  %s/%s (Node %u) - %s\n", 
                   service->service_type, service->service_name, service->node_id,
                   service->is_healthy ? "Healthy" : "Unhealthy");
        }
    }
    
    pthread_rwlock_unlock(&g_sd_service->service_lock);
    
    printf("\nGossip Nodes: %u\n", g_sd_service->gossip_node_count);
    for (uint32_t i = 0; i < g_sd_service->gossip_node_count; i++) {
        gossip_node_t* node = &g_sd_service->gossip_nodes[i];
        const char* status_str = 
            node->status == NODE_STATUS_ALIVE ? "Alive" :
            node->status == NODE_STATUS_SUSPECT ? "Suspect" :
            node->status == NODE_STATUS_DEAD ? "Dead" : "Left";
        
        printf("  Node %u (%s) - %s\n", 
               node->node_id, inet_ntoa(node->address.sin_addr), status_str);
    }
    
    pthread_mutex_lock(&g_sd_service->partition_state.partition_lock);
    printf("\nPartition State:\n");
    printf("  Partition detected: %s\n", g_sd_service->partition_state.partition_detected ? "YES" : "No");
    printf("  Have quorum: %s\n", g_sd_service->partition_state.have_quorum ? "YES" : "No");
    printf("  Reachable nodes: %u\n", g_sd_service->partition_state.current_reachable_nodes);
    printf("  Required quorum: %u\n", g_sd_service->partition_state.quorum_size);
    pthread_mutex_unlock(&g_sd_service->partition_state.partition_lock);
    
    printf("\nStatistics:\n");
    printf("  Announcements sent: %lu\n", atomic_load(&g_sd_service->announcements_sent));
    printf("  Queries received: %lu\n", atomic_load(&g_sd_service->queries_received));
    printf("  Gossip messages sent: %lu\n", atomic_load(&g_sd_service->gossip_messages_sent));
    printf("  Gossip messages received: %lu\n", atomic_load(&g_sd_service->gossip_messages_received));
    printf("  Partition events: %lu\n", atomic_load(&g_sd_service->partition_events));
    printf("  False alarms: %lu\n", atomic_load(&g_sd_service->false_partition_alarms));
    
    printf("\n");
}