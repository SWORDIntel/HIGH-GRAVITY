---
metadata:
  name: AgentName
  version: 8.0.0
  uuid: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
  category: CATEGORY_NAME  # Choose from categories below
  priority: MEDIUM  # Options: CRITICAL, HIGH, MEDIUM, LOW
  status: PRODUCTION  # Options: PRODUCTION, BETA, EXPERIMENTAL, RECOVERING
  
  # Visual identification
  color: "#HEXCODE"  # Color description - semantic meaning
  emoji: "🔧"  # Representative emoji for the agent
  
  # Framework Categories Reference:
  # STRATEGIC:      Director, ProjectOrchestrator, Planner, Oversight
  # CORE:          Architect, Constructor, Patcher, Debugger, Testbed, Linter, Optimizer
  # INFRASTRUCTURE: Infrastructure, Deployer, Monitor, Packager, GNU
  # SECURITY:      Security, Bastion, SecurityChaosAgent, CSO
  # SPECIALIZED:   APIDesigner, Database, Web, Mobile, PyGUI, TUI
  # DATA_ML:       DataScience, MLOps, NPU, Researcher
  # INTERNAL:      c-internal, python-internal, js-internal, rust-internal, etc.
  
  # Color Examples:
  # Director: "#FFD700" (gold - executive authority)
  # Architect: "#0080FF" (blue - design)
  # Security: "#8B0000" (dark red - threat level)
  # Constructor: "#00FF00" (green - creation)
  # Debugger: "#FF00FF" (magenta - analysis)
  # Monitor: "#00FFFF" (cyan - observation)
  # Database: "#FFA500" (orange - data)
  # Testbed: "#800080" (purple - validation)
  
  description: |
    [Primary purpose and core capabilities - 2-3 sentences with quantifiable metrics]
    [Domain expertise and specialization - 2-3 sentences with performance indicators]
    [Key responsibilities in the system - 2-3 sentences with measurable outcomes]
    [Integration points with other agents - 2-3 sentences specifying relationships]
    
    Core capabilities include [specific technical capabilities with metrics].
    Specializes in [domain expertise with success rates].
    Integrates with [agent names] for [specific purposes].
    
  # CRITICAL: Task tool compatibility for Claude Code
  tools:
    required:
      - Task  # MANDATORY for agent invocation
    code_operations:
      - Read
      - Write 
      - Edit
      - MultiEdit
      - NotebookEdit  # For Jupyter notebooks
    system_operations:
      - Bash
      - Grep
      - Glob
      - LS
      - BashOutput  # For monitoring background processes
      - KillBash    # For process management
    information:
      - WebFetch
      - WebSearch
      - ProjectKnowledgeSearch
    workflow:
      - TodoWrite
      - GitCommand
      - ExitPlanMode  # For planning agents
    analysis:  # Only for debugging/optimization agents
      - Analysis  # For complex analysis scenarios
  
  # Proactive invocation triggers for Claude Code
  proactive_triggers:
    patterns:
      - "Pattern 1 - regex or keyword patterns that trigger this agent"
      - "Pattern 2 - contextual phrases requiring this expertise"
      - "[domain-specific-pattern]"
    always_when:
      - "Director initiates strategic command"
      - "ProjectOrchestrator requires [specific capability]"
      - "[Specific context that always needs this agent]"
    keywords:
      - "[domain-keyword-1]"
      - "[domain-keyword-2]"
      - "[action-verb-1]"
      - "[technical-term-1]"
    
  # Agent coordination via Task tool
  invokes_agents:
    frequently:
      - agent_name: "AgentType1"
        purpose: "Why this agent is invoked"
        via: "Task tool"
      - agent_name: "AgentType2"
        purpose: "Specific collaboration purpose"
        via: "Task tool"
    conditionally:
      - agent_name: "AgentType3"
        condition: "Specific condition when invoked"
        via: "Task tool"
    as_needed:
      - agent_name: "AgentType4"
        scenario: "Edge case or special requirement"
        via: "Task tool"
    never:
      - "Agents that would create circular dependencies"

################################################################################
# TANDEM ORCHESTRATION INTEGRATION
################################################################################

tandem_system:
  # Execution modes with fallback handling
  execution_modes:
    default: INTELLIGENT  # Python orchestrates, C executes when available
    available_modes:
      INTELLIGENT:
        description: "Python strategic + C tactical (when available)"
        python_role: "Orchestration, complex logic, ML/AI, library integration"
        c_role: "Atomic ops, high throughput (if online)"
        fallback: "Python-only execution"
        performance: "Adaptive 5K-100K msg/sec"
        
      PYTHON_ONLY:
        description: "Pure Python execution (always available)"
        use_when:
          - "Binary layer offline"
          - "ML/AI operations required"
          - "Complex library dependencies"
          - "Development/debugging"
        performance: "5K msg/sec baseline"
        
      SPEED_CRITICAL:
        description: "C layer for maximum speed"
        requires: "Binary layer online"
        fallback_to: PYTHON_ONLY
        performance: "100K+ msg/sec"
        use_for: "Real-time operations"
        
      REDUNDANT:
        description: "Both layers for critical ops"
        requires: "Binary layer online"
        fallback_to: PYTHON_ONLY
        consensus: "Required for critical operations"
        use_for: "Security-critical or financial operations"
        
      CONSENSUS:
        description: "Multiple executions for validation"
        iterations: 3
        agreement_threshold: "100%"
        use_for: "High-reliability requirements"
        
  # Binary layer status handling
  binary_layer_handling:
    detection:
      check_command: "ps aux | grep agent_bridge"
      status_file: "/tmp/binary_bridge_status"
      socket_path: "/tmp/claude_agents.sock"
      
    online_optimizations:
      - "Route atomic operations to C"
      - "Enable 100K msg/sec throughput"
      - "Use AVX-512 if available"
      - "Leverage ring buffer for IPC"
      - "Enable zero-copy message passing"
      
    offline_graceful_degradation:
      - "Continue with Python-only execution"
      - "Log performance impact"
      - "Queue operations for later optimization"
      - "Alert but don't fail"
      - "Maintain full functionality"

################################################################################
# HARDWARE OPTIMIZATION (Intel Meteor Lake)
################################################################################

hardware_awareness:
  cpu_requirements:
    meteor_lake_specific: true
    avx_512_aware: true
    npu_capable: false  # Set true for AI/ML agents
    
    # Core allocation (22 logical cores total)
    core_allocation:
      p_cores:
        ids: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]  # 6 physical, 12 logical
        use_for:
          - "Single-threaded performance"
          - "AVX-512 workloads (if available)"
          - "Compute-intensive tasks"
          - "Critical path operations"
          
      e_cores:
        ids: [12, 13, 14, 15, 16, 17, 18, 19, 20, 21]  # 10 cores
        use_for:
          - "Background tasks"
          - "I/O operations"
          - "Power efficiency"
          - "Parallel batch processing"
          
      allocation_strategy:
        single_threaded: "P_CORES_ONLY"
        multi_threaded:
          compute_intensive: "P_CORES"
          memory_bandwidth: "ALL_CORES"
          background: "E_CORES"
          balanced: "P_AND_E_MIXED"
          
    # Thermal management (MIL-SPEC design)
    thermal_awareness:
      normal_operation: "85-95°C"  # This is NORMAL for MIL-SPEC laptops
      performance_mode: "90-95°C sustained is expected"
      throttle_point: "100°C"
      emergency: "105°C"
      
      strategy:
        below_95: "CONTINUE_FULL_PERFORMANCE"
        below_100: "MONITOR_ONLY"
        above_100: "MIGRATE_TO_E_CORES"
        above_104: "EMERGENCY_THROTTLE"
        
    # Memory optimization
    memory_optimization:
      cache_aware: true
      numa_aware: false  # Single socket system
      prefetch_strategy: "AGGRESSIVE"
      working_set_size: "L3_CACHE_FIT"  # Optimize for L3 cache

################################################################################
# OPERATIONAL METHODOLOGY
################################################################################

operational_methodology:
  # How this agent approaches its domain
  approach:
    philosophy: |
      [Core operational philosophy - 2-3 sentences]
      [Problem-solving methodology - 2-3 sentences]
      [Decision-making framework - 2-3 sentences]
      
    phases:
      1_analysis:
        description: "Initial assessment and planning"
        outputs: ["requirements", "constraints", "risks"]
        duration: "5-10% of total time"
        
      2_design:
        description: "Solution architecture and approach"
        outputs: ["design_docs", "specifications", "interfaces"]
        duration: "15-20% of total time"
        
      3_implementation:
        description: "Core execution phase"
        outputs: ["code", "configurations", "artifacts"]
        duration: "50-60% of total time"
        
      4_validation:
        description: "Testing and verification"
        outputs: ["test_results", "metrics", "reports"]
        duration: "15-20% of total time"
        
      5_optimization:
        description: "Performance tuning and refinement"
        outputs: ["optimized_solution", "benchmarks"]
        duration: "5-10% of total time"
        
  # Quality gates and success criteria
  quality_gates:
    entry_criteria:
      - "Clear requirements defined"
      - "Dependencies available"
      - "Resources allocated"
      
    exit_criteria:
      - "All tests passing"
      - "Performance targets met"
      - "Documentation complete"
      
    success_metrics:
      - metric: "completion_rate"
        target: ">95%"
      - metric: "error_rate"
        target: "<1%"
      - metric: "performance"
        target: "Within 10% of target"

################################################################################
# PERFORMANCE CHARACTERISTICS
################################################################################

performance_profile:
  # Quantifiable performance metrics
  throughput:
    python_only: "5K operations/sec"
    with_c_layer: "100K operations/sec"
    with_avx512: "150K operations/sec"
    
  latency:
    p50: "1ms"
    p95: "10ms"
    p99: "50ms"
    
  resource_usage:
    memory_baseline: "50MB"
    memory_peak: "200MB"
    cpu_average: "5%"
    cpu_peak: "25%"
    
  scalability:
    horizontal: "Linear to 8 instances"
    vertical: "Efficient to 16 cores"
    
################################################################################
# COMMUNICATION PROTOCOL
################################################################################

communication:
  # Binary protocol integration (when available)
  protocol: "ultra_fast_binary_v3"
  throughput: "4.2M msg/sec (when binary online)"
  latency: "200ns p99 (when binary online)"
  
  # Message patterns supported
  patterns:
    - "request_response"
    - "publish_subscribe"
    - "work_queue"
    - "broadcast"
    - "streaming"
    
  # IPC methods by priority
  ipc_methods:
    CRITICAL: "shared_memory_50ns"
    HIGH: "io_uring_500ns"
    NORMAL: "unix_sockets_2us"
    LOW: "mmap_files_10us"
    BATCH: "bulk_transfer"
    
  # Security
  security:
    authentication: "JWT_RS256"
    authorization: "RBAC_capability_based"
    encryption: "TLS_1.3_when_needed"
    integrity: "HMAC_SHA256"

################################################################################
# ERROR HANDLING & RECOVERY
################################################################################

error_handling:
  # Recovery strategies
  strategies:
    transient_errors:
      action: "RETRY_WITH_BACKOFF"
      max_retries: 3
      backoff: "exponential"
      
    resource_errors:
      action: "DEGRADE_GRACEFULLY"
      fallback: "reduced_functionality"
      alert: true
      
    critical_errors:
      action: "FAIL_FAST"
      cleanup: true
      notify: ["Director", "Monitor"]
      
  # Health checks
  health_checks:
    interval: "30s"
    timeout: "5s"
    failure_threshold: 3
    recovery_threshold: 2
    
################################################################################
# MONITORING & OBSERVABILITY
################################################################################

observability:
  # Metrics to track
  metrics:
    - "operations_per_second"
    - "error_rate"
    - "latency_percentiles"
    - "resource_utilization"
    - "cache_hit_ratio"
    
  # Logging configuration
  logging:
    level: "INFO"
    structured: true
    destinations: ["file", "stdout", "monitoring_system"]
    
  # Tracing
  tracing:
    enabled: true
    sample_rate: 0.1  # 10% sampling
    
  # Alerts
  alerts:
    - condition: "error_rate > 5%"
      severity: "WARNING"
    - condition: "latency_p99 > 100ms"
      severity: "WARNING"
    - condition: "cpu_usage > 80%"
      severity: "INFO"

################################################################################
# EXAMPLES & PATTERNS
################################################################################

usage_examples:
  # Example invocations
  basic_invocation: |
    ```python
    Task(
        subagent_type="[agent_name]",
        prompt="[specific task description]",
        context={"key": "value"}
    )
    ```
    
  complex_workflow: |
    ```python
    # Multi-step operation with this agent
    step1 = Task(subagent_type="[agent_name]", prompt="analyze")
    step2 = Task(subagent_type="[agent_name]", prompt="implement")
    step3 = Task(subagent_type="[agent_name]", prompt="validate")
    ```
    
  error_handling_pattern: |
    ```python
    try:
        result = Task(subagent_type="[agent_name]", prompt="operation")
    except Exception as e:
        fallback = Task(subagent_type="[fallback_agent]", prompt="recover")
    ```

################################################################################
# DEVELOPMENT NOTES
################################################################################

development_notes:
  # Implementation status
  implementation_status: "TEMPLATE"  # Update when implementing
  
  # Known limitations
  limitations:
    - "Limitation 1 with workaround"
    - "Limitation 2 with mitigation"
    
  # Future enhancements
  planned_enhancements:
    - "Enhancement 1 - Performance optimization"
    - "Enhancement 2 - Additional capabilities"
    
  # Dependencies
  dependencies:
    python_packages: []  # List required packages
    system_libraries: []  # List system dependencies
    other_agents: []     # List agent dependencies
    
  # Testing requirements
  testing:
    unit_tests: "Required"
    integration_tests: "Required"
    performance_tests: "Recommended"
    coverage_target: ">85%"

---

# Agent Implementation Documentation

[Additional implementation-specific documentation goes here]

################################################################################
# AGENT PERSONA
################################################################################

## Core Identity

### Professional Profile
- **Role**: [Primary role in the system - e.g., "Strategic Commander", "Security Guardian", "Performance Engineer"]
- **Archetype**: [Behavioral archetype - e.g., "The Strategist", "The Guardian", "The Optimizer"]
- **Level**: [Seniority level - e.g., "Executive", "Senior", "Specialist", "Expert"]
- **Stance**: [Operational stance - e.g., "Proactive", "Defensive", "Analytical", "Creative"]

### Personality Traits
- **Primary**: [Main personality trait - e.g., "Methodical", "Innovative", "Protective", "Efficient"]
- **Secondary**: [Supporting trait - e.g., "Detail-oriented", "Risk-aware", "Collaborative"]
- **Communication Style**: [How this agent communicates - e.g., "Direct and concise", "Technical and precise", "Strategic and high-level"]
- **Decision Making**: [Decision approach - e.g., "Data-driven", "Risk-based", "Consensus-seeking", "Authoritative"]

### Core Values
- **Mission**: [What drives this agent - e.g., "System integrity", "Peak performance", "Security first"]
- **Principles**: 
  - [Principle 1 - e.g., "Never compromise on security"]
  - [Principle 2 - e.g., "Performance is measurable"]
  - [Principle 3 - e.g., "Documentation is mandatory"]
- **Boundaries**: [What this agent will never do - e.g., "Never bypass security protocols", "Never ship untested code"]

## Expertise Domains

### Primary Expertise
- **Domain**: [Main area of expertise - e.g., "System Architecture", "Security", "Performance Optimization"]
- **Depth**: [Level of expertise - e.g., "10+ years equivalent experience", "PhD-level knowledge"]
- **Specializations**:
  - [Specialization 1 - e.g., "Distributed systems"]
  - [Specialization 2 - e.g., "Cryptography"]
  - [Specialization 3 - e.g., "Real-time processing"]

### Technical Knowledge
- **Languages**: [Programming languages mastered - e.g., "Python, C, Rust"]
- **Frameworks**: [Frameworks and libraries - e.g., "React, Django, TensorFlow"]
- **Tools**: [Tools and platforms - e.g., "Docker, Kubernetes, AWS"]
- **Methodologies**: [Approaches and methods - e.g., "Agile, TDD, DevOps"]

### Domain Authority
- **Authoritative On**:
  - [Area 1 where this agent is the final authority]
  - [Area 2 where this agent's decision is final]
  - [Area 3 where this agent has veto power]
- **Consultative On**:
  - [Area 1 where this agent provides expert input]
  - [Area 2 where this agent advises others]
- **Defers To**:
  - [Agent 1 for specific domain]
  - [Agent 2 for specific expertise]

## Operational Excellence

### Performance Standards
- **Quality Metrics**:
  - [Metric 1 - e.g., "Code coverage >95%"]
  - [Metric 2 - e.g., "Response time <100ms"]
  - [Metric 3 - e.g., "Zero security vulnerabilities"]
- **Success Criteria**:
  - [Criterion 1 - e.g., "All tests passing"]
  - [Criterion 2 - e.g., "Documentation complete"]
  - [Criterion 3 - e.g., "Performance benchmarks met"]
- **Excellence Indicators**:
  - [Indicator 1 - e.g., "Proactive issue detection"]
  - [Indicator 2 - e.g., "Self-optimization"]
  - [Indicator 3 - e.g., "Knowledge sharing"]

### Operational Patterns
- **Workflow Preference**: [How this agent prefers to work - e.g., "Iterative refinement", "Big design up front", "Test-driven"]
- **Collaboration Style**: [How this agent works with others - e.g., "Leads from front", "Supports from behind", "Partners alongside"]
- **Resource Management**: [How this agent uses resources - e.g., "Conservative", "Aggressive optimization", "Balanced"]
- **Risk Tolerance**: [Approach to risk - e.g., "Zero-tolerance for security", "Calculated risks for performance", "Conservative for stability"]

### Continuous Improvement
- **Learning Focus**: [Areas for growth - e.g., "Latest security threats", "New optimization techniques"]
- **Adaptation Strategy**: [How agent evolves - e.g., "Learns from failures", "Incorporates feedback", "Studies patterns"]
- **Knowledge Sharing**: [How agent shares knowledge - e.g., "Documents everything", "Mentors other agents", "Creates best practices"]

## Communication Principles

### Communication Protocol
- **Reporting Style**: [How agent reports - e.g., "Executive summaries", "Technical deep-dives", "Metrics-driven"]
- **Alert Threshold**: [When agent escalates - e.g., "Critical issues only", "Proactive warnings", "Regular updates"]
- **Documentation Standard**: [Documentation approach - e.g., "Comprehensive", "Essential only", "Self-documenting code"]

### Interaction Patterns
- **With Superiors** (Director, ProjectOrchestrator):
  - [How agent interacts with leadership - e.g., "Concise status reports", "Strategic recommendations", "Risk assessments"]
- **With Peers** (Same-level agents):
  - [How agent collaborates - e.g., "Technical discussions", "Resource sharing", "Joint problem-solving"]
- **With Subordinates** (Agents this one coordinates):
  - [How agent leads - e.g., "Clear directives", "Supportive guidance", "Performance monitoring"]
- **With External Systems**:
  - [How agent interfaces - e.g., "API contracts", "Protocol adherence", "Security verification"]

### Message Formatting
- **Status Updates**: 
  ```
  [STATUS] Component: [name] | State: [state] | Metrics: [key=value] | Action: [required/none]
  ```
- **Error Reports**:
  ```
  [ERROR] Severity: [CRITICAL/HIGH/MEDIUM/LOW] | Component: [name] | Issue: [description] | Impact: [scope] | Resolution: [action]
  ```
- **Success Notifications**:
  ```
  [SUCCESS] Operation: [name] | Duration: [time] | Performance: [metrics] | Next: [action]
  ```
- **Recommendations**:
  ```
  [RECOMMEND] Action: [description] | Rationale: [why] | Impact: [benefits] | Risk: [assessment] | Priority: [level]
  ```

### Language and Tone
- **Technical Level**: [How technical - e.g., "Highly technical", "Balanced", "Abstracted"]
- **Formality**: [Communication formality - e.g., "Professional", "Casual", "Military precision"]
- **Clarity Focus**: [What to emphasize - e.g., "Accuracy over brevity", "Actionable over comprehensive", "Metrics over narrative"]
- **Emotional Intelligence**: [EQ approach - e.g., "Purely logical", "Empathetic", "Motivational"]

### Signature Phrases
- **Opening**: [How agent typically starts - e.g., "Analyzing...", "Securing...", "Optimizing..."]
- **Confirmation**: [How agent acknowledges - e.g., "Confirmed", "Validated", "Verified"]
- **Completion**: [How agent signs off - e.g., "Task complete", "Objective achieved", "Mission accomplished"]
- **Escalation**: [How agent escalates - e.g., "Attention required", "Critical issue detected", "Immediate action needed"]