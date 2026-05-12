# HIGH-GRAVITY Procedural HMI

This subtree is the first C++/Vulkan dashboard scaffold for the operational HMI directive.

It deliberately uses:

- offline GLSL to SPIR-V compilation with `glslc`
- a fullscreen triangle vertex shader
- fragment-shader SDF math for all visual widgets
- one 96-byte `alignas(16)` push-constant payload
- no raster assets, DOM, Canvas, Qt, SDL, or GLFW
- no dynamic telemetry allocation in the render ingestion path

## The Math

Shader sources:

```text
src/hmi/shaders/dashboard.vert
src/hmi/shaders/dashboard.frag
```

The fragment shader normalizes `gl_FragCoord` into `[-1.0, 1.0]`, uses SDF helpers for rings, bars, boxes, and segment sweeps, and anti-aliases boundaries with `smoothstep`.

## The Compilation Step

```bash
glslc -fshader-stage=vert src/hmi/shaders/dashboard.vert -o src/hmi/build/shaders/dashboard.vert.spv
glslc -fshader-stage=frag src/hmi/shaders/dashboard.frag -o src/hmi/build/shaders/dashboard.frag.spv
```

Or:

```bash
make -C src/hmi shaders
```

## The XCB/Vulkan Runner

```bash
make -C src/hmi runner
src/hmi/build/hmi-runner --shader-dir src/hmi/build/shaders
```

The runner uses raw XCB to create a fullscreen window and `VK_KHR_xcb_surface` for presentation. It loads `dashboard.vert.spv` and `dashboard.frag.spv` at startup, builds a fullscreen-triangle graphics pipeline, and updates the fragment push constants with a stack `HmiPush` snapshot each frame. The telemetry poller publishes snapshots through an atomic double buffer so the render-facing read path stays lock-free. There are no runtime GLSL strings, widget vertex buffers, or render-loop telemetry allocations.

For CI or hosts without XCB/Vulkan development packages:

```bash
make -C src/hmi runner-compile
```

That target still emits `build/hmi-runner`; when native support was unavailable at build time the executable exits with a clear runtime error instead of attempting to open a display or Vulkan instance.

## The Payload

The telemetry feed is [include/hmi_push.hpp](include/hmi_push.hpp). It is a 96-byte, 16-byte-aligned `HmiPush` struct:

```cpp
struct alignas(16) HmiPush {
    float resolution_time_health[4];
    float traffic[4];
    float stream[4];
    float rag[4];
    float accel[4];
    float pulse[4];
};
```

Static assertions pin every offset and keep the payload below Vulkan's 128-byte minimum push constant guarantee.

## The Ingestion

`hmi_ingest_update` builds a precomputed `HmiPush` snapshot from fixed scalar counters outside the render path. The render path should only call:

```cpp
hg::hmi::hmi_cmd_push(command_buffer, pipeline_layout, push);
```

`include/hmi_vulkan_ingest.hpp` always exposes a Vulkan-shaped range descriptor that can be compiled without Vulkan headers:

```cpp
constexpr auto range = hg::hmi::hmi_push_constant_range();
```

When `HIGHGRAVITY_HMI_ENABLE_VULKAN` is defined and Vulkan headers are available, it also exposes:

```cpp
hg::hmi::hmi_cmd_push(command_buffer, pipeline_layout, push);
```

That call expands to `vkCmdPushConstants` with a fragment-stage range.

`include/hmi_telemetry.hpp` adds native telemetry polling for the live proxy
control-plane endpoints:

- `/hg/telemetry`
- `/hg/khoj/status`
- `/hg/microproxy/status`

The runner reads `HG_HMI_TELEMETRY_HOST` and `HG_HMI_TELEMETRY_PORT` when set,
falling back to `127.0.0.1:9998`. The polling side may allocate while reading
HTTP responses and parsing JSON-ish payloads. The render-facing side remains
fixed: `TelemetryCounters` is copied into `hmi_ingest_update`, which produces
the 96-byte `HmiPush` payload without dynamic allocation. When the proxy is not
reachable, the runner marks proxy health unavailable rather than rendering
invented traffic.

## Validation

```bash
make -C src/hmi check
```

This compiles the shader SPIR-V files when `glslc` is available and runs ABI and telemetry validators. It does not require a display or swapchain.

## Runtime

```bash
make -C src/hmi runner
./hg.sh hmi run
```

The current runner uses raw XCB plus Vulkan when those development packages are available. It loads the offline SPIR-V files at startup, creates a fullscreen-triangle pipeline, polls proxy/Khoj/microproxy telemetry on a background thread, and pushes `HmiPush` each frame. If no display or Vulkan runtime is available, `./hg.sh hmi run` exits with the probe reason without altering proxy routing.
