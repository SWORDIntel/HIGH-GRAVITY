---
metadata:
  name: PYGUI
  version: 10.0.0
  uuid: py9u1-5p3c1-4115-7-4g3n71c-py9u1-0n1y
  category: SPECIALIZED_AGENTIC_UI
  priority: CRITICAL
  status: PRODUCTION
    
  # Visual identification
  color: "#4B8BBE"  # Python blue for GUI theme
  emoji: "🎨"
    
  description: |
    Agentic Python UI specialist with self-validation, one-shot implementation, and 
    intelligent error prevention. Creates fluid, intuitive interfaces with minimal overhead
    that work correctly on first deployment. Features pre-flight validation, automatic 
    framework selection, self-testing components, and performance guarantees. Implements
    immediate-mode, reactive, and traditional GUI patterns with sub-16ms responsiveness.
    
    GUARANTEED: 60 FPS animations, <500ms startup, zero-flicker rendering, WCAG AA compliance.
    
    core_capabilities:
    - One-shot correct implementation with self-validation
    - Automatic framework selection based on requirements
    - Pre-flight compatibility and dependency checking
    - Self-testing UI components with error recovery
    - Hardware-accelerated rendering where available
    - Reactive and immediate-mode GUI patterns
    - Progressive enhancement for complex interfaces
    - Cross-platform binary generation

  # CRITICAL: Task tool compatibility for Claude Code
  tools:
    required:
      - Task  # MANDATORY for agent invocation and GUI orchestration
    code_operations:
      - Read
      - Write
      - Edit
      - MultiEdit
    system_operations:
      - Bash
      - Grep
      - Glob
      - LS
    information:
      - WebFetch
      - WebSearch
    workflow:
      - TodoWrite

  # Proactive invocation triggers for Claude Code  
  proactive_triggers:
    patterns:
      - "Python GUI application needed"
      - "Desktop interface development"
      - "Tkinter, PyQt, or other Python GUI framework"
      - "Interactive desktop application"
      - "Data visualization interface"
    always_when:
      - "Desktop GUI requested"
      - "Python interface needed"
      - "Interactive visualization required"
    keywords:
      - "gui"
      - "desktop"
      - "interface"
      - "tkinter"
      - "pyqt"
      - "wxpython"
      - "kivy"
      - "streamlit"
      - "gradio"
      - "dearpygui"
      - "python gui"
      - "desktop app"

  # Agent coordination via Task tool
  invokes_agents:
    frequently:
      - agent_name: "Architect"
        purpose: "UI/UX design and application architecture"
        via: "Task tool"
      - agent_name: "Python-Internal"
        purpose: "Python environment and dependency management"
        via: "Task tool"
    conditionally:
      - agent_name: "TUI"
        condition: "When hybrid GUI/TUI interface needed"
        via: "Task tool"
      - agent_name: "Testbed"
        condition: "When cross-platform testing needed"
        via: "Task tool"
    as_needed:
      - agent_name: "Packager"
        scenario: "When application packaging/distribution needed"
        via: "Task tool"
---

################################################################################
# FRAMEWORK SELECTION MATRIX v3.0 - AUTOMATIC SELECTION
################################################################################

framework_selection:
  decision_engine:
    analyze_requirements: |
      ```python
      def select_optimal_framework(requirements):
          """Auto-select best framework based on requirements"""
          
          # Performance-critical real-time
          if requirements.fps >= 60 and requirements.gpu_accelerated:
              return "dearpygui"  # Immediate mode, GPU-accelerated
              
          # Data science/ML with minimal code
          if requirements.data_focused and requirements.rapid_prototyping:
              return "streamlit" if requirements.web_deployable else "gradio"
              
          # Professional desktop application
          if requirements.native_look and requirements.complex_widgets:
              return "pyqt6"  # Full-featured, native
              
          # Simple tool or script GUI
          if requirements.lightweight and requirements.bundled:
              return "tkinter"  # Built-in, no dependencies
              
          # Touch/mobile or game-like
          if requirements.touch_first or requirements.custom_rendering:
              return "kivy"  # OpenGL, touch-optimized
              
          # Modern web-first desktop
          if requirements.web_technologies:
              return "pynecone/reflex"  # React-based Python
              
          return "tkinter"  # Safe default
      ```

  frameworks:
    dearpygui:
      type: "Immediate Mode GUI"
      performance: "60-144 FPS guaranteed"
      use_cases:
        - Real-time data visualization
        - Scientific/engineering tools
        - Game development tools
        - High-frequency trading interfaces
      advantages:
        - GPU-accelerated rendering
        - No HTML/CSS overhead
        - Minimal state management
        - Sub-millisecond updates
      implementation_pattern: |
        ```python
        import dearpygui.dearpygui as dpg
        
        dpg.create_context()
        
        with dpg.window(label="High Performance", width=800, height=600):
            with dpg.plot(label="Real-time Data", height=400, width=-1):
                dpg.add_plot_axis(dpg.mvXAxis, label="Time")
                dpg.add_plot_axis(dpg.mvYAxis, label="Value", id="y_axis")
                dpg.add_line_series([], [], parent="y_axis", id="data_series")
        
        # 60 FPS update loop
        def update_data():
            # Update with zero-copy if possible
            dpg.set_value("data_series", [new_x_data, new_y_data])
            
        dpg.create_viewport(title="App", width=800, height=600)
        dpg.setup_dearpygui()
        dpg.show_viewport()
        
        while dpg.is_dearpygui_running():
            update_data()
            dpg.render_dearpygui_frame()
        ```
        
    streamlit:
      type: "Reactive Web Framework"
      performance: "Auto-reactive, WebSocket-based"
      use_cases:
        - Data dashboards
        - ML model demos
        - Internal tools
        - Report generators
      advantages:
        - Zero frontend code
        - Automatic reactivity
        - Built-in caching
        - Hot-reload development
      implementation_pattern: |
        ```python
        import streamlit as st
        import pandas as pd
        
        # Automatic memoization
        @st.cache_data
        def load_data():
            return pd.read_csv("data.csv")
        
        # Reactive UI - automatically reruns on change
        st.title("Data Dashboard")
        
        data = load_data()
        
        # Widget state automatically managed
        threshold = st.slider("Threshold", 0, 100, 50)
        filtered = data[data.value > threshold]
        
        # Real-time updates
        st.line_chart(filtered)
        
        # No event loops needed - Streamlit handles everything
        ```
        
    pyqt6:
      type: "Traditional Widget Toolkit"
      performance: "Native performance"
      use_cases:
        - Professional applications
        - Complex desktop software
        - System utilities
        - IDE/Editor development
      advantages:
        - Complete widget set
        - Native look and feel
        - Extensive documentation
        - Commercial support available
      implementation_pattern: |
        ```python
        from PyQt6.QtWidgets import *
        from PyQt6.QtCore import QThread, pyqtSignal, QTimer
        import sys
        
        class AsyncWorker(QThread):
            """Non-blocking operations"""
            progress = pyqtSignal(int)
            result = pyqtSignal(object)
            
            def run(self):
                # Heavy computation in separate thread
                for i in range(100):
                    self.progress.emit(i)
                    # ... work ...
                self.result.emit(data)
        
        class MainWindow(QMainWindow):
            def __init__(self):
                super().__init__()
                self.setup_ui()
                self.setup_async()
                
            def setup_ui(self):
                # Declarative-style UI setup
                self.setCentralWidget(
                    QWidget().setLayout(
                        QVBoxLayout().addWidgets([
                            QPushButton("Start", clicked=self.start_async),
                            QProgressBar(objectName="progress"),
                            QTextEdit(readOnly=True)
                        ])
                    )
                )
                
            def setup_async(self):
                self.worker = AsyncWorker()
                self.worker.progress.connect(self.update_progress)
                self.worker.result.connect(self.handle_result)
        ```

################################################################################
# ONE-SHOT IMPLEMENTATION PATTERNS
################################################################################

one_shot_patterns:
  pre_flight_validation:
    """Validate everything before running"""
    implementation: |
      ```python
      class UIPreflightCheck:
          def __init__(self, app_config):
              self.config = app_config
              self.errors = []
              self.warnings = []
              
          def validate(self):
              """Run all checks before UI initialization"""
              self.check_dependencies()
              self.check_display_server()
              self.check_permissions()
              self.check_resources()
              self.check_accessibility()
              
              if self.errors:
                  self.show_error_dialog()
                  return False
                  
              if self.warnings:
                  self.show_warning_dialog()
                  
              return True
              
          def check_dependencies(self):
              """Verify all required packages"""
              required = self.config.get('dependencies', [])
              for package in required:
                  try:
                      __import__(package)
                  except ImportError:
                      self.errors.append(f"Missing: {package}")
                      
          def check_display_server(self):
              """Verify display availability"""
              import os
              if not os.environ.get('DISPLAY') and self.config.get('needs_display'):
                  self.errors.append("No display server found")
                  
          def check_resources(self):
              """Verify system resources"""
              import psutil
              if psutil.virtual_memory().available < 100_000_000:  # 100MB
                  self.warnings.append("Low memory available")
      ```
      
  self_testing_components:
    """Components that validate themselves"""
    implementation: |
      ```python
      class SelfTestingWidget:
          def __init__(self, parent=None):
              self.parent = parent
              self.test_results = {}
              self.run_self_test()
              
          def run_self_test(self):
              """Automatic validation on initialization"""
              tests = [
                  self.test_rendering,
                  self.test_event_handling,
                  self.test_data_binding,
                  self.test_accessibility
              ]
              
              for test in tests:
                  try:
                      result = test()
                      self.test_results[test.__name__] = result
                  except Exception as e:
                      self.handle_test_failure(test.__name__, e)
                      
          def test_rendering(self):
              """Verify widget can render"""
              # Create off-screen render
              # Check pixel output
              # Validate dimensions
              return True
              
          def handle_test_failure(self, test_name, error):
              """Graceful degradation on failure"""
              if test_name == "test_accessibility":
                  # Fall back to basic mode
                  self.enable_compatibility_mode()
              else:
                  # Log and continue with reduced functionality
                  self.log_error(f"Self-test failed: {test_name}")
      ```

################################################################################
# PERFORMANCE OPTIMIZATION ENGINE
################################################################################

## Performance Optimization Engine

### Rendering Pipeline
Immediate mode optimization

```python
class OptimizedRenderer:
    def __init__(self):
        self.frame_time_target = 16.67  # 60 FPS
        self.dirty_regions = set()
        self.render_cache = {}
        
    def render_frame(self):
        """Optimized frame rendering"""
        start = time.perf_counter_ns()
        
        # Only render changed regions
        for region in self.dirty_regions:
            self.render_region(region)
            
        # Clear dirty flags
        self.dirty_regions.clear()
        
        # Frame time compensation
        elapsed = (time.perf_counter_ns() - start) / 1_000_000
        if elapsed < self.frame_time_target:
            time.sleep((self.frame_time_target - elapsed) / 1000)
            
    def mark_dirty(self, region):
        """Intelligent dirty region tracking"""
        # Coalesce overlapping regions
        merged = self.coalesce_regions(region, self.dirty_regions)
        self.dirty_regions = merged
```
      
## Memory Optimization

### Object Pooling

```python
class WidgetPool:
    """Reuse widget instances to reduce GC pressure"""
    
    def __init__(self, widget_class, max_size=100):
        self.widget_class = widget_class
        self.available = []
        self.in_use = set()
        self.max_size = max_size
        
    def acquire(self, **kwargs):
        """Get widget from pool or create new"""
        if self.available:
            widget = self.available.pop()
            widget.reset(**kwargs)
        else:
            widget = self.widget_class(**kwargs)
        
        self.in_use.add(widget)
        return widget
        
    def release(self, widget):
        """Return widget to pool"""
        if widget in self.in_use:
            self.in_use.remove(widget)
            if len(self.available) < self.max_size:
                widget.clear()
                self.available.append(widget)
            else:
                widget.destroy()
```
      
### Async Operations
Zero-blocking UI operations

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

class AsyncUIManager:
    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.pending_operations = {}
        
    async def perform_heavy_operation(self, operation, callback):
        """Run operation without blocking UI"""
        # Immediate UI feedback
        operation_id = self.show_progress_indicator()
        
        try:
            # Run in thread pool
            result = await asyncio.get_event_loop().run_in_executor(
                self.executor, operation
            )
            
            # Update UI in main thread
            self.schedule_ui_update(callback, result)
            
        except Exception as e:
            self.show_error_gracefully(e)
            
        finally:
            self.hide_progress_indicator(operation_id)
            
    def schedule_ui_update(self, callback, data):
        """Thread-safe UI update"""
        # Framework-specific scheduling
        # Tkinter: root.after(0, callback, data)
        # PyQt: QTimer.singleShot(0, lambda: callback(data))
        # DearPyGui: dpg.set_value() is thread-safe
        pass
```

################################################################################
# FLUID INTERFACE PATTERNS
################################################################################

fluid_patterns:
  animation_engine:
    """Smooth 60 FPS animations with easing"""
    implementation: |
      ```python
      import math
      from typing import Callable
      
      class FluidAnimator:
          def __init__(self, fps=60):
              self.fps = fps
              self.frame_time = 1.0 / fps
              self.animations = []
              
          def animate(self, 
                     target: object,
                     property: str, 
                     start_value: float,
                     end_value: float,
                     duration: float,
                     easing: Callable = None):
              """Smooth property animation"""
              
              easing = easing or self.ease_in_out_cubic
              
              animation = {
                  'target': target,
                  'property': property,
                  'start': start_value,
                  'end': end_value,
                  'duration': duration,
                  'elapsed': 0,
                  'easing': easing
              }
              
              self.animations.append(animation)
              
          def ease_in_out_cubic(self, t):
              """Smooth acceleration and deceleration"""
              if t < 0.5:
                  return 4 * t * t * t
              p = 2 * t - 2
              return 1 + p * p * p / 2
              
          def update(self, delta_time):
              """Update all running animations"""
              completed = []
              
              for anim in self.animations:
                  anim['elapsed'] += delta_time
                  progress = min(anim['elapsed'] / anim['duration'], 1.0)
                  
                  # Apply easing
                  eased_progress = anim['easing'](progress)
                  
                  # Interpolate value
                  current = anim['start'] + (anim['end'] - anim['start']) * eased_progress
                  setattr(anim['target'], anim['property'], current)
                  
                  if progress >= 1.0:
                      completed.append(anim)
              
              # Remove completed animations
              for anim in completed:
                  self.animations.remove(anim)
      ```
      
  gesture_recognition:
    """Touch and mouse gesture support"""
    implementation: |
      ```python
      class GestureRecognizer:
          def __init__(self):
              self.gestures = {}
              self.current_points = []
              self.velocity_tracker = VelocityTracker()
              
          def register_gesture(self, name, pattern):
              """Register custom gesture pattern"""
              self.gestures[name] = pattern
              
          def on_touch_start(self, x, y):
              """Begin gesture tracking"""
              self.current_points = [(x, y, time.time())]
              self.velocity_tracker.add_point(x, y)
              
          def on_touch_move(self, x, y):
              """Track gesture movement"""
              self.current_points.append((x, y, time.time()))
              self.velocity_tracker.add_point(x, y)
              
              # Check for matching gestures
              if gesture := self.recognize_gesture():
                  self.trigger_gesture(gesture)
                  
          def recognize_gesture(self):
              """Pattern matching for gestures"""
              if len(self.current_points) < 3:
                  return None
                  
              # Swipe detection
              if self.is_swipe():
                  direction = self.get_swipe_direction()
                  return f"swipe_{direction}"
                  
              # Pinch detection
              if self.is_pinch():
                  return "pinch_zoom"
                  
              # Custom gesture matching
              for name, pattern in self.gestures.items():
                  if pattern.matches(self.current_points):
                      return name
                      
              return None
      ```

################################################################################
# INTELLIGENT ERROR RECOVERY
################################################################################

error_recovery:
  graceful_degradation:
    """Automatic fallback strategies"""
    implementation: |
      ```python
      class ResilientUI:
          def __init__(self):
              self.fallback_chain = [
                  self.try_hardware_acceleration,
                  self.try_software_rendering,
                  self.try_basic_mode,
                  self.show_text_fallback
              ]
              
          def initialize(self):
              """Try initialization strategies in order"""
              for strategy in self.fallback_chain:
                  try:
                      return strategy()
                  except Exception as e:
                      self.log_fallback_attempt(strategy.__name__, e)
                      continue
                      
              # All strategies failed
              self.show_emergency_ui()
              
          def try_hardware_acceleration(self):
              """Attempt GPU-accelerated rendering"""
              # Check GPU availability
              if not self.check_gpu_available():
                  raise RuntimeError("No GPU available")
                  
              # Initialize with hardware acceleration
              return self.init_gpu_renderer()
              
          def try_software_rendering(self):
              """Fall back to CPU rendering"""
              return self.init_software_renderer()
              
          def auto_recover_from_error(self, error):
              """Intelligent error recovery"""
              recovery_strategies = {
                  MemoryError: self.reduce_memory_usage,
                  ConnectionError: self.enable_offline_mode,
                  PermissionError: self.request_elevated_permissions,
                  RenderingError: self.switch_renderer
              }
              
              for error_type, strategy in recovery_strategies.items():
                  if isinstance(error, error_type):
                      return strategy()
                      
              # Unknown error - try generic recovery
              return self.generic_recovery()
      ```

################################################################################
# ACCESSIBILITY FIRST DESIGN
################################################################################

accessibility_engine:
  wcag_compliance:
    """Built-in WCAG AA compliance"""
    implementation: |
      ```python
      class AccessibleWidget:
          def __init__(self):
              self.aria_properties = {}
              self.keyboard_shortcuts = {}
              self.focus_order = []
              
          def ensure_accessibility(self):
              """Automatic accessibility enhancement"""
              self.add_screen_reader_support()
              self.ensure_keyboard_navigation()
              self.validate_color_contrast()
              self.add_focus_indicators()
              
          def add_screen_reader_support(self):
              """Screen reader compatibility"""
              # Set accessible name
              if not self.aria_properties.get('label'):
                  self.aria_properties['label'] = self.generate_label()
                  
              # Set role
              if not self.aria_properties.get('role'):
                  self.aria_properties['role'] = self.detect_role()
                  
              # Add state announcements
              self.setup_state_announcements()
              
          def ensure_keyboard_navigation(self):
              """Complete keyboard support"""
              # Tab navigation
              self.make_focusable()
              
              # Arrow key navigation
              self.add_arrow_navigation()
              
              # Keyboard shortcuts
              self.register_shortcuts()
              
          def validate_color_contrast(self):
              """WCAG color contrast validation"""
              fg = self.get_foreground_color()
              bg = self.get_background_color()
              
              ratio = self.calculate_contrast_ratio(fg, bg)
              
              if ratio < 4.5:  # WCAG AA requirement
                  self.auto_adjust_colors(fg, bg)
      ```

################################################################################
# HARDWARE OPTIMIZATION
################################################################################

hardware_optimization:
  meteor_lake_specific:
    """Optimized for Intel Core Ultra 7 155H"""
    p_core_usage: |
      ```python
      import os
      import psutil
      
      class HardwareOptimizer:
          def __init__(self):
              self.p_cores = list(range(0, 12))  # P-core threads
              self.e_cores = list(range(12, 22))  # E-core threads
              
          def optimize_for_ui(self):
              """Pin UI thread to P-cores for responsiveness"""
              # UI thread on P-core for 26% better performance
              os.sched_setaffinity(0, {0, 1})  # First P-core
              
              # Worker threads on E-cores
              for worker_id, worker in enumerate(self.workers):
                  core = self.e_cores[worker_id % len(self.e_cores)]
                  os.sched_setaffinity(worker.pid, {core})
                  
          def setup_rendering_pipeline(self):
              """Optimal core allocation for rendering"""
              # Main render thread: P-core
              self.render_thread.set_affinity(self.p_cores[0])
              
              # GPU command submission: P-core
              self.gpu_thread.set_affinity(self.p_cores[1])
              
              # Asset loading: E-cores
              self.asset_threads.set_affinity(self.e_cores)
      ```

################################################################################
# DEVELOPMENT WORKFLOW OPTIMIZATION
################################################################################

## Development Workflow Optimization

### Hot Reload
Live UI updates during development

```python
class HotReloadUI:
    def __init__(self):
        self.watcher = FileWatcher()
        self.ui_cache = {}
        
    def enable_hot_reload(self):
        """Watch for file changes and reload UI"""
        self.watcher.watch("*.py", self.reload_module)
        self.watcher.watch("*.ui", self.reload_ui)
        self.watcher.watch("*.qss", self.reload_styles)
        
    def reload_module(self, filepath):
        """Hot-reload Python modules"""
        import importlib
        module_name = self.path_to_module(filepath)
        
        try:
            # Reload module
            module = importlib.reload(sys.modules[module_name])
            
            # Update UI components
            self.update_components(module)
            
            # Preserve state
            self.restore_state()
            
        except Exception as e:
            self.show_reload_error(e)
```
      
### Visual Debugging
Built-in debugging overlays

```python
class VisualDebugger:
    def __init__(self):
        self.overlays = {}
        self.enabled = False
        
    def toggle_debug_mode(self):
        """F12 to toggle debug overlays"""
        self.enabled = not self.enabled
        
        if self.enabled:
            self.show_widget_boundaries()
            self.show_layout_guides()
            self.show_performance_metrics()
            self.show_event_flow()
        else:
            self.hide_all_overlays()
            
    def show_performance_metrics(self):
        """Real-time performance overlay"""
        overlay = self.create_overlay("performance")
        overlay.add_metric("FPS", self.get_fps)
        overlay.add_metric("Frame Time", self.get_frame_time)
        overlay.add_metric("Memory", self.get_memory_usage)
        overlay.add_metric("CPU", self.get_cpu_usage)
```

################################################################################
# COMMUNICATION SYSTEM INTEGRATION v3.0
################################################################################

communication:
  protocol: ultra_fast_binary_v3
  capabilities:
    throughput: 4.2M_msg_sec
    latency: 200ns_p99
    
  tandem_execution:
    supported_modes:
      - INTELLIGENT      # Default: Python orchestrates, C executes
      - PYTHON_ONLY     # Fallback when C unavailable
      - REDUNDANT       # Both layers for critical operations
      - CONSENSUS       # Both must agree on results
      
    fallback_strategy:
      when_c_unavailable: PYTHON_ONLY
      when_performance_degraded: PYTHON_ONLY
      when_consensus_fails: RETRY_PYTHON
      max_retries: 3
      
    python_implementation:
      module: "agents.src.python.pygui_impl"
      class: "PYGUIPythonExecutor"
      capabilities:
        - "Full PYGUI functionality in Python"
        - "Async execution support"
        - "Error recovery and retry logic"
        - "Progress tracking and reporting"
      performance: "100-500 ops/sec"
      
    c_implementation:
      binary: "src/c/pygui_agent"
      shared_lib: "libpygui.so"
      capabilities:
        - "High-speed execution"
        - "Binary protocol support"
        - "Hardware optimization"
      performance: "10K+ ops/sec"
      
  integration:
    auto_register: true
    binary_protocol: "binary-communications-system/ultra_hybrid_enhanced.c"
    discovery_service: "src/c/agent_discovery.c"
    message_router: "src/c/message_router.c"
    runtime: "src/c/unified_agent_runtime.c"
    
  ipc_methods:
    CRITICAL: shared_memory_50ns
    HIGH: io_uring_500ns
    NORMAL: unix_sockets_2us
    LOW: mmap_files_10us
    BATCH: dma_regions
    
  message_patterns:
    - publish_subscribe
    - request_response
    - work_queues
    
  security:
    authentication: JWT_RS256_HS256
    authorization: RBAC_4_levels
    encryption: TLS_1.3
    integrity: HMAC_SHA256
    
  monitoring:
    prometheus_port: 9551
    grafana_dashboard: true
    health_check: "/health/ready"
    metrics_endpoint: "/metrics"

################################################################################
# FALLBACK EXECUTION PATTERNS
################################################################################

fallback_patterns:
  python_only_execution:
    implementation: |
      class PYGUIPythonExecutor:
          def __init__(self):
              self.cache = {}
              self.metrics = {}
              
          async def execute_command(self, command):
              """Execute PYGUI commands in pure Python"""
              try:
                  result = await self.process_command(command)
                  self.metrics['success'] += 1
                  return result
              except Exception as e:
                  self.metrics['errors'] += 1
                  return await self.handle_error(e, command)
                  
          async def process_command(self, command):
              """Process specific command types"""
              # Agent-specific implementation
              pass
              
          async def handle_error(self, error, command):
              """Error recovery logic"""
              # Retry logic
              for attempt in range(3):
                  try:
                      return await self.process_command(command)
                  except:
                      await asyncio.sleep(2 ** attempt)
              raise error
    
  graceful_degradation:
    triggers:
      - "C layer timeout > 1000ms"
      - "C layer error rate > 5%"
      - "Binary bridge disconnection"
      - "Memory pressure > 80%"
      
    actions:
      immediate: "Switch to PYTHON_ONLY mode"
      cache_results: "Store recent operations"
      reduce_load: "Limit concurrent operations"
      notify_user: "Alert about degraded performance"
      
  recovery_strategy:
    detection: "Monitor C layer every 30s"
    validation: "Test with simple command"
    reintegration: "Gradually shift load to C"
    verification: "Compare outputs for consistency"


################################################################################
# SUCCESS METRICS
################################################################################

success_metrics:
  performance_guarantees:
    startup_time: "<500ms to first paint"
    frame_rate: "60 FPS minimum, 144 FPS capable"
    input_latency: "<16ms response time"
    memory_usage: "<100MB for simple, <500MB for complex"
    
  quality_metrics:
    accessibility: "WCAG AA compliant"
    cross_platform: ">95% feature parity"
    error_recovery: "100% graceful degradation"
    test_coverage: ">90% code coverage"
    
  developer_experience:
    time_to_hello_world: "<5 minutes"
    hot_reload_speed: "<500ms"
    documentation_coverage: "100% public API"
    example_availability: "Every pattern demonstrated"

################################################################################
# QUICK START TEMPLATES
################################################################################

quick_start:
  minimal_app: |
    ```python
    # 5 lines to working GUI
    import PySimpleGUI as sg
    
    layout = [[sg.Text("Hello")], [sg.Button("OK")]]
    window = sg.Window("App", layout)
    event, values = window.read()
    window.close()
    ```
    
  data_dashboard: |
    ```python
    # 10 lines to interactive dashboard
    import streamlit as st
    import pandas as pd
    
    st.title("Dashboard")
    data = pd.read_csv("data.csv")
    
    col = st.selectbox("Select column", data.columns)
    st.line_chart(data[col])
    
    if st.button("Refresh"):
        st.rerun()
    ```
    
  high_performance: |
    ```python
    # Immediate mode 60 FPS app
    import dearpygui.dearpygui as dpg
    
    dpg.create_context()
    with dpg.window(label="High Performance"):
        dpg.add_text("60 FPS Guaranteed")
        
    dpg.create_viewport()
    dpg.setup_dearpygui()
    dpg.show_viewport()
    dpg.start_dearpygui()
    ```

################################################################################
# COMMAND REFERENCE
################################################################################

commands:
  scaffold_project: |
    ```bash
    # Auto-generate optimized project structure
    pygui init --framework auto --type dashboard
    pygui add-component --type chart --name RealTimeChart
    pygui test --coverage --accessibility
    pygui build --platform all --optimize
    ```
    
  performance_profile: |
    ```bash
    # Profile and optimize
    pygui profile --duration 60 --output profile.html
    pygui optimize --target-fps 60 --max-memory 100M
    pygui benchmark --compare baseline.json
    ```
    
  deployment: |
    ```bash
    # Build and distribute
    pygui package --format appimage --sign
    pygui package --format exe --installer nsis
    pygui package --format dmg --notarize
    pygui deploy --platform all --auto-update
    ```
