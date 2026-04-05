#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <signal.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <sys/stat.h>
#include <sys/ipc.h>
#include <sys/shm.h>
#include <sys/msg.h>
#include <fcntl.h>
#include <errno.h>
#include <pthread.h>
#include <time.h>
#include <stdatomic.h>
#include <dirent.h>
#include <fnmatch.h>
#include <sys/mman.h>
#include <immintrin.h>
#include <sched.h>
#include <numa.h>
#include <regex.h>
#include <ctype.h>
#include <math.h>
#include <json-c/json.h>
#include <limits.h>
#include <stdbool.h>
#include <stdint.h>
#include <sys/resource.h>
#include "agent_protocol.h"
#include "agent_system.h"

#define LINTER_VERSION "2.0.0-ULTIMATE"
#define MAX_WORKERS 64
#define MAX_FILES 10000
#define MAX_LINE_LENGTH 8192
#define MAX_RULES 2048
#define MAX_VIOLATIONS 100000
#define HASH_TABLE_SIZE 65536
#define CHUNK_SIZE 4096
#define MAX_LANGUAGES 32
#define MAX_PATTERNS 512
#define MAX_CONFIG_SIZE 1048576
#define CACHE_SIZE 4096
#define METRICS_BUFFER_SIZE 8192
#define MAX_AGENT_CONNECTIONS 32
#define RULE_PATTERN_SIZE 512
#define FILE_BUFFER_SIZE 65536
#define MAX_FILE_SIZE 10485760
#define QUALITY_SCORE_MAX 100
#define BATCH_SIZE 32

typedef enum {
    SEVERITY_CRITICAL = 0,
    SEVERITY_HIGH = 1,
    SEVERITY_MEDIUM = 2,
    SEVERITY_LOW = 3,
    SEVERITY_INFO = 4
} severity_level_t;

typedef enum {
    LANG_C = 0,
    LANG_CPP = 1,
    LANG_PYTHON = 2,
    LANG_JAVASCRIPT = 3,
    LANG_TYPESCRIPT = 4,
    LANG_RUST = 5,
    LANG_GO = 6,
    LANG_JAVA = 7,
    LANG_RUBY = 8,
    LANG_PHP = 9,
    LANG_SWIFT = 10,
    LANG_KOTLIN = 11,
    LANG_SCALA = 12,
    LANG_SHELL = 13,
    LANG_UNKNOWN = 99
} language_t;

typedef enum {
    RULE_SECURITY = 0,
    RULE_PERFORMANCE,
    RULE_STYLE,
    RULE_COMPLEXITY,
    RULE_DOCUMENTATION,
    RULE_DEPENDENCIES,
    RULE_MEMORY,
    RULE_CONCURRENCY,
    RULE_ERROR_HANDLING,
    RULE_BEST_PRACTICE
} rule_category_t;

typedef struct {
    uint32_t id;
    char name[128];
    char description[512];
    char pattern_str[RULE_PATTERN_SIZE];
    language_t language;
    rule_category_t category;
    severity_level_t severity;
    regex_t pattern;
    bool enabled;
    uint32_t hits;
    double weight;
    double avg_fix_time;
    void (*custom_checker)(const char*, void*);
} lint_rule_t;

typedef struct {
    uint32_t rule_id;
    char file_path[PATH_MAX];
    uint32_t line_number;
    uint32_t column;
    char snippet[256];
    char suggested_fix[512];
    severity_level_t severity;
    language_t language;
    double impact_score;
    time_t timestamp;
    bool fixed;
} violation_t;

typedef struct {
    char file_path[PATH_MAX];
    language_t language;
    uint32_t total_lines;
    uint32_t code_lines;
    uint32_t comment_lines;
    uint32_t blank_lines;
    uint32_t violations[5];
    double quality_score;
    double complexity_score;
    double maintainability_index;
    time_t last_analyzed;
    char checksum[65];
    bool cached;
} file_metrics_t;

typedef struct {
    language_t type;
    char name[32];
    char extensions[10][16];
    uint32_t extension_count;
    uint32_t rule_count;
    lint_rule_t* rules[MAX_RULES];
    void (*analyze_func)(const char*, violation_t*, uint32_t*);
    double avg_analysis_time;
    uint64_t files_analyzed;
} language_analyzer_t;

typedef struct {
    pthread_t thread_id;
    uint32_t worker_id;
    uint32_t cpu_affinity;
    atomic_uint tasks_completed;
    atomic_bool active;
    char current_file[PATH_MAX];
    language_t current_language;
    double total_time;
    pthread_mutex_t lock;
    void *local_buffer;
    size_t buffer_size;
} worker_context_t;

typedef struct task_item {
    char file_path[PATH_MAX];
    language_t language;
    uint32_t priority;
    time_t enqueue_time;
    struct task_item* next;
} task_item_t;

typedef struct {
    task_item_t* head;
    task_item_t* tail;
    atomic_uint size;
    pthread_mutex_t lock;
    pthread_cond_t not_empty;
    pthread_cond_t not_full;
    uint32_t max_size;
} task_queue_t;

typedef struct {
    atomic_uint total_files;
    atomic_uint total_violations;
    atomic_uint critical_violations;
    atomic_uint high_violations;
    atomic_uint medium_violations;
    atomic_uint low_violations;
    atomic_uint info_violations;
    atomic_ullong total_lines_analyzed;
    double avg_file_quality;
    double project_quality_score;
    time_t last_update;
    uint32_t violations_by_category[10];
    uint32_t violations_by_language[MAX_LANGUAGES];
} quality_metrics_t;

typedef struct {
    int agent_id;
    char agent_name[64];
    int msg_queue_id;
    bool connected;
    uint32_t messages_sent;
    uint32_t messages_received;
    time_t last_contact;
} agent_connection_t;

typedef struct {
    atomic_ullong files_processed;
    atomic_ullong bytes_analyzed;
    double total_analysis_time;
    double avg_file_time;
    uint32_t cache_hits;
    uint32_t cache_misses;
    double cpu_usage;
    uint64_t memory_usage;
} performance_stats_t;

typedef struct {
    char file_path[PATH_MAX];
    time_t last_modified;
    uint32_t violation_count;
    violation_t* violations;
    double quality_score;
    bool valid;
} cache_entry_t;

typedef struct {
    bool initialized;
    bool running;
    int shared_mem_id;
    int msg_queue_id;
    void* shared_mem_ptr;
    
    language_analyzer_t analyzers[MAX_LANGUAGES];
    uint32_t analyzer_count;
    
    lint_rule_t rules[MAX_RULES];
    uint32_t rule_count;
    
    worker_context_t workers[MAX_WORKERS];
    uint32_t worker_count;
    task_queue_t task_queue;
    
    violation_t violations[MAX_VIOLATIONS];
    atomic_uint violation_count;
    pthread_mutex_t violation_lock;
    
    quality_metrics_t metrics;
    performance_stats_t perf_stats;
    
    cache_entry_t cache[CACHE_SIZE];
    uint32_t cache_index;
    pthread_rwlock_t cache_lock;
    
    agent_connection_t agents[MAX_AGENT_CONNECTIONS];
    uint32_t agent_count;
    pthread_mutex_t agent_lock;
    
    char project_root[PATH_MAX];
    char config_file[PATH_MAX];
    bool real_time_mode;
    uint32_t batch_size;
    severity_level_t min_severity;
    
} linter_context_t;

static linter_context_t g_linter = {0};

static void init_language_analyzers(void);
static void init_rule_engine(void);
static void init_worker_pool(uint32_t num_workers);
static void* worker_thread_func(void* arg);
static void enqueue_task(const char* file_path, language_t lang, uint32_t priority);
static task_item_t* dequeue_task(void);
static language_t detect_language(const char* file_path);
static void analyze_c_file(const char* content, violation_t* violations, uint32_t* count);
static void analyze_python_file(const char* content, violation_t* violations, uint32_t* count);
static void analyze_javascript_file(const char* content, violation_t* violations, uint32_t* count);
static void analyze_rust_file(const char* content, violation_t* violations, uint32_t* count);
static void analyze_go_file(const char* content, violation_t* violations, uint32_t* count);
static void analyze_typescript_file(const char* content, violation_t* violations, uint32_t* count);
static void apply_rules(const char* content, language_t lang, violation_t* violations, uint32_t* count);
static double calculate_quality_score(uint32_t violations[], uint32_t count);
static double calculate_complexity(const char *content, language_t language);
static double calculate_maintainability_index(const char *content, language_t language);
static void update_metrics(const violation_t* violations, uint32_t count);
static void cache_results(const char* file_path, violation_t* violations, uint32_t count);
static bool check_cache(const char* file_path, violation_t** violations, uint32_t* count);
static void send_to_agent(int agent_id, const violation_t* violation);
static void broadcast_quality_update(double score);
static void handle_agent_message(enhanced_msg_header_t* msg);
static void cleanup_resources(void);
static void signal_handler(int sig);

static void init_language_analyzers(void) {
    language_analyzer_t* c_analyzer = &g_linter.analyzers[LANG_C];
    c_analyzer->type = LANG_C;
    strcpy(c_analyzer->name, "C/C++");
    strcpy(c_analyzer->extensions[0], ".c");
    strcpy(c_analyzer->extensions[1], ".h");
    strcpy(c_analyzer->extensions[2], ".cpp");
    strcpy(c_analyzer->extensions[3], ".hpp");
    strcpy(c_analyzer->extensions[4], ".cc");
    c_analyzer->extension_count = 5;
    c_analyzer->analyze_func = analyze_c_file;
    
    language_analyzer_t* py_analyzer = &g_linter.analyzers[LANG_PYTHON];
    py_analyzer->type = LANG_PYTHON;
    strcpy(py_analyzer->name, "Python");
    strcpy(py_analyzer->extensions[0], ".py");
    strcpy(py_analyzer->extensions[1], ".pyw");
    strcpy(py_analyzer->extensions[2], ".pyi");
    py_analyzer->extension_count = 3;
    py_analyzer->analyze_func = analyze_python_file;
    
    language_analyzer_t* js_analyzer = &g_linter.analyzers[LANG_JAVASCRIPT];
    js_analyzer->type = LANG_JAVASCRIPT;
    strcpy(js_analyzer->name, "JavaScript");
    strcpy(js_analyzer->extensions[0], ".js");
    strcpy(js_analyzer->extensions[1], ".jsx");
    strcpy(js_analyzer->extensions[2], ".mjs");
    js_analyzer->extension_count = 3;
    js_analyzer->analyze_func = analyze_javascript_file;
    
    language_analyzer_t* ts_analyzer = &g_linter.analyzers[LANG_TYPESCRIPT];
    ts_analyzer->type = LANG_TYPESCRIPT;
    strcpy(ts_analyzer->name, "TypeScript");
    strcpy(ts_analyzer->extensions[0], ".ts");
    strcpy(ts_analyzer->extensions[1], ".tsx");
    ts_analyzer->extension_count = 2;
    ts_analyzer->analyze_func = analyze_typescript_file;
    
    language_analyzer_t* rust_analyzer = &g_linter.analyzers[LANG_RUST];
    rust_analyzer->type = LANG_RUST;
    strcpy(rust_analyzer->name, "Rust");
    strcpy(rust_analyzer->extensions[0], ".rs");
    rust_analyzer->extension_count = 1;
    rust_analyzer->analyze_func = analyze_rust_file;
    
    language_analyzer_t* go_analyzer = &g_linter.analyzers[LANG_GO];
    go_analyzer->type = LANG_GO;
    strcpy(go_analyzer->name, "Go");
    strcpy(go_analyzer->extensions[0], ".go");
    go_analyzer->extension_count = 1;
    go_analyzer->analyze_func = analyze_go_file;
    
    g_linter.analyzer_count = 6;
    
    printf("[LINTER] Initialized %u language analyzers\n", g_linter.analyzer_count);
}

static void init_rule_engine(void) {
    uint32_t rule_id = 0;
    
    lint_rule_t* rule = &g_linter.rules[rule_id++];
    rule->id = rule_id;
    strcpy(rule->name, "unsafe_strcpy");
    strcpy(rule->description, "Use of unsafe strcpy function");
    rule->language = LANG_C;
    rule->category = RULE_SECURITY;
    rule->severity = SEVERITY_CRITICAL;
    strcpy(rule->pattern_str, "\\bstrcpy\\s*\\(");
    regcomp(&rule->pattern, rule->pattern_str, REG_EXTENDED);
    rule->enabled = true;
    rule->weight = 10.0;
    
    rule = &g_linter.rules[rule_id++];
    rule->id = rule_id;
    strcpy(rule->name, "unsafe_gets");
    strcpy(rule->description, "Use of unsafe gets function");
    rule->language = LANG_C;
    rule->category = RULE_SECURITY;
    rule->severity = SEVERITY_CRITICAL;
    strcpy(rule->pattern_str, "\\bgets\\s*\\(");
    regcomp(&rule->pattern, rule->pattern_str, REG_EXTENDED);
    rule->enabled = true;
    rule->weight = 10.0;
    
    rule = &g_linter.rules[rule_id++];
    rule->id = rule_id;
    strcpy(rule->name, "unsafe_sprintf");
    strcpy(rule->description, "Use of unsafe sprintf function");
    rule->language = LANG_C;
    rule->category = RULE_SECURITY;
    rule->severity = SEVERITY_HIGH;
    strcpy(rule->pattern_str, "\\bsprintf\\s*\\(");
    regcomp(&rule->pattern, rule->pattern_str, REG_EXTENDED);
    rule->enabled = true;
    rule->weight = 8.0;
    
    rule = &g_linter.rules[rule_id++];
    rule->id = rule_id;
    strcpy(rule->name, "buffer_overflow_risk");
    strcpy(rule->description, "Potential buffer overflow with strcat");
    rule->language = LANG_C;
    rule->category = RULE_SECURITY;
    rule->severity = SEVERITY_HIGH;
    strcpy(rule->pattern_str, "\\bstrcat\\s*\\(");
    regcomp(&rule->pattern, rule->pattern_str, REG_EXTENDED);
    rule->enabled = true;
    rule->weight = 8.0;
    
    rule = &g_linter.rules[rule_id++];
    rule->id = rule_id;
    strcpy(rule->name, "unchecked_malloc");
    strcpy(rule->description, "malloc without NULL check");
    rule->language = LANG_C;
    rule->category = RULE_MEMORY;
    rule->severity = SEVERITY_HIGH;
    strcpy(rule->pattern_str, "malloc\\s*\\([^)]*\\)\\s*;");
    regcomp(&rule->pattern, rule->pattern_str, REG_EXTENDED);
    rule->enabled = true;
    rule->weight = 7.0;
    
    rule = &g_linter.rules[rule_id++];
    rule->id = rule_id;
    strcpy(rule->name, "unsafe_eval");
    strcpy(rule->description, "Use of eval() function");
    rule->language = LANG_PYTHON;
    rule->category = RULE_SECURITY;
    rule->severity = SEVERITY_CRITICAL;
    strcpy(rule->pattern_str, "\\beval\\s*\\(");
    regcomp(&rule->pattern, rule->pattern_str, REG_EXTENDED);
    rule->enabled = true;
    rule->weight = 10.0;
    
    rule = &g_linter.rules[rule_id++];
    rule->id = rule_id;
    strcpy(rule->name, "unsafe_exec");
    strcpy(rule->description, "Use of exec() function");
    rule->language = LANG_PYTHON;
    rule->category = RULE_SECURITY;
    rule->severity = SEVERITY_CRITICAL;
    strcpy(rule->pattern_str, "\\bexec\\s*\\(");
    regcomp(&rule->pattern, rule->pattern_str, REG_EXTENDED);
    rule->enabled = true;
    rule->weight = 10.0;
    
    rule = &g_linter.rules[rule_id++];
    rule->id = rule_id;
    strcpy(rule->name, "hardcoded_password");
    strcpy(rule->description, "Hardcoded password detected");
    rule->language = LANG_PYTHON;
    rule->category = RULE_SECURITY;
    rule->severity = SEVERITY_HIGH;
    strcpy(rule->pattern_str, "password\\s*=\\s*[\"'][^\"']{3,}[\"']");
    regcomp(&rule->pattern, rule->pattern_str, REG_EXTENDED | REG_ICASE);
    rule->enabled = true;
    rule->weight = 9.0;
    
    rule = &g_linter.rules[rule_id++];
    rule->id = rule_id;
    strcpy(rule->name, "unsafe_innerhtml");
    strcpy(rule->description, "Direct innerHTML assignment (XSS risk)");
    rule->language = LANG_JAVASCRIPT;
    rule->category = RULE_SECURITY;
    rule->severity = SEVERITY_HIGH;
    strcpy(rule->pattern_str, "\\.innerHTML\\s*=");
    regcomp(&rule->pattern, rule->pattern_str, REG_EXTENDED);
    rule->enabled = true;
    rule->weight = 8.0;
    
    rule = &g_linter.rules[rule_id++];
    rule->id = rule_id;
    strcpy(rule->name, "unsafe_eval_js");
    strcpy(rule->description, "Use of eval() in JavaScript");
    rule->language = LANG_JAVASCRIPT;
    rule->category = RULE_SECURITY;
    rule->severity = SEVERITY_CRITICAL;
    strcpy(rule->pattern_str, "\\beval\\s*\\(");
    regcomp(&rule->pattern, rule->pattern_str, REG_EXTENDED);
    rule->enabled = true;
    rule->weight = 10.0;
    
    rule = &g_linter.rules[rule_id++];
    rule->id = rule_id;
    strcpy(rule->name, "unsafe_block");
    strcpy(rule->description, "Use of unsafe block");
    rule->language = LANG_RUST;
    rule->category = RULE_MEMORY;
    rule->severity = SEVERITY_MEDIUM;
    strcpy(rule->pattern_str, "\\bunsafe\\s*\\{");
    regcomp(&rule->pattern, rule->pattern_str, REG_EXTENDED);
    rule->enabled = true;
    rule->weight = 6.0;
    
    rule = &g_linter.rules[rule_id++];
    rule->id = rule_id;
    strcpy(rule->name, "unwrap_usage");
    strcpy(rule->description, "Direct unwrap() without error handling");
    rule->language = LANG_RUST;
    rule->category = RULE_ERROR_HANDLING;
    rule->severity = SEVERITY_MEDIUM;
    strcpy(rule->pattern_str, "\\.unwrap\\(\\)");
    regcomp(&rule->pattern, rule->pattern_str, REG_EXTENDED);
    rule->enabled = true;
    rule->weight = 6.0;
    
    rule = &g_linter.rules[rule_id++];
    rule->id = rule_id;
    strcpy(rule->name, "unhandled_error");
    strcpy(rule->description, "Error return value ignored");
    rule->language = LANG_GO;
    rule->category = RULE_ERROR_HANDLING;
    rule->severity = SEVERITY_HIGH;
    strcpy(rule->pattern_str, "_\\s*,\\s*:=.*\\berr\\b");
    regcomp(&rule->pattern, rule->pattern_str, REG_EXTENDED);
    rule->enabled = true;
    rule->weight = 7.0;
    
    rule = &g_linter.rules[rule_id++];
    rule->id = rule_id;
    strcpy(rule->name, "any_type");
    strcpy(rule->description, "Use of 'any' type");
    rule->language = LANG_TYPESCRIPT;
    rule->category = RULE_BEST_PRACTICE;
    rule->severity = SEVERITY_LOW;
    strcpy(rule->pattern_str, ":\\s*any\\b");
    regcomp(&rule->pattern, rule->pattern_str, REG_EXTENDED);
    rule->enabled = true;
    rule->weight = 3.0;
    
    rule = &g_linter.rules[rule_id++];
    rule->id = rule_id;
    strcpy(rule->name, "nested_loops");
    strcpy(rule->description, "Deeply nested loops detected");
    rule->language = LANG_C;
    rule->category = RULE_PERFORMANCE;
    rule->severity = SEVERITY_MEDIUM;
    strcpy(rule->pattern_str, "for\\s*\\([^)]*\\)\\s*\\{[^}]*for\\s*\\([^)]*\\)\\s*\\{[^}]*for\\s*\\(");
    regcomp(&rule->pattern, rule->pattern_str, REG_EXTENDED);
    rule->enabled = true;
    rule->weight = 5.0;
    
    rule = &g_linter.rules[rule_id++];
    rule->id = rule_id;
    strcpy(rule->name, "hardcoded_secrets");
    strcpy(rule->description, "Hardcoded API key or token");
    rule->language = LANG_UNKNOWN;
    rule->category = RULE_SECURITY;
    rule->severity = SEVERITY_CRITICAL;
    strcpy(rule->pattern_str, "(api_key|token|secret)\\s*=\\s*[\"'][^\"']{10,}[\"']");
    regcomp(&rule->pattern, rule->pattern_str, REG_EXTENDED | REG_ICASE);
    rule->enabled = true;
    rule->weight = 10.0;
    
    rule = &g_linter.rules[rule_id++];
    rule->id = rule_id;
    strcpy(rule->name, "debug_statements");
    strcpy(rule->description, "Debug/console statements in production");
    rule->language = LANG_JAVASCRIPT;
    rule->category = RULE_STYLE;
    rule->severity = SEVERITY_LOW;
    strcpy(rule->pattern_str, "console\\.(log|debug|info)\\s*\\(");
    regcomp(&rule->pattern, rule->pattern_str, REG_EXTENDED);
    rule->enabled = true;
    rule->weight = 2.0;
    
    rule = &g_linter.rules[rule_id++];
    rule->id = rule_id;
    strcpy(rule->name, "technical_debt");
    strcpy(rule->description, "Technical debt markers");
    rule->language = LANG_UNKNOWN;
    rule->category = RULE_DOCUMENTATION;
    rule->severity = SEVERITY_INFO;
    strcpy(rule->pattern_str, "(TODO|FIXME|HACK|XXX|BUG)");
    regcomp(&rule->pattern, rule->pattern_str, REG_EXTENDED | REG_ICASE);
    rule->enabled = true;
    rule->weight = 1.0;
    
    g_linter.rule_count = rule_id;
    printf("[LINTER] Loaded %u linting rules across %d categories\n", 
           g_linter.rule_count, RULE_BEST_PRACTICE + 1);
}

static void init_worker_pool(uint32_t num_workers) {
    if (num_workers > MAX_WORKERS) {
        num_workers = MAX_WORKERS;
    }
    
    g_linter.task_queue.max_size = 1024;
    pthread_mutex_init(&g_linter.task_queue.lock, NULL);
    pthread_cond_init(&g_linter.task_queue.not_empty, NULL);
    pthread_cond_init(&g_linter.task_queue.not_full, NULL);
    
    for (uint32_t i = 0; i < num_workers; i++) {
        worker_context_t* worker = &g_linter.workers[i];
        worker->worker_id = i;
        worker->cpu_affinity = i % sysconf(_SC_NPROCESSORS_ONLN);
        worker->active = true;
        worker->buffer_size = FILE_BUFFER_SIZE;
        worker->local_buffer = malloc(worker->buffer_size);
        pthread_mutex_init(&worker->lock, NULL);
        
        if (pthread_create(&worker->thread_id, NULL, worker_thread_func, worker) != 0) {
            fprintf(stderr, "[ERROR] Failed to create worker thread %u\n", i);
            continue;
        }
        
        cpu_set_t cpuset;
        CPU_ZERO(&cpuset);
        CPU_SET(worker->cpu_affinity, &cpuset);
        pthread_setaffinity_np(worker->thread_id, sizeof(cpu_set_t), &cpuset);
        
        g_linter.worker_count++;
    }
    
    printf("[LINTER] Created %u worker threads with CPU affinity\n", g_linter.worker_count);
}

static void* worker_thread_func(void* arg) {
    worker_context_t* worker = (worker_context_t*)arg;
    char thread_name[16];
    snprintf(thread_name, sizeof(thread_name), "lint_worker_%u", worker->worker_id);
    pthread_setname_np(pthread_self(), thread_name);
    
    while (worker->active) {
        task_item_t* task = dequeue_task();
        if (!task) {
            usleep(1000);
            continue;
        }
        
        struct timespec start, end;
        clock_gettime(CLOCK_MONOTONIC, &start);
        
        pthread_mutex_lock(&worker->lock);
        strcpy(worker->current_file, task->file_path);
        worker->current_language = task->language;
        pthread_mutex_unlock(&worker->lock);
        
        violation_t* cached_violations = NULL;
        uint32_t cached_count = 0;
        
        if (check_cache(task->file_path, &cached_violations, &cached_count)) {
            atomic_fetch_add(&g_linter.perf_stats.cache_hits, 1);
            update_metrics(cached_violations, cached_count);
        } else {
            atomic_fetch_add(&g_linter.perf_stats.cache_misses, 1);
            
            FILE* fp = fopen(task->file_path, "r");
            if (!fp) {
                free(task);
                continue;
            }
            
            fseek(fp, 0, SEEK_END);
            long file_size = ftell(fp);
            fseek(fp, 0, SEEK_SET);
            
            if (file_size > MAX_FILE_SIZE) {
                fclose(fp);
                free(task);
                continue;
            }
            
            char* content = malloc(file_size + 1);
            if (!content) {
                fclose(fp);
                free(task);
                continue;
            }
            
            fread(content, 1, file_size, fp);
            content[file_size] = '\0';
            fclose(fp);
            
            violation_t violations[1000];
            uint32_t violation_count = 0;
            
            if (task->language < g_linter.analyzer_count && 
                g_linter.analyzers[task->language].analyze_func) {
                g_linter.analyzers[task->language].analyze_func(content, violations, &violation_count);
            }
            
            apply_rules(content, task->language, violations, &violation_count);
            
            cache_results(task->file_path, violations, violation_count);
            update_metrics(violations, violation_count);
            
            for (uint32_t i = 0; i < violation_count; i++) {
                if (violations[i].severity == SEVERITY_CRITICAL) {
                    send_to_agent(AGENT_SECURITY, &violations[i]);
                }
            }
            
            atomic_fetch_add(&g_linter.perf_stats.bytes_analyzed, file_size);
            free(content);
        }
        
        clock_gettime(CLOCK_MONOTONIC, &end);
        double elapsed = (end.tv_sec - start.tv_sec) + (end.tv_nsec - start.tv_nsec) / 1e9;
        
        pthread_mutex_lock(&worker->lock);
        worker->total_time += elapsed;
        atomic_fetch_add(&worker->tasks_completed, 1);
        pthread_mutex_unlock(&worker->lock);
        
        atomic_fetch_add(&g_linter.perf_stats.files_processed, 1);
        
        free(task);
    }
    
    return NULL;
}

static void enqueue_task(const char* file_path, language_t lang, uint32_t priority) {
    pthread_mutex_lock(&g_linter.task_queue.lock);
    
    while (g_linter.task_queue.size >= g_linter.task_queue.max_size) {
        pthread_cond_wait(&g_linter.task_queue.not_full, &g_linter.task_queue.lock);
    }
    
    task_item_t* task = malloc(sizeof(task_item_t));
    strcpy(task->file_path, file_path);
    task->language = lang;
    task->priority = priority;
    task->enqueue_time = time(NULL);
    task->next = NULL;
    
    if (!g_linter.task_queue.head) {
        g_linter.task_queue.head = task;
        g_linter.task_queue.tail = task;
    } else {
        g_linter.task_queue.tail->next = task;
        g_linter.task_queue.tail = task;
    }
    
    atomic_fetch_add(&g_linter.task_queue.size, 1);
    pthread_cond_signal(&g_linter.task_queue.not_empty);
    pthread_mutex_unlock(&g_linter.task_queue.lock);
}

static task_item_t* dequeue_task(void) {
    pthread_mutex_lock(&g_linter.task_queue.lock);
    
    while (g_linter.task_queue.size == 0 && g_linter.running) {
        struct timespec ts;
        clock_gettime(CLOCK_REALTIME, &ts);
        ts.tv_sec += 1;
        pthread_cond_timedwait(&g_linter.task_queue.not_empty, 
                               &g_linter.task_queue.lock, &ts);
    }
    
    if (!g_linter.running) {
        pthread_mutex_unlock(&g_linter.task_queue.lock);
        return NULL;
    }
    
    task_item_t* task = g_linter.task_queue.head;
    if (task) {
        g_linter.task_queue.head = task->next;
        if (!g_linter.task_queue.head) {
            g_linter.task_queue.tail = NULL;
        }
        atomic_fetch_sub(&g_linter.task_queue.size, 1);
        pthread_cond_signal(&g_linter.task_queue.not_full);
    }
    
    pthread_mutex_unlock(&g_linter.task_queue.lock);
    return task;
}

static language_t detect_language(const char* file_path) {
    const char* ext = strrchr(file_path, '.');
    if (!ext) return LANG_UNKNOWN;
    
    for (uint32_t i = 0; i < g_linter.analyzer_count; i++) {
        language_analyzer_t* analyzer = &g_linter.analyzers[i];
        for (uint32_t j = 0; j < analyzer->extension_count; j++) {
            if (strcmp(ext, analyzer->extensions[j]) == 0) {
                return analyzer->type;
            }
        }
    }
    
    return LANG_UNKNOWN;
}

static void analyze_c_file(const char* content, violation_t* violations, uint32_t* count) {
    char* line_start = (char*)content;
    char* line_end;
    uint32_t line_num = 1;
    
    while ((line_end = strchr(line_start, '\n')) != NULL) {
        *line_end = '\0';
        
        if (strstr(line_start, "strcpy(")) {
            violations[(*count)].rule_id = 1;
            strcpy(violations[(*count)].file_path, "current_file");
            violations[(*count)].line_number = line_num;
            violations[(*count)].severity = SEVERITY_CRITICAL;
            strncpy(violations[(*count)].snippet, line_start, 255);
            strcpy(violations[(*count)].suggested_fix, "Use strncpy() or strlcpy() instead");
            violations[(*count)].impact_score = 10.0;
            violations[(*count)].timestamp = time(NULL);
            (*count)++;
        }
        
        if (strstr(line_start, "gets(")) {
            violations[(*count)].rule_id = 2;
            violations[(*count)].line_number = line_num;
            violations[(*count)].severity = SEVERITY_CRITICAL;
            strncpy(violations[(*count)].snippet, line_start, 255);
            strcpy(violations[(*count)].suggested_fix, "Use fgets() instead");
            violations[(*count)].impact_score = 10.0;
            (*count)++;
        }
        
        *line_end = '\n';
        line_start = line_end + 1;
        line_num++;
    }
}

static void analyze_python_file(const char* content, violation_t* violations, uint32_t* count) {
    char* line_start = (char*)content;
    char* line_end;
    uint32_t line_num = 1;
    
    while ((line_end = strchr(line_start, '\n')) != NULL) {
        *line_end = '\0';
        
        if (strstr(line_start, "eval(")) {
            violations[(*count)].rule_id = 6;
            violations[(*count)].line_number = line_num;
            violations[(*count)].severity = SEVERITY_CRITICAL;
            strncpy(violations[(*count)].snippet, line_start, 255);
            strcpy(violations[(*count)].suggested_fix, "Use ast.literal_eval() for safe evaluation");
            violations[(*count)].impact_score = 10.0;
            (*count)++;
        }
        
        if (strstr(line_start, "exec(")) {
            violations[(*count)].rule_id = 7;
            violations[(*count)].line_number = line_num;
            violations[(*count)].severity = SEVERITY_CRITICAL;
            strncpy(violations[(*count)].snippet, line_start, 255);
            strcpy(violations[(*count)].suggested_fix, "Avoid exec() or use restricted execution context");
            violations[(*count)].impact_score = 10.0;
            (*count)++;
        }
        
        *line_end = '\n';
        line_start = line_end + 1;
        line_num++;
    }
}

static void analyze_javascript_file(const char* content, violation_t* violations, uint32_t* count) {
    char* line_start = (char*)content;
    char* line_end;
    uint32_t line_num = 1;
    
    while ((line_end = strchr(line_start, '\n')) != NULL) {
        *line_end = '\0';
        
        if (strstr(line_start, ".innerHTML =")) {
            violations[(*count)].rule_id = 9;
            violations[(*count)].line_number = line_num;
            violations[(*count)].severity = SEVERITY_HIGH;
            strncpy(violations[(*count)].snippet, line_start, 255);
            strcpy(violations[(*count)].suggested_fix, "Use textContent or createElement() instead");
            violations[(*count)].impact_score = 8.0;
            (*count)++;
        }
        
        if (strstr(line_start, "eval(")) {
            violations[(*count)].rule_id = 10;
            violations[(*count)].line_number = line_num;
            violations[(*count)].severity = SEVERITY_CRITICAL;
            strncpy(violations[(*count)].snippet, line_start, 255);
            strcpy(violations[(*count)].suggested_fix, "Avoid eval() - use JSON.parse() for data");
            violations[(*count)].impact_score = 10.0;
            (*count)++;
        }
        
        *line_end = '\n';
        line_start = line_end + 1;
        line_num++;
    }
}

static void analyze_rust_file(const char* content, violation_t* violations, uint32_t* count) {
    char* line_start = (char*)content;
    char* line_end;
    uint32_t line_num = 1;
    
    while ((line_end = strchr(line_start, '\n')) != NULL) {
        *line_end = '\0';
        
        if (strstr(line_start, "unsafe {")) {
            violations[(*count)].rule_id = 11;
            violations[(*count)].line_number = line_num;
            violations[(*count)].severity = SEVERITY_MEDIUM;
            strncpy(violations[(*count)].snippet, line_start, 255);
            strcpy(violations[(*count)].suggested_fix, "Minimize unsafe blocks and document safety invariants");
            violations[(*count)].impact_score = 6.0;
            (*count)++;
        }
        
        if (strstr(line_start, ".unwrap()")) {
            violations[(*count)].rule_id = 12;
            violations[(*count)].line_number = line_num;
            violations[(*count)].severity = SEVERITY_MEDIUM;
            strncpy(violations[(*count)].snippet, line_start, 255);
            strcpy(violations[(*count)].suggested_fix, "Use ? operator or match for proper error handling");
            violations[(*count)].impact_score = 6.0;
            (*count)++;
        }
        
        *line_end = '\n';
        line_start = line_end + 1;
        line_num++;
    }
}

static void analyze_go_file(const char* content, violation_t* violations, uint32_t* count) {
    char* line_start = (char*)content;
    char* line_end;
    uint32_t line_num = 1;
    
    while ((line_end = strchr(line_start, '\n')) != NULL) {
        *line_end = '\0';
        
        if (strstr(line_start, "_, :=") && strstr(line_start, "err")) {
            violations[(*count)].rule_id = 13;
            violations[(*count)].line_number = line_num;
            violations[(*count)].severity = SEVERITY_HIGH;
            strncpy(violations[(*count)].snippet, line_start, 255);
            strcpy(violations[(*count)].suggested_fix, "Handle error return values properly");
            violations[(*count)].impact_score = 7.0;
            (*count)++;
        }
        
        *line_end = '\n';
        line_start = line_end + 1;
        line_num++;
    }
}

static void analyze_typescript_file(const char* content, violation_t* violations, uint32_t* count) {
    char* line_start = (char*)content;
    char* line_end;
    uint32_t line_num = 1;
    
    while ((line_end = strchr(line_start, '\n')) != NULL) {
        *line_end = '\0';
        
        if (strstr(line_start, ": any")) {
            violations[(*count)].rule_id = 14;
            violations[(*count)].line_number = line_num;
            violations[(*count)].severity = SEVERITY_LOW;
            strncpy(violations[(*count)].snippet, line_start, 255);
            strcpy(violations[(*count)].suggested_fix, "Use specific types instead of 'any'");
            violations[(*count)].impact_score = 3.0;
            (*count)++;
        }
        
        *line_end = '\n';
        line_start = line_end + 1;
        line_num++;
    }
}

static void apply_rules(const char* content, language_t lang, violation_t* violations, uint32_t* count) {
    for (uint32_t i = 0; i < g_linter.rule_count; i++) {
        lint_rule_t* rule = &g_linter.rules[i];
        
        if (!rule->enabled || (rule->language != lang && rule->language != LANG_UNKNOWN)) {
            continue;
        }
        
        regmatch_t matches[1];
        const char* cursor = content;
        uint32_t line_num = 1;
        
        while (regexec(&rule->pattern, cursor, 1, matches, 0) == 0) {
            for (int j = 0; j < matches[0].rm_so; j++) {
                if (cursor[j] == '\n') line_num++;
            }
            
            violations[*count].rule_id = rule->id;
            violations[*count].line_number = line_num;
            violations[*count].column = matches[0].rm_so;
            violations[*count].severity = rule->severity;
            violations[*count].impact_score = rule->weight;
            violations[*count].timestamp = time(NULL);
            
            int start = matches[0].rm_so - 20;
            if (start < 0) start = 0;
            int len = 60;
            strncpy(violations[*count].snippet, cursor + start, len);
            violations[*count].snippet[len] = '\0';
            
            strcpy(violations[*count].suggested_fix, "Apply rule-specific fix");
            
            (*count)++;
            rule->hits++;
            
            if (*count >= MAX_VIOLATIONS) {
                break;
            }
            
            cursor += matches[0].rm_eo;
        }
    }
}

static double calculate_quality_score(uint32_t violations[], uint32_t count) {
    double score = QUALITY_SCORE_MAX;
    
    for (uint32_t i = 0; i < count; i++) {
        switch (violations[i]) {
            case SEVERITY_CRITICAL:
                score -= 20.0;
                break;
            case SEVERITY_HIGH:
                score -= 10.0;
                break;
            case SEVERITY_MEDIUM:
                score -= 5.0;
                break;
            case SEVERITY_LOW:
                score -= 2.0;
                break;
            case SEVERITY_INFO:
                score -= 0.5;
                break;
        }
    }
    
    if (score < 0) score = 0;
    return score;
}

static double calculate_complexity(const char *content, language_t language) {
    double complexity = 1.0;
    const char *p = content;
    
    const char *complexity_patterns[] = {
        "if\\s*\\(", "else\\s*if", "while\\s*\\(", "for\\s*\\(",
        "switch\\s*\\(", "case\\s*", "&&", "\\|\\|", "\\?\\s*.*:",
        "catch\\s*\\(", "except\\s*:", "elif\\s*", "match\\s*"
    };
    
    int pattern_count = sizeof(complexity_patterns) / sizeof(complexity_patterns[0]);
    
    for (int i = 0; i < pattern_count; i++) {
        regex_t regex;
        if (regcomp(&regex, complexity_patterns[i], REG_EXTENDED) == 0) {
            regmatch_t matches[1];
            const char *cursor = content;
            
            while (regexec(&regex, cursor, 1, matches, 0) == 0) {
                complexity += 1.0;
                cursor += matches[0].rm_eo;
            }
            
            regfree(&regex);
        }
    }
    
    return complexity;
}

static double calculate_maintainability_index(const char *content, language_t language) {
    int total_lines = 0;
    int code_lines = 0;
    int comment_lines = 0;
    double avg_line_length = 0;
    
    const char *p = content;
    while (*p) {
        if (*p == '\n') {
            total_lines++;
        }
        p++;
    }
    
    if (total_lines == 0) total_lines = 1;
    
    p = content;
    char line[MAX_LINE_LENGTH];
    int line_start = 0;
    
    for (int i = 0; content[i]; i++) {
        if (content[i] == '\n') {
            int line_len = i - line_start;
            strncpy(line, content + line_start, line_len);
            line[line_len] = '\0';
            
            char *trimmed = line;
            while (*trimmed == ' ' || *trimmed == '\t') trimmed++;
            
            if (strlen(trimmed) > 0) {
                if (strstr(trimmed, "//") == trimmed || 
                    strstr(trimmed, "#") == trimmed ||
                    strstr(trimmed, "/*") == trimmed) {
                    comment_lines++;
                } else {
                    code_lines++;
                }
                avg_line_length += strlen(trimmed);
            }
            
            line_start = i + 1;
        }
    }
    
    if (code_lines > 0) {
        avg_line_length /= code_lines;
    }
    
    double comment_ratio = (double)comment_lines / total_lines;
    double complexity = calculate_complexity(content, language);
    
    double maintainability = 171 - 5.2 * log(complexity) - 
                           0.23 * complexity - 
                           16.2 * log(total_lines) +
                           50 * sin(sqrt(2.4 * comment_ratio));
    
    if (maintainability > 100) maintainability = 100;
    if (maintainability < 0) maintainability = 0;
    
    return maintainability;
}

static void update_metrics(const violation_t* violations, uint32_t count) {
    pthread_mutex_lock(&g_linter.violation_lock);
    
    for (uint32_t i = 0; i < count; i++) {
        switch (violations[i].severity) {
            case SEVERITY_CRITICAL:
                atomic_fetch_add(&g_linter.metrics.critical_violations, 1);
                break;
            case SEVERITY_HIGH:
                atomic_fetch_add(&g_linter.metrics.high_violations, 1);
                break;
            case SEVERITY_MEDIUM:
                atomic_fetch_add(&g_linter.metrics.medium_violations, 1);
                break;
            case SEVERITY_LOW:
                atomic_fetch_add(&g_linter.metrics.low_violations, 1);
                break;
            case SEVERITY_INFO:
                atomic_fetch_add(&g_linter.metrics.info_violations, 1);
                break;
        }
        
        for (uint32_t j = 0; j < g_linter.rule_count; j++) {
            if (g_linter.rules[j].id == violations[i].rule_id) {
                g_linter.metrics.violations_by_category[g_linter.rules[j].category]++;
                g_linter.metrics.violations_by_language[g_linter.rules[j].language]++;
                break;
            }
        }
    }
    
    atomic_fetch_add(&g_linter.metrics.total_violations, count);
    atomic_fetch_add(&g_linter.metrics.total_files, 1);
    g_linter.metrics.last_update = time(NULL);
    
    uint32_t total = atomic_load(&g_linter.metrics.total_violations);
    uint32_t files = atomic_load(&g_linter.metrics.total_files);
    if (files > 0) {
        g_linter.metrics.avg_file_quality = QUALITY_SCORE_MAX - (total / (double)files * 10);
        if (g_linter.metrics.avg_file_quality < 0) {
            g_linter.metrics.avg_file_quality = 0;
        }
    }
    
    pthread_mutex_unlock(&g_linter.violation_lock);
    
    static double last_broadcast_score = 0;
    if (fabs(g_linter.metrics.avg_file_quality - last_broadcast_score) > 5.0) {
        broadcast_quality_update(g_linter.metrics.avg_file_quality);
        last_broadcast_score = g_linter.metrics.avg_file_quality;
    }
}

static void cache_results(const char* file_path, violation_t* violations, uint32_t count) {
    pthread_rwlock_wrlock(&g_linter.cache_lock);
    
    uint32_t index = g_linter.cache_index % CACHE_SIZE;
    cache_entry_t* entry = &g_linter.cache[index];
    
    if (entry->violations) {
        free(entry->violations);
    }
    
    strcpy(entry->file_path, file_path);
    entry->last_modified = time(NULL);
    entry->violation_count = count;
    
    if (count > 0) {
        entry->violations = malloc(sizeof(violation_t) * count);
        memcpy(entry->violations, violations, sizeof(violation_t) * count);
    } else {
        entry->violations = NULL;
    }
    
    entry->quality_score = calculate_quality_score((uint32_t*)violations, count);
    entry->valid = true;
    
    g_linter.cache_index++;
    
    pthread_rwlock_unlock(&g_linter.cache_lock);
}

static bool check_cache(const char* file_path, violation_t** violations, uint32_t* count) {
    pthread_rwlock_rdlock(&g_linter.cache_lock);
    
    for (uint32_t i = 0; i < CACHE_SIZE; i++) {
        cache_entry_t* entry = &g_linter.cache[i];
        if (entry->valid && strcmp(entry->file_path, file_path) == 0) {
            if (time(NULL) - entry->last_modified < 300) {
                *count = entry->violation_count;
                if (entry->violation_count > 0) {
                    *violations = malloc(sizeof(violation_t) * entry->violation_count);
                    memcpy(*violations, entry->violations, 
                           sizeof(violation_t) * entry->violation_count);
                }
                pthread_rwlock_unlock(&g_linter.cache_lock);
                return true;
            }
        }
    }
    
    pthread_rwlock_unlock(&g_linter.cache_lock);
    return false;
}

static void send_to_agent(int agent_id, const violation_t* violation) {
    pthread_mutex_lock(&g_linter.agent_lock);
    
    for (uint32_t i = 0; i < g_linter.agent_count; i++) {
        if (g_linter.agents[i].agent_id == agent_id && g_linter.agents[i].connected) {
            enhanced_msg_header_t msg = {0};
            msg.msg_type = MSG_TYPE_DATA;
            msg.agent_id = AGENT_LINTER;
            msg.priority = violation->severity == SEVERITY_CRITICAL ? 10 : 5;
            msg.timestamp = time(NULL);
            msg.data_size = sizeof(violation_t);
            
            memcpy(msg.data, violation, sizeof(violation_t));
            
            if (msgsnd(g_linter.agents[i].msg_queue_id, &msg, 
                      sizeof(enhanced_msg_header_t) - sizeof(long), IPC_NOWAIT) == 0) {
                g_linter.agents[i].messages_sent++;
                g_linter.agents[i].last_contact = time(NULL);
            }
            
            break;
        }
    }
    
    pthread_mutex_unlock(&g_linter.agent_lock);
}

static void broadcast_quality_update(double score) {
    pthread_mutex_lock(&g_linter.agent_lock);
    
    enhanced_msg_header_t msg = {0};
    msg.msg_type = MSG_TYPE_QUALITY_UPDATE;
    msg.agent_id = AGENT_LINTER;
    msg.priority = 5;
    msg.timestamp = time(NULL);
    msg.data_size = sizeof(double);
    memcpy(msg.data, &score, sizeof(double));
    
    for (uint32_t i = 0; i < g_linter.agent_count; i++) {
        if (g_linter.agents[i].connected) {
            msgsnd(g_linter.agents[i].msg_queue_id, &msg, 
                   sizeof(enhanced_msg_header_t) - sizeof(long), IPC_NOWAIT);
            g_linter.agents[i].messages_sent++;
        }
    }
    
    pthread_mutex_unlock(&g_linter.agent_lock);
}

static void handle_agent_message(enhanced_msg_header_t* msg) {
    switch (msg->msg_type) {
        case MSG_TYPE_COMMAND:
            if (strcmp(msg->data, "START_ANALYSIS") == 0) {
                g_linter.running = true;
                printf("[LINTER] Starting analysis\n");
            } else if (strcmp(msg->data, "STOP_ANALYSIS") == 0) {
                g_linter.running = false;
                printf("[LINTER] Stopping analysis\n");
            } else if (strcmp(msg->data, "GET_METRICS") == 0) {
                enhanced_msg_header_t response = {0};
                response.msg_type = MSG_TYPE_DATA;
                response.agent_id = AGENT_LINTER;
                response.data_size = sizeof(quality_metrics_t);
                memcpy(response.data, &g_linter.metrics, sizeof(quality_metrics_t));
                msgsnd(g_linter.msg_queue_id, &response, 
                       sizeof(enhanced_msg_header_t) - sizeof(long), IPC_NOWAIT);
            }
            break;
            
        case MSG_TYPE_CONFIG:
            printf("[LINTER] Configuration update received\n");
            break;
            
        case MSG_TYPE_FILE_PATH:
            language_t lang = detect_language(msg->data);
            if (lang != LANG_UNKNOWN) {
                enqueue_task(msg->data, lang, msg->priority);
                printf("[LINTER] Queued file: %s\n", msg->data);
            }
            break;
    }
}

static void cleanup_resources(void) {
    printf("[LINTER] Cleaning up resources...\n");
    
    g_linter.running = false;
    
    for (uint32_t i = 0; i < g_linter.worker_count; i++) {
        g_linter.workers[i].active = false;
        pthread_join(g_linter.workers[i].thread_id, NULL);
        pthread_mutex_destroy(&g_linter.workers[i].lock);
        if (g_linter.workers[i].local_buffer) {
            free(g_linter.workers[i].local_buffer);
        }
    }
    
    task_item_t* task = g_linter.task_queue.head;
    while (task) {
        task_item_t* next = task->next;
        free(task);
        task = next;
    }
    
    pthread_rwlock_wrlock(&g_linter.cache_lock);
    for (uint32_t i = 0; i < CACHE_SIZE; i++) {
        if (g_linter.cache[i].violations) {
            free(g_linter.cache[i].violations);
        }
    }
    pthread_rwlock_unlock(&g_linter.cache_lock);
    
    for (uint32_t i = 0; i < g_linter.rule_count; i++) {
        regfree(&g_linter.rules[i].pattern);
    }
    
    pthread_mutex_destroy(&g_linter.task_queue.lock);
    pthread_cond_destroy(&g_linter.task_queue.not_empty);
    pthread_cond_destroy(&g_linter.task_queue.not_full);
    pthread_mutex_destroy(&g_linter.violation_lock);
    pthread_mutex_destroy(&g_linter.agent_lock);
    pthread_rwlock_destroy(&g_linter.cache_lock);
    
    if (g_linter.shared_mem_ptr) {
        shmdt(g_linter.shared_mem_ptr);
    }
    
    printf("[LINTER] Cleanup complete\n");
}

static void signal_handler(int sig) {
    printf("\n[LINTER] Received signal %d\n", sig);
    cleanup_resources();
    exit(0);
}

int main(int argc, char* argv[]) {
    printf("================================================================\n");
    printf("     Enhanced Linter Agent v2.0-ULTIMATE                      \n");
    printf("     Multi-Language Support & Advanced Rule Engine            \n");
    printf("     Intel Meteor Lake Optimized & Agent Coordination         \n");
    printf("================================================================\n");
    
    signal(SIGINT, signal_handler);
    signal(SIGTERM, signal_handler);
    
    g_linter.initialized = false;
    g_linter.running = true;
    g_linter.min_severity = SEVERITY_LOW;
    g_linter.batch_size = BATCH_SIZE;
    g_linter.real_time_mode = true;
    
    if (argc > 1) {
        strcpy(g_linter.project_root, argv[1]);
    } else {
        char* env_root = getenv("PROJECT_ROOT");
        if (env_root) {
            strcpy(g_linter.project_root, env_root);
        } else {
            getcwd(g_linter.project_root, PATH_MAX);
        }
    }
    
    printf("[LINTER] Project root: %s\n", g_linter.project_root);
    
    init_language_analyzers();
    init_rule_engine();
    init_worker_pool(8);
    
    key_t shm_key = ftok("/tmp", 'L');
    g_linter.shared_mem_id = shmget(shm_key, sizeof(shared_memory_t), 
                                     IPC_CREAT | 0666);
    if (g_linter.shared_mem_id < 0) {
        perror("[ERROR] Failed to create shared memory");
        return 1;
    }
    
    g_linter.shared_mem_ptr = shmat(g_linter.shared_mem_id, NULL, 0);
    if (g_linter.shared_mem_ptr == (void*)-1) {
        perror("[ERROR] Failed to attach shared memory");
        return 1;
    }
    
    key_t msg_key = ftok("/tmp", 'M');
    g_linter.msg_queue_id = msgget(msg_key, IPC_CREAT | 0666);
    if (g_linter.msg_queue_id < 0) {
        perror("[ERROR] Failed to create message queue");
        return 1;
    }
    
    pthread_mutex_init(&g_linter.violation_lock, NULL);
    pthread_mutex_init(&g_linter.agent_lock, NULL);
    pthread_rwlock_init(&g_linter.cache_lock, NULL);
    
    agent_connection_t* security_agent = &g_linter.agents[g_linter.agent_count++];
    security_agent->agent_id = AGENT_SECURITY;
    strcpy(security_agent->agent_name, "Security");
    security_agent->msg_queue_id = g_linter.msg_queue_id;
    security_agent->connected = true;
    
    agent_connection_t* director_agent = &g_linter.agents[g_linter.agent_count++];
    director_agent->agent_id = AGENT_DIRECTOR;
    strcpy(director_agent->agent_name, "Director");
    director_agent->msg_queue_id = g_linter.msg_queue_id;
    director_agent->connected = true;
    
    g_linter.initialized = true;
    
    printf("[LINTER] Initialization complete\n");
    printf("[LINTER] Workers: %u | Rules: %u | Languages: %u\n",
           g_linter.worker_count, g_linter.rule_count, g_linter.analyzer_count);
    printf("[LINTER] Cache size: %d | Max violations: %d\n", CACHE_SIZE, MAX_VIOLATIONS);
    printf("[LINTER] Waiting for analysis requests...\n");
    
    while (g_linter.running) {
        enhanced_msg_header_t msg;
        if (msgrcv(g_linter.msg_queue_id, &msg, 
                   sizeof(enhanced_msg_header_t) - sizeof(long), 
                   AGENT_LINTER, IPC_NOWAIT) > 0) {
            handle_agent_message(&msg);
        }
        
        static time_t last_status = 0;
        if (time(NULL) - last_status > 10) {
            printf("[LINTER] Status - Files: %llu | Violations: %u | Queue: %u | Quality: %.1f%% | Cache: %u/%u\n",
                   (unsigned long long)atomic_load(&g_linter.perf_stats.files_processed),
                   atomic_load(&g_linter.metrics.total_violations),
                   atomic_load(&g_linter.task_queue.size),
                   g_linter.metrics.avg_file_quality,
                   g_linter.perf_stats.cache_hits,
                   g_linter.perf_stats.cache_hits + g_linter.perf_stats.cache_misses);
            last_status = time(NULL);
        }
        
        usleep(10000);
    }
    
    cleanup_resources();
    return 0;
}