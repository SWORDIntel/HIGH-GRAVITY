#include "hmi_ingest.hpp"

#include <algorithm>
#include <cstring>

namespace hg::hmi {

namespace {

float clamp01(float value) noexcept {
    return std::max(0.0F, std::min(1.0F, value));
}

float safe_ratio(float numerator, float denominator) noexcept {
    if (denominator <= 0.0F) {
        return 0.0F;
    }
    return clamp01(numerator / denominator);
}

}  // namespace

void hmi_ingest_init(HmiIngestState* state) noexcept {
    if (state == nullptr) {
        return;
    }
    std::memset(state, 0, sizeof(*state));
}

void hmi_ingest_update(HmiIngestState* state,
                       const TelemetryCounters* counters,
                       float width,
                       float height,
                       float time_s) noexcept {
    if (state == nullptr || counters == nullptr) {
        return;
    }

    const float request_load = safe_ratio(counters->latency_p95_ms, 3000.0F);
    const float error_load = safe_ratio(
        counters->microproxy_upstream_errors + counters->microproxy_connect_errors +
            counters->microproxy_quota_exhausted + counters->status_5xx,
        std::max(
            1.0F,
            counters->microproxy_streams_finished + counters->microproxy_upstream_errors +
                counters->microproxy_connect_errors + counters->microproxy_quota_exhausted));
    const float proxy_health = counters->proxy_online >= 0.5F ? 1.0F : 0.0F;
    const float health = proxy_health * clamp01(1.0F - (request_load * 0.45F) - (error_load * 0.55F));
    const float alert = clamp01((1.0F - health) + safe_ratio(counters->binary_fail_open, 8.0F));
    const float swarm_failures = counters->swarm_failed + counters->swarm_denied;
    const float response_cache_hits = counters->exact_response_cache_hits + counters->canonical_response_cache_hits;
    const float response_cache_stores = counters->exact_response_cache_stores + counters->canonical_response_cache_stores;
    const float response_cache_ratio = safe_ratio(response_cache_hits, response_cache_stores);
    const float upstream_block_ratio = safe_ratio(
        counters->upstream_inference_blocks,
        counters->upstream_inference_cache_misses + counters->upstream_inference_blocks);
    const float local_ack_pressure = clamp01(
        safe_ratio(counters->local_ack_telemetry, 256.0F) +
        safe_ratio(counters->local_ack_bytes_avoided, 1024.0F * 1024.0F));
    const float usage_reduction = std::max(
        std::max(response_cache_ratio, upstream_block_ratio),
        std::max(
            safe_ratio(counters->control_plane_cache_hits, counters->control_plane_cache_stores),
            local_ack_pressure));

    HmiPush next{};
    next.resolution_time_health[0] = width;
    next.resolution_time_health[1] = height;
    next.resolution_time_health[2] = time_s;
    next.resolution_time_health[3] = health;

    next.traffic[0] = counters->total_requests;
    next.traffic[1] = counters->microproxy_streams_open;
    next.traffic[2] = counters->route_hits;
    next.traffic[3] = counters->microproxy_upstream_errors + counters->upstream_inference_forwards;

    next.stream[0] = counters->microproxy_streams_finished;
    next.stream[1] = counters->status_2xx;
    next.stream[2] = counters->microproxy_quota_exhausted;
    next.stream[3] = counters->microproxy_connect_errors + counters->upstream_inference_blocks;

    next.rag[0] = counters->khoj_injections;
    next.rag[1] = counters->cache_hits + response_cache_hits;
    next.rag[2] = counters->tokens_saved / 1000.0F;
    next.rag[3] = counters->reasoning_injections + counters->swarm_success;

    next.accel[0] = counters->cuda_active;
    next.accel[1] = counters->openvino_active;
    next.accel[2] = counters->myriad_visible;
    next.accel[3] = counters->myriad_boot_failed;

    next.pulse[0] = time_s;
    next.pulse[1] = alert;
    next.pulse[2] = counters->binary_fail_open + swarm_failures;
    next.pulse[3] = std::max(
        usage_reduction,
        clamp01(1.0F - safe_ratio(counters->swarm_avg_latency_ms, 3000.0F))
    );

    state->back = next;
    state->front = state->back;
}

HmiPush hmi_ingest_snapshot(const HmiIngestState* state) noexcept {
    if (state == nullptr) {
        return HmiPush{};
    }
    return state->front;
}

}  // namespace hg::hmi
