#include "hmi_telemetry.hpp"

#include <algorithm>
#include <array>
#include <cerrno>
#include <chrono>
#include <cstdlib>
#include <cstring>
#include <sstream>
#include <thread>
#include <utility>

#include <arpa/inet.h>
#include <fcntl.h>
#include <netdb.h>
#include <poll.h>
#include <sys/socket.h>
#include <unistd.h>

namespace hg::hmi {
namespace {

constexpr std::string_view kHgTelemetryPath = "/hg/telemetry";
constexpr std::string_view kKhojStatusPath = "/hg/khoj/status";
constexpr std::string_view kMicroproxyStatusPath = "/hg/microproxy/status";

bool is_digit(char ch) noexcept {
    return ch >= '0' && ch <= '9';
}

std::size_t find_key(std::string_view json, std::string_view key) noexcept {
    std::size_t pos = 0;
    while (pos < json.size()) {
        pos = json.find('"', pos);
        if (pos == std::string_view::npos) {
            return pos;
        }
        const std::size_t value_start = pos + 1;
        const std::size_t value_end = json.find('"', value_start);
        if (value_end == std::string_view::npos) {
            return std::string_view::npos;
        }
        if (json.substr(value_start, value_end - value_start) == key) {
            return pos;
        }
        pos = value_end + 1;
    }
    return std::string_view::npos;
}

std::string_view object_for_key(std::string_view json, std::string_view key) noexcept {
    const std::size_t key_pos = find_key(json, key);
    if (key_pos == std::string_view::npos) {
        return {};
    }
    const std::size_t colon = json.find(':', key_pos);
    if (colon == std::string_view::npos) {
        return {};
    }
    const std::size_t open = json.find('{', colon + 1);
    if (open == std::string_view::npos) {
        return {};
    }

    int depth = 0;
    bool in_string = false;
    bool escaped = false;
    for (std::size_t idx = open; idx < json.size(); ++idx) {
        const char ch = json[idx];
        if (in_string) {
            if (escaped) {
                escaped = false;
            } else if (ch == '\\') {
                escaped = true;
            } else if (ch == '"') {
                in_string = false;
            }
            continue;
        }
        if (ch == '"') {
            in_string = true;
        } else if (ch == '{') {
            ++depth;
        } else if (ch == '}') {
            --depth;
            if (depth == 0) {
                return json.substr(open, idx - open + 1);
            }
        }
    }
    return {};
}

bool number_for_key(std::string_view json, std::string_view key, float* out) noexcept {
    if (out == nullptr) {
        return false;
    }
    const std::size_t key_pos = find_key(json, key);
    if (key_pos == std::string_view::npos) {
        return false;
    }
    const std::size_t colon = json.find(':', key_pos);
    if (colon == std::string_view::npos) {
        return false;
    }
    std::size_t start = colon + 1;
    while (start < json.size() && (json[start] == ' ' || json[start] == '\t' ||
                                   json[start] == '\r' || json[start] == '\n')) {
        ++start;
    }
    if (start >= json.size()) {
        return false;
    }
    if (json.compare(start, 4, "true") == 0) {
        *out = 1.0F;
        return true;
    }
    if (json.compare(start, 5, "false") == 0) {
        *out = 0.0F;
        return true;
    }

    std::size_t end = start;
    if (json[end] == '-') {
        ++end;
    }
    while (end < json.size() && is_digit(json[end])) {
        ++end;
    }
    if (end < json.size() && json[end] == '.') {
        ++end;
        while (end < json.size() && is_digit(json[end])) {
            ++end;
        }
    }
    if (end < json.size() && (json[end] == 'e' || json[end] == 'E')) {
        ++end;
        if (end < json.size() && (json[end] == '-' || json[end] == '+')) {
            ++end;
        }
        while (end < json.size() && is_digit(json[end])) {
            ++end;
        }
    }
    if (end == start || (end == start + 1 && json[start] == '-')) {
        return false;
    }

    char buf[48]{};
    const std::size_t len = std::min<std::size_t>(sizeof(buf) - 1, end - start);
    std::memcpy(buf, json.data() + start, len);
    char* parse_end = nullptr;
    const float value = std::strtof(buf, &parse_end);
    if (parse_end == buf) {
        return false;
    }
    *out = value;
    return true;
}

void max_number(std::string_view json,
                std::string_view key,
                float* target,
                bool* any = nullptr) noexcept {
    float value = 0.0F;
    if (number_for_key(json, key, &value)) {
        *target = std::max(*target, value);
        if (any != nullptr) {
            *any = true;
        }
    }
}

void add_number(std::string_view json,
                std::string_view key,
                float* target,
                bool* any = nullptr) noexcept {
    float value = 0.0F;
    if (number_for_key(json, key, &value)) {
        *target += value;
        if (any != nullptr) {
            *any = true;
        }
    }
}

float number_or_zero(std::string_view json, std::string_view key) noexcept {
    float value = 0.0F;
    number_for_key(json, key, &value);
    return value;
}

bool parse_status_buckets(std::string_view status_codes, TelemetryCounters* counters) noexcept {
    bool any = false;
    std::size_t pos = 0;
    while (pos < status_codes.size()) {
        const std::size_t quote = status_codes.find('"', pos);
        if (quote == std::string_view::npos || quote + 4 >= status_codes.size()) {
            return any;
        }
        const char c0 = status_codes[quote + 1];
        const char c1 = status_codes[quote + 2];
        const char c2 = status_codes[quote + 3];
        if (is_digit(c0) && is_digit(c1) && is_digit(c2) && status_codes[quote + 4] == '"') {
            const std::string_view key = status_codes.substr(quote + 1, 3);
            const float count = number_or_zero(status_codes, key);
            if (c0 == '2') {
                counters->status_2xx += count;
                any = true;
            } else if (c0 == '4') {
                counters->status_4xx += count;
                any = true;
            } else if (c0 == '5') {
                counters->status_5xx += count;
                any = true;
            }
            pos = quote + 5;
        } else {
            pos = quote + 1;
        }
    }
    return any;
}

bool parse_hg_telemetry(std::string_view json, TelemetryCounters* counters) noexcept {
    bool any = false;
    max_number(json, "enabled", &counters->proxy_online, &any);
    max_number(json, "total_requests", &counters->total_requests, &any);
    max_number(json, "cache_hits", &counters->cache_hits, &any);
    max_number(json, "tokens_saved", &counters->tokens_saved, &any);

    const std::string_view latency = object_for_key(json, "latency_ms");
    max_number(latency, "p95", &counters->latency_p95_ms, &any);

    const std::string_view shared = object_for_key(json, "shared_metrics");
    max_number(shared, "binary_fail_open", &counters->binary_fail_open, &any);
    max_number(shared, "exact_response_cache_hits", &counters->exact_response_cache_hits, &any);
    max_number(shared, "exact_response_cache_stores", &counters->exact_response_cache_stores, &any);
    max_number(shared, "canonical_response_cache_hits", &counters->canonical_response_cache_hits, &any);
    max_number(shared, "canonical_response_cache_stores", &counters->canonical_response_cache_stores, &any);
    max_number(shared, "control_plane_cache_hits", &counters->control_plane_cache_hits, &any);
    max_number(shared, "control_plane_cache_stores", &counters->control_plane_cache_stores, &any);
    max_number(shared, "local_ack_telemetry", &counters->local_ack_telemetry, &any);
    max_number(shared, "local_ack_bytes_avoided", &counters->local_ack_bytes_avoided, &any);
    max_number(shared, "upstream_inference_forwards", &counters->upstream_inference_forwards, &any);
    max_number(shared, "upstream_inference_cache_misses", &counters->upstream_inference_cache_misses, &any);
    add_number(shared, "upstream_inference_blocks", &counters->upstream_inference_blocks, &any);
    add_number(shared, "upstream_inference_cache_only_blocks", &counters->upstream_inference_blocks, &any);
    max_number(shared, "mitm_reasoning_injections", &counters->reasoning_injections, &any);
    max_number(shared, "pegasus_swarm_triggers", &counters->swarm_triggers, &any);
    max_number(shared, "pegasus_swarm_success", &counters->swarm_success, &any);
    max_number(shared, "pegasus_swarm_fail", &counters->swarm_failed, &any);
    max_number(shared, "pegasus_swarm_denied", &counters->swarm_denied, &any);
    max_number(shared, "khoj_binary_injections", &counters->khoj_injections, &any);
    max_number(shared, "khoj_search_cache_hits", &counters->cache_hits, &any);
    max_number(shared, "khoj_tokens_avoided", &counters->tokens_saved, &any);

    const std::string_view khoj = object_for_key(json, "khoj");
    max_number(khoj, "injection_count", &counters->khoj_injections, &any);
    max_number(khoj, "binary_injection_count", &counters->khoj_injections, &any);
    max_number(khoj, "search_cache_hits", &counters->cache_hits, &any);
    max_number(khoj, "binary_tokens_avoided", &counters->tokens_saved, &any);

    const std::string_view swarm = object_for_key(json, "pegasus_swarm");
    max_number(swarm, "attempts", &counters->swarm_triggers, &any);
    max_number(swarm, "success", &counters->swarm_success, &any);
    max_number(swarm, "failed", &counters->swarm_failed, &any);
    max_number(swarm, "denied", &counters->swarm_denied, &any);
    max_number(swarm, "avg_latency_ms", &counters->swarm_avg_latency_ms, &any);

    return any;
}

bool parse_khoj_status(std::string_view json, TelemetryCounters* counters) noexcept {
    bool any = false;
    max_number(json, "injection_count", &counters->khoj_injections, &any);
    max_number(json, "binary_injection_count", &counters->khoj_injections, &any);
    max_number(json, "search_cache_hits", &counters->cache_hits, &any);
    max_number(json, "binary_tokens_avoided", &counters->tokens_saved, &any);

    const std::string_view shared = object_for_key(json, "shared_metrics");
    max_number(shared, "binary_fail_open", &counters->binary_fail_open, &any);
    max_number(shared, "mitm_reasoning_injections", &counters->reasoning_injections, &any);
    max_number(shared, "pegasus_swarm_triggers", &counters->swarm_triggers, &any);
    max_number(shared, "pegasus_swarm_success", &counters->swarm_success, &any);
    max_number(shared, "pegasus_swarm_fail", &counters->swarm_failed, &any);
    max_number(shared, "pegasus_swarm_denied", &counters->swarm_denied, &any);
    max_number(shared, "khoj_binary_injections", &counters->khoj_injections, &any);
    max_number(shared, "khoj_search_cache_hits", &counters->cache_hits, &any);
    max_number(shared, "khoj_tokens_avoided", &counters->tokens_saved, &any);

    const std::string_view acceleration = object_for_key(json, "acceleration");
    const std::string_view runtime = object_for_key(acceleration, "runtime_active");
    max_number(runtime, "cuda", &counters->cuda_active, &any);
    max_number(runtime, "openvino", &counters->openvino_active, &any);
    max_number(runtime, "openvino_compile_ok", &counters->openvino_active, &any);
    max_number(runtime, "myriad_visible", &counters->myriad_visible, &any);
    max_number(runtime, "myriad", &counters->myriad_visible, &any);
    max_number(runtime, "myriad_boot_failed", &counters->myriad_boot_failed, &any);
    return any;
}

bool parse_microproxy_status(std::string_view json, TelemetryCounters* counters) noexcept {
    bool any = false;
    const std::string_view routes = object_for_key(json, "routes");
    max_number(routes, "total", &counters->route_hits, &any);

    const std::string_view streams = object_for_key(json, "streams");
    max_number(streams, "streams_open", &counters->microproxy_streams_open, &any);
    max_number(streams, "streams_finished", &counters->microproxy_streams_finished, &any);
    max_number(streams, "quota_exhausted_signals", &counters->microproxy_quota_exhausted, &any);
    max_number(streams, "connect_error_signals", &counters->microproxy_connect_errors, &any);
    any = parse_status_buckets(object_for_key(streams, "status_codes"), counters) || any;

    const std::string_view upstream = object_for_key(json, "upstream_errors");
    max_number(upstream, "total", &counters->microproxy_upstream_errors, &any);
    return any;
}

int connect_with_timeout(const HmiTelemetrySource& source) {
    addrinfo hints{};
    hints.ai_family = AF_UNSPEC;
    hints.ai_socktype = SOCK_STREAM;

    const std::string port = std::to_string(source.port);
    addrinfo* result = nullptr;
    if (getaddrinfo(source.host.c_str(), port.c_str(), &hints, &result) != 0) {
        return -1;
    }

    int connected = -1;
    for (addrinfo* rp = result; rp != nullptr; rp = rp->ai_next) {
        int fd = socket(rp->ai_family, rp->ai_socktype, rp->ai_protocol);
        if (fd < 0) {
            continue;
        }
        const int flags = fcntl(fd, F_GETFL, 0);
        if (flags >= 0) {
            (void)fcntl(fd, F_SETFL, flags | O_NONBLOCK);
        }

        int rc = connect(fd, rp->ai_addr, rp->ai_addrlen);
        if (rc != 0 && errno == EINPROGRESS) {
            pollfd pfd{};
            pfd.fd = fd;
            pfd.events = POLLOUT;
            rc = poll(&pfd, 1, static_cast<int>(source.timeout.count()));
            if (rc > 0) {
                int err = 0;
                socklen_t len = sizeof(err);
                (void)getsockopt(fd, SOL_SOCKET, SO_ERROR, &err, &len);
                rc = err == 0 ? 0 : -1;
            } else {
                rc = -1;
            }
        }
        if (rc == 0) {
            if (flags >= 0) {
                (void)fcntl(fd, F_SETFL, flags);
            }
            connected = fd;
            break;
        }
        close(fd);
    }

    freeaddrinfo(result);
    return connected;
}

bool send_all(int fd, const std::string& request) {
    const char* data = request.data();
    std::size_t remaining = request.size();
    while (remaining > 0) {
        const ssize_t sent = send(fd, data, remaining, MSG_NOSIGNAL);
        if (sent <= 0) {
            return false;
        }
        data += sent;
        remaining -= static_cast<std::size_t>(sent);
    }
    return true;
}

}  // namespace

bool hmi_telemetry_parse(HmiTelemetryEndpoint endpoint,
                         std::string_view json,
                         TelemetryCounters* counters) noexcept {
    if (counters == nullptr || json.empty()) {
        return false;
    }
    switch (endpoint) {
        case HmiTelemetryEndpoint::HgTelemetry:
            return parse_hg_telemetry(json, counters);
        case HmiTelemetryEndpoint::KhojStatus:
            return parse_khoj_status(json, counters);
        case HmiTelemetryEndpoint::MicroproxyStatus:
            return parse_microproxy_status(json, counters);
    }
    return false;
}

bool hmi_telemetry_http_get(const HmiTelemetrySource& source,
                            std::string_view path,
                            std::string* response) {
    if (response == nullptr || path.empty() || path.front() != '/') {
        return false;
    }
    response->clear();

    const int fd = connect_with_timeout(source);
    if (fd < 0) {
        return false;
    }

    timeval tv{};
    tv.tv_sec = static_cast<long>(source.timeout.count() / 1000);
    tv.tv_usec = static_cast<long>((source.timeout.count() % 1000) * 1000);
    (void)setsockopt(fd, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof(tv));
    (void)setsockopt(fd, SOL_SOCKET, SO_SNDTIMEO, &tv, sizeof(tv));

    std::ostringstream request;
    request << "GET " << path << " HTTP/1.1\r\n"
            << "Host: " << source.host << ':' << source.port << "\r\n"
            << "Accept: application/json\r\n"
            << "Connection: close\r\n\r\n";
    if (!send_all(fd, request.str())) {
        close(fd);
        return false;
    }

    char buffer[4096];
    bool ok = false;
    for (;;) {
        const ssize_t got = recv(fd, buffer, sizeof(buffer), 0);
        if (got > 0) {
            response->append(buffer, static_cast<std::size_t>(got));
            ok = true;
            continue;
        }
        break;
    }
    close(fd);
    if (!ok) {
        return false;
    }

    const std::size_t status_end = response->find("\r\n");
    if (status_end == std::string::npos ||
        response->compare(0, 9, "HTTP/1.1 ") != 0 ||
        response->compare(9, 3, "200") != 0) {
        return false;
    }
    const std::size_t body = response->find("\r\n\r\n");
    if (body == std::string::npos) {
        return false;
    }
    response->erase(0, body + 4);
    return true;
}

bool hmi_telemetry_poll_once(const HmiTelemetrySource& source,
                             TelemetryCounters* counters) {
    if (counters == nullptr) {
        return false;
    }

    TelemetryCounters next{};
    std::string body;
    bool ok = false;
    if (hmi_telemetry_http_get(source, kHgTelemetryPath, &body)) {
        const bool parsed = hmi_telemetry_parse(HmiTelemetryEndpoint::HgTelemetry, body, &next);
        if (parsed && next.proxy_online < 0.5F) {
            next.proxy_online = 1.0F;
        }
        ok = parsed || ok;
    }
    if (hmi_telemetry_http_get(source, kKhojStatusPath, &body)) {
        ok = hmi_telemetry_parse(HmiTelemetryEndpoint::KhojStatus, body, &next) || ok;
    }
    if (hmi_telemetry_http_get(source, kMicroproxyStatusPath, &body)) {
        ok = hmi_telemetry_parse(HmiTelemetryEndpoint::MicroproxyStatus, body, &next) || ok;
    }

    if (ok) {
        *counters = next;
    }
    return ok;
}

HmiTelemetryPoller::~HmiTelemetryPoller() {
    stop();
}

bool HmiTelemetryPoller::start(HmiTelemetrySource source,
                               std::chrono::milliseconds interval) {
    if (running_.exchange(true)) {
        return false;
    }
    thread_ = std::thread(&HmiTelemetryPoller::run, this, std::move(source), interval);
    return true;
}

void HmiTelemetryPoller::stop() noexcept {
    if (!running_.exchange(false)) {
        return;
    }
    if (thread_.joinable()) {
        thread_.join();
    }
}

TelemetryCounters HmiTelemetryPoller::snapshot() const noexcept {
    const unsigned int index = active_index_.load(std::memory_order_acquire) & 1U;
    return buffers_[index];
}

bool HmiTelemetryPoller::last_poll_ok() const noexcept {
    return last_ok_.load();
}

void HmiTelemetryPoller::run(HmiTelemetrySource source, std::chrono::milliseconds interval) {
    while (running_.load()) {
        TelemetryCounters next{};
        const bool ok = hmi_telemetry_poll_once(source, &next);
        if (ok) {
            const unsigned int current = active_index_.load(std::memory_order_relaxed) & 1U;
            const unsigned int write_index = current ^ 1U;
            buffers_[write_index] = next;
            active_index_.store(write_index, std::memory_order_release);
        }
        last_ok_.store(ok);
        std::this_thread::sleep_for(interval);
    }
}

}  // namespace hg::hmi
