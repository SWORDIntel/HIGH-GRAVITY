#pragma once

#include "hmi_push.hpp"

#include <cstdint>

#if defined(HIGHGRAVITY_HMI_ENABLE_VULKAN)
#include <vulkan/vulkan_core.h>
#endif

namespace hg::hmi {

constexpr std::uint32_t HMI_PUSH_STAGE_FRAGMENT_BIT = 0x00000010U;
constexpr std::uint32_t HMI_PUSH_OFFSET = 0;
constexpr std::uint32_t HMI_PUSH_SIZE = sizeof(HmiPush);

struct HmiPushConstantRange {
    std::uint32_t stage_flags;
    std::uint32_t offset;
    std::uint32_t size;
};

static_assert(HMI_PUSH_SIZE <= 128U, "Vulkan push constants must stay under 128 bytes");

constexpr HmiPushConstantRange hmi_push_constant_range() noexcept {
    return HmiPushConstantRange{HMI_PUSH_STAGE_FRAGMENT_BIT, HMI_PUSH_OFFSET, HMI_PUSH_SIZE};
}

#if defined(HIGHGRAVITY_HMI_ENABLE_VULKAN)
inline VkPushConstantRange hmi_vk_push_constant_range() noexcept {
    return VkPushConstantRange{VK_SHADER_STAGE_FRAGMENT_BIT, HMI_PUSH_OFFSET, HMI_PUSH_SIZE};
}

inline void hmi_cmd_push(VkCommandBuffer command_buffer,
                         VkPipelineLayout pipeline_layout,
                         const HmiPush& push) noexcept {
    vkCmdPushConstants(command_buffer,
                       pipeline_layout,
                       VK_SHADER_STAGE_FRAGMENT_BIT,
                       HMI_PUSH_OFFSET,
                       HMI_PUSH_SIZE,
                       &push);
}
#endif

}  // namespace hg::hmi
