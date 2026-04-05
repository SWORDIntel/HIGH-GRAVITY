#ifndef MODULE_INTERFACE_H
#define MODULE_INTERFACE_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

#define MODULE_API_VERSION 1
#define MODULE_NAME_MAX 64
#define MODULE_DESC_MAX 256

// Message header - cache-line aligned for performance
typedef struct __attribute__((aligned(64))) {
    uint32_t msg_type;
    uint32_t src_module_id;
    uint32_t dst_module_id;
    uint32_t payload_offset;
    uint32_t payload_len;
    uint32_t flags;
    uint64_t timestamp;
    uint8_t padding[24];
} shm_msg_header_t;

// Module information structure
typedef struct {
    uint32_t id;
    char name[MODULE_NAME_MAX];
    char description[MODULE_DESC_MAX];
    uint32_t version_major;
    uint32_t version_minor;
    uint32_t version_patch;
    uint64_t capabilities;
    uint64_t cpu_affinity_mask;
} module_info_t;

// Module operations
typedef struct {
    int (*init)(module_info_t* info);
    void (*cleanup)(void);
    int (*handle_message)(uint32_t src_id, const void* data, size_t len);
    void (*run)(void);
    void (*stop)(void);
    int (*configure)(const char* config);
    int (*get_status)(char* buffer, size_t max_len);
} module_ops_t;

// Module capabilities flags
#define CAP_ROUTING      (1ULL << 0)
#define CAP_PROCESSING   (1ULL << 1)
#define CAP_MONITORING   (1ULL << 2)
#define CAP_SECURITY     (1ULL << 3)
#define CAP_AI_ENHANCED  (1ULL << 4)
#define CAP_HARDWARE_ACCEL (1ULL << 5)

// CPU affinity helpers
#define AFFINITY_P_CORES  0x0000000000000555  // P-cores: 0,2,4,6,8,10
#define AFFINITY_E_CORES  0x00000000000FF000  // E-cores: 12-19
#define AFFINITY_LP_CORES 0x0000000000300000  // LP E-cores: 20-21

// Module registration macros
#define MODULE_EXPORT __attribute__((visibility("default")))

// Required exports for all modules - simplified without macro
// Modules should define g_module_info directly

// Shared memory arena functions (provided by runtime)
int shm_arena_init(const char* name, size_t size);
int shm_ring_create(uint32_t ring_id, size_t size);
int shm_ring_enqueue(uint32_t ring_id, const void* data, size_t len);
int shm_ring_dequeue(uint32_t ring_id, void* data, size_t max_len, size_t* actual_len);
void shm_arena_stats(uint64_t* messages, uint64_t* bytes);
void shm_arena_cleanup(void);

// Module loader functions (provided by runtime)
int module_loader_init(void);
int module_load(const char* path);
int module_unload(uint32_t id);
int module_reload(uint32_t id);
int module_start(uint32_t id);
int module_stop(uint32_t id);
int module_send_message(uint32_t src_id, uint32_t dst_id, const void* data, size_t len);
void module_list(void);
void module_loader_cleanup(void);

// I/O dispatcher functions (provided by runtime)
typedef struct io_request io_request_t;
int io_dispatcher_init(int num_workers);
int io_submit_read(int fd, void* buffer, size_t size, off_t offset,
                   void (*callback)(io_request_t*, int));
int io_submit_write(int fd, const void* buffer, size_t size, off_t offset,
                    void (*callback)(io_request_t*, int));
void io_dispatcher_stats(void);
void io_dispatcher_cleanup(void);

#endif // MODULE_INTERFACE_H