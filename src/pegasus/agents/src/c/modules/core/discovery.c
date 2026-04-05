#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <pthread.h>
#include <unistd.h>
#include "../../runtime/module_interface.h"

// Module information
static module_info_t g_module_info = {
    .id = 0x00001001,
    .name = "discovery",
    .description = "Agent discovery and health monitoring",
    .version_major = 1,
    .version_minor = 0,
    .version_patch = 0,
    .capabilities = CAP_ROUTING | CAP_MONITORING,
    .cpu_affinity_mask = AFFINITY_E_CORES
};

MODULE_EXPORT module_info_t* module_get_info(void) {
    return &g_module_info;
}

typedef struct {
    uint32_t module_id;
    char name[64];
    uint64_t last_heartbeat;
    uint32_t message_count;
    uint32_t error_count;
    bool active;
} module_registry_entry_t;

typedef struct {
    module_registry_entry_t entries[256];
    int count;
    pthread_mutex_t lock;
    pthread_t monitor_thread;
    volatile bool running;
} discovery_state_t;

static discovery_state_t g_state = {0};
static module_ops_t g_ops;

static void* monitor_thread(void* arg) {
    (void)arg;
    
    while (g_state.running) {
        pthread_mutex_lock(&g_state.lock);
        
        time_t now = time(NULL);
        for (int i = 0; i < g_state.count; i++) {
            if (g_state.entries[i].active) {
                if (now - g_state.entries[i].last_heartbeat > 30) {
                    printf("[Discovery] Module %s (0x%08x) is unresponsive\n",
                           g_state.entries[i].name, g_state.entries[i].module_id);
                    g_state.entries[i].active = false;
                }
            }
        }
        
        pthread_mutex_unlock(&g_state.lock);
        sleep(5);
    }
    
    return NULL;
}

static int discovery_init(module_info_t* info) {
    (void)info;  // Already set in g_module_info
    
    pthread_mutex_init(&g_state.lock, NULL);
    g_state.running = true;
    g_state.count = 0;
    
    // Start monitoring thread
    pthread_create(&g_state.monitor_thread, NULL, monitor_thread, NULL);
    
    printf("[Discovery] Module initialized\n");
    return 0;
}

static void discovery_cleanup(void) {
    g_state.running = false;
    pthread_join(g_state.monitor_thread, NULL);
    pthread_mutex_destroy(&g_state.lock);
    
    printf("[Discovery] Module cleaned up\n");
}

static int discovery_handle_message(uint32_t src_id, const void* data, size_t len) {
    if (len < sizeof(uint32_t)) return -1;
    
    uint32_t msg_type = *(uint32_t*)data;
    
    pthread_mutex_lock(&g_state.lock);
    
    switch (msg_type) {
        case 0x01: {  // Register
            if (len < sizeof(uint32_t) + 64) break;
            
            const char* name = (const char*)data + sizeof(uint32_t);
            
            // Find or create entry
            int idx = -1;
            for (int i = 0; i < g_state.count; i++) {
                if (g_state.entries[i].module_id == src_id) {
                    idx = i;
                    break;
                }
            }
            
            if (idx == -1 && g_state.count < 256) {
                idx = g_state.count++;
            }
            
            if (idx >= 0) {
                g_state.entries[idx].module_id = src_id;
                strncpy(g_state.entries[idx].name, name, 63);
                g_state.entries[idx].last_heartbeat = time(NULL);
                g_state.entries[idx].active = true;
                
                printf("[Discovery] Registered module: %s (0x%08x)\n", name, src_id);
            }
            break;
        }
        
        case 0x02: {  // Heartbeat
            for (int i = 0; i < g_state.count; i++) {
                if (g_state.entries[i].module_id == src_id) {
                    g_state.entries[i].last_heartbeat = time(NULL);
                    g_state.entries[i].message_count++;
                    break;
                }
            }
            break;
        }
        
        case 0x03: {  // Query
            // Return list of active modules
            printf("[Discovery] Query from 0x%08x - %d active modules\n", 
                   src_id, g_state.count);
            break;
        }
    }
    
    pthread_mutex_unlock(&g_state.lock);
    return 0;
}

static void discovery_run(void) {
    // Main loop handled by monitor thread
    while (g_state.running) {
        sleep(1);
    }
}

static void discovery_stop(void) {
    g_state.running = false;
}

static int discovery_get_status(char* buffer, size_t max_len) {
    pthread_mutex_lock(&g_state.lock);
    
    int active_count = 0;
    for (int i = 0; i < g_state.count; i++) {
        if (g_state.entries[i].active) active_count++;
    }
    
    snprintf(buffer, max_len, 
             "Discovery: %d modules registered, %d active",
             g_state.count, active_count);
    
    pthread_mutex_unlock(&g_state.lock);
    return 0;
}

// Export module operations
MODULE_EXPORT module_ops_t* module_get_ops(void) {
    g_ops.init = discovery_init;
    g_ops.cleanup = discovery_cleanup;
    g_ops.handle_message = discovery_handle_message;
    g_ops.run = discovery_run;
    g_ops.stop = discovery_stop;
    g_ops.configure = NULL;
    g_ops.get_status = discovery_get_status;
    
    return &g_ops;
}