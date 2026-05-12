#include "hmi_ingest.hpp"
#include "hmi_vulkan_ingest.hpp"

#include <cstdio>

int main() {
    hg::hmi::HmiIngestState state{};
    hg::hmi::hmi_ingest_init(&state);

    hg::hmi::TelemetryCounters counters{};
    counters.proxy_online = 1.0F;
    counters.total_requests = 512.0F;
    counters.latency_p95_ms = 180.0F;
    counters.cache_hits = 154.0F;
    counters.tokens_saved = 42420.0F;
    counters.khoj_injections = 84.0F;
    counters.reasoning_injections = 115.0F;
    counters.microproxy_streams_open = 1.0F;
    counters.microproxy_streams_finished = 4.0F;
    counters.route_hits = 4.0F;
    counters.status_2xx = 4.0F;
    counters.cuda_active = 1.0F;
    counters.openvino_active = 1.0F;
    counters.myriad_visible = 1.0F;
    counters.myriad_boot_failed = 1.0F;

    hg::hmi::hmi_ingest_update(&state, &counters, 1920.0F, 1080.0F, 1.25F);
    const hg::hmi::HmiPush push = hg::hmi::hmi_ingest_snapshot(&state);
    const auto range = hg::hmi::hmi_push_constant_range();

    const bool ok = range.stage_flags == hg::hmi::HMI_PUSH_STAGE_FRAGMENT_BIT &&
                    range.offset == 0 &&
                    range.size == sizeof(hg::hmi::HmiPush) &&
                    push.resolution_time_health[0] == 1920.0F &&
                    push.resolution_time_health[1] == 1080.0F &&
                    push.accel[3] == 1.0F;

    std::printf("hmi_push_size=%zu align=%zu range_size=%u health=%.3f\n",
                sizeof(hg::hmi::HmiPush),
                alignof(hg::hmi::HmiPush),
                range.size,
                push.resolution_time_health[3]);

    return ok ? 0 : 1;
}
