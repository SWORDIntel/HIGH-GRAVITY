/*
 * UNIFIED AGENT RUNTIME SYSTEM
 * 
 * A hybrid IPC system that uses the optimal communication method
 * based on message priority, size, and requirements.
 * 
 * Architecture:
 * - CRITICAL: Shared memory ring buffers (50ns latency)
 * - HIGH: io_uring with shared buffers (500ns latency)
 * - NORMAL: Unix domain sockets (2μs latency)
 * - LOW: Memory-mapped files (10μs latency)
 * - BATCH: DMA regions for GPU/NPU
 */

#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <stdbool.h>
#include <pthread.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>
#include <errno.h>
#include "compatibility_layer.h"
#include <sched.h>
#include <signal.h>
#include <time.h>

#include "agent_protocol.h"  // Our enhanced protocol

// ============================================================================
// AGENT DEFINITIONS
// ============================================================================

typedef enum {
    AGENT_DIRECTOR = 0,
    AGENT_PROJECT_ORCHESTRATOR,
    AGENT_ARCHITECT,
    AGENT_SECURITY,
    AGENT_CONSTRUCTOR,
    AGENT_TESTBED,
    AGENT_OPTIMIZER,
    AGENT_DEBUGGER,
    AGENT_DEPLOYER,
    AGENT_MONITOR,
    AGENT_DATABASE,
    AGENT_ML_OPS,
    AGENT_PATCHER,
    AGENT_LINTER,
    AGENT_DOCGEN,
    AGENT_PACKAGER,
    AGENT_API_DESIGNER,
    AGENT_WEB,
    AGENT_MOBILE,
    AGENT_PYGUI,
    AGENT_C_INTERNAL,
    AGENT_PYTHON_INTERNAL,
    AGENT_SECURITY_CHAOS,
    AGENT_MAX
} agent_type_t;

typedef struct {
    agent_type_t type;
    char name[64];
    uint32_t capabilities;
    priority_level_t default_priority;
    core_type_t preferred_core;
    size_t memory_quota;
    bool requires_gpu;
    bool requires_npu;
} agent_definition_t;

// Agent definitions with their characteristics
static const agent_definition_t AGENT_DEFINITIONS[AGENT_MAX] = {
    [AGENT_DIRECTOR] = {
        .type = AGENT_DIRECTOR,
        .name = "DIRECTOR",
        .capabilities = 0xFFFFFFFF,  // All capabilities
        .default_priority = PRIORITY_CRITICAL,
        .preferred_core = CORE_TYPE_PERFORMANCE,
        .memory_quota = 1024 * 1024 * 1024,  // 1GB
        .requires_gpu = false,
        .requires_npu = true  // For decision making
    },
    [AGENT_PROJECT_ORCHESTRATOR] = {
        .type = AGENT_PROJECT_ORCHESTRATOR,
        .name = "PROJECT_ORCHESTRATOR",
        .capabilities = 0x7FFFFFFF,
        .default_priority = PRIORITY_HIGH,
        .preferred_core = CORE_TYPE_PERFORMANCE,
        .memory_quota = 512 * 1024 * 1024,
        .requires_gpu = false,
        .requires_npu = false
    },
    [AGENT_OPTIMIZER] = {
        .type = AGENT_OPTIMIZER,
        .name = "OPTIMIZER",
        .capabilities = 0x0F0F0F0F,
        .default_priority = PRIORITY_HIGH,
        .preferred_core = CORE_TYPE_PERFORMANCE,
        .memory_quota = 2048 * 1024 * 1024,  // 2GB for profiling
        .requires_gpu = true,  // For parallel optimization
        .requires_npu = false
    },
    // ... other agents configured similarly
};

// ============================================================================
// UNIFIED IPC CHANNELS
// ============================================================================

typedef struct {
    // Shared memory for critical messages (P-core to P-core)
    struct {
        void* base_addr;
        size_t size;
        enhanced_ring_buffer_t* ring;
        pthread_mutex_t lock;
    } shared_mem;
    
    // io_uring for high priority async
    struct {
        struct io_uring ring;
        struct io_uring_sqe* sqe;
        struct io_uring_cqe* cqe;
        bool initialized;
    } io_uring_channel;
    
    // Unix domain sockets for reliable communication
    struct {
        int server_fd;
        int client_fds[AGENT_MAX];
        struct sockaddr_un addr;
        char socket_path[108];
    } unix_socket;
    
    // Memory-mapped file for persistent queue
    struct {
        int fd;
        void* addr;
        size_t size;
        _Atomic uint64_t write_offset;
        _Atomic uint64_t read_offset;
    } mmap_queue;
    
    // DMA region for GPU/NPU
    struct {
        void* pinned_memory;
        size_t size;
        bool gpu_registered;
        bool npu_registered;
    } dma_region;
    
} unified_ipc_t;

// ============================================================================
// AGENT RUNTIME CONTEXT
// ============================================================================

typedef struct agent_context {
    // Agent identity
    agent_type_t type;
    uint32_t instance_id;
    char name[64];
    
    // Execution context
    pthread_t thread;
    cpu_set_t cpu_affinity;
    int numa_node;
    volatile bool running;
    
    // IPC channels
    unified_ipc_t* ipc;
    
    // Message handlers
    void (*message_handler)(struct agent_context*, enhanced_msg_header_t*, void*);
    void (*init_handler)(struct agent_context*);
    void (*shutdown_handler)(struct agent_context*);
    
    // Statistics
    _Atomic uint64_t messages_sent;
    _Atomic uint64_t messages_received;
    _Atomic uint64_t bytes_processed;
    
    // Agent-specific data
    void* private_data;
    
} agent_context_t;

// ============================================================================
// GLOBAL RUNTIME STATE
// ============================================================================

typedef struct {
    // All agents
    agent_context_t* agents[AGENT_MAX];
    int num_active_agents;
    
    // Global IPC
    unified_ipc_t* global_ipc;
    
    // Discovery service
    struct {
        _Atomic uint32_t registry[AGENT_MAX];
        pthread_rwlock_t lock;
    } discovery;
    
    // Resource management
    struct {
        _Atomic uint64_t memory_used;
        _Atomic uint64_t cpu_cycles;
        uint64_t memory_limit;
    } resources;
    
    // Runtime control
    volatile bool running;
    pthread_t monitor_thread;
    
} agent_runtime_t;

static agent_runtime_t* g_runtime = NULL;

// ============================================================================
// IPC INITIALIZATION
// ============================================================================

static unified_ipc_t* init_unified_ipc(const char* namespace) {
    unified_ipc_t* ipc = calloc(1, sizeof(unified_ipc_t));
    if (!ipc) return NULL;
    
    // 1. Initialize shared memory (fastest path)
    ipc->shared_mem.size = 256 * 1024 * 1024;  // 256MB
    ipc->shared_mem.base_addr = mmap(NULL, ipc->shared_mem.size,
                                     PROT_READ | PROT_WRITE,
                                     MAP_SHARED | MAP_ANONYMOUS | MAP_HUGETLB,
                                     -1, 0);
    
    if (ipc->shared_mem.base_addr == MAP_FAILED) {
        // Fallback to regular pages
        ipc->shared_mem.base_addr = mmap(NULL, ipc->shared_mem.size,
                                        PROT_READ | PROT_WRITE,
                                        MAP_SHARED | MAP_ANONYMOUS,
                                        -1, 0);
    }
    
    // Create ring buffer in shared memory
    ipc->shared_mem.ring = (enhanced_ring_buffer_t*)ipc->shared_mem.base_addr;
    // Initialize ring buffer...
    
    pthread_mutex_init(&ipc->shared_mem.lock, NULL);
    
    // 2. Initialize io_uring (async path)
    if (io_uring_queue_init(256, &ipc->io_uring_channel.ring, 
                           IORING_SETUP_SQPOLL) == 0) {
        ipc->io_uring_channel.initialized = true;
        printf("io_uring initialized with 256 entries\n");
    }
    
    // 3. Initialize Unix domain socket (reliable path)
    ipc->unix_socket.server_fd = socket(AF_UNIX, SOCK_DGRAM, 0);
    if (ipc->unix_socket.server_fd >= 0) {
        snprintf(ipc->unix_socket.socket_path, sizeof(ipc->unix_socket.socket_path),
                "/tmp/agent_%s.sock", namespace);
        
        unlink(ipc->unix_socket.socket_path);  // Remove if exists
        
        ipc->unix_socket.addr.sun_family = AF_UNIX;
        strncpy(ipc->unix_socket.addr.sun_path, ipc->unix_socket.socket_path,
               sizeof(ipc->unix_socket.addr.sun_path) - 1);
        
        if (bind(ipc->unix_socket.server_fd, 
                (struct sockaddr*)&ipc->unix_socket.addr,
                sizeof(ipc->unix_socket.addr)) == 0) {
            printf("Unix socket bound to %s\n", ipc->unix_socket.socket_path);
        }
    }
    
    // 4. Initialize memory-mapped queue (persistent path)
    char mmap_path[256];
    snprintf(mmap_path, sizeof(mmap_path), "/tmp/agent_%s.queue", namespace);
    
    ipc->mmap_queue.fd = open(mmap_path, O_RDWR | O_CREAT, 0666);
    if (ipc->mmap_queue.fd >= 0) {
        ipc->mmap_queue.size = 64 * 1024 * 1024;  // 64MB
        
        // Ensure file size
        ftruncate(ipc->mmap_queue.fd, ipc->mmap_queue.size);
        
        ipc->mmap_queue.addr = mmap(NULL, ipc->mmap_queue.size,
                                   PROT_READ | PROT_WRITE,
                                   MAP_SHARED, ipc->mmap_queue.fd, 0);
        
        if (ipc->mmap_queue.addr != MAP_FAILED) {
            atomic_store(&ipc->mmap_queue.write_offset, 0);
            atomic_store(&ipc->mmap_queue.read_offset, 0);
            printf("Memory-mapped queue initialized: %s\n", mmap_path);
        }
    }
    
    // 5. Initialize DMA region for GPU/NPU
    ipc->dma_region.size = 128 * 1024 * 1024;  // 128MB
    
    // Allocate pinned memory for DMA
    if (posix_memalign(&ipc->dma_region.pinned_memory, 4096, 
                       ipc->dma_region.size) == 0) {
        // Lock pages to prevent swapping
        mlock(ipc->dma_region.pinned_memory, ipc->dma_region.size);
        
        // Register with GPU if available
        // ... GPU registration code
        
        // Register with NPU if available
        // ... NPU registration code
        
        printf("DMA region allocated: %zu MB\n", ipc->dma_region.size / (1024*1024));
    }
    
    return ipc;
}

// ============================================================================
// ADAPTIVE MESSAGE SENDING
// ============================================================================

static int send_agent_message(unified_ipc_t* ipc, 
                             agent_type_t source,
                             agent_type_t target,
                             enhanced_msg_header_t* msg,
                             void* payload) {
    // Select IPC method based on priority and requirements
    
    if (msg->priority == PRIORITY_CRITICAL) {
        // CRITICAL: Use shared memory (50ns latency)
        return ring_buffer_write_priority(ipc->shared_mem.ring, msg, payload);
        
    } else if (msg->priority == PRIORITY_HIGH && ipc->io_uring_channel.initialized) {
        // HIGH: Use io_uring for async (500ns latency)
        struct io_uring_sqe* sqe = io_uring_get_sqe(&ipc->io_uring_channel.ring);
        if (sqe) {
            // Prepare io_uring submission
            io_uring_prep_write(sqe, target, msg, 
                              sizeof(*msg) + msg->payload_len, 0);
            io_uring_sqe_set_data(sqe, msg);
            return io_uring_submit(&ipc->io_uring_channel.ring);
        }
        
    } else if (msg->priority == PRIORITY_NORMAL) {
        // NORMAL: Use Unix socket (2μs latency)
        struct msghdr msghdr = {0};
        struct iovec iov[2];
        
        iov[0].iov_base = msg;
        iov[0].iov_len = sizeof(*msg);
        iov[1].iov_base = payload;
        iov[1].iov_len = msg->payload_len;
        
        msghdr.msg_iov = iov;
        msghdr.msg_iovlen = 2;
        
        return sendmsg(ipc->unix_socket.client_fds[target], &msghdr, 0);
        
    } else if (msg->priority == PRIORITY_LOW) {
        // LOW: Use memory-mapped queue (10μs latency)
        size_t total_size = sizeof(*msg) + msg->payload_len;
        uint64_t write_offset = atomic_fetch_add(&ipc->mmap_queue.write_offset, 
                                                total_size);
        
        if (write_offset + total_size <= ipc->mmap_queue.size) {
            uint8_t* dst = (uint8_t*)ipc->mmap_queue.addr + write_offset;
            memcpy(dst, msg, sizeof(*msg));
            if (payload && msg->payload_len > 0) {
                memcpy(dst + sizeof(*msg), payload, msg->payload_len);
            }
            return total_size;
        }
        
    } else if (msg->priority == PRIORITY_BATCH && ipc->dma_region.pinned_memory) {
        // BATCH: Use DMA region for GPU/NPU
        // This would queue work for batch processing
        // ... DMA transfer code
    }
    
    return -1;  // Failed to send
}

// ============================================================================
// AGENT EXECUTION ENGINE
// ============================================================================

static void* agent_thread_main(void* arg) {
    agent_context_t* agent = (agent_context_t*)arg;
    
    // Set thread name
    char thread_name[16];
    snprintf(thread_name, sizeof(thread_name), "AG_%s", 
            AGENT_DEFINITIONS[agent->type].name);
    pthread_setname_np(pthread_self(), thread_name);
    
    // Set CPU affinity based on agent type
    sched_setaffinity(0, sizeof(cpu_set_t), &agent->cpu_affinity);
    
    // Set scheduling priority
    struct sched_param param;
    if (AGENT_DEFINITIONS[agent->type].default_priority <= PRIORITY_HIGH) {
        param.sched_priority = 10;  // Higher priority
        pthread_setschedparam(pthread_self(), SCHED_FIFO, &param);
    }
    
    // Initialize agent
    if (agent->init_handler) {
        agent->init_handler(agent);
    }
    
    printf("Agent %s started on CPU %d\n", agent->name, sched_getcpu());
    
    // Main message loop
    enhanced_msg_header_t msg;
    uint8_t payload[65536];
    
    while (agent->running) {
        bool received = false;
        
        // Check all IPC channels in priority order
        
        // 1. Check shared memory (critical)
        for (int p = PRIORITY_CRITICAL; p <= PRIORITY_HIGH; p++) {
            if (ring_buffer_read_priority(agent->ipc->shared_mem.ring, 
                                        p, &msg, payload)) {
                received = true;
                break;
            }
        }
        
        // 2. Check io_uring (high priority async)
        if (!received && agent->ipc->io_uring_channel.initialized) {
            struct io_uring_cqe* cqe;
            if (io_uring_peek_cqe(&agent->ipc->io_uring_channel.ring, &cqe) == 0) {
                // Process async completion
                // ...
                io_uring_cqe_seen(&agent->ipc->io_uring_channel.ring, cqe);
                received = true;
            }
        }
        
        // 3. Check Unix socket (normal)
        if (!received) {
            struct pollfd pfd = {
                .fd = agent->ipc->unix_socket.server_fd,
                .events = POLLIN
            };
            
            if (poll(&pfd, 1, 0) > 0) {
                ssize_t n = recv(agent->ipc->unix_socket.server_fd,
                               &msg, sizeof(msg), MSG_DONTWAIT);
                if (n > 0) {
                    if (msg.payload_len > 0) {
                        recv(agent->ipc->unix_socket.server_fd,
                            payload, msg.payload_len, MSG_DONTWAIT);
                    }
                    received = true;
                }
            }
        }
        
        // Process message
        if (received) {
            if (msg.target_agent == agent->type || 
                msg.target_agent == AGENT_MAX) {  // Broadcast
                
                atomic_fetch_add(&agent->messages_received, 1);
                atomic_fetch_add(&agent->bytes_processed, 
                                sizeof(msg) + msg.payload_len);
                
                if (agent->message_handler) {
                    agent->message_handler(agent, &msg, payload);
                }
            }
        } else {
            // No messages - yield CPU
            if (AGENT_DEFINITIONS[agent->type].preferred_core == CORE_TYPE_EFFICIENCY) {
                usleep(100);  // E-cores can sleep longer
            } else {
                sched_yield();  // P-cores just yield
            }
        }
    }
    
    // Cleanup
    if (agent->shutdown_handler) {
        agent->shutdown_handler(agent);
    }
    
    printf("Agent %s stopped\n", agent->name);
    return NULL;
}

// ============================================================================
// AGENT CREATION AND MANAGEMENT
// ============================================================================

static agent_context_t* create_agent(agent_type_t type, unified_ipc_t* ipc) {
    agent_context_t* agent = calloc(1, sizeof(agent_context_t));
    if (!agent) return NULL;
    
    const agent_definition_t* def = &AGENT_DEFINITIONS[type];
    
    agent->type = type;
    agent->instance_id = rand();
    strncpy(agent->name, def->name, sizeof(agent->name) - 1);
    agent->ipc = ipc;
    agent->running = true;
    
    // Set CPU affinity based on agent requirements
    CPU_ZERO(&agent->cpu_affinity);
    
    if (def->preferred_core == CORE_TYPE_PERFORMANCE) {
        // Assign to P-cores
        for (int i = 0; i < g_system_caps.num_p_cores; i++) {
            CPU_SET(g_system_caps.p_core_ids[i], &agent->cpu_affinity);
        }
    } else {
        // Assign to E-cores
        for (int i = 0; i < g_system_caps.num_e_cores; i++) {
            CPU_SET(g_system_caps.e_core_ids[i], &agent->cpu_affinity);
        }
    }
    
    // Set NUMA node
    if (numa_available() >= 0) {
        agent->numa_node = numa_node_of_cpu(sched_getcpu());
    }
    
    // Initialize statistics
    atomic_store(&agent->messages_sent, 0);
    atomic_store(&agent->messages_received, 0);
    atomic_store(&agent->bytes_processed, 0);
    
    return agent;
}

// ============================================================================
// RUNTIME INITIALIZATION
// ============================================================================

static agent_runtime_t* init_agent_runtime() {
    agent_runtime_t* runtime = calloc(1, sizeof(agent_runtime_t));
    if (!runtime) return NULL;
    
    // Detect system capabilities (from our enhanced protocol)
    detect_system_capabilities();
    
    // Initialize global IPC
    runtime->global_ipc = init_unified_ipc("global");
    if (!runtime->global_ipc) {
        free(runtime);
        return NULL;
    }
    
    // Initialize discovery service
    pthread_rwlock_init(&runtime->discovery.lock, NULL);
    
    // Set resource limits
    runtime->resources.memory_limit = 16ULL * 1024 * 1024 * 1024;  // 16GB
    
    runtime->running = true;
    
    printf("Agent runtime initialized\n");
    printf("  P-cores: %d\n", g_system_caps.num_p_cores);
    printf("  E-cores: %d\n", g_system_caps.num_e_cores);
    printf("  NUMA nodes: %d\n", g_system_caps.num_numa_nodes);
    
    return runtime;
}

// ============================================================================
// EXAMPLE AGENT HANDLERS
// ============================================================================

// Director agent handler
static void director_message_handler(agent_context_t* agent,
                                    enhanced_msg_header_t* msg,
                                    void* payload) {
    printf("[DIRECTOR] Received %s priority message from agent %d\n",
           msg->priority == PRIORITY_CRITICAL ? "CRITICAL" : "NORMAL",
           msg->source_agent);
    
    // Director logic: Route to appropriate agents
    if (msg->msg_type == 0x01) {  // Task assignment
        // Send to Project Orchestrator
        enhanced_msg_header_t response = *msg;
        response.source_agent = AGENT_DIRECTOR;
        response.target_agent = AGENT_PROJECT_ORCHESTRATOR;
        response.priority = PRIORITY_HIGH;
        
        send_agent_message(agent->ipc, AGENT_DIRECTOR, 
                         AGENT_PROJECT_ORCHESTRATOR, &response, payload);
    }
}

// Optimizer agent handler
static void optimizer_message_handler(agent_context_t* agent,
                                     enhanced_msg_header_t* msg,
                                     void* payload) {
    printf("[OPTIMIZER] Analyzing performance request\n");
    
    // Optimizer would profile and optimize here
    // Using our enhanced protocol for maximum speed
}

// ============================================================================
// MAIN - EXAMPLE USAGE
// ============================================================================

int main(int argc, char* argv[]) {
    printf("UNIFIED AGENT RUNTIME SYSTEM\n");
    printf("============================\n\n");
    
    // Initialize runtime
    g_runtime = init_agent_runtime();
    if (!g_runtime) {
        fprintf(stderr, "Failed to initialize runtime\n");
        return 1;
    }
    
    // Create critical agents
    agent_context_t* director = create_agent(AGENT_DIRECTOR, g_runtime->global_ipc);
    director->message_handler = director_message_handler;
    
    agent_context_t* orchestrator = create_agent(AGENT_PROJECT_ORCHESTRATOR, 
                                                g_runtime->global_ipc);
    
    agent_context_t* optimizer = create_agent(AGENT_OPTIMIZER, g_runtime->global_ipc);
    optimizer->message_handler = optimizer_message_handler;
    
    // Start agents
    pthread_create(&director->thread, NULL, agent_thread_main, director);
    pthread_create(&orchestrator->thread, NULL, agent_thread_main, orchestrator);
    pthread_create(&optimizer->thread, NULL, agent_thread_main, optimizer);
    
    // Register agents
    g_runtime->agents[AGENT_DIRECTOR] = director;
    g_runtime->agents[AGENT_PROJECT_ORCHESTRATOR] = orchestrator;
    g_runtime->agents[AGENT_OPTIMIZER] = optimizer;
    g_runtime->num_active_agents = 3;
    
    // Send test message
    enhanced_msg_header_t test_msg = {
        .magic = 0x4147454E,
        .msg_id = 1,
        .msg_type = 0x01,
        .priority = PRIORITY_CRITICAL,
        .source_agent = AGENT_DIRECTOR,
        .target_agent = AGENT_PROJECT_ORCHESTRATOR,
        .payload_len = 128
    };
    
    uint8_t test_payload[128];
    memset(test_payload, 0xAA, sizeof(test_payload));
    
    printf("\nSending test message...\n");
    send_agent_message(g_runtime->global_ipc, AGENT_DIRECTOR,
                      AGENT_PROJECT_ORCHESTRATOR, &test_msg, test_payload);
    
    // Run for a while
    sleep(2);
    
    // Shutdown
    printf("\nShutting down agents...\n");
    director->running = false;
    orchestrator->running = false;
    optimizer->running = false;
    
    pthread_join(director->thread, NULL);
    pthread_join(orchestrator->thread, NULL);
    pthread_join(optimizer->thread, NULL);
    
    // Print statistics
    printf("\nStatistics:\n");
    printf("  Director: %lu messages received\n", 
           atomic_load(&director->messages_received));
    printf("  Orchestrator: %lu messages received\n",
           atomic_load(&orchestrator->messages_received));
    printf("  Optimizer: %lu messages received\n",
           atomic_load(&optimizer->messages_received));
    
    // Cleanup
    free(director);
    free(orchestrator);
    free(optimizer);
    
    // Cleanup IPC
    if (g_runtime->global_ipc) {
        munmap(g_runtime->global_ipc->shared_mem.base_addr,
              g_runtime->global_ipc->shared_mem.size);
        if (g_runtime->global_ipc->io_uring_channel.initialized) {
            io_uring_queue_exit(&g_runtime->global_ipc->io_uring_channel.ring);
        }
        close(g_runtime->global_ipc->unix_socket.server_fd);
        close(g_runtime->global_ipc->mmap_queue.fd);
        free(g_runtime->global_ipc);
    }
    
    free(g_runtime);
    
    return 0;
}