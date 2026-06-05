#pragma GCC diagnostic ignored "-Wunused-parameter"
#pragma GCC diagnostic ignored "-Wunused-function"
#include <errno.h>
#include <ctype.h>
#include <limits.h>
#include <netdb.h>
#include <poll.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <signal.h>
#include <sys/file.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

#define HG_EDGE_VERSION "0.2.0"
#define HG_EDGE_DEFAULT_LISTEN "127.0.0.1:18080"
#define HG_EDGE_DEFAULT_UPSTREAM "127.0.0.1:8000"
#define HG_EDGE_DEFAULT_EVENT_LOG "logs/microproxy_events.jsonl"
#define HG_EDGE_EVENT_LOG_ENV "HG_EDGE_EVENT_LOG"
#define HG_EDGE_MAX_ENDPOINT 256
#define HG_EDGE_BUFFER_SIZE 16384
#define HG_EDGE_DEFAULT_IDLE_TIMEOUT_SECONDS 30
#define HG_EDGE_DEFAULT_MAX_STREAM_SECONDS 300
#define HG_EDGE_DEFAULT_MAX_ACTIVE_STREAMS 64
#define HG_EDGE_DIRECT_FAILURE_THRESHOLD 2
#define HG_EDGE_DIRECT_COOLDOWN_SECONDS 3
#define HG_EDGE_MAX_METHOD 16
#define HG_EDGE_MAX_PATH 512
#define HG_EDGE_MAX_HOST 256
#define HG_EDGE_MAX_CONTENT_TYPE 128
#define HG_EDGE_LARGE_EDIT_BYTES 262144ULL

/* Antigravity observe-only edge: no response fabrication or credential/header injection logic is compiled. */

typedef struct {
    char host[HG_EDGE_MAX_ENDPOINT];
    unsigned int port;
} endpoint_t;

typedef struct {
    const char *listen_raw;
    const char *upstream_raw;
    const char *direct_upstream_raw;
    const char *event_log_path;
    unsigned int idle_timeout_seconds;
    unsigned int max_stream_seconds;
    unsigned int max_active_streams;
    bool listen_set;
    bool upstream_set;
    bool direct_upstream_set;
    bool check_config;
    bool print_flow;
    bool relay;
    bool hot_path_observe;
    bool direct_hot_path;
} edge_config_t;

typedef struct {
    unsigned long long bytes_in;
    unsigned long long bytes_out;
    bool upstream_connect_error_signal;
    bool upstream_quota_exhausted_signal;
} relay_stats_t;

typedef struct {
    char method[HG_EDGE_MAX_METHOD];
    char path[HG_EDGE_MAX_PATH];
    char host[HG_EDGE_MAX_HOST];
    char content_type[HG_EDGE_MAX_CONTENT_TYPE];
    unsigned long long content_length;
    bool has_content_length;
} http_request_t;

typedef struct {
    const char *classification;
    const char *route;
    const char *candidate;
    const char *reason;
    char path[HG_EDGE_MAX_PATH];
    char content_type[HG_EDGE_MAX_CONTENT_TYPE];
    bool hot_path_candidate;
    const char *fallback_state;
    bool direct_cooldown_active;
    unsigned int direct_failure_count;
    unsigned long long direct_cooldown_remaining_ms;
} route_decision_t;

typedef struct {
    unsigned int failure_count;
    unsigned long long cooldown_until_ms;
} direct_upstream_health_t;

static volatile sig_atomic_t g_stop_requested = 0;
static unsigned long long g_next_stream_id = 1;

static void handle_stop_signal(int signal_number) {
    (void)signal_number;
    g_stop_requested = 1;
}

static void print_usage(FILE *stream, const char *program) {
    fprintf(stream,
            "Usage: %s [--listen HOST:PORT] [--upstream HOST:PORT] "
            "[--check-config] [--print-flow]\n"
            "       %s --relay --listen HOST:PORT --upstream HOST:PORT "
            "[--direct-upstream HOST:PORT] [--direct-hot-path] "
            "[--idle-timeout SECONDS] [--max-stream-seconds SECONDS] "
            "[--max-active-streams COUNT] [--event-log PATH] "
            "[--hot-path-observe]\n\n"
            "hg-edge prototype for the planned flow:\n"
            "  Antigravity CLI/client -> C microproxy series -> Python TLS observer\n\n"
            "Passive defaults, used only when --relay is not set:\n"
            "  --listen   %s\n"
            "  --upstream %s\n\n"
            "Relay mode opens sockets only when --relay is set. Relay mode requires\n"
            "explicit --listen and --upstream values and never defaults to port 443.\n",
            program,
            program,
            HG_EDGE_DEFAULT_LISTEN,
            HG_EDGE_DEFAULT_UPSTREAM);
}

static bool parse_port(const char *raw, unsigned int *port_out) {
    unsigned long port = 0;

    if (raw == NULL || *raw == '\0') {
        return false;
    }
    for (const char *cursor = raw; *cursor != '\0'; cursor++) {
        unsigned int digit;
        if (!isdigit((unsigned char)*cursor)) {
            return false;
        }
        digit = (unsigned int)(*cursor - '0');
        if (port > (65535UL - digit) / 10UL) {
            return false;
        }
        port = (port * 10UL) + digit;
    }
    if (port < 1UL || port > 65535UL) {
        return false;
    }
    *port_out = (unsigned int)port;
    return true;
}

static bool parse_timeout(const char *raw, unsigned int *seconds_out) {
    unsigned long value = 0;

    if (raw == NULL || *raw == '\0') {
        return false;
    }
    for (const char *cursor = raw; *cursor != '\0'; cursor++) {
        unsigned int digit;
        if (!isdigit((unsigned char)*cursor)) {
            return false;
        }
        digit = (unsigned int)(*cursor - '0');
        if (value > (86400UL - digit) / 10UL) {
            return false;
        }
        value = (value * 10UL) + digit;
    }
    if (value < 1UL || value > 86400UL) {
        return false;
    }
    *seconds_out = (unsigned int)value;
    return true;
}

static bool parse_endpoint(const char *raw, endpoint_t *endpoint, char *error, size_t error_size) {
    const char *colon;
    size_t host_len;

    if (raw == NULL || *raw == '\0') {
        snprintf(error, error_size, "endpoint is empty");
        return false;
    }

    colon = strrchr(raw, ':');
    if (colon == NULL) {
        snprintf(error, error_size, "endpoint '%s' is missing ':PORT'", raw);
        return false;
    }

    host_len = (size_t)(colon - raw);
    if (host_len == 0) {
        snprintf(error, error_size, "endpoint '%s' is missing host", raw);
        return false;
    }
    if (host_len >= sizeof(endpoint->host)) {
        snprintf(error, error_size, "endpoint host is too long");
        return false;
    }

    memcpy(endpoint->host, raw, host_len);
    endpoint->host[host_len] = '\0';

    if (!parse_port(colon + 1, &endpoint->port)) {
        snprintf(error, error_size, "endpoint '%s' has invalid port", raw);
        return false;
    }

    return true;
}

static bool validate_config(const edge_config_t *config,
                            endpoint_t *listen,
                            endpoint_t *upstream,
                            endpoint_t *direct_upstream) {
    char error[160];

    if (config->relay) {
        if (!config->listen_set || !config->upstream_set) {
            fprintf(stderr, "hg-edge: --relay requires explicit --listen and --upstream\n");
            return false;
        }
    }

    if (!parse_endpoint(config->listen_raw, listen, error, sizeof(error))) {
        fprintf(stderr, "hg-edge: invalid --listen: %s\n", error);
        return false;
    }

    if (!parse_endpoint(config->upstream_raw, upstream, error, sizeof(error))) {
        fprintf(stderr, "hg-edge: invalid --upstream: %s\n", error);
        return false;
    }

    if (config->direct_upstream_set &&
        !parse_endpoint(config->direct_upstream_raw, direct_upstream, error, sizeof(error))) {
        fprintf(stderr, "hg-edge: invalid --direct-upstream: %s\n", error);
        return false;
    }

    return true;
}

static void print_flow(const edge_config_t *config, const endpoint_t *listen, const endpoint_t *upstream) {
    printf("hg-edge %s configuration OK\n", HG_EDGE_VERSION);
    printf("flow: Antigravity client -> hg-edge(%s:%u) -> Python TLS observer(%s:%u)\n",
           listen->host,
           listen->port,
           upstream->host,
           upstream->port);
    if (config->relay) {
        printf("mode: relay prototype; raw TCP bytes are forwarded without TLS parsing\n");
        printf("idle-timeout: %u seconds\n", config->idle_timeout_seconds);
        printf("max-stream-seconds: %u seconds\n", config->max_stream_seconds);
        printf("max-active-streams: %u\n", config->max_active_streams);
        printf("event-log: %s\n", config->event_log_path);
        printf("hot-path-observe: %s\n", config->hot_path_observe ? "enabled" : "disabled");
        if (config->direct_upstream_set) {
            printf("direct-upstream: %s\n", config->direct_upstream_raw);
            printf("direct-hot-path: %s\n", config->direct_hot_path ? "enabled" : "disabled");
        }
    } else {
        printf("max-active-streams: %u\n", config->max_active_streams);
        printf("mode: passive skeleton; no sockets are opened and no traffic is forwarded\n");
    }
}

static bool read_value_arg(int argc, char **argv, int *index, const char **value_out) {
    if (*index + 1 >= argc) {
        return false;
    }

    *index += 1;
    *value_out = argv[*index];
    return true;
}

static void utc_timestamp(char *buffer, size_t buffer_size) {
    struct timespec ts;
    struct tm utc;

    if (clock_gettime(CLOCK_REALTIME, &ts) != 0) {
        ts.tv_sec = time(NULL);
        ts.tv_nsec = 0;
    }

    gmtime_r(&ts.tv_sec, &utc);
    snprintf(buffer,
             buffer_size,
             "%04d-%02d-%02dT%02d:%02d:%02d.%03ldZ",
             utc.tm_year + 1900,
             utc.tm_mon + 1,
             utc.tm_mday,
             utc.tm_hour,
             utc.tm_min,
             utc.tm_sec,
             ts.tv_nsec / 1000000L);
}

static unsigned long long monotonic_ms(void) {
    struct timespec ts;

    if (clock_gettime(CLOCK_MONOTONIC, &ts) != 0) {
        return 0;
    }

    return ((unsigned long long)ts.tv_sec * 1000ULL) + ((unsigned long long)ts.tv_nsec / 1000000ULL);
}

static void sleep_ms(unsigned int delay_ms) {
    struct timespec requested;

    requested.tv_sec = (time_t)(delay_ms / 1000U);
    requested.tv_nsec = (long)(delay_ms % 1000U) * 1000000L;
    while (nanosleep(&requested, &requested) != 0 && errno == EINTR) {
    }
}

static void direct_upstream_health_reset(direct_upstream_health_t *health) {
    health->failure_count = 0;
    health->cooldown_until_ms = 0;
}

static unsigned long long direct_upstream_health_cooldown_remaining_ms(const direct_upstream_health_t *health,
                                                                       unsigned long long now_ms) {
    if (health->cooldown_until_ms <= now_ms) {
        return 0;
    }

    return health->cooldown_until_ms - now_ms;
}

static bool direct_upstream_health_in_cooldown(const direct_upstream_health_t *health,
                                               unsigned long long now_ms) {
    return health->cooldown_until_ms != 0 && now_ms < health->cooldown_until_ms;
}

static void direct_upstream_health_record_success(direct_upstream_health_t *health) {
    direct_upstream_health_reset(health);
}

static void direct_upstream_health_record_failure(direct_upstream_health_t *health,
                                                  unsigned long long now_ms) {
    if (health->failure_count < UINT_MAX) {
        health->failure_count++;
    }
    if (health->failure_count >= HG_EDGE_DIRECT_FAILURE_THRESHOLD) {
        health->failure_count = HG_EDGE_DIRECT_FAILURE_THRESHOLD;
        health->cooldown_until_ms = now_ms + ((unsigned long long)HG_EDGE_DIRECT_COOLDOWN_SECONDS * 1000ULL);
    }
}

static void direct_upstream_health_snapshot(const direct_upstream_health_t *health,
                                            unsigned long long now_ms,
                                            route_decision_t *decision,
                                            const char *fallback_state) {
    decision->fallback_state = fallback_state;
    decision->direct_failure_count = health->failure_count;
    decision->direct_cooldown_active = direct_upstream_health_in_cooldown(health, now_ms);
    decision->direct_cooldown_remaining_ms =
        direct_upstream_health_cooldown_remaining_ms(health, now_ms);
}

static void ensure_event_log_parent(const char *path) {
    char parent[4096];
    char *slash;
    size_t length;

    if (path == NULL) {
        return;
    }

    slash = strrchr(path, '/');
    if (slash == NULL || slash == path) {
        return;
    }

    length = (size_t)(slash - path);
    if (length >= sizeof(parent)) {
        return;
    }

    memcpy(parent, path, length);
    parent[length] = '\0';
    if (mkdir(parent, 0775) != 0 && errno != EEXIST) {
        fprintf(stderr, "hg-edge: cannot create event log directory %s: %s\n", parent, strerror(errno));
    }
}

static void write_json_string(FILE *file, const char *value) {
    fputc('"', file);
    for (const unsigned char *cursor = (const unsigned char *)value; *cursor != '\0'; cursor++) {
        switch (*cursor) {
            case '"':
                fputs("\\\"", file);
                break;
            case '\\':
                fputs("\\\\", file);
                break;
            case '\b':
                fputs("\\b", file);
                break;
            case '\f':
                fputs("\\f", file);
                break;
            case '\n':
                fputs("\\n", file);
                break;
            case '\r':
                fputs("\\r", file);
                break;
            case '\t':
                fputs("\\t", file);
                break;
            default:
                if (*cursor < 0x20) {
                    fprintf(file, "\\u%04x", *cursor);
                } else {
                    fputc(*cursor, file);
                }
                break;
        }
    }
    fputc('"', file);
}

static void append_event(const char *path,
                         const char *event,
                         unsigned long long stream_id,
                         const endpoint_t *listen,
                         const endpoint_t *upstream,
                         unsigned long long bytes_in,
                         unsigned long long bytes_out,
                         unsigned long long duration_ms,
                         const relay_stats_t *stats,
                         const direct_upstream_health_t *direct_health,
                         unsigned long long direct_health_sample_ms,
                         const char *fallback_state) {
    FILE *file;
    char ts[64];
    char request_id[32];
    char stream_id_text[32];
    char connection_id[32];
    char listen_text[HG_EDGE_MAX_ENDPOINT + 16];
    char upstream_text[HG_EDGE_MAX_ENDPOINT + 16];

    ensure_event_log_parent(path);
    file = fopen(path, "a");
    if (file == NULL) {
        fprintf(stderr, "hg-edge: cannot append event log %s: %s\n", path, strerror(errno));
        return;
    }
    if (flock(fileno(file), LOCK_EX) != 0) {
        fprintf(stderr, "hg-edge: cannot lock event log %s: %s\n", path, strerror(errno));
        fclose(file);
        return;
    }

    utc_timestamp(ts, sizeof(ts));
    snprintf(request_id, sizeof(request_id), "req-%llu", stream_id);
    snprintf(stream_id_text, sizeof(stream_id_text), "stream-%llu", stream_id);
    snprintf(connection_id, sizeof(connection_id), "conn-%llu", stream_id);
    snprintf(listen_text, sizeof(listen_text), "%s:%u", listen->host, listen->port);
    snprintf(upstream_text, sizeof(upstream_text), "%s:%u", upstream->host, upstream->port);

    fputs("{\"details\":{", file);
    if (strcmp(event, "stream_started") == 0) {
        fputs("\"stream_id\":", file);
        write_json_string(file, stream_id_text);
    } else if (strcmp(event, "stream_finished") == 0) {
        fputs("\"stream_id\":", file);
        write_json_string(file, stream_id_text);
        fprintf(file,
                ",\"status_code\":0,\"bytes_in\":%llu,\"bytes_out\":%llu,\"duration_ms\":%llu",
                bytes_in,
                bytes_out,
                duration_ms);
        if (stats != NULL) {
            fputs(",\"connect_error_signal\":", file);
            fputs(stats->upstream_connect_error_signal ? "true" : "false", file);
            fputs(",\"quota_exhausted_signal\":", file);
            fputs(stats->upstream_quota_exhausted_signal ? "true" : "false", file);
        }
    } else if (strcmp(event, "upstream_error") == 0) {
        fputs("\"upstream\":", file);
        write_json_string(file, upstream_text);
        fputs(",\"error_type\":\"connect_failed\",\"message\":\"could not connect upstream\"", file);
        if (direct_health != NULL) {
            fprintf(file, ",\"direct_failure_count\":%u", direct_health->failure_count);
            fputs(",\"direct_cooldown_active\":", file);
            fputs(direct_upstream_health_in_cooldown(direct_health, direct_health_sample_ms) ? "true" : "false", file);
            fprintf(file,
                    ",\"direct_cooldown_remaining_ms\":%llu",
                    direct_upstream_health_cooldown_remaining_ms(direct_health, direct_health_sample_ms));
            fputs(",\"fallback_state\":", file);
            write_json_string(file, fallback_state != NULL ? fallback_state : "none");
        }
    }
    fputs("},\"event\":", file);
    write_json_string(file, event);
    fputs(",\"request_id\":", file);
    write_json_string(file, request_id);
    fputs(",\"schema_version\":1,\"service\":\"microproxy\",\"connection_id\":", file);
    write_json_string(file, connection_id);
    fputs(",\"stream_id\":", file);
    write_json_string(file, stream_id_text);
    fputs(",\"ts\":", file);
    write_json_string(file, ts);
    fprintf(file, ",\"pid\":%ld,\"listen\":", (long)getpid());
    write_json_string(file, listen_text);
    fputs(",\"upstream\":", file);
    write_json_string(file, upstream_text);
    fputs("}\n", file);

    if (fclose(file) != 0) {
        fprintf(stderr, "hg-edge: cannot close event log %s: %s\n", path, strerror(errno));
    }
}

static void append_backpressure_event(const char *path,
                                      const endpoint_t *listen,
                                      const endpoint_t *upstream,
                                      unsigned int active_streams,
                                      unsigned int max_active_streams,
                                      unsigned long long wait_ms) {
    FILE *file;
    char ts[64];
    char request_id[32];
    char connection_id[32];
    char listen_text[HG_EDGE_MAX_ENDPOINT + 16];
    char upstream_text[HG_EDGE_MAX_ENDPOINT + 16];
    unsigned long long event_id = g_next_stream_id;

    ensure_event_log_parent(path);
    file = fopen(path, "a");
    if (file == NULL) {
        fprintf(stderr, "hg-edge: cannot append event log %s: %s\n", path, strerror(errno));
        return;
    }
    if (flock(fileno(file), LOCK_EX) != 0) {
        fprintf(stderr, "hg-edge: cannot lock event log %s: %s\n", path, strerror(errno));
        fclose(file);
        return;
    }

    utc_timestamp(ts, sizeof(ts));
    snprintf(request_id, sizeof(request_id), "req-%llu", event_id);
    snprintf(connection_id, sizeof(connection_id), "conn-%llu", event_id);
    snprintf(listen_text, sizeof(listen_text), "%s:%u", listen->host, listen->port);
    snprintf(upstream_text, sizeof(upstream_text), "%s:%u", upstream->host, upstream->port);

    fprintf(file,
            "{\"details\":{\"active_streams\":%u,\"max_active_streams\":%u,\"wait_ms\":%llu",
            active_streams,
            max_active_streams,
            wait_ms);
    fputs(",\"listen\":", file);
    write_json_string(file, listen_text);
    fputs(",\"upstream\":", file);
    write_json_string(file, upstream_text);
    fputs("},\"event\":\"backpressure\",\"request_id\":", file);
    write_json_string(file, request_id);
    fputs(",\"schema_version\":1,\"service\":\"microproxy\",\"connection_id\":", file);
    write_json_string(file, connection_id);
    fputs(",\"ts\":", file);
    write_json_string(file, ts);
    fputs(",\"pid\":", file);
    fprintf(file, "%ld", (long)getpid());
    fputs(",\"listen\":", file);
    write_json_string(file, listen_text);
    fputs(",\"upstream\":", file);
    write_json_string(file, upstream_text);
    fputs("}\n", file);

    if (fclose(file) != 0) {
        fprintf(stderr, "hg-edge: cannot close event log %s: %s\n", path, strerror(errno));
    }
}

static void reap_relay_children(unsigned int *active_children) {
    int status;

    while (waitpid(-1, &status, WNOHANG) > 0) {
        if (active_children != NULL && *active_children > 0) {
            (*active_children)--;
        }
    }
}

static bool starts_with_ci(const char *value, const char *prefix) {
    while (*prefix != '\0') {
        if (*value == '\0' ||
            tolower((unsigned char)*value) != tolower((unsigned char)*prefix)) {
            return false;
        }
        value++;
        prefix++;
    }
    return true;
}

static bool contains_ci(const char *haystack, const char *needle) {
    size_t needle_len = strlen(needle);

    for (const char *cursor = haystack; *cursor != '\0'; cursor++) {
        size_t i = 0;
        while (i < needle_len &&
               cursor[i] != '\0' &&
               tolower((unsigned char)cursor[i]) == tolower((unsigned char)needle[i])) {
            i++;
        }
        if (i == needle_len) {
            return true;
        }
    }

    return needle_len == 0;
}

static bool method_is_one_of(const char *method, const char *a, const char *b, const char *c) {
    return strcmp(method, a) == 0 ||
           (b != NULL && strcmp(method, b) == 0) ||
           (c != NULL && strcmp(method, c) == 0);
}

static bool parse_unsigned_header(const char *value,
                                  size_t value_len,
                                  unsigned long long *number_out) {
    unsigned long long number = 0;

    if (value_len == 0) {
        return false;
    }
    for (size_t i = 0; i < value_len; i++) {
        unsigned int digit;
        if (!isdigit((unsigned char)value[i])) {
            return false;
        }
        digit = (unsigned int)(value[i] - '0');
        if (number > (ULLONG_MAX - digit) / 10ULL) {
            return false;
        }
        number = (number * 10ULL) + digit;
    }

    *number_out = number;
    return true;
}

static route_decision_t classify_http_request(const http_request_t *request) {
    route_decision_t decision = {
        .classification = "unknown",
        .route = "passthrough",
        .candidate = "",
        .reason = "no_known_plaintext_hot_path_shape",
        .path = {0},
        .content_type = {0},
        .hot_path_candidate = false,
        .fallback_state = "none",
        .direct_cooldown_active = false,
        .direct_failure_count = 0,
        .direct_cooldown_remaining_ms = 0,
    };
    snprintf(decision.path, sizeof(decision.path), "%s", request->path);
    snprintf(decision.content_type, sizeof(decision.content_type), "%s", request->content_type);

    bool mutating_method = method_is_one_of(request->method, "POST", "PUT", "PATCH");
    bool proto_content =
        contains_ci(request->content_type, "application/connect+proto") ||
        contains_ci(request->content_type, "application/grpc") ||
        contains_ci(request->content_type, "application/protobuf") ||
        contains_ci(request->content_type, "application/x-protobuf");
    bool json_content =
        contains_ci(request->content_type, "json") ||
        request->content_type[0] == '\0';
    bool chat_path =
        contains_ci(request->path, "/v1/chat/completions") ||
        contains_ci(request->path, "/v1/completions") ||
        contains_ci(request->path, "/v1/responses") ||
        contains_ci(request->path, "/v1/messages") ||
        contains_ci(request->path, "/messages") ||
        contains_ci(request->path, "/generate") ||
        contains_ci(request->path, "getchatmessage") ||
        contains_ci(request->path, "streamchat") ||
        contains_ci(request->path, "getcompletion") ||
        contains_ci(request->path, "getstreamingcompletions") ||
        contains_ci(request->path, "getdevstralstream");
    bool edit_path =
        contains_ci(request->path, "edit") ||
        contains_ci(request->path, "apply") ||
        contains_ci(request->path, "rewrite") ||
        contains_ci(request->path, "composer") ||
        contains_ci(request->path, "cascade");

    bool telemetry_path =
        contains_ci(request->path, "recordanalyticsevent") ||
        contains_ci(request->path, "recordasynctelemetry") ||
        contains_ci(request->path, "client/metrics") ||
        contains_ci(request->path, "analyticsservice") ||
        contains_ci(request->path, "telemetry") ||
        contains_ci(request->path, "pulse");

    /* Antigravity observe-only mode: all control-plane metadata passes through for logging only. */

    if (telemetry_path) {
        decision.classification = "telemetry";
        decision.route = "passthrough";
        decision.reason = "observe_only_telemetry_passthrough";
        return decision;
    }

    if (method_is_one_of(request->method, "GET", "HEAD", NULL) &&
        (contains_ci(request->path, "/v1/models") ||
         contains_ci(request->path, "/models"))) {
        decision.classification = "model_list";
        decision.reason = "model_listing_endpoint";
        return decision;
    }

    if (contains_ci(request->path, "auth") ||
        contains_ci(request->path, "oauth") ||
        contains_ci(request->path, "login") ||
        contains_ci(request->path, "token") ||
        contains_ci(request->path, "session")) {
        decision.classification = "auth";
        decision.reason = "auth_endpoint";
        return decision;
    }

    if (strcmp(request->method, "OPTIONS") == 0 ||
        contains_ci(request->path, "config") ||
        contains_ci(request->path, "health") ||
        contains_ci(request->path, "status") ||
        contains_ci(request->path, "metrics") ||
        contains_ci(request->path, "telemetry") ||
        contains_ci(request->path, "analytics") ||
        contains_ci(request->path, "ping")) {
        decision.classification = "control";
        decision.reason = "control_or_telemetry_endpoint";
        return decision;
    }

    if (mutating_method &&
        request->has_content_length &&
        request->content_length >= HG_EDGE_LARGE_EDIT_BYTES &&
        (edit_path || json_content || proto_content)) {
        decision.classification = "large_edit";
        decision.candidate = "large_edit_passthrough";
        decision.reason = "large_mutating_request";
        decision.hot_path_candidate = true;
        return decision;
    }

    if (chat_path) {
        decision.classification = "chat_completion";
        decision.candidate = contains_ci(request->path, "getchatmessage")
                                 ? "connect_get_chat_message"
                                 : "chat_completion_passthrough";
        decision.reason = "chat_completion_endpoint";
        decision.hot_path_candidate =
            strcmp(request->method, "POST") == 0 &&
            contains_ci(request->path, "getchatmessage") &&
            proto_content;
        return decision;
    }

    if (proto_content) {
        decision.classification = "opaque_proto";
        decision.reason = "unrecognized_protobuf_payload";
        return decision;
    }

    return decision;
}

static void append_http_event(const char *event_log_path,
                              const char *event,
                              unsigned long long stream_id,
                              const http_request_t *request,
                              const route_decision_t *decision) {
    FILE *file;
    char ts[64];
    char request_id[32];
    char stream_id_text[32];
    char connection_id[32];

    ensure_event_log_parent(event_log_path);
    file = fopen(event_log_path, "a");
    if (file == NULL) {
        fprintf(stderr, "hg-edge: cannot append event log %s: %s\n", event_log_path, strerror(errno));
        return;
    }
    if (flock(fileno(file), LOCK_EX) != 0) {
        fprintf(stderr, "hg-edge: cannot lock event log %s: %s\n", event_log_path, strerror(errno));
        fclose(file);
        return;
    }

    utc_timestamp(ts, sizeof(ts));
    snprintf(request_id, sizeof(request_id), "req-%llu", stream_id);
    snprintf(stream_id_text, sizeof(stream_id_text), "stream-%llu", stream_id);
    snprintf(connection_id, sizeof(connection_id), "conn-%llu", stream_id);

    fputs("{\"details\":{", file);
    if (strcmp(event, "route_selected") == 0) {
        fputs("\"route\":", file);
        write_json_string(file, decision->route);
        fputs(",", file);
    } else if (strcmp(event, "hot_path_candidate") == 0) {
        fputs("\"candidate\":", file);
        write_json_string(file, decision->candidate);
        fputs(",\"route\":", file);
        write_json_string(file, decision->route);
        fputs(",", file);
    }
    fputs("\"method\":", file);
    write_json_string(file, request->method);
    fputs(",\"path\":", file);
    write_json_string(file, request->path);
    fputs(",\"host\":", file);
    write_json_string(file, request->host);
    fputs(",\"content_type\":", file);
    write_json_string(file, request->content_type);
    if (request->has_content_length) {
        fprintf(file, ",\"content_length\":%llu", request->content_length);
    } else {
        fputs(",\"content_length\":null", file);
    }
    fputs(",\"classification\":", file);
    write_json_string(file, decision->classification);
    fputs(",\"reason\":", file);
    write_json_string(file, decision->reason);
    if (strcmp(event, "route_selected") == 0) {
        fputs(",\"direct_failure_count\":", file);
        fprintf(file, "%u", decision->direct_failure_count);
        fputs(",\"direct_cooldown_active\":", file);
        fputs(decision->direct_cooldown_active ? "true" : "false", file);
        fprintf(file, ",\"direct_cooldown_remaining_ms\":%llu", decision->direct_cooldown_remaining_ms);
        fputs(",\"fallback_state\":", file);
        write_json_string(file, decision->fallback_state);
    }
    fputs("},\"event\":", file);
    write_json_string(file, event);
    fputs(",\"request_id\":", file);
    write_json_string(file, request_id);
    fputs(",\"schema_version\":1,\"ts\":", file);
    write_json_string(file, ts);
    fputs(",\"service\":\"microproxy\",\"connection_id\":", file);
    write_json_string(file, connection_id);
    fputs(",\"stream_id\":", file);
    write_json_string(file, stream_id_text);
    fputs("}\n", file);

    if (fclose(file) != 0) {
        fprintf(stderr, "hg-edge: cannot close event log %s: %s\n", event_log_path, strerror(errno));
    }
}

static bool extract_http_request(const char *buffer,
                                 ssize_t length,
                                 http_request_t *request) {
    const char *end = buffer + length;
    const char *line_end = NULL;
    const char *first_space;
    const char *second_space;
    size_t method_len;
    size_t path_len;

    if (length <= 0) {
        return false;
    }

    for (const char *cursor = buffer; cursor + 1 < end; cursor++) {
        if (cursor[0] == '\r' && cursor[1] == '\n') {
            line_end = cursor;
            break;
        }
    }
    if (line_end == NULL) {
        return false;
    }

    first_space = memchr(buffer, ' ', (size_t)(line_end - buffer));
    if (first_space == NULL) {
        return false;
    }
    second_space = memchr(first_space + 1, ' ', (size_t)(line_end - first_space - 1));
    if (second_space == NULL ||
        second_space + 6 > line_end ||
        memcmp(second_space + 1, "HTTP/", 5) != 0) {
        return false;
    }

    method_len = (size_t)(first_space - buffer);
    path_len = (size_t)(second_space - first_space - 1);
    if (method_len == 0 || method_len >= sizeof(request->method) ||
        path_len == 0 || path_len >= sizeof(request->path)) {
        return false;
    }

    for (size_t i = 0; i < method_len; i++) {
        if (!isupper((unsigned char)buffer[i])) {
            return false;
        }
    }

    memcpy(request->method, buffer, method_len);
    request->method[method_len] = '\0';
    memcpy(request->path, first_space + 1, path_len);
    request->path[path_len] = '\0';
    request->host[0] = '\0';
    request->content_type[0] = '\0';
    request->content_length = 0;
    request->has_content_length = false;

    for (const char *line = line_end + 2; line < end; ) {
        const char *next_line = NULL;

        if (line + 1 < end && line[0] == '\r' && line[1] == '\n') {
            break;
        }
        for (const char *cursor = line; cursor + 1 < end; cursor++) {
            if (cursor[0] == '\r' && cursor[1] == '\n') {
                next_line = cursor;
                break;
            }
        }
        if (next_line == NULL) {
            break;
        }
        if (starts_with_ci(line, "Host:") ||
            starts_with_ci(line, "Content-Type:") ||
            starts_with_ci(line, "Content-Length:")) {
            const char *value = line + 5;
            size_t value_len;
            char *target = request->host;
            size_t target_size = sizeof(request->host);

            if (starts_with_ci(line, "Content-Type:")) {
                value = line + 13;
                target = request->content_type;
                target_size = sizeof(request->content_type);
            } else if (starts_with_ci(line, "Content-Length:")) {
                value = line + 15;
                target = NULL;
                target_size = 0;
            }

            while (value < next_line && (*value == ' ' || *value == '\t')) {
                value++;
            }
            value_len = (size_t)(next_line - value);
            while (value_len > 0 &&
                   (value[value_len - 1] == ' ' || value[value_len - 1] == '\t')) {
                value_len--;
            }
            if (target == NULL) {
                unsigned long long parsed_length;
                if (parse_unsigned_header(value, value_len, &parsed_length)) {
                    request->content_length = parsed_length;
                    request->has_content_length = true;
                }
            } else {
                if (value_len >= target_size) {
                    value_len = target_size - 1;
                }
                memcpy(target, value, value_len);
                target[value_len] = '\0';
            }
        }
        line = next_line + 2;
    }

    return true;
}

static void sniff_client_bytes(const char *event_log_path,
                               unsigned long long stream_id,
                               const char *buffer,
                               ssize_t length,
                               bool *client_sniffed,
                               bool hot_path_observe) {
    http_request_t request;
    route_decision_t decision;

    if (*client_sniffed) {
        return;
    }
    *client_sniffed = true;

    if (!extract_http_request(buffer, length, &request)) {
        return;
    }

    decision = classify_http_request(&request);
    append_http_event(event_log_path,
                      "request_seen",
                      stream_id,
                      &request,
                      &decision);
    append_http_event(event_log_path,
                      "route_selected",
                      stream_id,
                      &request,
                      &decision);
    if (hot_path_observe && decision.hot_path_candidate) {
        append_http_event(event_log_path,
                          "hot_path_candidate",
                          stream_id,
                          &request,
                          &decision);
    }
}

static bool peek_client_http_decision(int client_fd,
                                      const char *event_log_path,
                                      unsigned long long stream_id,
                                      route_decision_t *decision_out,
                                      bool *client_sniffed,
                                      bool hot_path_observe,
                                      bool emit_events,
                                      const char *route_override,
                                      const route_decision_t *decision_override,
                                      unsigned int wait_ms) {
    char buffer[HG_EDGE_BUFFER_SIZE];
    struct pollfd pfd;
    ssize_t count;
    http_request_t request;
    route_decision_t decision;

    pfd.fd = client_fd;
    pfd.events = POLLIN;
    pfd.revents = 0;

    if (poll(&pfd, 1, (int)wait_ms) <= 0 || (pfd.revents & POLLIN) == 0) {
        return false;
    }

    count = recv(client_fd, buffer, sizeof(buffer), MSG_PEEK);
    if (count <= 0 || !extract_http_request(buffer, count, &request)) {
        return false;
    }

    decision = classify_http_request(&request);
    if (route_override != NULL && *route_override != '\0') {
        decision.route = route_override;
    }
    if (decision_override != NULL) {
        decision = *decision_override;
    }
    if (decision_out != NULL) {
        *decision_out = decision;
    }

    if (emit_events) {
        append_http_event(event_log_path,
                          "request_seen",
                          stream_id,
                          &request,
                          decision_override != NULL ? decision_override : &decision);
        append_http_event(event_log_path,
                          "route_selected",
                          stream_id,
                          &request,
                          decision_override != NULL ? decision_override : &decision);
        if (hot_path_observe && decision.hot_path_candidate) {
            append_http_event(event_log_path,
                              "hot_path_candidate",
                              stream_id,
                              &request,
                              decision_override != NULL ? decision_override : &decision);
        }
        if (client_sniffed != NULL) {
            *client_sniffed = true;
        }
    }

    return true;
}

static int close_fd(int fd) {
    if (fd >= 0 && close(fd) != 0) {
        return -1;
    }
    return 0;
}

static int open_listener(const endpoint_t *listen_endpoint) {
    struct addrinfo hints;
    struct addrinfo *results = NULL;
    struct addrinfo *item;
    char port_text[16];
    int listener = -1;
    int gai_result;

    memset(&hints, 0, sizeof(hints));
    hints.ai_family = AF_UNSPEC;
    hints.ai_socktype = SOCK_STREAM;
    hints.ai_flags = AI_PASSIVE;
    snprintf(port_text, sizeof(port_text), "%u", listen_endpoint->port);

    gai_result = getaddrinfo(listen_endpoint->host, port_text, &hints, &results);
    if (gai_result != 0) {
        fprintf(stderr, "hg-edge: cannot resolve listen endpoint %s:%u: %s\n",
                listen_endpoint->host, listen_endpoint->port, gai_strerror(gai_result));
        return -1;
    }

    for (item = results; item != NULL; item = item->ai_next) {
        int enabled = 1;
        listener = socket(item->ai_family, item->ai_socktype, item->ai_protocol);
        if (listener < 0) {
            continue;
        }

        (void)setsockopt(listener, SOL_SOCKET, SO_REUSEADDR, &enabled, sizeof(enabled));
        if (bind(listener, item->ai_addr, item->ai_addrlen) == 0 && listen(listener, 16) == 0) {
            break;
        }

        close_fd(listener);
        listener = -1;
    }

    freeaddrinfo(results);
    if (listener < 0) {
        fprintf(stderr, "hg-edge: cannot bind listen endpoint %s:%u: %s\n",
                listen_endpoint->host, listen_endpoint->port, strerror(errno));
    }

    return listener;
}

static int connect_upstream(const endpoint_t *upstream) {
    struct addrinfo hints;
    struct addrinfo *results = NULL;
    struct addrinfo *item;
    char port_text[16];
    int upstream_fd = -1;
    int gai_result;

    memset(&hints, 0, sizeof(hints));
    hints.ai_family = AF_UNSPEC;
    hints.ai_socktype = SOCK_STREAM;
    snprintf(port_text, sizeof(port_text), "%u", upstream->port);

    gai_result = getaddrinfo(upstream->host, port_text, &hints, &results);
    if (gai_result != 0) {
        fprintf(stderr, "hg-edge: cannot resolve upstream endpoint %s:%u: %s\n",
                upstream->host, upstream->port, gai_strerror(gai_result));
        return -1;
    }

    for (item = results; item != NULL; item = item->ai_next) {
        upstream_fd = socket(item->ai_family, item->ai_socktype, item->ai_protocol);
        if (upstream_fd < 0) {
            continue;
        }

        if (connect(upstream_fd, item->ai_addr, item->ai_addrlen) == 0) {
            break;
        }

        close_fd(upstream_fd);
        upstream_fd = -1;
    }

    freeaddrinfo(results);
    if (upstream_fd < 0) {
        fprintf(stderr, "hg-edge: cannot connect upstream %s:%u: %s\n",
                upstream->host, upstream->port, strerror(errno));
    }

    return upstream_fd;
}

static bool send_all(int fd, const char *buffer, ssize_t length) {
    ssize_t sent = 0;

    while (sent < length) {
        ssize_t result = send(fd, buffer + sent, (size_t)(length - sent), 0);
        if (result < 0) {
            if (errno == EINTR) {
                continue;
            }
            return false;
        }
        if (result == 0) {
            return false;
        }
        sent += result;
    }

    return true;
}

static bool bytes_contains_ci(const char *buffer, ssize_t length, const char *needle) {
    size_t needle_len;
    if (buffer == NULL || needle == NULL || length <= 0) {
        return false;
    }
    needle_len = strlen(needle);
    if (needle_len == 0 || (size_t)length < needle_len) {
        return false;
    }
    for (ssize_t i = 0; i <= length - (ssize_t)needle_len; i++) {
        size_t j = 0;
        for (; j < needle_len; j++) {
            unsigned char a = (unsigned char)buffer[i + (ssize_t)j];
            unsigned char b = (unsigned char)needle[j];
            if (tolower(a) != tolower(b)) {
                break;
            }
        }
        if (j == needle_len) {
            return true;
        }
    }
    return false;
}

static bool forward_ready_bytes(int from_fd,
                                int to_fd,
                                bool *from_open,
                                bool *to_open,
                                unsigned long long *bytes_forwarded,
                                const char *event_log_path,
                                unsigned long long stream_id,
                                bool *client_sniffed,
                                bool hot_path_observe,
                                relay_stats_t *stats,
                                bool upstream_to_client) {
    char buffer[HG_EDGE_BUFFER_SIZE];
    ssize_t count;

    count = recv(from_fd, buffer, sizeof(buffer), 0);
    if (count < 0) {
        if (errno == EINTR) {
            return true;
        }
        return false;
    }

    if (count == 0) {
        *from_open = false;
        (void)shutdown(to_fd, SHUT_WR);
        return true;
    }

    /* Observe plaintext request metadata when available, but never modify bytes. */
    if (!upstream_to_client && client_sniffed != NULL) {
        sniff_client_bytes(
            event_log_path,
            stream_id,
            buffer,
            count,
            client_sniffed,
            hot_path_observe
        );
    }

    /* Pure L4 relay: always forward the original bytes in full. */
    if (!send_all(to_fd, buffer, count)) {
        return false;
    }

    *bytes_forwarded += (unsigned long long)count;
    return true;
}

static void relay_connection(int client_fd,
                             int upstream_fd,
                             unsigned int idle_timeout_seconds,
                             unsigned int max_stream_seconds,
                             relay_stats_t *stats,
                             const char *event_log_path,
                             unsigned long long stream_id,
                             bool hot_path_observe,
                             bool client_sniffed_initial) {
    bool client_open = true;
    bool upstream_open = true;
    bool client_sniffed = client_sniffed_initial;
    unsigned long long start_ms = monotonic_ms();

    while (!g_stop_requested && (client_open || upstream_open)) {
        struct pollfd fds[2];
        int nfds = 0;
        int poll_result;
        int poll_timeout_ms = (int)(idle_timeout_seconds * 1000);

        if (max_stream_seconds > 0) {
            unsigned long long elapsed_ms = monotonic_ms() - start_ms;
            unsigned long long max_ms = (unsigned long long)max_stream_seconds * 1000ULL;

            if (elapsed_ms >= max_ms) {
                fprintf(stderr, "hg-edge: relay max stream time after %u seconds\n", max_stream_seconds);
                break;
            }
            if (max_ms - elapsed_ms < (unsigned long long)poll_timeout_ms) {
                poll_timeout_ms = (int)(max_ms - elapsed_ms);
            }
        }

        if (client_open) {
            fds[nfds].fd = client_fd;
            fds[nfds].events = POLLIN;
            fds[nfds].revents = 0;
            nfds++;
        }
        if (upstream_open) {
            fds[nfds].fd = upstream_fd;
            fds[nfds].events = POLLIN;
            fds[nfds].revents = 0;
            nfds++;
        }

        poll_result = poll(fds, (nfds_t)nfds, poll_timeout_ms);
        if (poll_result < 0) {
            if (errno == EINTR) {
                continue;
            }
            fprintf(stderr, "hg-edge: relay poll failed: %s\n", strerror(errno));
            break;
        }
        if (poll_result == 0) {
            fprintf(stderr, "hg-edge: relay idle timeout after %u seconds\n", idle_timeout_seconds);
            break;
        }

        for (int i = 0; i < nfds; i++) {
            if (fds[i].revents == 0) {
                continue;
            }
            if ((fds[i].revents & (POLLERR | POLLNVAL)) != 0) {
                client_open = false;
                upstream_open = false;
                break;
            }
            if (fds[i].fd == client_fd && client_open) {
                if ((fds[i].revents & POLLHUP) != 0 && (fds[i].revents & POLLIN) == 0) {
                    client_open = false;
                    (void)shutdown(upstream_fd, SHUT_WR);
                } else if (!forward_ready_bytes(client_fd,
                                                upstream_fd,
                                                &client_open,
                                                &upstream_open,
                                                &stats->bytes_in,
                                                event_log_path,
                                                stream_id,
                                                &client_sniffed,
                                                hot_path_observe,
                                                stats,
                                                false)) {
                    break;
                }
            } else if (fds[i].fd == upstream_fd && upstream_open) {
                if ((fds[i].revents & POLLHUP) != 0 && (fds[i].revents & POLLIN) == 0) {
                    upstream_open = false;
                    (void)shutdown(client_fd, SHUT_WR);
                } else if (!forward_ready_bytes(upstream_fd,
                                                client_fd,
                                                &upstream_open,
                                                &client_open,
                                                &stats->bytes_out,
                                                event_log_path,
                                                stream_id,
                                                NULL,
                                                false,
                                                stats,
                                                true)) {
                    break;
                }
            }
        }
    }
}

static int run_relay(const endpoint_t *listen,
                     const endpoint_t *upstream,
                     const endpoint_t *direct_upstream,
                     bool direct_hot_path,
                     unsigned int idle_timeout_seconds,
                     unsigned int max_stream_seconds,
                     const char *event_log_path,
                     bool hot_path_observe,
                     unsigned int max_active_streams) {
    int listener;
    struct sigaction action;
    direct_upstream_health_t direct_health = {0, 0};
    unsigned int active_children = 0;
    unsigned long long last_backpressure_log_ms = 0;

    memset(&action, 0, sizeof(action));
    action.sa_handler = handle_stop_signal;
    sigemptyset(&action.sa_mask);
    (void)sigaction(SIGINT, &action, NULL);
    (void)sigaction(SIGTERM, &action, NULL);
    signal(SIGPIPE, SIG_IGN);

    listener = open_listener(listen);
    if (listener < 0) {
        return 1;
    }

    printf("hg-edge %s relay listening on %s:%u -> %s:%u\n",
           HG_EDGE_VERSION, listen->host, listen->port, upstream->host, upstream->port);
    fflush(stdout);

    srand((unsigned int)time(NULL) ^ (unsigned int)getpid());

    while (!g_stop_requested) {
        struct pollfd poll_fd;
        int poll_result;
        int client_fd;
        int upstream_fd;
        const endpoint_t *selected_upstream = upstream;
        bool selected_direct_upstream = false;
        route_decision_t peek_decision;
        route_decision_t route_decision;
        bool client_sniffed_initial = false;
        unsigned long long stream_id;
        unsigned long long start_ms;
        unsigned long long route_ms;
        const char *selected_fallback_state = "none";
        relay_stats_t stats;

        reap_relay_children(&active_children);
        while (!g_stop_requested && active_children >= max_active_streams) {
            unsigned long long now_ms = monotonic_ms();
            if (last_backpressure_log_ms == 0 ||
                now_ms - last_backpressure_log_ms >= 1000ULL) {
                append_backpressure_event(event_log_path,
                                          listen,
                                          upstream,
                                          active_children,
                                          max_active_streams,
                                          last_backpressure_log_ms == 0
                                              ? 0
                                              : now_ms - last_backpressure_log_ms);
                last_backpressure_log_ms = now_ms;
            }
            reap_relay_children(&active_children);
            sleep_ms(50);
        }
        if (active_children < max_active_streams) {
            last_backpressure_log_ms = 0;
        }
        if (g_stop_requested) {
            break;
        }

        poll_fd.fd = listener;
        poll_fd.events = POLLIN;
        poll_fd.revents = 0;

        poll_result = poll(&poll_fd, 1, 1000);
        if (poll_result < 0) {
            if (errno == EINTR) {
                continue;
            }
            fprintf(stderr, "hg-edge: listener poll failed: %s\n", strerror(errno));
            close_fd(listener);
            return 1;
        }
        if (poll_result == 0) {
            continue;
        }

        client_fd = accept(listener, NULL, NULL);
        if (client_fd < 0) {
            if (errno == EINTR) {
                continue;
            }
            fprintf(stderr, "hg-edge: accept failed: %s\n", strerror(errno));
            continue;
        }

        stream_id = g_next_stream_id++;
        start_ms = monotonic_ms();
        route_ms = start_ms;

        /* Peek only for routing labels and observability metadata. */
        if (peek_client_http_decision(client_fd,
                                      event_log_path,
                                      stream_id,
                                      &peek_decision,
                                      &client_sniffed_initial,
                                      hot_path_observe,
                                      false,
                                      NULL,
                                      NULL,
                                      1000)) {
            route_decision = peek_decision;
            route_ms = monotonic_ms();

            /* Observe-only: no prompt injection or response fabrication. */

            /* Local cache hits, local ACKs, and timing jitter are disabled: this C edge observes and forwards only. */

            if (direct_hot_path && direct_upstream != NULL &&
                (peek_decision.hot_path_candidate ||
                 strcmp(peek_decision.classification, "large_edit") == 0)) {
                if (direct_upstream_health_in_cooldown(&direct_health, route_ms)) {
                    selected_upstream = upstream;
                    selected_direct_upstream = false;
                    selected_fallback_state = "direct_upstream_cooldown";
                    route_decision.route = "python_fallback";
                    route_decision.reason = "direct_upstream_cooldown";
                } else {
                    selected_upstream = direct_upstream;
                    selected_direct_upstream = true;
                    selected_fallback_state = "none";
                    route_decision.route = "direct_upstream";
                }
                direct_upstream_health_snapshot(&direct_health,
                                                route_ms,
                                                &route_decision,
                                                selected_fallback_state);
                (void)peek_client_http_decision(client_fd,
                                                event_log_path,
                                                stream_id,
                                                &peek_decision,
                                                &client_sniffed_initial,
                                                hot_path_observe,
                                                true,
                                                NULL,
                                                &route_decision,
                                                0);
            }
        }

        upstream_fd = connect_upstream(selected_upstream);
        if (upstream_fd < 0) {
            if (selected_direct_upstream) {
                direct_upstream_health_record_failure(&direct_health, route_ms);
                selected_fallback_state = "direct_connect_failed";
            }
        append_event(event_log_path,
                     "upstream_error",
                     stream_id,
                     listen,
                     selected_upstream,
                     0,
                     0,
                     0,
                     NULL,
                     &direct_health,
                     route_ms,
                     selected_fallback_state);
            if (selected_direct_upstream) {
                selected_upstream = upstream;
                selected_direct_upstream = false;
                selected_fallback_state = "direct_connect_failed";
                upstream_fd = connect_upstream(selected_upstream);
                if (upstream_fd >= 0) {
                    route_decision = peek_decision;
                    route_decision.route = "python_fallback";
                    route_decision.reason = "direct_connect_failed";
                    direct_upstream_health_snapshot(&direct_health,
                                                    route_ms,
                                                    &route_decision,
                                                    selected_fallback_state);
                    (void)peek_client_http_decision(client_fd,
                                                    event_log_path,
                                                    stream_id,
                                                    &peek_decision,
                                                    &client_sniffed_initial,
                                                    hot_path_observe,
                                                    true,
                                                    NULL,
                                                    &route_decision,
                                                    0);
                } else {
                    append_event(event_log_path,
                                 "upstream_error",
                                 stream_id,
                                 listen,
                                 selected_upstream,
                                 0,
                                 0,
                                 0,
                                 NULL,
                                 &direct_health,
                                 route_ms,
                                 "python_fallback_failed");
                }
            }
            if (upstream_fd < 0) {
                close_fd(client_fd);
                continue;
            }
        }

        if (selected_direct_upstream) {
            direct_upstream_health_record_success(&direct_health);
        }

        stats.bytes_in = 0;
        stats.bytes_out = 0;
        stats.upstream_connect_error_signal = false;
        stats.upstream_quota_exhausted_signal = false;
        append_event(event_log_path,
                     "stream_started",
                     stream_id,
                     listen,
                     selected_upstream,
                     0,
                     0,
                     0,
                     NULL,
                     NULL,
                     route_ms,
                     "none");
        {
            pid_t worker_pid = fork();
            if (worker_pid < 0) {
                fprintf(stderr, "hg-edge: fork failed: %s\n", strerror(errno));
                close_fd(upstream_fd);
                close_fd(client_fd);
                continue;
            } else if (worker_pid > 0) {
                active_children++;
                close_fd(upstream_fd);
                close_fd(client_fd);
                continue;
            } else {
                close_fd(listener);
            }
        }

        relay_connection(client_fd,
                         upstream_fd,
                         idle_timeout_seconds,
                         max_stream_seconds,
                         &stats,
                         event_log_path,
                         stream_id,
                         hot_path_observe,
                         client_sniffed_initial);
        append_event(event_log_path,
                     "stream_finished",
                     stream_id,
                     listen,
                     selected_upstream,
                     stats.bytes_in,
                     stats.bytes_out,
                     monotonic_ms() - start_ms,
                     &stats,
                     NULL,
                     route_ms,
                     "none");
        close_fd(upstream_fd);
        close_fd(client_fd);
        _exit(0);
    }

    close_fd(listener);
    return 0;
}

int main(int argc, char **argv) {
    const char *event_log_env = getenv(HG_EDGE_EVENT_LOG_ENV);
    const char *max_active_streams_env = getenv("HG_EDGE_MAX_ACTIVE_STREAMS");
    edge_config_t config = {
        .listen_raw = HG_EDGE_DEFAULT_LISTEN,
        .upstream_raw = HG_EDGE_DEFAULT_UPSTREAM,
        .direct_upstream_raw = NULL,
        .event_log_path = (event_log_env != NULL && *event_log_env != '\0')
                              ? event_log_env
                              : HG_EDGE_DEFAULT_EVENT_LOG,
        .idle_timeout_seconds = HG_EDGE_DEFAULT_IDLE_TIMEOUT_SECONDS,
        .max_stream_seconds = HG_EDGE_DEFAULT_MAX_STREAM_SECONDS,
        .max_active_streams = HG_EDGE_DEFAULT_MAX_ACTIVE_STREAMS,
        .listen_set = false,
        .upstream_set = false,
        .direct_upstream_set = false,
        .check_config = false,
        .print_flow = false,
        .relay = false,
        .hot_path_observe = false,
        .direct_hot_path = false,
    };
    endpoint_t listen_endpoint;
    endpoint_t upstream_endpoint;
    endpoint_t direct_upstream_endpoint;

    if (max_active_streams_env != NULL &&
        *max_active_streams_env != '\0' &&
        !parse_timeout(max_active_streams_env, &config.max_active_streams)) {
        fprintf(stderr, "hg-edge: HG_EDGE_MAX_ACTIVE_STREAMS requires count in range 1..86400\n");
        return 2;
    }

    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "--listen") == 0) {
            if (!read_value_arg(argc, argv, &i, &config.listen_raw)) {
                fprintf(stderr, "hg-edge: --listen requires HOST:PORT\n");
                return 2;
            }
            config.listen_set = true;
        } else if (strcmp(argv[i], "--upstream") == 0) {
            if (!read_value_arg(argc, argv, &i, &config.upstream_raw)) {
                fprintf(stderr, "hg-edge: --upstream requires HOST:PORT\n");
                return 2;
            }
            config.upstream_set = true;
        } else if (strcmp(argv[i], "--direct-upstream") == 0) {
            if (!read_value_arg(argc, argv, &i, &config.direct_upstream_raw)) {
                fprintf(stderr, "hg-edge: --direct-upstream requires HOST:PORT\n");
                return 2;
            }
            config.direct_upstream_set = true;
        } else if (strcmp(argv[i], "--idle-timeout") == 0) {
            const char *timeout_raw = NULL;
            if (!read_value_arg(argc, argv, &i, &timeout_raw) ||
                !parse_timeout(timeout_raw, &config.idle_timeout_seconds)) {
                fprintf(stderr, "hg-edge: --idle-timeout requires seconds in range 1..86400\n");
                return 2;
            }
        } else if (strcmp(argv[i], "--max-stream-seconds") == 0) {
            const char *timeout_raw = NULL;
            if (!read_value_arg(argc, argv, &i, &timeout_raw) ||
                !parse_timeout(timeout_raw, &config.max_stream_seconds)) {
                fprintf(stderr, "hg-edge: --max-stream-seconds requires seconds in range 1..86400\n");
                return 2;
            }
        } else if (strcmp(argv[i], "--max-active-streams") == 0) {
            const char *count_raw = NULL;
            if (!read_value_arg(argc, argv, &i, &count_raw) ||
                !parse_timeout(count_raw, &config.max_active_streams)) {
                fprintf(stderr, "hg-edge: --max-active-streams requires count in range 1..86400\n");
                return 2;
            }
        } else if (strcmp(argv[i], "--event-log") == 0) {
            if (!read_value_arg(argc, argv, &i, &config.event_log_path) ||
                config.event_log_path == NULL ||
                *config.event_log_path == '\0') {
                fprintf(stderr, "hg-edge: --event-log requires PATH\n");
                return 2;
            }
        } else if (strcmp(argv[i], "--check-config") == 0) {
            config.check_config = true;
        } else if (strcmp(argv[i], "--print-flow") == 0) {
            config.print_flow = true;
        } else if (strcmp(argv[i], "--relay") == 0) {
            config.relay = true;
        } else if (strcmp(argv[i], "--hot-path-observe") == 0) {
            config.hot_path_observe = true;
        } else if (strcmp(argv[i], "--direct-hot-path") == 0) {
            config.direct_hot_path = true;
        } else if (strcmp(argv[i], "--version") == 0) {
            printf("hg-edge %s\n", HG_EDGE_VERSION);
            return 0;
        } else if (strcmp(argv[i], "--help") == 0 || strcmp(argv[i], "-h") == 0) {
            print_usage(stdout, argv[0]);
            return 0;
        } else {
            fprintf(stderr, "hg-edge: unknown option '%s'\n", argv[i]);
            print_usage(stderr, argv[0]);
            return 2;
        }
    }

    if (!config.relay && !config.check_config && !config.print_flow) {
        config.print_flow = true;
    }

    if (config.direct_hot_path && !config.direct_upstream_set) {
        fprintf(stderr, "hg-edge: --direct-hot-path requires --direct-upstream\n");
        return 2;
    }

    if (!validate_config(&config, &listen_endpoint, &upstream_endpoint, &direct_upstream_endpoint)) {
        return 1;
    }

    if (config.check_config || config.print_flow) {
        print_flow(&config, &listen_endpoint, &upstream_endpoint);
    }

    if (config.relay && !config.check_config) {
        return run_relay(&listen_endpoint,
                         &upstream_endpoint,
                         config.direct_upstream_set ? &direct_upstream_endpoint : NULL,
                         config.direct_hot_path,
                         config.idle_timeout_seconds,
                         config.max_stream_seconds,
                         config.event_log_path,
                         config.hot_path_observe,
                         config.max_active_streams);
    }

    return 0;
}
