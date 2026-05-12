# Procedural HMI Control Plane

The procedural C++ HMI is managed through:

```bash
./hg.sh hmi status
./hg.sh hmi build
./hg.sh hmi check
./hg.sh hmi run
./hg.sh hmi tui
./hg.sh hmi-dashboard
```

These commands are isolated from the HIGH-GRAVITY proxy control plane. They do
not start or stop proxy services, edit routing, or change iptables state.

`build` delegates to the existing `src/hmi/Makefile` and builds the validator
plus shader artifacts. `check` is safe on headless hosts: when `glslc` is
available it runs the full Makefile check, and when it is missing it still
builds and runs the C++ ABI/layout validator without requiring a display,
swapchain, or Vulkan runtime link.

`run` is conservative. It refuses to start when neither `DISPLAY` nor
`WAYLAND_DISPLAY` is set, and it also skips launch when `vulkaninfo` is not
available. `status` prints the Vulkan probe reason, the proxy telemetry source,
and whether `/hg/telemetry` is reachable. For specialized offscreen launchers,
set:

```bash
HG_HMI_ALLOW_HEADLESS_RUN=1 HG_HMI_ALLOW_NO_VULKANINFO=1 ./hg.sh hmi run
```

Use `HG_HMI_BIN=/path/to/runtime` if the runtime executable is outside the
default `src/hmi/build/` search paths.

The native runner consumes live counters from the Python proxy by polling:

- `http://127.0.0.1:9998/hg/telemetry`
- `http://127.0.0.1:9998/hg/khoj/status`
- `http://127.0.0.1:9998/hg/microproxy/status`

Override the source with `HG_HMI_TELEMETRY_HOST` and
`HG_HMI_TELEMETRY_PORT`. If telemetry is unavailable, the runtime renders the
proxy health as unavailable instead of substituting synthetic traffic.

`tui` launches the existing terminal UI dashboard for real-time monitoring.
