# Makefile for Claude Agent Communication System v7.0
# Builds Director, Project Orchestrator, Architect, and Coordination components

CC = gcc
CFLAGS = -Wall -Wextra -O3 -std=c11 -D_GNU_SOURCE -fPIC
LDFLAGS = -lpthread -lm -lrt
INCLUDES = -I.

# Source files
DIRECTOR_SRC = director_agent.c compatibility_layer.c
ORCHESTRATOR_SRC = project_orchestrator.c compatibility_layer.c  
ARCHITECT_SRC = architect_agent.c compatibility_layer.c
COORDINATION_SRC = agent_coordination.c compatibility_layer.c
TEST_SRC = test_agents.c

# Object files
DIRECTOR_OBJ = $(DIRECTOR_SRC:.c=.o)
ORCHESTRATOR_OBJ = $(ORCHESTRATOR_SRC:.c=.o)
ARCHITECT_OBJ = $(ARCHITECT_SRC:.c=.o)
COORDINATION_OBJ = $(COORDINATION_SRC:.c=.o)

# Executables
DIRECTOR_BIN = director_agent
ORCHESTRATOR_BIN = project_orchestrator
ARCHITECT_BIN = architect_agent
COORDINATION_BIN = agent_coordination
TEST_BIN = test_agents

# Default target
all: $(DIRECTOR_BIN) $(ORCHESTRATOR_BIN) $(ARCHITECT_BIN) $(COORDINATION_BIN) $(TEST_BIN)

# Individual agent binaries
$(DIRECTOR_BIN): $(DIRECTOR_OBJ)
	$(CC) $(CFLAGS) -DDIRECTOR_TEST_MODE -o $@ $^ $(LDFLAGS)

$(ORCHESTRATOR_BIN): $(ORCHESTRATOR_OBJ)
	$(CC) $(CFLAGS) -DORCHESTRATOR_TEST_MODE -o $@ $^ $(LDFLAGS)

$(ARCHITECT_BIN): $(ARCHITECT_OBJ)  
	$(CC) $(CFLAGS) -DARCHITECT_TEST_MODE -o $@ $^ $(LDFLAGS)

$(COORDINATION_BIN): $(COORDINATION_OBJ)
	$(CC) $(CFLAGS) -o $@ $^ $(LDFLAGS)

# Integrated test binary
$(TEST_BIN): $(TEST_SRC)
	$(CC) $(CFLAGS) $(INCLUDES) -o $@ $^ $(LDFLAGS)

# Object file compilation
%.o: %.c
	$(CC) $(CFLAGS) $(INCLUDES) -c $< -o $@

# Create compatibility layer if it doesn't exist
compatibility_layer.c:
	@echo "// Compatibility layer implementation" > $@
	@echo "#include \"compatibility_layer.h\"" >> $@
	@echo "" >> $@
	@echo "int io_uring_fallback_read(int fd, void *buf, size_t count, off_t offset) {" >> $@
	@echo "    lseek(fd, offset, SEEK_SET);" >> $@
	@echo "    return read(fd, buf, count);" >> $@
	@echo "}" >> $@
	@echo "" >> $@
	@echo "int io_uring_fallback_write(int fd, const void *buf, size_t count, off_t offset) {" >> $@
	@echo "    lseek(fd, offset, SEEK_SET);" >> $@
	@echo "    return write(fd, buf, count);" >> $@
	@echo "}" >> $@
	@echo "" >> $@
	@echo "// Stub implementations for missing functions" >> $@
	@echo "int ring_buffer_read_priority(void* rb, int priority, enhanced_msg_header_t* msg, uint8_t* payload) {" >> $@
	@echo "    (void)rb; (void)priority; (void)msg; (void)payload; return -1;" >> $@
	@echo "}" >> $@
	@echo "" >> $@
	@echo "void process_message_pcore(enhanced_msg_header_t* msg, uint8_t* payload) {" >> $@
	@echo "    (void)msg; (void)payload;" >> $@
	@echo "}" >> $@
	@echo "" >> $@  
	@echo "void process_message_ecore(enhanced_msg_header_t* msg, uint8_t* payload) {" >> $@
	@echo "    (void)msg; (void)payload;" >> $@
	@echo "}" >> $@
	@echo "" >> $@
	@echo "void* work_queue_steal(void* queue) {" >> $@
	@echo "    (void)queue; return NULL;" >> $@
	@echo "}" >> $@

# Test targets
test: $(TEST_BIN)
	./$(TEST_BIN)

test-director: $(DIRECTOR_BIN)
	./$(DIRECTOR_BIN)

test-orchestrator: $(ORCHESTRATOR_BIN)
	./$(ORCHESTRATOR_BIN)

test-architect: $(ARCHITECT_BIN)
	./$(ARCHITECT_BIN)

# Static analysis
analyze:
	@echo "Running static analysis..."
	@which cppcheck >/dev/null 2>&1 && cppcheck --enable=all --std=c11 *.c || echo "cppcheck not found, skipping analysis"

# Memory check (requires valgrind)
memcheck: $(TEST_BIN)
	@which valgrind >/dev/null 2>&1 && valgrind --leak-check=full --track-origins=yes ./$(TEST_BIN) || echo "valgrind not found, skipping memory check"

# Performance profiling (requires perf)
profile: $(TEST_BIN)
	@which perf >/dev/null 2>&1 && perf record -g ./$(TEST_BIN) && perf report || echo "perf not found, skipping profiling"

# Coverage analysis (requires gcov/lcov)
coverage: CFLAGS += -fprofile-arcs -ftest-coverage
coverage: LDFLAGS += -lgcov --coverage
coverage: clean $(TEST_BIN)
	./$(TEST_BIN)
	@which lcov >/dev/null 2>&1 && lcov --capture --directory . --output-file coverage.info && genhtml coverage.info --output-directory coverage_html || echo "lcov not found, skipping coverage report"

# Debug build
debug: CFLAGS += -g -DDEBUG -O0
debug: all

# Release build  
release: CFLAGS += -DNDEBUG -march=native -flto
release: LDFLAGS += -flto
release: all

# Documentation generation
docs:
	@echo "Generating documentation..."
	@which doxygen >/dev/null 2>&1 && doxygen || echo "doxygen not found, skipping documentation generation"

# Installation
install: all
	@echo "Installing agent binaries..."
	@mkdir -p /usr/local/bin/claude-agents
	@cp $(DIRECTOR_BIN) $(ORCHESTRATOR_BIN) $(ARCHITECT_BIN) $(COORDINATION_BIN) /usr/local/bin/claude-agents/
	@cp *.h /usr/local/include/ 2>/dev/null || true
	@echo "Installation complete"

# Uninstall
uninstall:
	@echo "Removing agent binaries..."
	@rm -rf /usr/local/bin/claude-agents
	@rm -f /usr/local/include/ultra_fast_protocol.h /usr/local/include/compatibility_layer.h
	@echo "Uninstallation complete"

# Clean up
clean:
	rm -f *.o *.so *.a
	rm -f $(DIRECTOR_BIN) $(ORCHESTRATOR_BIN) $(ARCHITECT_BIN) $(COORDINATION_BIN) $(TEST_BIN)
	rm -f compatibility_layer.c
	rm -f *.gcno *.gcda *.gcov coverage.info
	rm -rf coverage_html
	rm -f perf.data*

# Clean everything including generated files
distclean: clean
	rm -f *~
	rm -f core core.*
	rm -f vgcore.*

# Show build information
info:
	@echo "Claude Agent Communication System v7.0 Build Information"
	@echo "========================================================"
	@echo "Compiler: $(CC)"
	@echo "CFLAGS: $(CFLAGS)"
	@echo "LDFLAGS: $(LDFLAGS)"
	@echo "Targets: $(DIRECTOR_BIN) $(ORCHESTRATOR_BIN) $(ARCHITECT_BIN) $(COORDINATION_BIN) $(TEST_BIN)"
	@echo "Build date: $$(date)"
	@echo "System: $$(uname -a)"

# Check dependencies
check-deps:
	@echo "Checking build dependencies..."
	@which $(CC) >/dev/null 2>&1 && echo "✓ $(CC) found" || echo "✗ $(CC) not found"
	@echo "  Required libraries:"
	@echo "    ✓ pthread (usually available)"
	@echo "    ✓ math (usually available)" 
	@echo "    ✓ rt (usually available)"
	@echo "  Optional tools:"
	@which cppcheck >/dev/null 2>&1 && echo "    ✓ cppcheck found" || echo "    ✗ cppcheck not found (for static analysis)"
	@which valgrind >/dev/null 2>&1 && echo "    ✓ valgrind found" || echo "    ✗ valgrind not found (for memory checking)"
	@which perf >/dev/null 2>&1 && echo "    ✓ perf found" || echo "    ✗ perf not found (for profiling)"
	@which lcov >/dev/null 2>&1 && echo "    ✓ lcov found" || echo "    ✗ lcov not found (for coverage)"

# Help
help:
	@echo "Claude Agent Communication System v7.0 - Build System"
	@echo "====================================================="
	@echo ""
	@echo "Available targets:"
	@echo "  all              - Build all agent components (default)"
	@echo "  director_agent   - Build Director agent only"
	@echo "  project_orchestrator - Build Project Orchestrator only" 
	@echo "  architect_agent  - Build Architect agent only"
	@echo "  agent_coordination - Build Coordination system only"
	@echo "  test_agents      - Build integrated test suite"
	@echo ""
	@echo "Testing:"
	@echo "  test             - Run integrated test suite"
	@echo "  test-director    - Test Director agent"
	@echo "  test-orchestrator - Test Project Orchestrator"
	@echo "  test-architect   - Test Architect agent"
	@echo ""
	@echo "Quality assurance:"
	@echo "  analyze          - Run static code analysis"
	@echo "  memcheck         - Run memory leak detection"
	@echo "  profile          - Run performance profiling"
	@echo "  coverage         - Generate code coverage report"
	@echo ""
	@echo "Build variants:"
	@echo "  debug            - Build with debug symbols"
	@echo "  release          - Build optimized release version"
	@echo ""
	@echo "Maintenance:"
	@echo "  clean            - Remove build artifacts"
	@echo "  distclean        - Remove all generated files"
	@echo "  install          - Install to system directories"
	@echo "  uninstall        - Remove from system directories"
	@echo ""
	@echo "Information:"
	@echo "  info             - Show build configuration"
	@echo "  check-deps       - Check build dependencies"
	@echo "  help             - Show this help message"

.PHONY: all test test-director test-orchestrator test-architect analyze memcheck profile coverage debug release docs install uninstall clean distclean info check-deps help