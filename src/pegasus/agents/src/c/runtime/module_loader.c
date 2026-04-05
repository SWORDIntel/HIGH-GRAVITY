#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <dirent.h>
#include <sys/stat.h>
#include <unistd.h>
#include <pthread.h>
#include <stdatomic.h>
#include "module_interface.h"

#define MAX_MODULES 64
#define MODULE_DIR "./modules"

typedef struct {
    void* handle;
    module_info_t* info;
    module_ops_t* ops;
    uint32_t id;
    atomic_int state;  // 0=unloaded, 1=loaded, 2=running, 3=error
    pthread_t thread;
    char path[256];
} module_entry_t;

typedef struct {
    module_entry_t modules[MAX_MODULES];
    atomic_int module_count;
    pthread_rwlock_t lock;
    
    // Module discovery
    char search_paths[8][256];
    int num_paths;
    
    // Statistics
    atomic_uint_fast64_t loads;
    atomic_uint_fast64_t unloads;
    atomic_uint_fast64_t reloads;
} module_manager_t;

static module_manager_t g_manager = {0};

int module_loader_init(void) {
    pthread_rwlock_init(&g_manager.lock, NULL);
    atomic_store(&g_manager.module_count, 0);
    
    // Default search paths
    strcpy(g_manager.search_paths[0], "./modules");
    strcpy(g_manager.search_paths[1], "./modules/core");
    strcpy(g_manager.search_paths[2], "./modules/agents");
    strcpy(g_manager.search_paths[3], "./modules/security");
    g_manager.num_paths = 4;
    
    // Create module directories if they don't exist
    for (int i = 0; i < g_manager.num_paths; i++) {
        mkdir(g_manager.search_paths[i], 0755);
    }
    
    return 0;
}

static module_entry_t* find_free_slot(void) {
    for (int i = 0; i < MAX_MODULES; i++) {
        if (atomic_load(&g_manager.modules[i].state) == 0) {
            return &g_manager.modules[i];
        }
    }
    return NULL;
}

static module_entry_t* find_module_by_id(uint32_t id) {
    for (int i = 0; i < MAX_MODULES; i++) {
        if (g_manager.modules[i].id == id && 
            atomic_load(&g_manager.modules[i].state) > 0) {
            return &g_manager.modules[i];
        }
    }
    return NULL;
}

int module_load(const char* path) {
    pthread_rwlock_wrlock(&g_manager.lock);
    
    // Find free slot
    module_entry_t* entry = find_free_slot();
    if (!entry) {
        pthread_rwlock_unlock(&g_manager.lock);
        return -1;
    }
    
    // Try to load from each search path
    char full_path[512];
    void* handle = NULL;
    
    for (int i = 0; i < g_manager.num_paths; i++) {
        snprintf(full_path, sizeof(full_path), "%s/%s", 
                 g_manager.search_paths[i], path);
        
        handle = dlopen(full_path, RTLD_NOW | RTLD_LOCAL);
        if (handle) break;
        
        // Try with .so extension
        snprintf(full_path, sizeof(full_path), "%s/%s.so", 
                 g_manager.search_paths[i], path);
        handle = dlopen(full_path, RTLD_NOW | RTLD_LOCAL);
        if (handle) break;
    }
    
    if (!handle) {
        // Try absolute path
        handle = dlopen(path, RTLD_NOW | RTLD_LOCAL);
        if (!handle) {
            fprintf(stderr, "Failed to load module %s: %s\n", path, dlerror());
            pthread_rwlock_unlock(&g_manager.lock);
            return -1;
        }
        strcpy(full_path, path);
    }
    
    // Get module info
    module_info_t* (*get_info)(void) = dlsym(handle, "module_get_info");
    if (!get_info) {
        fprintf(stderr, "Module %s missing module_get_info\n", path);
        dlclose(handle);
        pthread_rwlock_unlock(&g_manager.lock);
        return -1;
    }
    
    // Get module ops
    module_ops_t* (*get_ops)(void) = dlsym(handle, "module_get_ops");
    if (!get_ops) {
        fprintf(stderr, "Module %s missing module_get_ops\n", path);
        dlclose(handle);
        pthread_rwlock_unlock(&g_manager.lock);
        return -1;
    }
    
    // Initialize entry
    entry->handle = handle;
    entry->info = get_info();
    entry->ops = get_ops();
    entry->id = entry->info->id;
    strcpy(entry->path, full_path);
    atomic_store(&entry->state, 1);  // Loaded
    
    // Call module init
    if (entry->ops->init) {
        if (entry->ops->init(entry->info) != 0) {
            fprintf(stderr, "Module %s init failed\n", entry->info->name);
            dlclose(handle);
            atomic_store(&entry->state, 0);
            pthread_rwlock_unlock(&g_manager.lock);
            return -1;
        }
    }
    
    atomic_fetch_add(&g_manager.module_count, 1);
    atomic_fetch_add(&g_manager.loads, 1);
    
    printf("Loaded module: %s (ID: 0x%08x)\n", entry->info->name, entry->id);
    
    pthread_rwlock_unlock(&g_manager.lock);
    return entry->id;
}

int module_unload(uint32_t id) {
    pthread_rwlock_wrlock(&g_manager.lock);
    
    module_entry_t* entry = find_module_by_id(id);
    if (!entry) {
        pthread_rwlock_unlock(&g_manager.lock);
        return -1;
    }
    
    // Stop module if running
    if (atomic_load(&entry->state) == 2) {
        if (entry->ops->stop) {
            entry->ops->stop();
        }
        atomic_store(&entry->state, 1);
    }
    
    // Cleanup
    if (entry->ops->cleanup) {
        entry->ops->cleanup();
    }
    
    // Unload
    dlclose(entry->handle);
    atomic_store(&entry->state, 0);
    atomic_fetch_sub(&g_manager.module_count, 1);
    atomic_fetch_add(&g_manager.unloads, 1);
    
    printf("Unloaded module ID: 0x%08x\n", id);
    
    pthread_rwlock_unlock(&g_manager.lock);
    return 0;
}

int module_reload(uint32_t id) {
    pthread_rwlock_rdlock(&g_manager.lock);
    
    module_entry_t* entry = find_module_by_id(id);
    if (!entry) {
        pthread_rwlock_unlock(&g_manager.lock);
        return -1;
    }
    
    char path_copy[256];
    strcpy(path_copy, entry->path);
    
    pthread_rwlock_unlock(&g_manager.lock);
    
    // Unload and reload
    module_unload(id);
    
    atomic_fetch_add(&g_manager.reloads, 1);
    
    return module_load(path_copy);
}

static void* module_thread_wrapper(void* arg) {
    module_entry_t* entry = (module_entry_t*)arg;
    
    // Set thread name
    char thread_name[16];
    snprintf(thread_name, sizeof(thread_name), "mod_%s", entry->info->name);
    pthread_setname_np(pthread_self(), thread_name);
    
    // Set CPU affinity if specified
    if (entry->info->cpu_affinity_mask) {
        cpu_set_t cpuset;
        CPU_ZERO(&cpuset);
        for (int i = 0; i < 64; i++) {
            if (entry->info->cpu_affinity_mask & (1ULL << i)) {
                CPU_SET(i, &cpuset);
            }
        }
        pthread_setaffinity_np(pthread_self(), sizeof(cpuset), &cpuset);
    }
    
    // Run module
    atomic_store(&entry->state, 2);  // Running
    
    if (entry->ops->run) {
        entry->ops->run();
    }
    
    atomic_store(&entry->state, 1);  // Back to loaded
    return NULL;
}

int module_start(uint32_t id) {
    pthread_rwlock_rdlock(&g_manager.lock);
    
    module_entry_t* entry = find_module_by_id(id);
    if (!entry || atomic_load(&entry->state) != 1) {
        pthread_rwlock_unlock(&g_manager.lock);
        return -1;
    }
    
    // Create thread for module
    if (pthread_create(&entry->thread, NULL, module_thread_wrapper, entry) != 0) {
        pthread_rwlock_unlock(&g_manager.lock);
        return -1;
    }
    
    pthread_rwlock_unlock(&g_manager.lock);
    return 0;
}

int module_stop(uint32_t id) {
    pthread_rwlock_rdlock(&g_manager.lock);
    
    module_entry_t* entry = find_module_by_id(id);
    if (!entry || atomic_load(&entry->state) != 2) {
        pthread_rwlock_unlock(&g_manager.lock);
        return -1;
    }
    
    // Signal stop
    if (entry->ops->stop) {
        entry->ops->stop();
    }
    
    pthread_rwlock_unlock(&g_manager.lock);
    
    // Wait for thread
    pthread_join(entry->thread, NULL);
    
    return 0;
}

int module_send_message(uint32_t src_id, uint32_t dst_id, 
                        const void* data, size_t len) {
    pthread_rwlock_rdlock(&g_manager.lock);
    
    module_entry_t* dst = find_module_by_id(dst_id);
    if (!dst || atomic_load(&dst->state) < 1) {
        pthread_rwlock_unlock(&g_manager.lock);
        return -1;
    }
    
    int result = -1;
    if (dst->ops->handle_message) {
        result = dst->ops->handle_message(src_id, data, len);
    }
    
    pthread_rwlock_unlock(&g_manager.lock);
    return result;
}

void module_list(void) {
    pthread_rwlock_rdlock(&g_manager.lock);
    
    printf("Loaded Modules:\n");
    printf("%-20s %-10s %-10s %s\n", "Name", "ID", "State", "Version");
    printf("%-20s %-10s %-10s %s\n", "----", "--", "-----", "-------");
    
    for (int i = 0; i < MAX_MODULES; i++) {
        module_entry_t* entry = &g_manager.modules[i];
        int state = atomic_load(&entry->state);
        if (state > 0) {
            const char* state_str = state == 1 ? "Loaded" : 
                                   state == 2 ? "Running" : "Error";
            printf("%-20s 0x%08x %-10s %d.%d.%d\n",
                   entry->info->name,
                   entry->id,
                   state_str,
                   entry->info->version_major,
                   entry->info->version_minor,
                   entry->info->version_patch);
        }
    }
    
    printf("\nStatistics:\n");
    printf("  Total modules: %d\n", atomic_load(&g_manager.module_count));
    printf("  Loads: %lu\n", atomic_load(&g_manager.loads));
    printf("  Unloads: %lu\n", atomic_load(&g_manager.unloads));
    printf("  Reloads: %lu\n", atomic_load(&g_manager.reloads));
    
    pthread_rwlock_unlock(&g_manager.lock);
}

void module_loader_cleanup(void) {
    // Stop and unload all modules
    for (int i = 0; i < MAX_MODULES; i++) {
        if (atomic_load(&g_manager.modules[i].state) > 0) {
            module_unload(g_manager.modules[i].id);
        }
    }
    
    pthread_rwlock_destroy(&g_manager.lock);
}