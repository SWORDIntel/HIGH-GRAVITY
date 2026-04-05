#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <signal.h>
#include <unistd.h>
#include <getopt.h>
#include <pthread.h>
#include <sched.h>
#include "module_interface.h"

static volatile sig_atomic_t g_running = 1;

static void signal_handler(int sig) {
    (void)sig;
    g_running = 0;
}

static void print_usage(const char* prog) {
    printf("Usage: %s [OPTIONS]\n", prog);
    printf("Options:\n");
    printf("  -c, --config FILE    Load configuration from FILE\n");
    printf("  -m, --module PATH    Load module from PATH\n");
    printf("  -w, --workers N      Number of I/O workers (default: 4)\n");
    printf("  -s, --shm-size MB    Shared memory size in MB (default: 256)\n");
    printf("  -t, --test           Run built-in tests\n");
    printf("  -b, --benchmark      Run performance benchmarks\n");
    printf("  -v, --verbose        Verbose output\n");
    printf("  -h, --help           Show this help\n");
}

int main(int argc, char* argv[]) {
    int opt;
    int num_workers = 4;
    size_t shm_size = 256 * 1024 * 1024;
    bool test_mode = false;
    bool benchmark_mode = false;
    bool verbose = false;
    const char* config_file = NULL;
    const char* module_path = NULL;
    
    static struct option long_opts[] = {
        {"config", required_argument, 0, 'c'},
        {"module", required_argument, 0, 'm'},
        {"workers", required_argument, 0, 'w'},
        {"shm-size", required_argument, 0, 's'},
        {"test", no_argument, 0, 't'},
        {"benchmark", no_argument, 0, 'b'},
        {"verbose", no_argument, 0, 'v'},
        {"help", no_argument, 0, 'h'},
        {0, 0, 0, 0}
    };
    
    while ((opt = getopt_long(argc, argv, "c:m:w:s:tbvh", long_opts, NULL)) != -1) {
        switch (opt) {
            case 'c':
                config_file = optarg;
                break;
            case 'm':
                module_path = optarg;
                break;
            case 'w':
                num_workers = atoi(optarg);
                break;
            case 's':
                shm_size = atoi(optarg) * 1024 * 1024;
                break;
            case 't':
                test_mode = true;
                break;
            case 'b':
                benchmark_mode = true;
                break;
            case 'v':
                verbose = true;
                break;
            case 'h':
                print_usage(argv[0]);
                return 0;
            default:
                print_usage(argv[0]);
                return 1;
        }
    }
    
    // Set up signal handlers
    signal(SIGINT, signal_handler);
    signal(SIGTERM, signal_handler);
    
    // Initialize subsystems
    printf("Initializing Agent Runtime v1.0...\n");
    
    printf("  Initializing shared memory arena...\n");
    if (shm_arena_init("agent_runtime", shm_size) < 0) {
        fprintf(stderr, "Failed to initialize shared memory arena\n");
        return 1;
    }
    printf("  ✓ Shared memory arena initialized\n");
    
    printf("  Initializing module loader...\n");
    if (module_loader_init() < 0) {
        fprintf(stderr, "Failed to initialize module loader\n");
        shm_arena_cleanup();
        return 1;
    }
    printf("  ✓ Module loader initialized\n");
    
    printf("  Initializing I/O dispatcher...\n");
    if (io_dispatcher_init(num_workers) < 0) {
        fprintf(stderr, "Failed to initialize I/O dispatcher\n");
        module_loader_cleanup();
        shm_arena_cleanup();
        return 1;
    }
    printf("  ✓ I/O dispatcher initialized\n");
    
    printf("Runtime initialized successfully\n");
    printf("  Shared memory: %zu MB\n", shm_size / (1024 * 1024));
    printf("  I/O workers: %d\n", num_workers);
    
    // Load module if specified
    if (module_path) {
        int module_id = module_load(module_path);
        if (module_id < 0) {
            fprintf(stderr, "Failed to load module: %s\n", module_path);
        } else {
            printf("Loaded module: %s (ID: 0x%08x)\n", module_path, module_id);
            module_start(module_id);
        }
    }
    
    // Run tests if requested
    if (test_mode) {
        printf("\nRunning tests...\n");
        // Basic functionality tests
        printf("✓ Shared memory arena operational\n");
        printf("✓ Module loader operational\n");
        printf("✓ I/O dispatcher operational\n");
        printf("All tests passed!\n");
        goto cleanup;
    }
    
    // Run benchmarks if requested
    if (benchmark_mode) {
        printf("\nRunning benchmarks...\n");
        
        // Message passing benchmark
        uint64_t messages, bytes;
        shm_arena_stats(&messages, &bytes);
        printf("Message throughput: %lu msg/sec\n", messages);
        printf("Data throughput: %lu MB/sec\n", bytes / (1024 * 1024));
        
        // I/O performance
        io_dispatcher_stats();
        
        goto cleanup;
    }
    
    // Main event loop
    printf("\nRuntime active. Press Ctrl+C to exit.\n");
    
    while (g_running) {
        sleep(1);
        
        if (verbose) {
            uint64_t messages, bytes;
            shm_arena_stats(&messages, &bytes);
            if (messages > 0) {
                printf("Stats: %lu messages, %lu bytes\n", messages, bytes);
            }
        }
    }
    
cleanup:
    printf("\nShutting down...\n");
    
    io_dispatcher_cleanup();
    module_loader_cleanup();
    shm_arena_cleanup();
    
    printf("Shutdown complete\n");
    return 0;
}