#pragma once

#include "hmi_ingest.hpp"

#include <atomic>
#include <chrono>
#include <cstdint>
#include <array>
#include <string>
#include <string_view>
#include <thread>

namespace hg::hmi {

enum class HmiTelemetryEndpoint : std::uint8_t {
    HgTelemetry,
    KhojStatus,
    MicroproxyStatus,
};

struct HmiTelemetrySource {
    std::string host{"127.0.0.1"};
    std::uint16_t port{9998};
    std::chrono::milliseconds timeout{750};
};

bool hmi_telemetry_parse(HmiTelemetryEndpoint endpoint,
                         std::string_view json,
                         TelemetryCounters* counters) noexcept;

bool hmi_telemetry_http_get(const HmiTelemetrySource& source,
                            std::string_view path,
                            std::string* response);

bool hmi_telemetry_poll_once(const HmiTelemetrySource& source,
                             TelemetryCounters* counters);

class HmiTelemetryPoller {
public:
    HmiTelemetryPoller() = default;
    HmiTelemetryPoller(const HmiTelemetryPoller&) = delete;
    HmiTelemetryPoller& operator=(const HmiTelemetryPoller&) = delete;
    ~HmiTelemetryPoller();

    bool start(HmiTelemetrySource source,
               std::chrono::milliseconds interval = std::chrono::milliseconds(1000));
    void stop() noexcept;
    TelemetryCounters snapshot() const noexcept;
    bool last_poll_ok() const noexcept;

private:
    void run(HmiTelemetrySource source, std::chrono::milliseconds interval);

    std::array<TelemetryCounters, 2> buffers_{};
    std::atomic<unsigned int> active_index_{0U};
    std::thread thread_;
    std::atomic<bool> running_{false};
    std::atomic<bool> last_ok_{false};
};

}  // namespace hg::hmi
