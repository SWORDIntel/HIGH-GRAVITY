#include "hmi_ingest.hpp"
#include "hmi_telemetry.hpp"

#include <cmath>
#include <cstdio>

namespace {

bool near(float lhs, float rhs) {
    return std::fabs(lhs - rhs) < 0.001F;
}

}  // namespace

int main() {
    hg::hmi::TelemetryCounters counters{};

    const char* telemetry = R"json({
        "total_requests": 42,
        "cache_hits": 7,
        "tokens_saved": 12000,
        "enabled": true,
        "latency_ms": {"p50": 20.5, "p95": 175.25, "p99": 250.0},
        "khoj": {
            "injection_count": 5,
            "search_cache_hits": 11,
            "binary_tokens_avoided": 6000
        },
        "shared_metrics": {
            "binary_fail_open": 2,
            "exact_response_cache_hits": 6,
            "exact_response_cache_stores": 12,
            "canonical_response_cache_hits": 4,
            "canonical_response_cache_stores": 8,
            "control_plane_cache_hits": 7,
            "control_plane_cache_stores": 14,
            "local_ack_telemetry": 9,
            "local_ack_bytes_avoided": 2048,
            "upstream_inference_forwards": 5,
            "upstream_inference_cache_misses": 7,
            "upstream_inference_blocks": 2,
            "upstream_inference_cache_only_blocks": 1,
            "mitm_reasoning_injections": 9,
            "pegasus_swarm_triggers": 3,
            "pegasus_swarm_success": 2,
            "pegasus_swarm_fail": 1,
            "pegasus_swarm_denied": 0,
            "khoj_binary_injections": 6,
            "khoj_search_cache_hits": 10,
            "khoj_tokens_avoided": 15000
        },
        "pegasus_swarm": {
            "attempts": 4,
            "success": 3,
            "failed": 1,
            "denied": 0,
            "avg_latency_ms": 125.5
        }
    })json";

    const char* khoj = R"json({
        "injection_count": 8,
        "binary_injection_count": 12,
        "search_cache_hits": 13,
        "binary_tokens_avoided": 18000,
        "shared_metrics": {"mitm_reasoning_injections": 14, "pegasus_swarm_triggers": 4, "pegasus_swarm_success": 3},
        "acceleration": {
            "runtime_active": {
                "cuda": true,
                "openvino": true,
                "myriad_visible": true,
                "myriad_boot_failed": false
            }
        }
    })json";

    const char* microproxy = R"json({
        "routes": {"total": 23, "routes": {"passthrough": 23}},
        "streams": {
            "streams_started": 6,
            "streams_finished": 4,
            "streams_open": 2,
            "quota_exhausted_signals": 1,
            "connect_error_signals": 2,
            "status_codes": {"200": 3, "204": 1, "404": 2, "502": 1}
        },
        "upstream_errors": {"total": 3}
    })json";

    const bool ok =
        hg::hmi::hmi_telemetry_parse(hg::hmi::HmiTelemetryEndpoint::HgTelemetry, telemetry, &counters) &&
        hg::hmi::hmi_telemetry_parse(hg::hmi::HmiTelemetryEndpoint::KhojStatus, khoj, &counters) &&
        hg::hmi::hmi_telemetry_parse(hg::hmi::HmiTelemetryEndpoint::MicroproxyStatus, microproxy, &counters);

    hg::hmi::HmiIngestState state{};
    hg::hmi::hmi_ingest_init(&state);
    hg::hmi::hmi_ingest_update(&state, &counters, 1280.0F, 720.0F, 2.0F);
    const hg::hmi::HmiPush push = hg::hmi::hmi_ingest_snapshot(&state);

    const bool mapped = ok &&
                        near(counters.total_requests, 42.0F) &&
                        near(counters.proxy_online, 1.0F) &&
                        near(counters.latency_p95_ms, 175.25F) &&
                        near(counters.cache_hits, 13.0F) &&
                        near(counters.exact_response_cache_hits, 6.0F) &&
                        near(counters.exact_response_cache_stores, 12.0F) &&
                        near(counters.canonical_response_cache_hits, 4.0F) &&
                        near(counters.canonical_response_cache_stores, 8.0F) &&
                        near(counters.control_plane_cache_hits, 7.0F) &&
                        near(counters.control_plane_cache_stores, 14.0F) &&
                        near(counters.local_ack_telemetry, 9.0F) &&
                        near(counters.local_ack_bytes_avoided, 2048.0F) &&
                        near(counters.upstream_inference_forwards, 5.0F) &&
                        near(counters.upstream_inference_cache_misses, 7.0F) &&
                        near(counters.upstream_inference_blocks, 3.0F) &&
                        near(counters.tokens_saved, 18000.0F) &&
                        near(counters.binary_fail_open, 2.0F) &&
                        near(counters.khoj_injections, 12.0F) &&
                        near(counters.reasoning_injections, 14.0F) &&
                        near(counters.swarm_triggers, 4.0F) &&
                        near(counters.swarm_success, 3.0F) &&
                        near(counters.swarm_failed, 1.0F) &&
                        near(counters.swarm_denied, 0.0F) &&
                        near(counters.swarm_avg_latency_ms, 125.5F) &&
                        near(counters.microproxy_streams_open, 2.0F) &&
                        near(counters.microproxy_streams_finished, 4.0F) &&
                        near(counters.microproxy_quota_exhausted, 1.0F) &&
                        near(counters.microproxy_connect_errors, 2.0F) &&
                        near(counters.microproxy_upstream_errors, 3.0F) &&
                        near(counters.route_hits, 23.0F) &&
                        near(counters.status_2xx, 4.0F) &&
                        near(counters.cuda_active, 1.0F) &&
                        near(counters.openvino_active, 1.0F) &&
                        near(counters.myriad_visible, 1.0F) &&
                        near(counters.myriad_boot_failed, 0.0F) &&
                        near(push.rag[0], 12.0F) &&
                        near(push.rag[2], 18.0F) &&
                        near(push.stream[1], 4.0F) &&
                        near(push.stream[2], 1.0F) &&
                        near(push.stream[3], 5.0F) &&
                        near(push.rag[1], 23.0F) &&
                        near(push.rag[3], 17.0F) &&
                        near(push.accel[2], 1.0F);

    std::printf("hmi_telemetry_parse=%s requests=%.0f p95=%.2f status_2xx=%.0f route_hits=%.0f response_cache=%.0f/%.0f gate=%.0f/%.0f/%.0f local_ack=%.0f/%.0f\n",
                mapped ? "ok" : "fail",
                counters.total_requests,
                counters.latency_p95_ms,
                counters.status_2xx,
                counters.route_hits,
                counters.exact_response_cache_hits + counters.canonical_response_cache_hits,
                counters.exact_response_cache_stores + counters.canonical_response_cache_stores,
                counters.upstream_inference_forwards,
                counters.upstream_inference_cache_misses,
                counters.upstream_inference_blocks,
                counters.local_ack_telemetry,
                counters.local_ack_bytes_avoided);

    return mapped ? 0 : 1;
}
