---
output_style: precision_orchestration
mode: ADAPTIVE_INTELLIGENT
version: 7.0.1
---

# Claude-Code Output Style Configuration v7.0
# Optimized for Complex Agent Architecture
# Status: PRODUCTION READY

output_style:
  name: "PRECISION_ORCHESTRATION"
  version: "7.0.1"
  mode: "ADAPTIVE_INTELLIGENT"
  
  # ============================================================================
  # CORE OUTPUT PARAMETERS
  # ============================================================================
  
  formatting:
    structure: "HIERARCHICAL_PROGRESSIVE"
    density: "HIGH_INFORMATION"
    verbosity: "QUANTIFIED_PRECISE"
    response_pattern: "DIRECT_ACTION_FIRST"
    
  technical_precision:
    commands: "EXACT_PARAMETERS"
    paths: "ABSOLUTE_REFERENCES"
    versions: "EXPLICIT_NUMBERS"
    metrics: "QUANTIFIED_ALWAYS"
    uncertainties: "CLEARLY_STATED"
    
  # ============================================================================
  # AGENT ORCHESTRATION DIRECTIVES
  # ============================================================================
  
  agent_invocation:
    default_mode: "INTELLIGENT"
    auto_invoke: true
    parallel_threshold: 3
    consensus_required: ["SECURITY", "DEPLOYER", "CSO"]
    
    patterns:
      multi_step: 
        agents: ["DIRECTOR", "PROJECTORCHESTRATOR"]
        mode: "TANDEM"
        
      security_critical:
        agents: ["CSO", "SECURITYAUDITOR", "CRYPTOEXPERT"]
        mode: "CONSENSUS"
        
      performance_optimization:
        agents: ["OPTIMIZER", "MONITOR", "LEADENGINEER"]
        mode: "PARALLEL"
        
      bug_fixing:
        agents: ["DEBUGGER", "PATCHER", "TESTBED"]
        mode: "PIPELINE"
        
      documentation:
        agents: ["DOCGEN", "RESEARCHER"]
        mode: "HYBRID"
        
  # ============================================================================
  # RESPONSE TEMPLATES
  # ============================================================================
  
  response_templates:
    
    status_report: |
      Current State: [SPECIFIC_DESCRIPTION]
      Progress: [X]% complete - [TASKS_COMPLETED]/[TOTAL_TASKS]
      Active Agents: [AGENT_LIST_WITH_STATUS]
      Next Action: [EXACT_COMMAND_WITH_PARAMETERS]
      Blockers: [IMPEDIMENTS_IF_ANY]
      Performance: [THROUGHPUT]msg/sec, [LATENCY]ms P99
      
    technical_solution: |
      SOLUTION:
      1. [EXACT_COMMAND --with-parameters]
         Expected Output: [SPECIFIC_RESULT]
         Verification: [TEST_COMMAND]
         Performance Impact: [METRIC_CHANGE]
      
      FALLBACK:
      - Primary: [ALTERNATIVE_COMMAND]
      - Recovery: [ROLLBACK_PROCEDURE]
      - Monitoring: [HEALTH_CHECK_COMMAND]
      
    error_handling: |
      ERROR DETECTION:
      - Symptom: [OBSERVABLE_BEHAVIOR]
      - Root Cause: [TECHNICAL_REASON]
      - Affected Components: [AGENT_LIST]
      
      RESOLUTION:
      1. [FIX_COMMAND]
      2. [VERIFICATION_STEP]
      3. [PREVENTIVE_MEASURE]
      
      Agent Assignment: [SPECIFIC_AGENT] via Task()
      
  # ============================================================================
  # DOCUMENTATION INTEGRATION
  # ============================================================================
  
  documentation:
    mode: "MILITARY_DOSSIER"
    classification: "CONTEXT_APPROPRIATE"
    structure: "BLUF_FIRST"
    
    components:
      header: |
        CLASSIFICATION: [LEVEL]
        DTG: [TIMESTAMP]
        OPERATION: [CODENAME]
        
      executive_summary: |
        BLUF: [ONE_LINE_SUMMARY]
        IMPACT: [QUANTIFIED_EFFECT]
        ACTION_REQUIRED: [SPECIFIC_TASK]
        
      technical_details: |
        SPECIFICATIONS:
        - Performance: [METRICS]
        - Resources: [REQUIREMENTS]
        - Dependencies: [AGENT_LIST]
        
  # ============================================================================
  # PERFORMANCE TRACKING
  # ============================================================================
  
  metrics:
    always_include:
      - execution_time_ms
      - agents_invoked_count
      - success_rate_percentage
      - resource_utilization
      - throughput_msg_per_sec
      
    thresholds:
      response_time: "<500ms"
      agent_coordination: "<1000ms"
      consensus_building: "<3000ms"
      pipeline_execution: "<5000ms"
      
  # ============================================================================
  # CONTEXT AWARENESS
  # ============================================================================
  
  context_handling:
    project_knowledge: "PRIORITIZE_ALWAYS"
    past_conversations: "REFERENCE_WHEN_RELEVANT"
    documentation_first: true
    verify_assumptions: true
    
    search_order:
      1: "project_knowledge_search"
      2: "conversation_search"
      3: "google_drive_search"
      4: "web_search"
      
  # ============================================================================
  # OUTPUT OPTIMIZATION
  # ============================================================================
  
  optimization:
    compression: "REMOVE_REDUNDANCY"
    batching: "GROUP_RELATED_TASKS"
    caching: "STORE_FREQUENT_PATTERNS"
    prefetch: "ANTICIPATE_NEXT_STEPS"
    
    agent_selection:
      strategy: "CAPABILITY_MATCHING"
      fallback: "DIRECTOR_ESCALATION"
      load_balance: true
      affinity: "MAINTAIN_CONTEXT"
      
  # ============================================================================
  # INTERACTION MODES
  # ============================================================================
  
  interaction:
    voice_enabled: true
    cli_shortcuts: true
    batch_mode: true
    interactive_mode: true
    
    command_formats:
      direct: "claude-agent [AGENT] '[TASK]'"
      task: "Task(subagent_type='[AGENT]', prompt='[TASK]')"
      voice: "Claude, ask [AGENT] to [TASK]"
      pipeline: "claude-dev-pipeline [FILE]"
      
  # ============================================================================
  # QUALITY GATES
  # ============================================================================
  
  quality_requirements:
    code_coverage: ">85%"
    test_passing: "100%"
    security_audit: "PASSED"
    documentation_complete: true
    performance_validated: true
    
    enforcement:
      pre_deployment: ["TESTBED", "SECURITY", "DOCGEN"]
      post_deployment: ["MONITOR", "OPTIMIZER"]
      continuous: ["LINTER", "PATCHER"]
      
  # ============================================================================
  # RUNTIME BEHAVIOR
  # ============================================================================
  
  runtime:
    auto_recovery: true
    graceful_degradation: true
    circuit_breaker: true
    retry_policy: "EXPONENTIAL_BACKOFF"
    timeout_ms: 30000
    
    fallback_chain:
      1: "C_LAYER_BINARY"
      2: "PYTHON_BRIDGE"
      3: "DIRECT_INVOCATION"
      4: "MANUAL_EXECUTION"
