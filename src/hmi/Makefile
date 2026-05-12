CXX ?= c++
GLSLC ?= glslc
PKG_CONFIG ?= pkg-config
CXXFLAGS ?= -std=c++17 -Wall -Wextra -Werror -O2
CPPFLAGS ?= -Iinclude

BUILD_DIR := build
SHADER_BUILD_DIR := $(BUILD_DIR)/shaders
VALIDATE_BIN := $(BUILD_DIR)/hmi-validate
TELEMETRY_VALIDATE_BIN := $(BUILD_DIR)/hmi-telemetry-validate
RUNNER_BIN := $(BUILD_DIR)/hmi-runner
VERT_SRC := shaders/dashboard.vert
FRAG_SRC := shaders/dashboard.frag
VERT_SPV := $(SHADER_BUILD_DIR)/dashboard.vert.spv
FRAG_SPV := $(SHADER_BUILD_DIR)/dashboard.frag.spv
NATIVE_RUNNER_DEPS := $(shell $(PKG_CONFIG) --exists vulkan xcb >/dev/null 2>&1 && echo yes)

ifeq ($(NATIVE_RUNNER_DEPS),yes)
RUNNER_CPPFLAGS := $(shell $(PKG_CONFIG) --cflags vulkan xcb) -DHG_HMI_RUNNER_ENABLE_NATIVE
RUNNER_LDLIBS := $(shell $(PKG_CONFIG) --libs vulkan xcb)
else
RUNNER_CPPFLAGS :=
RUNNER_LDLIBS :=
endif

.PHONY: all shaders runner runner-compile check clean print-compile-commands

all: $(VALIDATE_BIN) $(TELEMETRY_VALIDATE_BIN) runner shaders

$(BUILD_DIR):
	mkdir -p $@

$(SHADER_BUILD_DIR):
	mkdir -p $@

$(VALIDATE_BIN): hmi_validate.cpp hmi_ingest.cpp include/hmi_push.hpp include/hmi_ingest.hpp include/hmi_vulkan_ingest.hpp | $(BUILD_DIR)
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) -o $@ hmi_validate.cpp hmi_ingest.cpp

$(TELEMETRY_VALIDATE_BIN): hmi_telemetry_validate.cpp hmi_ingest.cpp hmi_telemetry.cpp include/hmi_push.hpp include/hmi_ingest.hpp include/hmi_telemetry.hpp | $(BUILD_DIR)
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) -pthread -o $@ hmi_telemetry_validate.cpp hmi_ingest.cpp hmi_telemetry.cpp

$(RUNNER_BIN): hmi_runner.cpp hmi_ingest.cpp hmi_telemetry.cpp include/hmi_push.hpp include/hmi_ingest.hpp include/hmi_telemetry.hpp include/hmi_vulkan_ingest.hpp include/hmi_runner.hpp | $(BUILD_DIR)
	$(CXX) $(CPPFLAGS) $(RUNNER_CPPFLAGS) $(CXXFLAGS) -pthread -o $@ hmi_runner.cpp hmi_ingest.cpp hmi_telemetry.cpp $(RUNNER_LDLIBS)

$(VERT_SPV): $(VERT_SRC) | $(SHADER_BUILD_DIR)
	$(GLSLC) -fshader-stage=vert $< -o $@

$(FRAG_SPV): $(FRAG_SRC) | $(SHADER_BUILD_DIR)
	$(GLSLC) -fshader-stage=frag $< -o $@

shaders: $(VERT_SPV) $(FRAG_SPV)

runner: shaders $(RUNNER_BIN)

runner-compile: $(RUNNER_BIN)

check: all $(TELEMETRY_VALIDATE_BIN)
	./$(VALIDATE_BIN)
	./$(TELEMETRY_VALIDATE_BIN)

print-compile-commands:
	@echo "$(GLSLC) -fshader-stage=vert $(VERT_SRC) -o $(VERT_SPV)"
	@echo "$(GLSLC) -fshader-stage=frag $(FRAG_SRC) -o $(FRAG_SPV)"

clean:
	rm -rf $(BUILD_DIR)
