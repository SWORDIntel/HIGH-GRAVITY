#if defined(HG_HMI_RUNNER_ENABLE_NATIVE)
#define HIGHGRAVITY_HMI_ENABLE_VULKAN
#endif

#include "hmi_ingest.hpp"
#include "hmi_runner.hpp"
#include "hmi_telemetry.hpp"
#include "hmi_vulkan_ingest.hpp"

#include <algorithm>
#include <chrono>
#include <cstdint>
#include <cstdlib>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <stdexcept>
#include <string>
#include <thread>
#include <vector>

#if defined(HG_HMI_RUNNER_ENABLE_NATIVE)
#define VK_USE_PLATFORM_XCB_KHR
#include <vulkan/vulkan.h>
#include <xcb/xcb.h>
#endif

namespace hg::hmi {

namespace {

constexpr std::uint32_t kDefaultWidth = 1280U;
constexpr std::uint32_t kDefaultHeight = 720U;

#if defined(HG_HMI_RUNNER_ENABLE_NATIVE)

std::string join_path(const std::string& left, const char* right) {
    if (left.empty()) {
        return right;
    }
    if (left[left.size() - 1U] == '/') {
        return left + right;
    }
    return left + "/" + right;
}

std::vector<char> read_file(const std::string& path) {
    std::ifstream file(path, std::ios::ate | std::ios::binary);
    if (!file) {
        throw std::runtime_error("failed to open shader file: " + path);
    }
    const std::streamsize size = file.tellg();
    if (size <= 0 || (size % 4) != 0) {
        throw std::runtime_error("invalid SPIR-V file size: " + path);
    }
    std::vector<char> bytes(static_cast<std::size_t>(size));
    file.seekg(0);
    file.read(bytes.data(), size);
    if (!file) {
        throw std::runtime_error("failed to read shader file: " + path);
    }
    return bytes;
}

std::string default_shader_dir(const HmiRunnerOptions& options) {
    if (options.shader_dir != nullptr && options.shader_dir[0] != '\0') {
        return options.shader_dir;
    }
    const char* env_dir = std::getenv("HIGHGRAVITY_HMI_SHADER_DIR");
    if (env_dir != nullptr && env_dir[0] != '\0') {
        return env_dir;
    }
    return "src/hmi/build/shaders";
}

float elapsed_seconds(std::chrono::steady_clock::time_point start) {
    const auto now = std::chrono::steady_clock::now();
    const auto elapsed = std::chrono::duration_cast<std::chrono::duration<float>>(now - start);
    return elapsed.count();
}

std::uint16_t env_port_or_default(const char* name, std::uint16_t fallback) {
    const char* raw = std::getenv(name);
    if (raw == nullptr || raw[0] == '\0') {
        return fallback;
    }
    char* end = nullptr;
    const unsigned long parsed = std::strtoul(raw, &end, 10);
    if (end == raw || *end != '\0' || parsed == 0UL || parsed > 65535UL) {
        return fallback;
    }
    return static_cast<std::uint16_t>(parsed);
}

HmiTelemetrySource telemetry_source_from_env() {
    HmiTelemetrySource source{};
    const char* host = std::getenv("HG_HMI_TELEMETRY_HOST");
    if (host != nullptr && host[0] != '\0') {
        source.host = host;
    } else if (const char* proxy_host = std::getenv("HG_PROXY_HOST");
               proxy_host != nullptr && proxy_host[0] != '\0') {
        source.host = proxy_host;
    }
    source.port = env_port_or_default("HG_HMI_TELEMETRY_PORT",
                                      env_port_or_default("PROXY_PORT", source.port));
    return source;
}

constexpr std::uint32_t kFramesInFlight = 2U;

void vk_check(VkResult result, const char* operation) {
    if (result != VK_SUCCESS) {
        const char* hint =
            result == VK_ERROR_INCOMPATIBLE_DRIVER
                ? " (no compatible Vulkan driver/runtime was reported by the loader)"
                : "";
        throw std::runtime_error(std::string(operation) + " failed with VkResult " +
                                 std::to_string(static_cast<int>(result)) + hint);
    }
}

struct QueueFamilySelection {
    std::uint32_t graphics_present;
};

struct SwapchainSupport {
    VkSurfaceCapabilitiesKHR capabilities{};
    std::vector<VkSurfaceFormatKHR> formats;
    std::vector<VkPresentModeKHR> present_modes;
};

class VulkanXcbRunner {
public:
    explicit VulkanXcbRunner(const HmiRunnerOptions& runner_options)
        : shader_dir_(default_shader_dir(runner_options)),
          requested_width_(runner_options.width == 0U ? kDefaultWidth : runner_options.width),
          requested_height_(runner_options.height == 0U ? kDefaultHeight : runner_options.height) {}

    VulkanXcbRunner(const VulkanXcbRunner&) = delete;
    VulkanXcbRunner& operator=(const VulkanXcbRunner&) = delete;

    ~VulkanXcbRunner() {
        cleanup();
    }

    int run() {
        load_shaders();
        init_window();
        init_vulkan();

        HmiIngestState ingest{};
        hmi_ingest_init(&ingest);
        HmiTelemetryPoller telemetry;
        const HmiTelemetrySource telemetry_source = telemetry_source_from_env();
        (void)telemetry.start(telemetry_source, std::chrono::milliseconds(1000));
        const auto start = std::chrono::steady_clock::now();

        while (!should_close_) {
            poll_events();

            const float now = elapsed_seconds(start);
            TelemetryCounters counters = telemetry.last_poll_ok() ? telemetry.snapshot() : TelemetryCounters{};
            counters.proxy_online = telemetry.last_poll_ok() ? 1.0F : 0.0F;

            hmi_ingest_update(&ingest,
                              &counters,
                              static_cast<float>(extent_.width),
                              static_cast<float>(extent_.height),
                              now);
            draw_frame(hmi_ingest_snapshot(&ingest));
        }

        vkDeviceWaitIdle(device_);
        telemetry.stop();
        return 0;
    }

private:
    void load_shaders() {
        vert_spv_ = read_file(join_path(shader_dir_, "dashboard.vert.spv"));
        frag_spv_ = read_file(join_path(shader_dir_, "dashboard.frag.spv"));
    }

    void init_window() {
        int screen_index = 0;
        connection_ = xcb_connect(nullptr, &screen_index);
        if (connection_ == nullptr || xcb_connection_has_error(connection_) != 0) {
            throw std::runtime_error("failed to connect to XCB display");
        }

        const xcb_setup_t* setup = xcb_get_setup(connection_);
        xcb_screen_iterator_t iter = xcb_setup_roots_iterator(setup);
        for (int i = 0; i < screen_index && iter.rem != 0; ++i) {
            xcb_screen_next(&iter);
        }
        if (iter.rem == 0) {
            throw std::runtime_error("failed to resolve XCB screen");
        }
        screen_ = iter.data;
        width_ = screen_->width_in_pixels == 0U ? requested_width_ : screen_->width_in_pixels;
        height_ = screen_->height_in_pixels == 0U ? requested_height_ : screen_->height_in_pixels;

        window_ = xcb_generate_id(connection_);
        const std::uint32_t values[] = {
            screen_->black_pixel,
            XCB_EVENT_MASK_EXPOSURE | XCB_EVENT_MASK_STRUCTURE_NOTIFY | XCB_EVENT_MASK_KEY_PRESS};
        xcb_create_window(connection_,
                          XCB_COPY_FROM_PARENT,
                          window_,
                          screen_->root,
                          0,
                          0,
                          static_cast<std::uint16_t>(width_),
                          static_cast<std::uint16_t>(height_),
                          0,
                          XCB_WINDOW_CLASS_INPUT_OUTPUT,
                          screen_->root_visual,
                          XCB_CW_BACK_PIXEL | XCB_CW_EVENT_MASK,
                          values);

        wm_protocols_ = intern_atom("WM_PROTOCOLS");
        wm_delete_window_ = intern_atom("WM_DELETE_WINDOW");
        xcb_change_property(connection_,
                            XCB_PROP_MODE_REPLACE,
                            window_,
                            wm_protocols_,
                            XCB_ATOM_ATOM,
                            32,
                            1,
                            &wm_delete_window_);

        set_fullscreen_hint();
        xcb_map_window(connection_, window_);
        xcb_flush(connection_);
    }

    xcb_atom_t intern_atom(const char* name) {
        xcb_intern_atom_cookie_t cookie =
            xcb_intern_atom(connection_, 0, static_cast<std::uint16_t>(std::strlen(name)), name);
        xcb_intern_atom_reply_t* reply = xcb_intern_atom_reply(connection_, cookie, nullptr);
        if (reply == nullptr) {
            return XCB_ATOM_NONE;
        }
        const xcb_atom_t atom = reply->atom;
        std::free(reply);
        return atom;
    }

    void set_fullscreen_hint() {
        const xcb_atom_t wm_state = intern_atom("_NET_WM_STATE");
        const xcb_atom_t fullscreen = intern_atom("_NET_WM_STATE_FULLSCREEN");
        if (wm_state == XCB_ATOM_NONE || fullscreen == XCB_ATOM_NONE) {
            return;
        }
        xcb_change_property(connection_,
                            XCB_PROP_MODE_REPLACE,
                            window_,
                            wm_state,
                            XCB_ATOM_ATOM,
                            32,
                            1,
                            &fullscreen);
    }

    void init_vulkan() {
        create_instance();
        create_surface();
        pick_physical_device();
        create_device();
        create_swapchain();
        create_image_views();
        create_render_pass();
        create_pipeline();
        create_framebuffers();
        create_command_pool();
        create_sync_objects();
    }

    void create_instance() {
        const VkApplicationInfo app_info{
            VK_STRUCTURE_TYPE_APPLICATION_INFO,
            nullptr,
            "HIGH-GRAVITY HMI",
            VK_MAKE_VERSION(0, 1, 0),
            "HIGH-GRAVITY",
            VK_MAKE_VERSION(0, 1, 0),
            VK_API_VERSION_1_0};
        const char* extensions[] = {VK_KHR_SURFACE_EXTENSION_NAME, VK_KHR_XCB_SURFACE_EXTENSION_NAME};
        const VkInstanceCreateInfo create_info{
            VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO,
            nullptr,
            0,
            &app_info,
            0,
            nullptr,
            2,
            extensions};
        vk_check(vkCreateInstance(&create_info, nullptr, &instance_), "vkCreateInstance");
    }

    void create_surface() {
        const VkXcbSurfaceCreateInfoKHR create_info{
            VK_STRUCTURE_TYPE_XCB_SURFACE_CREATE_INFO_KHR,
            nullptr,
            0,
            connection_,
            window_};
        vk_check(vkCreateXcbSurfaceKHR(instance_, &create_info, nullptr, &surface_),
                 "vkCreateXcbSurfaceKHR");
    }

    void pick_physical_device() {
        std::uint32_t count = 0;
        vk_check(vkEnumeratePhysicalDevices(instance_, &count, nullptr), "vkEnumeratePhysicalDevices");
        if (count == 0U) {
            throw std::runtime_error("no Vulkan physical devices available");
        }
        std::vector<VkPhysicalDevice> devices(count);
        vk_check(vkEnumeratePhysicalDevices(instance_, &count, devices.data()),
                 "vkEnumeratePhysicalDevices");
        for (VkPhysicalDevice candidate : devices) {
            if (try_select_queue(candidate, &queue_family_)) {
                physical_device_ = candidate;
                return;
            }
        }
        throw std::runtime_error("no Vulkan device supports graphics and XCB present");
    }

    bool try_select_queue(VkPhysicalDevice candidate, QueueFamilySelection* selected) const {
        std::uint32_t count = 0;
        vkGetPhysicalDeviceQueueFamilyProperties(candidate, &count, nullptr);
        std::vector<VkQueueFamilyProperties> families(count);
        vkGetPhysicalDeviceQueueFamilyProperties(candidate, &count, families.data());
        for (std::uint32_t i = 0; i < count; ++i) {
            VkBool32 present = VK_FALSE;
            vkGetPhysicalDeviceSurfaceSupportKHR(candidate, i, surface_, &present);
            if ((families[i].queueFlags & VK_QUEUE_GRAPHICS_BIT) != 0U && present == VK_TRUE) {
                selected->graphics_present = i;
                return true;
            }
        }
        return false;
    }

    void create_device() {
        const float priority = 1.0F;
        const VkDeviceQueueCreateInfo queue_info{
            VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO,
            nullptr,
            0,
            queue_family_.graphics_present,
            1,
            &priority};
        const char* extensions[] = {VK_KHR_SWAPCHAIN_EXTENSION_NAME};
        const VkDeviceCreateInfo create_info{
            VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO,
            nullptr,
            0,
            1,
            &queue_info,
            0,
            nullptr,
            1,
            extensions,
            nullptr};
        vk_check(vkCreateDevice(physical_device_, &create_info, nullptr, &device_), "vkCreateDevice");
        vkGetDeviceQueue(device_, queue_family_.graphics_present, 0, &queue_);
    }

    SwapchainSupport query_swapchain_support() const {
        SwapchainSupport support{};
        vk_check(vkGetPhysicalDeviceSurfaceCapabilitiesKHR(physical_device_,
                                                           surface_,
                                                           &support.capabilities),
                 "vkGetPhysicalDeviceSurfaceCapabilitiesKHR");
        std::uint32_t format_count = 0;
        vk_check(vkGetPhysicalDeviceSurfaceFormatsKHR(physical_device_, surface_, &format_count, nullptr),
                 "vkGetPhysicalDeviceSurfaceFormatsKHR");
        support.formats.resize(format_count);
        if (format_count != 0U) {
            vk_check(vkGetPhysicalDeviceSurfaceFormatsKHR(physical_device_,
                                                          surface_,
                                                          &format_count,
                                                          support.formats.data()),
                     "vkGetPhysicalDeviceSurfaceFormatsKHR");
        }
        std::uint32_t present_count = 0;
        vk_check(vkGetPhysicalDeviceSurfacePresentModesKHR(physical_device_,
                                                           surface_,
                                                           &present_count,
                                                           nullptr),
                 "vkGetPhysicalDeviceSurfacePresentModesKHR");
        support.present_modes.resize(present_count);
        if (present_count != 0U) {
            vk_check(vkGetPhysicalDeviceSurfacePresentModesKHR(physical_device_,
                                                               surface_,
                                                               &present_count,
                                                               support.present_modes.data()),
                     "vkGetPhysicalDeviceSurfacePresentModesKHR");
        }
        return support;
    }

    void create_swapchain() {
        const SwapchainSupport support = query_swapchain_support();
        if (support.formats.empty() || support.present_modes.empty()) {
            throw std::runtime_error("incomplete Vulkan swapchain support");
        }

        surface_format_ = choose_surface_format(support.formats);
        present_mode_ = choose_present_mode(support.present_modes);
        extent_ = choose_extent(support.capabilities);

        std::uint32_t image_count = support.capabilities.minImageCount + 1U;
        if (support.capabilities.maxImageCount > 0U && image_count > support.capabilities.maxImageCount) {
            image_count = support.capabilities.maxImageCount;
        }

        const VkSwapchainCreateInfoKHR create_info{
            VK_STRUCTURE_TYPE_SWAPCHAIN_CREATE_INFO_KHR,
            nullptr,
            0,
            surface_,
            image_count,
            surface_format_.format,
            surface_format_.colorSpace,
            extent_,
            1,
            VK_IMAGE_USAGE_COLOR_ATTACHMENT_BIT,
            VK_SHARING_MODE_EXCLUSIVE,
            0,
            nullptr,
            support.capabilities.currentTransform,
            VK_COMPOSITE_ALPHA_OPAQUE_BIT_KHR,
            present_mode_,
            VK_TRUE,
            VK_NULL_HANDLE};
        vk_check(vkCreateSwapchainKHR(device_, &create_info, nullptr, &swapchain_),
                 "vkCreateSwapchainKHR");

        std::uint32_t actual_count = 0;
        vk_check(vkGetSwapchainImagesKHR(device_, swapchain_, &actual_count, nullptr),
                 "vkGetSwapchainImagesKHR");
        swapchain_images_.resize(actual_count);
        vk_check(vkGetSwapchainImagesKHR(device_, swapchain_, &actual_count, swapchain_images_.data()),
                 "vkGetSwapchainImagesKHR");
    }

    static VkSurfaceFormatKHR choose_surface_format(const std::vector<VkSurfaceFormatKHR>& formats) {
        for (const VkSurfaceFormatKHR& format : formats) {
            if (format.format == VK_FORMAT_B8G8R8A8_SRGB &&
                format.colorSpace == VK_COLOR_SPACE_SRGB_NONLINEAR_KHR) {
                return format;
            }
        }
        return formats[0];
    }

    static VkPresentModeKHR choose_present_mode(const std::vector<VkPresentModeKHR>& modes) {
        for (VkPresentModeKHR mode : modes) {
            if (mode == VK_PRESENT_MODE_MAILBOX_KHR) {
                return mode;
            }
        }
        return VK_PRESENT_MODE_FIFO_KHR;
    }

    VkExtent2D choose_extent(const VkSurfaceCapabilitiesKHR& capabilities) const {
        if (capabilities.currentExtent.width != UINT32_MAX) {
            return capabilities.currentExtent;
        }
        VkExtent2D extent{width_, height_};
        extent.width = std::max(capabilities.minImageExtent.width,
                                std::min(capabilities.maxImageExtent.width, extent.width));
        extent.height = std::max(capabilities.minImageExtent.height,
                                 std::min(capabilities.maxImageExtent.height, extent.height));
        return extent;
    }

    void create_image_views() {
        image_views_.resize(swapchain_images_.size());
        for (std::size_t i = 0; i < swapchain_images_.size(); ++i) {
            const VkImageViewCreateInfo create_info{
                VK_STRUCTURE_TYPE_IMAGE_VIEW_CREATE_INFO,
                nullptr,
                0,
                swapchain_images_[i],
                VK_IMAGE_VIEW_TYPE_2D,
                surface_format_.format,
                {VK_COMPONENT_SWIZZLE_IDENTITY,
                 VK_COMPONENT_SWIZZLE_IDENTITY,
                 VK_COMPONENT_SWIZZLE_IDENTITY,
                 VK_COMPONENT_SWIZZLE_IDENTITY},
                {VK_IMAGE_ASPECT_COLOR_BIT, 0, 1, 0, 1}};
            vk_check(vkCreateImageView(device_, &create_info, nullptr, &image_views_[i]),
                     "vkCreateImageView");
        }
    }

    void create_render_pass() {
        const VkAttachmentDescription color_attachment{
            0,
            surface_format_.format,
            VK_SAMPLE_COUNT_1_BIT,
            VK_ATTACHMENT_LOAD_OP_CLEAR,
            VK_ATTACHMENT_STORE_OP_STORE,
            VK_ATTACHMENT_LOAD_OP_DONT_CARE,
            VK_ATTACHMENT_STORE_OP_DONT_CARE,
            VK_IMAGE_LAYOUT_UNDEFINED,
            VK_IMAGE_LAYOUT_PRESENT_SRC_KHR};
        const VkAttachmentReference color_ref{0, VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL};
        const VkSubpassDescription subpass{
            0,
            VK_PIPELINE_BIND_POINT_GRAPHICS,
            0,
            nullptr,
            1,
            &color_ref,
            nullptr,
            nullptr,
            0,
            nullptr};
        const VkSubpassDependency dependency{
            VK_SUBPASS_EXTERNAL,
            0,
            VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT,
            VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT,
            0,
            VK_ACCESS_COLOR_ATTACHMENT_WRITE_BIT,
            0};
        const VkRenderPassCreateInfo create_info{
            VK_STRUCTURE_TYPE_RENDER_PASS_CREATE_INFO,
            nullptr,
            0,
            1,
            &color_attachment,
            1,
            &subpass,
            1,
            &dependency};
        vk_check(vkCreateRenderPass(device_, &create_info, nullptr, &render_pass_), "vkCreateRenderPass");
    }

    VkShaderModule create_shader_module(const std::vector<char>& bytes) const {
        const VkShaderModuleCreateInfo create_info{
            VK_STRUCTURE_TYPE_SHADER_MODULE_CREATE_INFO,
            nullptr,
            0,
            bytes.size(),
            reinterpret_cast<const std::uint32_t*>(bytes.data())};
        VkShaderModule module = VK_NULL_HANDLE;
        vk_check(vkCreateShaderModule(device_, &create_info, nullptr, &module), "vkCreateShaderModule");
        return module;
    }

    void create_pipeline() {
        VkShaderModule vert = create_shader_module(vert_spv_);
        VkShaderModule frag = create_shader_module(frag_spv_);

        const VkPipelineShaderStageCreateInfo stages[] = {
            {VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO,
             nullptr,
             0,
             VK_SHADER_STAGE_VERTEX_BIT,
             vert,
             "main",
             nullptr},
            {VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO,
             nullptr,
             0,
             VK_SHADER_STAGE_FRAGMENT_BIT,
             frag,
             "main",
             nullptr}};

        const VkPipelineVertexInputStateCreateInfo vertex_input{
            VK_STRUCTURE_TYPE_PIPELINE_VERTEX_INPUT_STATE_CREATE_INFO,
            nullptr,
            0,
            0,
            nullptr,
            0,
            nullptr};
        const VkPipelineInputAssemblyStateCreateInfo input_assembly{
            VK_STRUCTURE_TYPE_PIPELINE_INPUT_ASSEMBLY_STATE_CREATE_INFO,
            nullptr,
            0,
            VK_PRIMITIVE_TOPOLOGY_TRIANGLE_LIST,
            VK_FALSE};
        const VkViewport viewport{0.0F,
                                  0.0F,
                                  static_cast<float>(extent_.width),
                                  static_cast<float>(extent_.height),
                                  0.0F,
                                  1.0F};
        const VkRect2D scissor{{0, 0}, extent_};
        const VkPipelineViewportStateCreateInfo viewport_state{
            VK_STRUCTURE_TYPE_PIPELINE_VIEWPORT_STATE_CREATE_INFO,
            nullptr,
            0,
            1,
            &viewport,
            1,
            &scissor};
        const VkPipelineRasterizationStateCreateInfo rasterizer{
            VK_STRUCTURE_TYPE_PIPELINE_RASTERIZATION_STATE_CREATE_INFO,
            nullptr,
            0,
            VK_FALSE,
            VK_FALSE,
            VK_POLYGON_MODE_FILL,
            VK_CULL_MODE_NONE,
            VK_FRONT_FACE_COUNTER_CLOCKWISE,
            VK_FALSE,
            0.0F,
            0.0F,
            0.0F,
            1.0F};
        const VkPipelineMultisampleStateCreateInfo multisample{
            VK_STRUCTURE_TYPE_PIPELINE_MULTISAMPLE_STATE_CREATE_INFO,
            nullptr,
            0,
            VK_SAMPLE_COUNT_1_BIT,
            VK_FALSE,
            1.0F,
            nullptr,
            VK_FALSE,
            VK_FALSE};
        const VkPipelineColorBlendAttachmentState blend_attachment{
            VK_FALSE,
            VK_BLEND_FACTOR_ONE,
            VK_BLEND_FACTOR_ZERO,
            VK_BLEND_OP_ADD,
            VK_BLEND_FACTOR_ONE,
            VK_BLEND_FACTOR_ZERO,
            VK_BLEND_OP_ADD,
            VK_COLOR_COMPONENT_R_BIT | VK_COLOR_COMPONENT_G_BIT | VK_COLOR_COMPONENT_B_BIT |
                VK_COLOR_COMPONENT_A_BIT};
        const VkPipelineColorBlendStateCreateInfo blend{
            VK_STRUCTURE_TYPE_PIPELINE_COLOR_BLEND_STATE_CREATE_INFO,
            nullptr,
            0,
            VK_FALSE,
            VK_LOGIC_OP_COPY,
            1,
            &blend_attachment,
            {0.0F, 0.0F, 0.0F, 0.0F}};

        const VkPushConstantRange push_range = hmi_vk_push_constant_range();
        const VkPipelineLayoutCreateInfo layout_info{
            VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO,
            nullptr,
            0,
            0,
            nullptr,
            1,
            &push_range};
        vk_check(vkCreatePipelineLayout(device_, &layout_info, nullptr, &pipeline_layout_),
                 "vkCreatePipelineLayout");

        const VkGraphicsPipelineCreateInfo pipeline_info{
            VK_STRUCTURE_TYPE_GRAPHICS_PIPELINE_CREATE_INFO,
            nullptr,
            0,
            2,
            stages,
            &vertex_input,
            &input_assembly,
            nullptr,
            &viewport_state,
            &rasterizer,
            &multisample,
            nullptr,
            &blend,
            nullptr,
            pipeline_layout_,
            render_pass_,
            0,
            VK_NULL_HANDLE,
            -1};
        vk_check(vkCreateGraphicsPipelines(device_,
                                           VK_NULL_HANDLE,
                                           1,
                                           &pipeline_info,
                                           nullptr,
                                           &pipeline_),
                 "vkCreateGraphicsPipelines");
        vkDestroyShaderModule(device_, frag, nullptr);
        vkDestroyShaderModule(device_, vert, nullptr);
    }

    void create_framebuffers() {
        framebuffers_.resize(image_views_.size());
        for (std::size_t i = 0; i < image_views_.size(); ++i) {
            const VkImageView attachments[] = {image_views_[i]};
            const VkFramebufferCreateInfo create_info{
                VK_STRUCTURE_TYPE_FRAMEBUFFER_CREATE_INFO,
                nullptr,
                0,
                render_pass_,
                1,
                attachments,
                extent_.width,
                extent_.height,
                1};
            vk_check(vkCreateFramebuffer(device_, &create_info, nullptr, &framebuffers_[i]),
                     "vkCreateFramebuffer");
        }
    }

    void create_command_pool() {
        const VkCommandPoolCreateInfo pool_info{
            VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO,
            nullptr,
            VK_COMMAND_POOL_CREATE_RESET_COMMAND_BUFFER_BIT,
            queue_family_.graphics_present};
        vk_check(vkCreateCommandPool(device_, &pool_info, nullptr, &command_pool_),
                 "vkCreateCommandPool");
        command_buffers_.resize(kFramesInFlight);
        const VkCommandBufferAllocateInfo alloc_info{
            VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO,
            nullptr,
            command_pool_,
            VK_COMMAND_BUFFER_LEVEL_PRIMARY,
            kFramesInFlight};
        vk_check(vkAllocateCommandBuffers(device_, &alloc_info, command_buffers_.data()),
                 "vkAllocateCommandBuffers");
    }

    void create_sync_objects() {
        const VkSemaphoreCreateInfo semaphore_info{VK_STRUCTURE_TYPE_SEMAPHORE_CREATE_INFO, nullptr, 0};
        const VkFenceCreateInfo fence_info{
            VK_STRUCTURE_TYPE_FENCE_CREATE_INFO,
            nullptr,
            VK_FENCE_CREATE_SIGNALED_BIT};
        image_available_.resize(kFramesInFlight);
        render_finished_.resize(kFramesInFlight);
        in_flight_.resize(kFramesInFlight);
        for (std::uint32_t i = 0; i < kFramesInFlight; ++i) {
            vk_check(vkCreateSemaphore(device_, &semaphore_info, nullptr, &image_available_[i]),
                     "vkCreateSemaphore");
            vk_check(vkCreateSemaphore(device_, &semaphore_info, nullptr, &render_finished_[i]),
                     "vkCreateSemaphore");
            vk_check(vkCreateFence(device_, &fence_info, nullptr, &in_flight_[i]), "vkCreateFence");
        }
    }

    void poll_events() {
        while (true) {
            xcb_generic_event_t* event = xcb_poll_for_event(connection_);
            if (event == nullptr) {
                break;
            }
            const std::uint8_t type = event->response_type & 0x7FU;
            if (type == XCB_KEY_PRESS) {
                should_close_ = true;
            } else if (type == XCB_CLIENT_MESSAGE) {
                const auto* client = reinterpret_cast<const xcb_client_message_event_t*>(event);
                if (client->data.data32[0] == wm_delete_window_) {
                    should_close_ = true;
                }
            } else if (type == XCB_CONFIGURE_NOTIFY) {
                const auto* configure = reinterpret_cast<const xcb_configure_notify_event_t*>(event);
                width_ = configure->width;
                height_ = configure->height;
            }
            std::free(event);
        }
    }

    void record_command_buffer(VkCommandBuffer command_buffer,
                               std::uint32_t image_index,
                               const HmiPush& push) {
        const VkCommandBufferBeginInfo begin_info{
            VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO,
            nullptr,
            0,
            nullptr};
        vk_check(vkBeginCommandBuffer(command_buffer, &begin_info), "vkBeginCommandBuffer");
        const VkClearValue clear{{{0.0F, 0.0F, 0.0F, 1.0F}}};
        const VkRenderPassBeginInfo render_info{
            VK_STRUCTURE_TYPE_RENDER_PASS_BEGIN_INFO,
            nullptr,
            render_pass_,
            framebuffers_[image_index],
            {{0, 0}, extent_},
            1,
            &clear};
        vkCmdBeginRenderPass(command_buffer, &render_info, VK_SUBPASS_CONTENTS_INLINE);
        vkCmdBindPipeline(command_buffer, VK_PIPELINE_BIND_POINT_GRAPHICS, pipeline_);
        hmi_cmd_push(command_buffer, pipeline_layout_, push);
        vkCmdDraw(command_buffer, 3, 1, 0, 0);
        vkCmdEndRenderPass(command_buffer);
        vk_check(vkEndCommandBuffer(command_buffer), "vkEndCommandBuffer");
    }

    void draw_frame(const HmiPush& push) {
        vk_check(vkWaitForFences(device_, 1, &in_flight_[frame_], VK_TRUE, UINT64_MAX),
                 "vkWaitForFences");

        std::uint32_t image_index = 0;
        VkResult acquire = vkAcquireNextImageKHR(device_,
                                                 swapchain_,
                                                 UINT64_MAX,
                                                 image_available_[frame_],
                                                 VK_NULL_HANDLE,
                                                 &image_index);
        if (acquire == VK_ERROR_OUT_OF_DATE_KHR || acquire == VK_SUBOPTIMAL_KHR) {
            should_close_ = true;
            return;
        }
        vk_check(acquire, "vkAcquireNextImageKHR");
        vk_check(vkResetFences(device_, 1, &in_flight_[frame_]), "vkResetFences");
        vk_check(vkResetCommandBuffer(command_buffers_[frame_], 0), "vkResetCommandBuffer");
        record_command_buffer(command_buffers_[frame_], image_index, push);

        const VkSemaphore wait_semaphores[] = {image_available_[frame_]};
        const VkPipelineStageFlags wait_stages[] = {VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT};
        const VkSemaphore signal_semaphores[] = {render_finished_[frame_]};
        const VkSubmitInfo submit_info{
            VK_STRUCTURE_TYPE_SUBMIT_INFO,
            nullptr,
            1,
            wait_semaphores,
            wait_stages,
            1,
            &command_buffers_[frame_],
            1,
            signal_semaphores};
        vk_check(vkQueueSubmit(queue_, 1, &submit_info, in_flight_[frame_]), "vkQueueSubmit");

        const VkPresentInfoKHR present_info{
            VK_STRUCTURE_TYPE_PRESENT_INFO_KHR,
            nullptr,
            1,
            signal_semaphores,
            1,
            &swapchain_,
            &image_index,
            nullptr};
        const VkResult present = vkQueuePresentKHR(queue_, &present_info);
        if (present == VK_ERROR_OUT_OF_DATE_KHR || present == VK_SUBOPTIMAL_KHR) {
            should_close_ = true;
        } else {
            vk_check(present, "vkQueuePresentKHR");
        }
        frame_ = (frame_ + 1U) % kFramesInFlight;
    }

    void cleanup() noexcept {
        if (device_ != VK_NULL_HANDLE) {
            vkDeviceWaitIdle(device_);
            for (VkFence fence : in_flight_) {
                if (fence != VK_NULL_HANDLE) {
                    vkDestroyFence(device_, fence, nullptr);
                }
            }
            for (VkSemaphore semaphore : render_finished_) {
                if (semaphore != VK_NULL_HANDLE) {
                    vkDestroySemaphore(device_, semaphore, nullptr);
                }
            }
            for (VkSemaphore semaphore : image_available_) {
                if (semaphore != VK_NULL_HANDLE) {
                    vkDestroySemaphore(device_, semaphore, nullptr);
                }
            }
            if (command_pool_ != VK_NULL_HANDLE) {
                vkDestroyCommandPool(device_, command_pool_, nullptr);
            }
            for (VkFramebuffer framebuffer : framebuffers_) {
                if (framebuffer != VK_NULL_HANDLE) {
                    vkDestroyFramebuffer(device_, framebuffer, nullptr);
                }
            }
            if (pipeline_ != VK_NULL_HANDLE) {
                vkDestroyPipeline(device_, pipeline_, nullptr);
            }
            if (pipeline_layout_ != VK_NULL_HANDLE) {
                vkDestroyPipelineLayout(device_, pipeline_layout_, nullptr);
            }
            if (render_pass_ != VK_NULL_HANDLE) {
                vkDestroyRenderPass(device_, render_pass_, nullptr);
            }
            for (VkImageView view : image_views_) {
                if (view != VK_NULL_HANDLE) {
                    vkDestroyImageView(device_, view, nullptr);
                }
            }
            if (swapchain_ != VK_NULL_HANDLE) {
                vkDestroySwapchainKHR(device_, swapchain_, nullptr);
            }
            vkDestroyDevice(device_, nullptr);
        }
        if (surface_ != VK_NULL_HANDLE) {
            vkDestroySurfaceKHR(instance_, surface_, nullptr);
        }
        if (instance_ != VK_NULL_HANDLE) {
            vkDestroyInstance(instance_, nullptr);
        }
        if (connection_ != nullptr) {
            if (window_ != XCB_WINDOW_NONE) {
                xcb_destroy_window(connection_, window_);
            }
            xcb_disconnect(connection_);
        }
    }

    std::string shader_dir_;
    std::uint32_t requested_width_;
    std::uint32_t requested_height_;
    std::uint32_t width_ = kDefaultWidth;
    std::uint32_t height_ = kDefaultHeight;
    bool should_close_ = false;
    std::uint32_t frame_ = 0;

    std::vector<char> vert_spv_;
    std::vector<char> frag_spv_;

    xcb_connection_t* connection_ = nullptr;
    xcb_screen_t* screen_ = nullptr;
    xcb_window_t window_ = XCB_WINDOW_NONE;
    xcb_atom_t wm_protocols_ = XCB_ATOM_NONE;
    xcb_atom_t wm_delete_window_ = XCB_ATOM_NONE;

    VkInstance instance_ = VK_NULL_HANDLE;
    VkSurfaceKHR surface_ = VK_NULL_HANDLE;
    VkPhysicalDevice physical_device_ = VK_NULL_HANDLE;
    VkDevice device_ = VK_NULL_HANDLE;
    VkQueue queue_ = VK_NULL_HANDLE;
    QueueFamilySelection queue_family_{};
    VkSwapchainKHR swapchain_ = VK_NULL_HANDLE;
    VkSurfaceFormatKHR surface_format_{};
    VkPresentModeKHR present_mode_ = VK_PRESENT_MODE_FIFO_KHR;
    VkExtent2D extent_{};
    std::vector<VkImage> swapchain_images_;
    std::vector<VkImageView> image_views_;
    VkRenderPass render_pass_ = VK_NULL_HANDLE;
    VkPipelineLayout pipeline_layout_ = VK_NULL_HANDLE;
    VkPipeline pipeline_ = VK_NULL_HANDLE;
    std::vector<VkFramebuffer> framebuffers_;
    VkCommandPool command_pool_ = VK_NULL_HANDLE;
    std::vector<VkCommandBuffer> command_buffers_;
    std::vector<VkSemaphore> image_available_;
    std::vector<VkSemaphore> render_finished_;
    std::vector<VkFence> in_flight_;
};

#endif

}  // namespace

int hmi_run_xcb_vulkan(const HmiRunnerOptions& options) {
#if defined(HG_HMI_RUNNER_ENABLE_NATIVE)
    try {
        VulkanXcbRunner runner(options);
        return runner.run();
    } catch (const std::exception& exc) {
        std::fprintf(stderr, "hmi-runner: %s\n", exc.what());
        return 2;
    }
#else
    (void)options;
    std::fprintf(stderr,
                 "hmi-runner: XCB/Vulkan support was not enabled at build time; "
                 "install Vulkan and XCB development packages and rebuild.\n");
    return 2;
#endif
}

}  // namespace hg::hmi

int main(int argc, char** argv) {
    hg::hmi::HmiRunnerOptions options{};
    options.shader_dir = nullptr;
    options.width = 1280U;
    options.height = 720U;

    for (int i = 1; i < argc; ++i) {
        if (std::strcmp(argv[i], "--shader-dir") == 0 && i + 1 < argc) {
            options.shader_dir = argv[++i];
        } else if (std::strcmp(argv[i], "--help") == 0) {
            std::printf("usage: hmi-runner [--shader-dir DIR]\n");
            return 0;
        } else {
            std::fprintf(stderr, "hmi-runner: unknown argument: %s\n", argv[i]);
            return 2;
        }
    }

    return hg::hmi::hmi_run_xcb_vulkan(options);
}
