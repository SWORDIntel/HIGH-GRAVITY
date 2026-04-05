/*
 * Performance Test for Binary Communication System
 * Tests actual worker throughput with message processing
 */

#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <pthread.h>
#include <time.h>
#include <sys/time.h>
#include <unistd.h>
#include <sched.h>

// Simplified message structure for testing
typedef struct {
    uint64_t timestamp;
    uint32_t source_agent;
    uint32_t target_agent;
    uint32_t msg_id;
    uint16_t payload_len;
    uint8_t priority;
    uint8_t flags;
} test_msg_header_t;

// Worker statistics
typedef struct {
    uint64_t messages_processed;
    uint64_t messages_stolen;
    uint64_t total_latency_ns;
    uint32_t worker_id;
    uint32_t cpu_id;
} worker_stats_t;

// Global test parameters
static volatile int test_running = 1;
static volatile uint64_t total_messages_sent = 0;
static volatile uint64_t total_messages_processed = 0;

// Worker configuration
#define MAX_WORKERS 24
#define TEST_DURATION_SECONDS 5
#define MESSAGES_PER_SECOND 100000
#define QUEUE_SIZE 1024

typedef struct {
    test_msg_header_t messages[QUEUE_SIZE];
    volatile uint32_t head;
    volatile uint32_t tail;
    volatile uint32_t count;
    pthread_mutex_t mutex;
} work_queue_t;

static work_queue_t worker_queues[MAX_WORKERS];
static worker_stats_t worker_stats[MAX_WORKERS];
static int num_workers = 0;
static int num_p_cores = 0;
static int num_e_cores = 0;

// Get current time in nanoseconds
static uint64_t get_time_ns(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec * 1000000000ULL + ts.tv_nsec;
}

// Detect CPU topology
static void detect_cpu_topology(void) {
    int total_cpus = sysconf(_SC_NPROCESSORS_ONLN);
    
    // For Intel Meteor Lake: assume first 12 are P-cores, rest are E-cores
    if (total_cpus >= 12) {
        num_p_cores = 12;
        num_e_cores = total_cpus - 12;
    } else {
        num_p_cores = total_cpus / 2;
        num_e_cores = total_cpus - num_p_cores;
    }
    
    num_workers = total_cpus;
    if (num_workers > MAX_WORKERS) num_workers = MAX_WORKERS;
    
    printf("Detected: %d P-cores, %d E-cores, using %d workers\n", 
           num_p_cores, num_e_cores, num_workers);
}

// Initialize work queue
static void init_work_queue(work_queue_t* queue) {
    memset(queue, 0, sizeof(work_queue_t));
    pthread_mutex_init(&queue->mutex, NULL);
}

// Add message to queue
static int enqueue_message(work_queue_t* queue, test_msg_header_t* msg) {
    pthread_mutex_lock(&queue->mutex);
    
    if (queue->count >= QUEUE_SIZE) {
        pthread_mutex_unlock(&queue->mutex);
        return -1; // Queue full
    }
    
    queue->messages[queue->tail] = *msg;
    queue->tail = (queue->tail + 1) % QUEUE_SIZE;
    queue->count++;
    
    pthread_mutex_unlock(&queue->mutex);
    return 0;
}

// Get message from queue
static int dequeue_message(work_queue_t* queue, test_msg_header_t* msg) {
    pthread_mutex_lock(&queue->mutex);
    
    if (queue->count == 0) {
        pthread_mutex_unlock(&queue->mutex);
        return -1; // Queue empty
    }
    
    *msg = queue->messages[queue->head];
    queue->head = (queue->head + 1) % QUEUE_SIZE;
    queue->count--;
    
    pthread_mutex_unlock(&queue->mutex);
    return 0;
}

// Try to steal work from another queue
static int steal_work(int worker_id, test_msg_header_t* msg) {
    for (int i = 0; i < num_workers; i++) {
        if (i == worker_id) continue;
        
        if (dequeue_message(&worker_queues[i], msg) == 0) {
            worker_stats[worker_id].messages_stolen++;
            return 0;
        }
    }
    return -1;
}

// Process a message (simulate work)
static void process_message(test_msg_header_t* msg, int worker_id) {
    // Simulate different processing based on message priority
    volatile int work = 0;
    int iterations = msg->priority * 10 + 50; // Variable work based on priority
    
    for (int i = 0; i < iterations; i++) {
        work += i * msg->msg_id;
    }
    
    // Calculate latency
    uint64_t now = get_time_ns();
    uint64_t latency = now - msg->timestamp;
    worker_stats[worker_id].total_latency_ns += latency;
}

// Worker thread function
static void* worker_thread(void* arg) {
    int worker_id = *(int*)arg;
    int cpu_id = worker_id;
    
    // Set CPU affinity
    cpu_set_t cpuset;
    CPU_ZERO(&cpuset);
    CPU_SET(cpu_id, &cpuset);
    pthread_setaffinity_np(pthread_self(), sizeof(cpu_set_t), &cpuset);
    
    worker_stats[worker_id].worker_id = worker_id;
    worker_stats[worker_id].cpu_id = cpu_id;
    
    printf("Worker %d started on CPU %d (%s-core)\n", 
           worker_id, cpu_id, 
           (cpu_id < num_p_cores) ? "P" : "E");
    
    test_msg_header_t msg;
    
    while (test_running) {
        // Try to get work from own queue first
        if (dequeue_message(&worker_queues[worker_id], &msg) == 0) {
            process_message(&msg, worker_id);
            worker_stats[worker_id].messages_processed++;
            __sync_fetch_and_add(&total_messages_processed, 1);
        } else if (steal_work(worker_id, &msg) == 0) {
            // Stolen work
            process_message(&msg, worker_id);
            worker_stats[worker_id].messages_processed++;
            __sync_fetch_and_add(&total_messages_processed, 1);
        } else {
            // No work available, brief sleep
            usleep(100);
        }
    }
    
    return NULL;
}

// Message generator thread
static void* generator_thread(void* arg) {
    uint64_t msg_id = 0;
    uint64_t start_time = get_time_ns();
    uint64_t messages_per_ns = MESSAGES_PER_SECOND / 1000000000ULL;
    if (messages_per_ns == 0) messages_per_ns = 1;
    
    printf("Message generator started, target: %d msg/sec\n", MESSAGES_PER_SECOND);
    
    while (test_running) {
        test_msg_header_t msg = {
            .timestamp = get_time_ns(),
            .source_agent = rand() % 32,
            .target_agent = rand() % 32,
            .msg_id = ++msg_id,
            .payload_len = rand() % 256,
            .priority = rand() % 10,
            .flags = 0
        };
        
        // Round-robin distribution to workers
        int target_worker = msg_id % num_workers;
        
        if (enqueue_message(&worker_queues[target_worker], &msg) == 0) {
            __sync_fetch_and_add(&total_messages_sent, 1);
        }
        
        // Rate limiting
        if (msg_id % 1000 == 0) {
            usleep(1000); // Brief pause every 1000 messages
        }
    }
    
    return NULL;
}

int main(void) {
    printf("BINARY COMMUNICATION SYSTEM - PERFORMANCE TEST\n");
    printf("===============================================\n\n");
    
    // Detect system capabilities
    detect_cpu_topology();
    
    // Initialize work queues
    printf("Initializing %d work queues...\n", num_workers);
    for (int i = 0; i < num_workers; i++) {
        init_work_queue(&worker_queues[i]);
        memset(&worker_stats[i], 0, sizeof(worker_stats_t));
    }
    
    // Start worker threads
    pthread_t worker_threads[MAX_WORKERS];
    int worker_ids[MAX_WORKERS];
    
    printf("Starting worker threads...\n");
    for (int i = 0; i < num_workers; i++) {
        worker_ids[i] = i;
        pthread_create(&worker_threads[i], NULL, worker_thread, &worker_ids[i]);
    }
    
    // Start message generator
    pthread_t gen_thread;
    pthread_create(&gen_thread, NULL, generator_thread, NULL);
    
    printf("\nRunning performance test for %d seconds...\n\n", TEST_DURATION_SECONDS);
    
    // Test progress monitoring
    for (int i = 0; i < TEST_DURATION_SECONDS; i++) {
        sleep(1);
        printf("Progress: %d/%ds - Messages: sent=%lu, processed=%lu, rate=%.1f msg/sec\n",
               i + 1, TEST_DURATION_SECONDS,
               total_messages_sent, total_messages_processed,
               (double)total_messages_processed / (i + 1));
    }
    
    // Stop test
    test_running = 0;
    
    // Wait for threads to finish
    pthread_join(gen_thread, NULL);
    for (int i = 0; i < num_workers; i++) {
        pthread_join(worker_threads[i], NULL);
    }
    
    // Print results
    printf("\n" "PERFORMANCE TEST RESULTS\n");
    printf("========================\n\n");
    
    printf("Overall Statistics:\n");
    printf("  Messages Sent:      %lu\n", total_messages_sent);
    printf("  Messages Processed: %lu\n", total_messages_processed);
    printf("  Processing Rate:    %.1f msg/sec\n", 
           (double)total_messages_processed / TEST_DURATION_SECONDS);
    printf("  Efficiency:         %.1f%%\n", 
           100.0 * total_messages_processed / total_messages_sent);
    
    printf("\nPer-Worker Statistics:\n");
    printf("Worker | CPU | Type   | Processed | Stolen | Avg Latency\n");
    printf("-------|-----|--------|-----------|--------|-----------\n");
    
    uint64_t total_stolen = 0;
    for (int i = 0; i < num_workers; i++) {
        worker_stats_t* stats = &worker_stats[i];
        double avg_latency = 0.0;
        
        if (stats->messages_processed > 0) {
            avg_latency = (double)stats->total_latency_ns / stats->messages_processed / 1000.0; // microseconds
        }
        
        printf("%6d | %3d | %s-core | %9lu | %6lu | %8.1f μs\n",
               stats->worker_id, stats->cpu_id,
               (stats->cpu_id < num_p_cores) ? "P" : "E",
               stats->messages_processed, stats->messages_stolen,
               avg_latency);
        
        total_stolen += stats->messages_stolen;
    }
    
    printf("\nWork Distribution:\n");
    printf("  Total Work Stealing Events: %lu\n", total_stolen);
    printf("  Work Stealing Efficiency:   %.1f%%\n", 
           100.0 * total_stolen / total_messages_processed);
    
    // Performance analysis
    printf("\nPerformance Analysis:\n");
    if (total_messages_processed > 0) {
        printf("  ✓ System successfully processed messages!\n");
        if ((double)total_messages_processed / TEST_DURATION_SECONDS > 10000) {
            printf("  ✓ High throughput achieved (>10K msg/sec)\n");
        }
        if (total_stolen > 0) {
            printf("  ✓ Work stealing is functioning\n");
        }
    } else {
        printf("  ⚠ No messages were processed - system may have issues\n");
    }
    
    return 0;
}