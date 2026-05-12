#pragma once

#include <cstddef>
#include <cstdint>
#include <type_traits>

namespace hg::hmi {

struct alignas(16) HmiPush {
    float resolution_time_health[4];  // width, height, time_s, health_0_1
    float traffic[4];                 // request_rate, open_streams, route_hits, errors
    float stream[4];                  // finished, status_2xx, status_4xx, status_5xx
    float rag[4];                     // injections, cache_hits, tokens_saved_k, reasoning
    float accel[4];                   // cuda, openvino, myriad_visible, myriad_boot_failed
    float pulse[4];                   // animation phase, alert_level, binary_fail_open, reserved
};

static_assert(std::is_standard_layout<HmiPush>::value, "HmiPush must be standard layout");
static_assert(std::is_trivially_copyable<HmiPush>::value, "HmiPush must be trivially copyable");
static_assert(alignof(HmiPush) == 16, "HmiPush must keep std140-compatible 16-byte alignment");
static_assert(sizeof(HmiPush) == 96, "HmiPush layout changed; update shader push constants");
static_assert(sizeof(HmiPush) <= 128, "Vulkan push constants must stay under 128 bytes");
static_assert(offsetof(HmiPush, resolution_time_health) == 0, "unexpected push offset");
static_assert(offsetof(HmiPush, traffic) == 16, "unexpected push offset");
static_assert(offsetof(HmiPush, stream) == 32, "unexpected push offset");
static_assert(offsetof(HmiPush, rag) == 48, "unexpected push offset");
static_assert(offsetof(HmiPush, accel) == 64, "unexpected push offset");
static_assert(offsetof(HmiPush, pulse) == 80, "unexpected push offset");

struct alignas(16) HmiSnapshot {
    HmiPush push;
    std::uint32_t schema_version;
    std::uint32_t source_mask;
    std::uint32_t reserved0;
    std::uint32_t reserved1;
};

static_assert(alignof(HmiSnapshot) == 16, "snapshot must preserve 16-byte alignment");
static_assert(sizeof(HmiSnapshot) == 112, "snapshot layout changed");

}  // namespace hg::hmi
