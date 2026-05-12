#pragma once

#include <cstdint>

namespace hg::hmi {

struct HmiRunnerOptions {
    const char* shader_dir;
    std::uint32_t width;
    std::uint32_t height;
};

int hmi_run_xcb_vulkan(const HmiRunnerOptions& options);

}  // namespace hg::hmi
