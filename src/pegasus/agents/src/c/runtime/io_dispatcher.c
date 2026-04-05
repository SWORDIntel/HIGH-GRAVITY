#define _GNU_SOURCE
#include <liburing.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <errno.h>
#include <pthread.h>
#include <stdatomic.h>
#include <sys/eventfd.h>
#include <sys/epoll.h>
#include "module_interface.h"

#define IO_QUEUE_DEPTH 4096
#define MAX_IO_WORKERS 16
#define BATCH_SIZE 64

typedef enum {
    IO_OP_READ = 1,
    IO_OP_WRITE,
    IO_OP_ACCEPT,
    IO_OP_CONNECT,
    IO_OP_SEND_MSG,
    IO_OP_RECV_MSG,
    IO_OP_TIMER,
    IO_OP_CANCEL
} io_op_type_t;

typedef struct io_request {
    io_op_type_t type;
    int fd;
    void* buffer;
    size_t size;
    off_t offset;
    void (*callback)(struct io_request*, int result);
    void* user_data;
    uint64_t submit_time;
} io_request_t;

typedef struct {
    struct io_uring ring;
    pthread_t thread;
    int event_fd;
    atomic_bool running;
    
    // Statistics
    atomic_uint_fast64_t ops_submitted;
    atomic_uint_fast64_t ops_completed;
    atomic_uint_fast64_t ops_failed;
    atomic_uint_fast64_t total_latency_ns;
} io_worker_t;

typedef struct {
    io_worker_t workers[MAX_IO_WORKERS];
    int num_workers;
    atomic_int next_worker;
    
    // Fallback for non io_uring systems
    int epoll_fd;
    pthread_t fallback_thread;
    
    // Global stats
    atomic_uint_fast64_t total_ops;
    atomic_uint_fast64_t total_bytes;
} io_dispatcher_t;

static io_dispatcher_t g_dispatcher = {0};

// Forward declarations
static void* io_worker_thread(void* arg);
static void* fallback_worker_thread(void* arg);
static int submit_io_request(io_request_t* req);

int io_dispatcher_init(int num_workers) {
    if (num_workers <= 0 || num_workers > MAX_IO_WORKERS) {
        num_workers = 4;  // Default
    }
    
    g_dispatcher.num_workers = num_workers;
    atomic_store(&g_dispatcher.next_worker, 0);
    
    
    // Try to initialize io_uring workers
    bool io_uring_available = false;
    
    for (int i = 0; i < num_workers; i++) {
        io_worker_t* worker = &g_dispatcher.workers[i];
        
        // Try to setup io_uring
        // NOTE: SQPOLL disabled due to microcode 0x24 restrictions
        // Directly use standard mode for compatibility
        int ret = io_uring_queue_init(IO_QUEUE_DEPTH, &worker->ring, 0);
        
        if (ret >= 0) {
            io_uring_available = true;
            
            // Create event fd for notifications
            worker->event_fd = eventfd(0, EFD_NONBLOCK | EFD_CLOEXEC);
            if (worker->event_fd < 0) {
                io_uring_queue_exit(&worker->ring);
                continue;
            }
            
            // Register event fd with io_uring
            io_uring_register_eventfd(&worker->ring, worker->event_fd);
            
            // Start worker thread
            atomic_store(&worker->running, true);
            if (pthread_create(&worker->thread, NULL, io_worker_thread, worker) != 0) {
                atomic_store(&worker->running, false);
                close(worker->event_fd);
                io_uring_queue_exit(&worker->ring);
                continue;
            }
            
            // Set thread affinity
            cpu_set_t cpuset;
            CPU_ZERO(&cpuset);
            CPU_SET(i % sysconf(_SC_NPROCESSORS_ONLN), &cpuset);
            pthread_setaffinity_np(worker->thread, sizeof(cpuset), &cpuset);
        }
    }
    
    // If io_uring not available, setup fallback epoll
    if (!io_uring_available) {
        g_dispatcher.epoll_fd = epoll_create1(EPOLL_CLOEXEC);
        if (g_dispatcher.epoll_fd < 0) {
            return -1;
        }
        
        if (pthread_create(&g_dispatcher.fallback_thread, NULL, 
                          fallback_worker_thread, NULL) != 0) {
            close(g_dispatcher.epoll_fd);
            return -1;
        }
    }
    
    return 0;
}

static void* io_worker_thread(void* arg) {
    io_worker_t* worker = (io_worker_t*)arg;
    struct io_uring_cqe* cqe;
    
    
    // Use timeout to avoid hanging
    struct __kernel_timespec ts = {
        .tv_sec = 1,
        .tv_nsec = 0
    };
    
    while (atomic_load(&worker->running)) {
        // Wait for completions with timeout
        int ret = io_uring_wait_cqe_timeout(&worker->ring, &cqe, &ts);
        if (ret < 0) {
            if (ret == -EINTR || ret == -ETIME) continue;  // Timeout is OK
            break;
        }
        
        // Process completion
        io_request_t* req = (io_request_t*)io_uring_cqe_get_data(cqe);
        if (req) {
            int result = cqe->res;
            
            // Update statistics
            if (result >= 0) {
                atomic_fetch_add(&worker->ops_completed, 1);
                atomic_fetch_add(&g_dispatcher.total_bytes, result);
            } else {
                atomic_fetch_add(&worker->ops_failed, 1);
            }
            
            // Calculate latency
            struct timespec ts;
            clock_gettime(CLOCK_MONOTONIC, &ts);
            uint64_t complete_time = ts.tv_sec * 1000000000ULL + ts.tv_nsec;
            uint64_t latency = complete_time - req->submit_time;
            atomic_fetch_add(&worker->total_latency_ns, latency);
            
            // Call completion callback
            if (req->callback) {
                req->callback(req, result);
            }
            
            // Free request
            free(req);
        }
        
        // Mark seen
        io_uring_cqe_seen(&worker->ring, cqe);
        
        // Process batch if available
        unsigned batch_count = 0;
        while (batch_count < BATCH_SIZE && 
               io_uring_peek_cqe(&worker->ring, &cqe) == 0) {
            req = (io_request_t*)io_uring_cqe_get_data(cqe);
            if (req && req->callback) {
                req->callback(req, cqe->res);
            }
            io_uring_cqe_seen(&worker->ring, cqe);
            free(req);
            batch_count++;
        }
    }
    
    return NULL;
}

static void* fallback_worker_thread(void* arg) {
    struct epoll_event events[BATCH_SIZE];
    
    while (1) {
        int nfds = epoll_wait(g_dispatcher.epoll_fd, events, BATCH_SIZE, 1000);
        if (nfds < 0) {
            if (errno == EINTR) continue;
            break;
        }
        
        for (int i = 0; i < nfds; i++) {
            io_request_t* req = (io_request_t*)events[i].data.ptr;
            if (!req) continue;
            
            // Handle based on type
            ssize_t result = 0;
            switch (req->type) {
                case IO_OP_READ:
                    result = pread(req->fd, req->buffer, req->size, req->offset);
                    break;
                case IO_OP_WRITE:
                    result = pwrite(req->fd, req->buffer, req->size, req->offset);
                    break;
                default:
                    result = -ENOTSUP;
            }
            
            if (req->callback) {
                req->callback(req, result);
            }
            
            free(req);
        }
    }
    
    return NULL;
}

int io_submit_read(int fd, void* buffer, size_t size, off_t offset,
                   void (*callback)(io_request_t*, int)) {
    io_request_t* req = calloc(1, sizeof(io_request_t));
    if (!req) return -ENOMEM;
    
    req->type = IO_OP_READ;
    req->fd = fd;
    req->buffer = buffer;
    req->size = size;
    req->offset = offset;
    req->callback = callback;
    
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    req->submit_time = ts.tv_sec * 1000000000ULL + ts.tv_nsec;
    
    return submit_io_request(req);
}

int io_submit_write(int fd, const void* buffer, size_t size, off_t offset,
                    void (*callback)(io_request_t*, int)) {
    io_request_t* req = calloc(1, sizeof(io_request_t));
    if (!req) return -ENOMEM;
    
    req->type = IO_OP_WRITE;
    req->fd = fd;
    req->buffer = (void*)buffer;
    req->size = size;
    req->offset = offset;
    req->callback = callback;
    
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    req->submit_time = ts.tv_sec * 1000000000ULL + ts.tv_nsec;
    
    return submit_io_request(req);
}

static int submit_io_request(io_request_t* req) {
    // Round-robin to next worker
    int worker_idx = atomic_fetch_add(&g_dispatcher.next_worker, 1) % g_dispatcher.num_workers;
    io_worker_t* worker = &g_dispatcher.workers[worker_idx];
    
    if (!atomic_load(&worker->running)) {
        // Fallback path
        if (g_dispatcher.epoll_fd >= 0) {
            // For fallback, execute synchronously for now
            ssize_t result = 0;
            switch (req->type) {
                case IO_OP_READ:
                    result = pread(req->fd, req->buffer, req->size, req->offset);
                    break;
                case IO_OP_WRITE:
                    result = pwrite(req->fd, req->buffer, req->size, req->offset);
                    break;
                default:
                    result = -ENOTSUP;
            }
            
            if (req->callback) {
                req->callback(req, result);
            }
            free(req);
            return result >= 0 ? 0 : result;
        }
        free(req);
        return -ENODEV;
    }
    
    // Submit to io_uring
    struct io_uring_sqe* sqe = io_uring_get_sqe(&worker->ring);
    if (!sqe) {
        free(req);
        return -EBUSY;
    }
    
    switch (req->type) {
        case IO_OP_READ:
            io_uring_prep_read(sqe, req->fd, req->buffer, req->size, req->offset);
            break;
        case IO_OP_WRITE:
            io_uring_prep_write(sqe, req->fd, req->buffer, req->size, req->offset);
            break;
        default:
            free(req);
            return -EINVAL;
    }
    
    io_uring_sqe_set_data(sqe, req);
    
    int ret = io_uring_submit(&worker->ring);
    if (ret < 0) {
        free(req);
        return ret;
    }
    
    atomic_fetch_add(&worker->ops_submitted, 1);
    atomic_fetch_add(&g_dispatcher.total_ops, 1);
    
    return 0;
}

void io_dispatcher_stats(void) {
    printf("I/O Dispatcher Statistics:\n");
    printf("  Workers: %d\n", g_dispatcher.num_workers);
    printf("  Total operations: %lu\n", atomic_load(&g_dispatcher.total_ops));
    printf("  Total bytes: %lu\n", atomic_load(&g_dispatcher.total_bytes));
    
    for (int i = 0; i < g_dispatcher.num_workers; i++) {
        io_worker_t* worker = &g_dispatcher.workers[i];
        if (!atomic_load(&worker->running)) continue;
        
        uint64_t completed = atomic_load(&worker->ops_completed);
        uint64_t total_latency = atomic_load(&worker->total_latency_ns);
        uint64_t avg_latency = completed > 0 ? total_latency / completed : 0;
        
        printf("  Worker %d:\n", i);
        printf("    Submitted: %lu\n", atomic_load(&worker->ops_submitted));
        printf("    Completed: %lu\n", completed);
        printf("    Failed: %lu\n", atomic_load(&worker->ops_failed));
        printf("    Avg latency: %lu ns\n", avg_latency);
    }
}

void io_dispatcher_cleanup(void) {
    // Stop all workers
    for (int i = 0; i < g_dispatcher.num_workers; i++) {
        io_worker_t* worker = &g_dispatcher.workers[i];
        if (atomic_load(&worker->running)) {
            atomic_store(&worker->running, false);
            
            // Wake up worker
            uint64_t val = 1;
            write(worker->event_fd, &val, sizeof(val));
            
            pthread_join(worker->thread, NULL);
            close(worker->event_fd);
            io_uring_queue_exit(&worker->ring);
        }
    }
    
    // Stop fallback thread
    if (g_dispatcher.epoll_fd >= 0) {
        close(g_dispatcher.epoll_fd);
        // pthread_join(g_dispatcher.fallback_thread, NULL);
    }
    
    memset(&g_dispatcher, 0, sizeof(g_dispatcher));
}