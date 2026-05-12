#pragma once

#include "hmi_push.hpp"

#include <array>
#include <cstddef>
#include <cstdint>

namespace hg::hmi {

struct TelemetryCounters {
    float proxy_online;
    float total_requests;
    float latency_p95_ms;
    float cache_hits;
    float exact_response_cache_hits;
    float exact_response_cache_stores;
    float canonical_response_cache_hits;
    float canonical_response_cache_stores;
    float control_plane_cache_hits;
    float control_plane_cache_stores;
    float local_ack_telemetry;
    float local_ack_bytes_avoided;
    float upstream_inference_forwards;
    float upstream_inference_cache_misses;
    float upstream_inference_blocks;
    float tokens_saved;
    float binary_fail_open;
    float khoj_injections;
    float reasoning_injections;
    float swarm_triggers;
    float swarm_success;
    float swarm_failed;
    float swarm_denied;
    float swarm_avg_latency_ms;
    float microproxy_streams_open;
    float microproxy_streams_finished;
    float microproxy_quota_exhausted;
    float microproxy_connect_errors;
    float microproxy_upstream_errors;
    float route_hits;
    float status_2xx;
    float status_4xx;
    float status_5xx;
    float cuda_active;
    float openvino_active;
    float myriad_visible;
    float myriad_boot_failed;
};

struct HmiIngestState {
    HmiPush front;
    HmiPush back;
};

void hmi_ingest_init(HmiIngestState* state) noexcept;

void hmi_ingest_update(HmiIngestState* state,
                       const TelemetryCounters* counters,
                       float width,
                       float height,
                       float time_s) noexcept;

HmiPush hmi_ingest_snapshot(const HmiIngestState* state) noexcept;

}  // namespace hg::hmi
