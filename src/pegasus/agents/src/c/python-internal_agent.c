/*
 * PYTHON-INTERNAL AGENT - Python/ML/AI Execution Environment
 * 
 * Specialized Python execution environment agent for John's local datascience setup.
 * Operates within virtual environment at /home/john/datascience/, executing internal
 * modules, AI/ML workloads, and NPU optimizations. Direct access to proprietary
 * sword_ai libraries, OpenVINO runtime, and hardware acceleration utilities.
 * 
 * HARDWARE OPTIMIZATION:
 * - P-cores (0-11) preferred for Python single-threaded operations (26% faster)
 * - AVX-512 provides 60% speedup for ML workloads (if ancient microcode present)
 * - NPU integration for AI inference (limited functionality with driver v1.17.0)
 * - Thermal-aware operation (85-95°C normal for MIL-SPEC hardware)
 * 
 * Author: Agent Communication System v7.0
 * Version: 7.0.0 Production
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <stdbool.h>
#include <stdatomic.h>
#include <pthread.h>
#include <sys/time.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <unistd.h>
#include <errno.h>
#include <math.h>
#include <signal.h>
#include <sched.h>
#include <time.h>
#include <dirent.h>
#include "compatibility_layer.h"
#include "agent_protocol.h"

// Python-Internal Agent Protocol Constants
#define PYID_MAGIC 0x50594944          // 'PYID' - Python Internal Magic
#define PYID_VERSION 0x0700             // v7.0
#define MAX_CONCURRENT_TASKS 32         // Python GIL limits true concurrency
#define MAX_ENV_VARS 64                 // Environment variables to track
// VENV_PATH now defined in paths.h - use claude_init_paths() to initialize
#define PYTHON_CMD "python3.11"
#define THERMAL_THRESHOLD_NORMAL 95    // 95°C normal operation limit
#define THERMAL_THRESHOLD_EMERGENCY 100 // 100°C emergency limit
#define NPU_DEVICE_PREFIX "/dev/intel_vsc"

// Python-Internal State Enums
typedef enum {
    PYID_STATE_UNINITIALIZED = 0,
    PYID_STATE_VENV_ACTIVATING,
    PYID_STATE_IDLE,
    PYID_STATE_EXECUTING,
    PYID_STATE_BENCHMARKING,
    PYID_STATE_NPU_TESTING,
    PYID_STATE_ERROR,
    PYID_STATE_THERMAL_PAUSE
} pyid_state_t;

typedef enum {
    PYID_TASK_SCRIPT_EXEC = 0,
    PYID_TASK_MODULE_IMPORT,
    PYID_TASK_AI_INFERENCE,
    PYID_TASK_ML_TRAINING,
    PYID_TASK_NPU_WORKLOAD,
    PYID_TASK_BENCHMARK,
    PYID_TASK_ENV_VALIDATION
} pyid_task_type_t;

typedef enum {
    PYID_EXEC_PROFILE_MAX_PERF = 0,    // AVX-512 + NPU + P-cores
    PYID_EXEC_PROFILE_HIGH_PERF,       // AVX2 + P-cores
    PYID_EXEC_PROFILE_BALANCED,        // All cores
    PYID_EXEC_PROFILE_EFFICIENCY,      // E-cores only
    PYID_EXEC_PROFILE_THERMAL_PROTECT  // Thermal throttled
} pyid_exec_profile_t;

// Python Environment Variable
typedef struct {
    char name[128];
    char value[512];
    bool critical;  // If true, agent fails without this var
} pyid_env_var_t;

// Python Task Structure
typedef struct {
    uint32_t task_id;
    pyid_task_type_t type;
    char script_path[256];
    char module_name[128];
    char arguments[512];
    pyid_exec_profile_t exec_profile;
    uint64_t start_time_ns;
    uint64_t end_time_ns;
    double progress;
    bool completed;
    int exit_code;
    char output[4096];
    char error[1024];
} pyid_task_t;

// AI/ML Performance Metrics
typedef struct {
    char model_name[64];
    double latency_ms;
    double throughput;
    double accuracy;
    uint32_t batch_size;
    bool npu_used;
    uint64_t timestamp;
} pyid_ml_metric_t;

// Virtual Environment Status
typedef struct {
    bool activated;
    char python_version[32];
    char pip_version[32];
    bool sword_ai_available;
    bool openvino_available;
    bool numpy_mkl;  // Intel MKL-optimized NumPy
    uint32_t package_count;
    char package_hash[64];  // Hash of installed packages for validation
} pyid_venv_status_t;

// NPU Device Information
typedef struct {
    bool available;
    char device_path[64];
    char driver_version[32];
    uint8_t utilization_percent;
    double temperature_c;
    uint32_t supported_ops_count;
    bool functional;  // Given driver v1.17.0 limitations
} pyid_npu_info_t;

// Python-Internal Agent Structure
typedef struct {
    ufp_context_t* comm_context;
    char name[64];
    uint32_t agent_id;
    agent_state_t state;
    
    // Python-specific state
    pyid_state_t pyid_state;
    pyid_venv_status_t venv_status;
    pyid_npu_info_t npu_info;
    pyid_exec_profile_t current_profile;
    
    // Task management
    pyid_task_t active_tasks[MAX_CONCURRENT_TASKS];
    uint32_t active_task_count;
    pthread_mutex_t task_mutex;
    pthread_cond_t task_available;
    
    // Environment variables
    pyid_env_var_t env_vars[MAX_ENV_VARS];
    uint32_t env_var_count;
    
    // Hardware configuration
    bool avx512_available;
    uint32_t p_cores_allocated;
    uint32_t e_cores_allocated;
    double cpu_temperature;
    uint64_t memory_used_mb;
    uint64_t memory_limit_mb;
    
    // Performance metrics
    pyid_ml_metric_t ml_metrics[16];
    uint32_t ml_metric_count;
    uint64_t scripts_executed;
    uint64_t scripts_succeeded;
    uint64_t npu_invocations;
    uint64_t npu_failures;
    double avg_execution_time_ms;
    
    // Threading
    pthread_t worker_thread;
    pthread_t monitor_thread;
    pthread_t venv_thread;
    bool running;
    
    // File descriptors for Python subprocess
    int python_stdin_fd;
    int python_stdout_fd;
    int python_stderr_fd;
    pid_t python_pid;
} pyid_agent_t;

// Global agent instance
static pyid_agent_t* g_pyid_agent = NULL;

// Function prototypes
static int pyid_init_hardware_config(pyid_agent_t* agent);
static int pyid_activate_venv(pyid_agent_t* agent);
static int pyid_validate_environment(pyid_agent_t* agent);
static int pyid_check_npu_availability(pyid_agent_t* agent);
static int pyid_execute_python_script(pyid_agent_t* agent, pyid_task_t* task);
static int pyid_import_module(pyid_agent_t* agent, const char* module_name);
static int pyid_run_ai_benchmark(pyid_agent_t* agent, const char* model_name);
static int pyid_select_execution_profile(pyid_agent_t* agent);
static void* pyid_worker_thread(void* arg);
static void* pyid_monitor_thread(void* arg);
static void* pyid_venv_manager_thread(void* arg);
static double pyid_get_cpu_temperature(void);
static uint64_t pyid_get_memory_usage_mb(void);
static uint64_t pyid_get_timestamp_ns(void);
static void pyid_update_ml_metrics(pyid_agent_t* agent);
static int pyid_add_task(pyid_agent_t* agent, pyid_task_type_t type, const char* target);

// Initialize Python-Internal agent
int pyid_init(pyid_agent_t* agent) {
    memset(agent, 0, sizeof(pyid_agent_t));
    
    // Initialize communication context
    agent->comm_context = ufp_create_context("python-internal");
    if (!agent->comm_context) {
        fprintf(stderr, "PYTHON-INTERNAL: Failed to create communication context\n");
        return -1;
    }
    
    strcpy(agent->name, "python-internal");
    agent->state = AGENT_STATE_IDLE;
    agent->pyid_state = PYID_STATE_UNINITIALIZED;
    agent->running = true;
    agent->memory_limit_mb = 48 * 1024;  // 48GB limit (75% of 64GB)
    
    // Initialize critical environment variables
    agent->env_var_count = 0;
    strcpy(agent->env_vars[0].name, "PYTHONPATH");
    snprintf(agent->env_vars[0].value, sizeof(agent->env_vars[0].value),
             "%s/src:%s", VENV_PATH, getenv("PYTHONPATH") ?: "");
    agent->env_vars[0].critical = true;
    agent->env_var_count++;
    
    strcpy(agent->env_vars[1].name, "OV_CACHE_DIR");
    strcpy(agent->env_vars[1].value, "/tmp/openvino_cache");
    agent->env_vars[1].critical = false;
    agent->env_var_count++;
    
    strcpy(agent->env_vars[2].name, "OMP_NUM_THREADS");
    strcpy(agent->env_vars[2].value, "1");  // Prevent thread explosion
    agent->env_vars[2].critical = false;
    agent->env_var_count++;
    
    strcpy(agent->env_vars[3].name, "NPU_COMPILER_TYPE");
    strcpy(agent->env_vars[3].value, "DRIVER");
    agent->env_vars[3].critical = false;
    agent->env_var_count++;
    
    strcpy(agent->env_vars[4].name, "SWORD_AI_DEBUG");
    strcpy(agent->env_vars[4].value, "1");
    agent->env_vars[4].critical = false;
    agent->env_var_count++;
    
    // Initialize hardware configuration
    if (pyid_init_hardware_config(agent) != 0) {
        fprintf(stderr, "PYTHON-INTERNAL: Failed to initialize hardware configuration\n");
        return -1;
    }
    
    // Initialize threading primitives
    pthread_mutex_init(&agent->task_mutex, NULL);
    pthread_cond_init(&agent->task_available, NULL);
    
    // Start worker threads
    if (pthread_create(&agent->worker_thread, NULL, pyid_worker_thread, agent) != 0) {
        fprintf(stderr, "PYTHON-INTERNAL: Failed to create worker thread\n");
        return -1;
    }
    
    if (pthread_create(&agent->monitor_thread, NULL, pyid_monitor_thread, agent) != 0) {
        fprintf(stderr, "PYTHON-INTERNAL: Failed to create monitor thread\n");
        return -1;
    }
    
    if (pthread_create(&agent->venv_thread, NULL, pyid_venv_manager_thread, agent) != 0) {
        fprintf(stderr, "PYTHON-INTERNAL: Failed to create venv manager thread\n");
        return -1;
    }
    
    // Register with discovery service
    if (agent_register("python-internal", AGENT_TYPE_PYTHON_INTERNAL, NULL, 0) != 0) {
        fprintf(stderr, "PYTHON-INTERNAL: Failed to register with discovery service\n");
        return -1;
    }
    
    // Activate virtual environment
    agent->pyid_state = PYID_STATE_VENV_ACTIVATING;
    if (pyid_activate_venv(agent) != 0) {
        fprintf(stderr, "PYTHON-INTERNAL: Warning - virtual environment activation failed\n");
        agent->pyid_state = PYID_STATE_ERROR;
    } else {
        agent->pyid_state = PYID_STATE_IDLE;
    }
    
    printf("PYTHON-INTERNAL: Agent initialized successfully\n");
    printf("  Virtual Environment: %s\n", VENV_PATH);
    printf("  Python Version: %s\n", agent->venv_status.python_version);
    printf("  Hardware: P-cores=%u, E-cores=%u, AVX-512=%s\n",
           agent->p_cores_allocated, agent->e_cores_allocated,
           agent->avx512_available ? "Available" : "Not Available");
    printf("  NPU: %s (driver v%s)\n",
           agent->npu_info.available ? "Available" : "Not Available",
           agent->npu_info.driver_version);
    printf("  Temperature: %.1f°C\n", agent->cpu_temperature);
    printf("  Memory Limit: %lu MB\n", agent->memory_limit_mb);
    
    return 0;
}

// Initialize hardware configuration
static int pyid_init_hardware_config(pyid_agent_t* agent) {
    // Check microcode version to determine AVX-512 availability
    FILE* f = fopen("/proc/cpuinfo", "r");
    if (f) {
        char line[256];
        while (fgets(line, sizeof(line), f)) {
            if (strstr(line, "microcode")) {
                unsigned int microcode;
                if (sscanf(line, "microcode : 0x%x", &microcode) == 1) {
                    // Ancient microcode (0x01, 0x02) enables AVX-512
                    if (microcode <= 0x02) {
                        agent->avx512_available = true;
                        printf("PYTHON-INTERNAL: Ancient microcode detected (0x%x) - AVX-512 enabled!\n", microcode);
                        printf("  WARNING: System vulnerable to Spectre/Meltdown\n");
                    } else {
                        printf("PYTHON-INTERNAL: Modern microcode (0x%x) - AVX-512 disabled\n", microcode);
                    }
                    break;
                }
            }
        }
        fclose(f);
    }
    
    // Allocate cores optimally for Python workloads
    // Python benefits from P-cores due to higher single-thread IPC
    agent->p_cores_allocated = 6;  // Use all P-cores for compute
    agent->e_cores_allocated = 4;  // Some E-cores for I/O and background
    
    // Check NPU availability
    pyid_check_npu_availability(agent);
    
    // Get initial temperature
    agent->cpu_temperature = pyid_get_cpu_temperature();
    
    // Get initial memory usage
    agent->memory_used_mb = pyid_get_memory_usage_mb();
    
    return 0;
}

// Check NPU availability
static int pyid_check_npu_availability(pyid_agent_t* agent) {
    agent->npu_info.available = false;
    strcpy(agent->npu_info.driver_version, "1.17.0");  // Known version
    
    // Check for NPU device files
    DIR* dir = opendir("/dev");
    if (dir) {
        struct dirent* entry;
        while ((entry = readdir(dir)) != NULL) {
            if (strncmp(entry->d_name, "intel_vsc", 9) == 0) {
                agent->npu_info.available = true;
                snprintf(agent->npu_info.device_path, sizeof(agent->npu_info.device_path),
                        "/dev/%s", entry->d_name);
                break;
            }
        }
        closedir(dir);
    }
    
    if (agent->npu_info.available) {
        // NPU present but driver v1.17.0 has limited functionality
        agent->npu_info.functional = false;  // Only ~5% ops work
        agent->npu_info.supported_ops_count = 3;  // element-wise, small matmul, basic tensor
        printf("PYTHON-INTERNAL: NPU detected at %s (limited functionality)\n",
               agent->npu_info.device_path);
    }
    
    return 0;
}

// Activate virtual environment
static int pyid_activate_venv(pyid_agent_t* agent) {
    char cmd[512];
    FILE* pipe;
    
    // Check if venv directory exists
    struct stat st;
    if (stat(VENV_PATH, &st) != 0 || !S_ISDIR(st.st_mode)) {
        fprintf(stderr, "PYTHON-INTERNAL: Virtual environment not found at %s\n", VENV_PATH);
        return -1;
    }
    
    // Get Python version
    snprintf(cmd, sizeof(cmd), "%s/bin/python --version 2>&1", VENV_PATH);
    pipe = popen(cmd, "r");
    if (pipe) {
        if (fgets(agent->venv_status.python_version, sizeof(agent->venv_status.python_version), pipe)) {
            // Remove newline
            agent->venv_status.python_version[strcspn(agent->venv_status.python_version, "\n")] = 0;
        }
        pclose(pipe);
    }
    
    // Get pip version
    snprintf(cmd, sizeof(cmd), "%s/bin/pip --version 2>&1", VENV_PATH);
    pipe = popen(cmd, "r");
    if (pipe) {
        char line[256];
        if (fgets(line, sizeof(line), pipe)) {
            // Extract version from pip output
            char* ver = strstr(line, "pip ");
            if (ver) {
                sscanf(ver, "pip %31s", agent->venv_status.pip_version);
            }
        }
        pclose(pipe);
    }
    
    // Check for sword_ai library
    snprintf(cmd, sizeof(cmd), "%s/bin/python -c 'import sword_ai; print(sword_ai.__version__)' 2>&1", VENV_PATH);
    pipe = popen(cmd, "r");
    if (pipe) {
        char line[256];
        if (fgets(line, sizeof(line), pipe) && !strstr(line, "Error") && !strstr(line, "ModuleNotFoundError")) {
            agent->venv_status.sword_ai_available = true;
            printf("PYTHON-INTERNAL: sword_ai library available\n");
        }
        pclose(pipe);
    }
    
    // Check for OpenVINO
    snprintf(cmd, sizeof(cmd), "%s/bin/python -c 'from openvino.runtime import Core; print(\"OpenVINO OK\")' 2>&1", VENV_PATH);
    pipe = popen(cmd, "r");
    if (pipe) {
        char line[256];
        if (fgets(line, sizeof(line), pipe) && strstr(line, "OpenVINO OK")) {
            agent->venv_status.openvino_available = true;
            printf("PYTHON-INTERNAL: OpenVINO runtime available\n");
        }
        pclose(pipe);
    }
    
    // Check for Intel MKL NumPy
    snprintf(cmd, sizeof(cmd), "%s/bin/python -c 'import numpy; print(numpy.show_config())' 2>&1 | grep -i mkl", VENV_PATH);
    pipe = popen(cmd, "r");
    if (pipe) {
        char line[256];
        if (fgets(line, sizeof(line), pipe)) {
            agent->venv_status.numpy_mkl = true;
            printf("PYTHON-INTERNAL: NumPy with Intel MKL detected\n");
        }
        pclose(pipe);
    }
    
    agent->venv_status.activated = true;
    return 0;
}

// Validate environment
static int pyid_validate_environment(pyid_agent_t* agent) {
    bool all_critical_present = true;
    
    // Set environment variables
    for (uint32_t i = 0; i < agent->env_var_count; i++) {
        setenv(agent->env_vars[i].name, agent->env_vars[i].value, 1);
        
        if (agent->env_vars[i].critical) {
            char* val = getenv(agent->env_vars[i].name);
            if (!val || strcmp(val, agent->env_vars[i].value) != 0) {
                fprintf(stderr, "PYTHON-INTERNAL: Critical env var %s not set correctly\n",
                       agent->env_vars[i].name);
                all_critical_present = false;
            }
        }
    }
    
    return all_critical_present ? 0 : -1;
}

// Select execution profile based on conditions
static int pyid_select_execution_profile(pyid_agent_t* agent) {
    pyid_exec_profile_t new_profile;
    
    if (agent->cpu_temperature >= THERMAL_THRESHOLD_EMERGENCY) {
        new_profile = PYID_EXEC_PROFILE_THERMAL_PROTECT;
    } else if (agent->avx512_available && agent->cpu_temperature < THERMAL_THRESHOLD_NORMAL && 
               agent->npu_info.functional) {
        new_profile = PYID_EXEC_PROFILE_MAX_PERF;
    } else if (agent->cpu_temperature < THERMAL_THRESHOLD_NORMAL) {
        new_profile = PYID_EXEC_PROFILE_HIGH_PERF;
    } else if (agent->memory_used_mb < agent->memory_limit_mb * 0.8) {
        new_profile = PYID_EXEC_PROFILE_BALANCED;
    } else {
        new_profile = PYID_EXEC_PROFILE_EFFICIENCY;
    }
    
    if (new_profile != agent->current_profile) {
        agent->current_profile = new_profile;
        
        const char* profile_names[] = {
            "Maximum Performance", "High Performance", "Balanced", 
            "Efficiency", "Thermal Protection"
        };
        printf("PYTHON-INTERNAL: Switched to %s profile\n", profile_names[new_profile]);
    }
    
    return 0;
}

// Execute Python script
static int pyid_execute_python_script(pyid_agent_t* agent, pyid_task_t* task) {
    char cmd[1024];
    char python_path[256];
    FILE* pipe;
    
    // Ensure environment is valid
    if (pyid_validate_environment(agent) != 0) {
        strcpy(task->error, "Environment validation failed");
        return -1;
    }
    
    // Build Python command
    snprintf(python_path, sizeof(python_path), "%s/bin/python", VENV_PATH);
    
    // Set CPU affinity based on execution profile
    char taskset_cmd[128] = "";
    switch (agent->current_profile) {
        case PYID_EXEC_PROFILE_MAX_PERF:
        case PYID_EXEC_PROFILE_HIGH_PERF:
            // Use P-cores only (0-11)
            snprintf(taskset_cmd, sizeof(taskset_cmd), "taskset -c 0-11 ");
            break;
        case PYID_EXEC_PROFILE_BALANCED:
            // Use all cores
            snprintf(taskset_cmd, sizeof(taskset_cmd), "taskset -c 0-21 ");
            break;
        case PYID_EXEC_PROFILE_EFFICIENCY:
        case PYID_EXEC_PROFILE_THERMAL_PROTECT:
            // Use E-cores only (12-21)
            snprintf(taskset_cmd, sizeof(taskset_cmd), "taskset -c 12-21 ");
            break;
    }
    
    // Build full command
    if (task->type == PYID_TASK_MODULE_IMPORT) {
        snprintf(cmd, sizeof(cmd), "%s%s -c 'import %s; print(\"%s imported successfully\")'",
                taskset_cmd, python_path, task->module_name, task->module_name);
    } else {
        snprintf(cmd, sizeof(cmd), "%s%s %s %s 2>&1",
                taskset_cmd, python_path, task->script_path, task->arguments);
    }
    
    // Execute command
    task->start_time_ns = pyid_get_timestamp_ns();
    pipe = popen(cmd, "r");
    
    if (!pipe) {
        snprintf(task->error, sizeof(task->error), "Failed to execute: %s", strerror(errno));
        return -1;
    }
    
    // Read output
    size_t output_len = 0;
    char line[512];
    while (fgets(line, sizeof(line), pipe) && output_len < sizeof(task->output) - 512) {
        size_t line_len = strlen(line);
        if (output_len + line_len < sizeof(task->output)) {
            strcat(task->output, line);
            output_len += line_len;
        }
        
        // Update progress (simplified - could parse actual progress markers)
        task->progress = (double)output_len / 1024.0;
        if (task->progress > 1.0) task->progress = 1.0;
    }
    
    task->exit_code = pclose(pipe);
    task->end_time_ns = pyid_get_timestamp_ns();
    task->completed = true;
    
    if (WIFEXITED(task->exit_code)) {
        task->exit_code = WEXITSTATUS(task->exit_code);
    }
    
    return task->exit_code;
}

// Import Python module
static int pyid_import_module(pyid_agent_t* agent, const char* module_name) {
    pyid_task_t import_task;
    memset(&import_task, 0, sizeof(import_task));
    
    import_task.type = PYID_TASK_MODULE_IMPORT;
    strncpy(import_task.module_name, module_name, sizeof(import_task.module_name) - 1);
    
    return pyid_execute_python_script(agent, &import_task);
}

// Run AI benchmark
static int pyid_run_ai_benchmark(pyid_agent_t* agent, const char* model_name) {
    pyid_task_t bench_task;
    memset(&bench_task, 0, sizeof(bench_task));
    
    bench_task.type = PYID_TASK_BENCHMARK;
    snprintf(bench_task.script_path, sizeof(bench_task.script_path),
             "%s/benchmarks/ai_bench.py", VENV_PATH);
    snprintf(bench_task.arguments, sizeof(bench_task.arguments),
             "--model %s --device %s", model_name,
             agent->npu_info.functional ? "NPU" : "CPU");
    
    int result = pyid_execute_python_script(agent, &bench_task);
    
    if (result == 0) {
        // Parse benchmark results (simplified)
        pyid_ml_metric_t* metric = &agent->ml_metrics[agent->ml_metric_count % 16];
        strncpy(metric->model_name, model_name, sizeof(metric->model_name) - 1);
        metric->timestamp = pyid_get_timestamp_ns();
        
        // Extract metrics from output (simplified parsing)
        char* latency_str = strstr(bench_task.output, "Latency:");
        if (latency_str) {
            sscanf(latency_str, "Latency: %lf ms", &metric->latency_ms);
        }
        
        char* throughput_str = strstr(bench_task.output, "Throughput:");
        if (throughput_str) {
            sscanf(throughput_str, "Throughput: %lf", &metric->throughput);
        }
        
        metric->npu_used = agent->npu_info.functional;
        agent->ml_metric_count++;
    }
    
    return result;
}

// Add task to queue
static int pyid_add_task(pyid_agent_t* agent, pyid_task_type_t type, const char* target) {
    pthread_mutex_lock(&agent->task_mutex);
    
    if (agent->active_task_count >= MAX_CONCURRENT_TASKS) {
        pthread_mutex_unlock(&agent->task_mutex);
        return -1;
    }
    
    pyid_task_t* task = &agent->active_tasks[agent->active_task_count];
    memset(task, 0, sizeof(pyid_task_t));
    
    task->task_id = agent->scripts_executed + 1;
    task->type = type;
    task->exec_profile = agent->current_profile;
    
    switch (type) {
        case PYID_TASK_SCRIPT_EXEC:
            strncpy(task->script_path, target, sizeof(task->script_path) - 1);
            break;
        case PYID_TASK_MODULE_IMPORT:
            strncpy(task->module_name, target, sizeof(task->module_name) - 1);
            break;
        case PYID_TASK_AI_INFERENCE:
        case PYID_TASK_ML_TRAINING:
        case PYID_TASK_BENCHMARK:
            strncpy(task->script_path, target, sizeof(task->script_path) - 1);
            break;
        default:
            break;
    }
    
    agent->active_task_count++;
    pthread_cond_signal(&agent->task_available);
    pthread_mutex_unlock(&agent->task_mutex);
    
    return 0;
}

// Worker thread
static void* pyid_worker_thread(void* arg) {
    pyid_agent_t* agent = (pyid_agent_t*)arg;
    
    while (agent->running) {
        pthread_mutex_lock(&agent->task_mutex);
        
        while (agent->active_task_count == 0 && agent->running) {
            pthread_cond_wait(&agent->task_available, &agent->task_mutex);
        }
        
        if (!agent->running) {
            pthread_mutex_unlock(&agent->task_mutex);
            break;
        }
        
        // Get next task
        pyid_task_t current_task;
        if (agent->active_task_count > 0) {
            memcpy(&current_task, &agent->active_tasks[0], sizeof(pyid_task_t));
            
            // Shift remaining tasks
            for (uint32_t i = 1; i < agent->active_task_count; i++) {
                memcpy(&agent->active_tasks[i-1], &agent->active_tasks[i], sizeof(pyid_task_t));
            }
            agent->active_task_count--;
        }
        
        pthread_mutex_unlock(&agent->task_mutex);
        
        // Execute task
        if (current_task.task_id > 0) {
            agent->pyid_state = PYID_STATE_EXECUTING;
            
            int result = pyid_execute_python_script(agent, &current_task);
            
            agent->scripts_executed++;
            if (result == 0) {
                agent->scripts_succeeded++;
            }
            
            // Calculate average execution time
            double exec_time_ms = (current_task.end_time_ns - current_task.start_time_ns) / 1000000.0;
            agent->avg_execution_time_ms = (agent->avg_execution_time_ms * (agent->scripts_executed - 1) + 
                                           exec_time_ms) / agent->scripts_executed;
            
            agent->pyid_state = PYID_STATE_IDLE;
            
            printf("PYTHON-INTERNAL: Task %u completed (exit: %d, time: %.2f ms)\n",
                   current_task.task_id, current_task.exit_code, exec_time_ms);
        }
    }
    
    return NULL;
}

// Monitor thread
static void* pyid_monitor_thread(void* arg) {
    pyid_agent_t* agent = (pyid_agent_t*)arg;
    
    while (agent->running) {
        // Update system metrics
        agent->cpu_temperature = pyid_get_cpu_temperature();
        agent->memory_used_mb = pyid_get_memory_usage_mb();
        
        // Select appropriate execution profile
        pyid_select_execution_profile(agent);
        
        // Thermal management
        if (agent->cpu_temperature > THERMAL_THRESHOLD_NORMAL) {
            printf("PYTHON-INTERNAL: High temperature warning (%.1f°C)\n", agent->cpu_temperature);
            if (agent->cpu_temperature > THERMAL_THRESHOLD_EMERGENCY) {
                agent->pyid_state = PYID_STATE_THERMAL_PAUSE;
                printf("PYTHON-INTERNAL: Emergency thermal pause\n");
            }
        } else if (agent->pyid_state == PYID_STATE_THERMAL_PAUSE) {
            agent->pyid_state = PYID_STATE_IDLE;
            printf("PYTHON-INTERNAL: Resuming from thermal pause (%.1f°C)\n", agent->cpu_temperature);
        }
        
        // Memory management
        if (agent->memory_used_mb > agent->memory_limit_mb * 0.9) {
            printf("PYTHON-INTERNAL: Memory warning (%lu MB / %lu MB)\n",
                   agent->memory_used_mb, agent->memory_limit_mb);
        }
        
        // NPU monitoring (if available)
        if (agent->npu_info.available) {
            // Simplified NPU utilization check
            agent->npu_info.utilization_percent = 0;  // Would query actual NPU stats
        }
        
        sleep(5);
    }
    
    return NULL;
}

// Virtual environment manager thread
static void* pyid_venv_manager_thread(void* arg) {
    pyid_agent_t* agent = (pyid_agent_t*)arg;
    
    while (agent->running) {
        // Periodically validate environment
        if (!agent->venv_status.activated) {
            printf("PYTHON-INTERNAL: Attempting to reactivate virtual environment\n");
            pyid_activate_venv(agent);
        }
        
        // Check critical packages periodically
        if (agent->venv_status.activated && agent->venv_status.sword_ai_available) {
            // Verify sword_ai is still importable
            if (pyid_import_module(agent, "sword_ai") != 0) {
                agent->venv_status.sword_ai_available = false;
                printf("PYTHON-INTERNAL: Warning - sword_ai no longer available\n");
            }
        }
        
        sleep(60);  // Check every minute
    }
    
    return NULL;
}

// Get CPU temperature
static double pyid_get_cpu_temperature(void) {
    FILE* f = fopen("/sys/class/thermal/thermal_zone0/temp", "r");
    if (!f) return 85.0;  // Default to normal operating temp
    
    int temp_millicelsius;
    if (fscanf(f, "%d", &temp_millicelsius) == 1) {
        fclose(f);
        return temp_millicelsius / 1000.0;
    }
    
    fclose(f);
    return 85.0;
}

// Get memory usage
static uint64_t pyid_get_memory_usage_mb(void) {
    FILE* f = fopen("/proc/self/status", "r");
    if (!f) return 0;
    
    char line[256];
    uint64_t vmrss_kb = 0;
    
    while (fgets(line, sizeof(line), f)) {
        if (strncmp(line, "VmRSS:", 6) == 0) {
            sscanf(line, "VmRSS: %lu kB", &vmrss_kb);
            break;
        }
    }
    
    fclose(f);
    return vmrss_kb / 1024;
}

// Get timestamp
static uint64_t pyid_get_timestamp_ns(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (uint64_t)ts.tv_sec * 1000000000UL + (uint64_t)ts.tv_nsec;
}

// Process incoming message
int pyid_process_message(pyid_agent_t* agent, ufp_message_t* msg) {
    if (!agent || !msg) return -1;
    
    printf("PYTHON-INTERNAL: Received message from %s\n", msg->source);
    
    // Parse message and handle different requests
    if (strstr(msg->payload, "execute_script")) {
        char script_path[256];
        if (sscanf(msg->payload, "execute_script:%255s", script_path) == 1) {
            int result = pyid_add_task(agent, PYID_TASK_SCRIPT_EXEC, script_path);
            
            // Send response
            ufp_message_t* response = ufp_message_create();
            strcpy(response->source, agent->name);
            strcpy(response->targets[0], msg->source);
            response->target_count = 1;
            response->msg_type = UFP_MSG_RESPONSE;
            
            if (result == 0) {
                snprintf(response->payload, sizeof(response->payload),
                        "script_queued:tasks_pending:%u", agent->active_task_count);
            } else {
                strcpy(response->payload, "script_rejected:queue_full");
            }
            
            ufp_send(agent->comm_context, response);
            ufp_message_destroy(response);
        }
        
    } else if (strstr(msg->payload, "import_module")) {
        char module_name[128];
        if (sscanf(msg->payload, "import_module:%127s", module_name) == 1) {
            int result = pyid_add_task(agent, PYID_TASK_MODULE_IMPORT, module_name);
            
            ufp_message_t* response = ufp_message_create();
            strcpy(response->source, agent->name);
            strcpy(response->targets[0], msg->source);
            response->target_count = 1;
            response->msg_type = UFP_MSG_RESPONSE;
            
            snprintf(response->payload, sizeof(response->payload),
                    "import_%s", result == 0 ? "queued" : "failed");
            
            ufp_send(agent->comm_context, response);
            ufp_message_destroy(response);
        }
        
    } else if (strstr(msg->payload, "run_benchmark")) {
        char model_name[64];
        if (sscanf(msg->payload, "run_benchmark:%63s", model_name) == 1) {
            pyid_run_ai_benchmark(agent, model_name);
            
            ufp_message_t* response = ufp_message_create();
            strcpy(response->source, agent->name);
            strcpy(response->targets[0], msg->source);
            response->target_count = 1;
            response->msg_type = UFP_MSG_RESPONSE;
            
            pyid_ml_metric_t* latest = &agent->ml_metrics[(agent->ml_metric_count - 1) % 16];
            snprintf(response->payload, sizeof(response->payload),
                    "benchmark_complete:model:%s,latency:%.2fms,throughput:%.1f",
                    latest->model_name, latest->latency_ms, latest->throughput);
            
            ufp_send(agent->comm_context, response);
            ufp_message_destroy(response);
        }
        
    } else if (strstr(msg->payload, "get_status")) {
        ufp_message_t* response = ufp_message_create();
        strcpy(response->source, agent->name);
        strcpy(response->targets[0], msg->source);
        response->target_count = 1;
        response->msg_type = UFP_MSG_RESPONSE;
        
        const char* state_names[] = {
            "uninitialized", "venv_activating", "idle", "executing",
            "benchmarking", "npu_testing", "error", "thermal_pause"
        };
        
        snprintf(response->payload, sizeof(response->payload),
                "status:%s,venv:%s,scripts_executed:%lu,success_rate:%.1f%%,"
                "temp:%.1fC,mem:%luMB,profile:%d,npu:%s",
                state_names[agent->pyid_state],
                agent->venv_status.activated ? "active" : "inactive",
                agent->scripts_executed,
                agent->scripts_succeeded * 100.0 / (agent->scripts_executed ?: 1),
                agent->cpu_temperature,
                agent->memory_used_mb,
                agent->current_profile,
                agent->npu_info.available ? "available" : "unavailable");
        
        ufp_send(agent->comm_context, response);
        ufp_message_destroy(response);
        
    } else if (strstr(msg->payload, "validate_env")) {
        int result = pyid_validate_environment(agent);
        
        ufp_message_t* response = ufp_message_create();
        strcpy(response->source, agent->name);
        strcpy(response->targets[0], msg->source);
        response->target_count = 1;
        response->msg_type = UFP_MSG_RESPONSE;
        
        snprintf(response->payload, sizeof(response->payload),
                "env_validation:%s,python:%s,sword_ai:%s,openvino:%s",
                result == 0 ? "passed" : "failed",
                agent->venv_status.python_version,
                agent->venv_status.sword_ai_available ? "yes" : "no",
                agent->venv_status.openvino_available ? "yes" : "no");
        
        ufp_send(agent->comm_context, response);
        ufp_message_destroy(response);
        
    } else {
        // Generic acknowledgment
        ufp_message_t* ack = ufp_message_create();
        strcpy(ack->source, agent->name);
        strcpy(ack->targets[0], msg->source);
        ack->target_count = 1;
        ack->msg_type = UFP_MSG_ACK;
        strcpy(ack->payload, "pyid_ack:ready");
        
        ufp_send(agent->comm_context, ack);
        ufp_message_destroy(ack);
    }
    
    return 0;
}

// Main agent loop
void pyid_run(pyid_agent_t* agent) {
    ufp_message_t msg;
    uint64_t last_stats_time = pyid_get_timestamp_ns();
    
    printf("PYTHON-INTERNAL: Starting main execution loop\n");
    printf("  Virtual Environment: %s\n", VENV_PATH);
    printf("  Execution Profile: %d\n", agent->current_profile);
    printf("  Hardware: AVX-512=%s, NPU=%s\n",
           agent->avx512_available ? "Yes" : "No",
           agent->npu_info.available ? "Yes" : "No");
    
    while (agent->state != AGENT_STATE_INACTIVE && agent->running) {
        // Handle thermal pause
        if (agent->pyid_state == PYID_STATE_THERMAL_PAUSE) {
            sleep(1);
            continue;
        }
        
        // Receive and process messages
        if (ufp_receive(agent->comm_context, &msg, 100) == UFP_SUCCESS) {
            pyid_process_message(agent, &msg);
        }
        
        // Periodic statistics
        uint64_t current_time = pyid_get_timestamp_ns();
        if (current_time - last_stats_time > 30000000000UL) {  // Every 30 seconds
            printf("PYTHON-INTERNAL: Stats - Scripts: %lu/%lu, Avg time: %.2fms, "
                   "Temp: %.1f°C, Mem: %luMB\n",
                   agent->scripts_succeeded, agent->scripts_executed,
                   agent->avg_execution_time_ms,
                   agent->cpu_temperature, agent->memory_used_mb);
            last_stats_time = current_time;
        }
        
        usleep(100000);  // 100ms
    }
    
    printf("PYTHON-INTERNAL: Main execution loop terminated\n");
}

// Cleanup
void pyid_cleanup(pyid_agent_t* agent) {
    if (!agent) return;
    
    agent->running = false;
    
    // Signal threads
    pthread_cond_broadcast(&agent->task_available);
    
    // Wait for threads
    pthread_join(agent->worker_thread, NULL);
    pthread_join(agent->monitor_thread, NULL);
    pthread_join(agent->venv_thread, NULL);
    
    // Cleanup synchronization
    pthread_mutex_destroy(&agent->task_mutex);
    pthread_cond_destroy(&agent->task_available);
    
    // Cleanup communication
    if (agent->comm_context) {
        ufp_destroy_context(agent->comm_context);
    }
    
    printf("PYTHON-INTERNAL: Cleanup completed\n");
    printf("  Scripts executed: %lu\n", agent->scripts_executed);
    printf("  Scripts succeeded: %lu\n", agent->scripts_succeeded);
    printf("  Success rate: %.1f%%\n",
           agent->scripts_succeeded * 100.0 / (agent->scripts_executed ?: 1));
    printf("  Average execution time: %.2f ms\n", agent->avg_execution_time_ms);
    printf("  NPU invocations: %lu (failures: %lu)\n",
           agent->npu_invocations, agent->npu_failures);
}

// Main function
int main(void) {
    printf("PYTHON-INTERNAL Agent v7.0 - Python/ML/AI Execution Environment\n");
    printf("═══════════════════════════════════════════════════════════════\n");
    
    // Create and initialize agent
    pyid_agent_t agent;
    if (pyid_init(&agent) != 0) {
        fprintf(stderr, "Failed to initialize Python-Internal agent\n");
        return 1;
    }
    
    g_pyid_agent = &agent;
    
    // Set up signal handling
    signal(SIGINT, SIG_DFL);
    signal(SIGTERM, SIG_DFL);
    
    // Run main loop
    pyid_run(&agent);
    
    // Cleanup
    pyid_cleanup(&agent);
    
    return 0;
}