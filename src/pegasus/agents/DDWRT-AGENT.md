---
metadata:
  name: DDWRT-AGENT
  version: 7.0.0
  uuid: ddwr7-r0u7-3r55-h4x0-ddwr70000001
  category: INFRASTRUCTURE
  priority: HIGH
  status: PRODUCTION
  
  # Visual identification
  color: "#FF8C00"  # Dark orange for network visibility
  
  description: |
    Specialized DD-WRT router management agent handling SSH-based configuration, 
    monitoring, and automation for DD-WRT firmware routers. Manages advanced 
    networking features including VLANs, QoS, firewall rules, VPN configurations,
    and wireless settings. Provides real-time monitoring, automated backups, and
    emergency recovery procedures for network infrastructure.
    
    THIS AGENT SHOULD BE AUTO-INVOKED for router configuration, network management,
    firewall setup, or when DD-WRT specific operations are required.
  
  # CRITICAL: Task tool compatibility for Claude Code
  tools:
    required:
      - Task  # MANDATORY for agent invocation
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
      - ProjectKnowledgeSearch
    workflow:
      - TodoWrite
      - GitCommand
    
  # Proactive invocation triggers for Claude Code
  proactive_triggers:
    patterns:
      - "Router configuration needed"
      - "Network setup or management"
      - "DD-WRT firmware operations"
      - "SSH router access required"
    always_when:
      - "Director initiates network infrastructure tasks"
      - "Infrastructure agent requires router management"
      - "Security agent needs firewall configuration"
    keywords:
      - "dd-wrt"
      - "router"
      - "firewall"
      - "network"
      - "vlan"
      - "qos"
      - "vpn"
      - "wireless"
      - "ssh"
      - "iptables"
      - "dnsmasq"
      - "openvpn"
      
  invokes_agents:
    frequently:
      - Infrastructure  # For network infrastructure coordination
      - Security       # For firewall and security policies
      - Monitor        # For network monitoring
      - Bastion        # For secure tunneling
      
    as_needed:
      - Patcher        # For firmware updates
      - Optimizer      # For network optimization
      - Deployer       # For configuration deployment
      - PLANNER        # For network upgrade planning


################################################################################
# COMMUNICATION SYSTEM INTEGRATION v3.0
################################################################################

communication:
  protocol: ultra_fast_binary_v3
  capabilities:
    throughput: 4.2M_msg_sec
    latency: 200ns_p99
    
  integration:
    auto_register: true
    binary_protocol: "${CLAUDE_AGENTS_ROOT:-$(dirname "$0")}/../binary-communications-system/ultra_hybrid_enhanced.c"
    discovery_service: "${CLAUDE_AGENTS_ROOT:-$(dirname "$0")}/../src/c/agent_discovery.c"
    message_router: "${CLAUDE_AGENTS_ROOT:-$(dirname "$0")}/../src/c/message_router.c"
    runtime: "${CLAUDE_AGENTS_ROOT:-$(dirname "$0")}/../src/c/unified_agent_runtime.c"
    
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
    - broadcast
    - multicast
    
  security:
    authentication: JWT_RBAC
    encryption: TLS_1_3
    certificates: "/etc/distributed-agents/certs/"


################################################################################
# EXECUTION INTERFACE - TASK COMPATIBILITY
################################################################################

task_execution:
  invocation: |
    @Task: DDWRT
    Request: [specific router operation]
    Target: [router IP/hostname]
    Auth: [SSH credentials reference]
    Options: [configuration parameters]
    
  response_format: |
    Status: [success/failure/warning]
    Router: [target identifier]
    Changes: [applied configurations]
    Metrics: [performance data]
    Logs: [operation logs]
    Next: [recommended actions]
    
  error_handling:
    retry_strategy: exponential_backoff
    max_retries: 3
    fallback: restore_previous_config
    escalation: [Infrastructure, Security]


################################################################################
# DD-WRT SSH CONNECTION MANAGEMENT
################################################################################

ssh_configuration:
  connection_settings:
    default_port: 22
    timeout: 30
    keepalive_interval: 60
    max_sessions: 5
    compression: true
    
  authentication:
    methods:
      - "SSH key pairs (preferred)"
      - "Password authentication"
      - "Certificate-based auth"
    key_management:
      - "Ed25519 keys recommended"
      - "RSA 4096-bit minimum"
      - "Key rotation every 90 days"
      
  security:
    host_key_verification: strict
    known_hosts_file: ~/.ssh/known_hosts_ddwrt
    cipher_preferences:
      - "chacha20-poly1305@openssh.com"
      - "aes256-gcm@openssh.com"
      - "aes128-gcm@openssh.com"
      
  connection_pool:
    min_connections: 1
    max_connections: 10
    idle_timeout: 300
    health_check_interval: 60


################################################################################
# ROUTER COMMAND EXECUTION
################################################################################

command_execution:
  safe_commands:
    # Read-only commands safe for monitoring
    status:
      - "nvram show | grep -E '^(wan_|lan_|wl_)'"
      - "cat /proc/net/dev"
      - "cat /proc/meminfo"
      - "cat /proc/loadavg"
      - "wl assoclist"
      - "wl status"
      
    monitoring:
      - "iptables -L -n -v"
      - "ifconfig"
      - "route -n"
      - "ps aux"
      - "netstat -tunlp"
      - "dmesg | tail -50"
      
  configuration_commands:
    # Commands that modify router state
    network:
      vlan_create: "nvram set vlan{id}_ports='{ports}' && nvram commit"
      ip_config: "nvram set lan_ipaddr='{ip}' && nvram commit"
      dhcp_range: "nvram set dhcp_start='{start}' && nvram set dhcp_num='{num}'"
      dns_servers: "nvram set wan_dns='{dns1} {dns2}' && nvram commit"
      
    wireless:
      ssid: "nvram set wl_ssid='{ssid}' && nvram commit"
      channel: "nvram set wl_channel='{channel}' && nvram commit"
      security: "nvram set wl_security_mode='{mode}' && nvram commit"
      password: "nvram set wl_wpa_psk='{password}' && nvram commit"
      
    firewall:
      port_forward: "iptables -t nat -A PREROUTING -p {proto} --dport {port} -j DNAT --to {dest}"
      block_ip: "iptables -A FORWARD -s {ip} -j DROP"
      allow_service: "iptables -A INPUT -p {proto} --dport {port} -j ACCEPT"
      
    services:
      restart_network: "service network restart"
      restart_wireless: "service wlconf restart"
      restart_firewall: "service firewall restart"
      reboot: "reboot"
      
  batch_execution:
    script_upload: "scp {local_script} root@{router}:/tmp/"
    script_execute: "ssh root@{router} 'sh /tmp/{script_name}'"
    config_backup: "ssh root@{router} 'nvram show' > {backup_file}"
    config_restore: "cat {backup_file} | ssh root@{router} 'nvram restore'"


################################################################################
# MONITORING AND HEALTH CHECKS
################################################################################

monitoring:
  metrics_collection:
    system:
      - cpu_usage
      - memory_usage
      - load_average
      - uptime
      - temperature
      
    network:
      - bandwidth_usage
      - packet_statistics
      - connection_count
      - error_rates
      - latency
      
    wireless:
      - connected_clients
      - signal_strength
      - channel_utilization
      - interference_levels
      - throughput
      
  health_checks:
    critical:
      - wan_connectivity
      - dns_resolution
      - dhcp_service
      - firewall_status
      
    standard:
      - cpu_threshold: 90
      - memory_threshold: 85
      - connection_limit: 4096
      - temperature_max: 80
      
  alerting:
    thresholds:
      critical: immediate
      high: 5_minutes
      medium: 15_minutes
      low: 1_hour
      
    channels:
      - log_file
      - monitoring_agent
      - email_notification
      - webhook


################################################################################
# CONFIGURATION TEMPLATES
################################################################################

configuration_templates:
  basic_setup:
    lan:
      ip: "192.168.1.1"
      netmask: "255.255.255.0"
      dhcp_start: "192.168.1.100"
      dhcp_end: "192.168.1.200"
      
    wan:
      proto: "dhcp"
      mtu: 1500
      dns: "1.1.1.1 8.8.8.8"
      
    wireless:
      mode: "ap"
      channel: "auto"
      width: "20/40"
      security: "wpa2"
      
  advanced_features:
    vlan:
      management: 1
      guest: 10
      iot: 20
      servers: 30
      
    qos:
      enabled: true
      algorithm: "htb"
      priorities:
        voip: highest
        gaming: high
        streaming: medium
        browsing: normal
        
    vpn:
      type: "openvpn"
      port: 1194
      protocol: "udp"
      cipher: "AES-256-GCM"
      
  security_hardening:
    ssh:
      port: 2222
      root_login: "no"
      password_auth: "no"
      
    firewall:
      default_policy: "drop"
      established: "accept"
      logging: "enabled"
      
    services:
      telnet: "disabled"
      upnp: "disabled"
      wps: "disabled"


################################################################################
# AUTOMATION WORKFLOWS
################################################################################

automation_workflows:
  backup_restore:
    scheduled_backup:
      frequency: "daily"
      retention: 30
      compression: "gzip"
      encryption: "aes256"
      
    emergency_restore:
      trigger: "health_check_failure"
      max_attempts: 3
      rollback_delay: 300
      
  firmware_management:
    update_check:
      frequency: "weekly"
      source: "dd-wrt.com"
      branch: "stable"
      
    update_process:
      - backup_current_config
      - verify_firmware_checksum
      - flash_firmware
      - wait_for_reboot
      - restore_configuration
      - verify_operation
      
  performance_optimization:
    auto_channel:
      scan_interval: "hourly"
      switch_threshold: 30
      blacklist_channels: [6, 11]
      
    connection_tuning:
      tcp_optimization: true
      buffer_adjustment: true
      congestion_control: "bbr"
      
  security_scanning:
    vulnerability_check:
      frequency: "weekly"
      scope: "full"
      report: "detailed"
      
    intrusion_detection:
      enabled: true
      sensitivity: "medium"
      block_duration: 3600


################################################################################
# ERROR RECOVERY PROCEDURES
################################################################################

error_recovery:
  connection_failures:
    ssh_timeout:
      - retry_with_increased_timeout
      - try_alternate_port
      - check_firewall_rules
      - alert_infrastructure_agent
      
    authentication_failure:
      - verify_credentials
      - check_key_permissions
      - regenerate_known_hosts
      - escalate_to_security
      
  configuration_errors:
    nvram_full:
      - clear_unused_variables
      - compact_nvram
      - backup_and_reset
      
    service_crash:
      - restart_service
      - check_memory_usage
      - review_recent_changes
      - restore_last_known_good
      
  network_issues:
    wan_down:
      - check_cable_connection
      - restart_wan_interface
      - release_renew_dhcp
      - switch_to_backup_wan
      
    high_latency:
      - check_bandwidth_usage
      - review_qos_rules
      - scan_for_interference
      - optimize_routing_table


################################################################################
# INTEGRATION EXAMPLES
################################################################################

integration_examples:
  basic_status_check: |
    @Task: DDWRT
    Request: status_check
    Target: 192.168.1.1
    Auth: ssh_key=/home/user/.ssh/ddwrt_key
    Options:
      - metrics: [cpu, memory, connections]
      - interfaces: [wan, lan, wlan0]
    
  vlan_configuration: |
    @Task: DDWRT
    Request: configure_vlan
    Target: router.local
    Auth: stored_credential=ddwrt_main
    Options:
      vlan_id: 10
      name: guest_network
      ports: "1t 2t 3"
      ip_range: 192.168.10.0/24
      isolation: true
    
  security_hardening: |
    @Task: DDWRT
    Request: apply_security_policy
    Target: 10.0.0.1
    Auth: certificate=/etc/ddwrt/certs/admin.pem
    Options:
      template: security_hardening
      firewall: strict
      services: minimal
      logging: verbose
    
  firmware_update: |
    @Task: DDWRT
    Request: firmware_upgrade
    Target: primary_router
    Auth: multi_factor
    Options:
      version: latest_stable
      backup: true
      verify: checksum
      rollback: automatic


################################################################################
# PERFORMANCE OPTIMIZATION
################################################################################

performance:
  caching:
    command_results: 60s
    configuration: 300s
    health_status: 30s
    
  batching:
    max_commands: 50
    timeout: 10s
    compression: true
    
  connection_reuse:
    enabled: true
    idle_timeout: 300s
    max_age: 3600s
    
  parallel_execution:
    max_routers: 10
    thread_pool: 20
    queue_size: 100


################################################################################
# DOMAIN-SPECIFIC CAPABILITIES
################################################################################

domain_capabilities:
  core_competencies:
    - router_management:
        name: "DD-WRT Configuration Management"
        description: "Complete control over DD-WRT router settings via SSH"
        implementation: "NVRAM manipulation, service control, UCI commands"
        
    - network_orchestration:
        name: "Advanced Network Orchestration"
        description: "VLAN, QoS, routing, and traffic management"
        implementation: "iptables, tc, iproute2, bridge utilities"
        
    - security_enforcement:
        name: "Security Policy Enforcement"
        description: "Firewall rules, access control, VPN configuration"
        implementation: "iptables, OpenVPN, IPSec, WireGuard"
        
    - monitoring_diagnostics:
        name: "Real-time Monitoring & Diagnostics"
        description: "Performance metrics, health checks, troubleshooting"
        implementation: "proc filesystem, netlink, wireless extensions"
        
  specialized_knowledge:
    - "DD-WRT firmware architecture and internals"
    - "NVRAM variable management and optimization"
    - "Linux networking stack and iptables/netfilter"
    - "802.11 wireless protocols and optimization"
    - "QoS algorithms (HTB, HFSC, FQ_CODEL)"
    - "VPN protocols and implementation"
    - "Network security best practices"
    - "SSH protocol and secure automation"
    
  output_formats:
    - status_report:
        type: "JSON"
        purpose: "Machine-readable status and metrics"
        structure: "Hierarchical with timestamp, metrics, and alerts"
        
    - configuration_dump:
        type: "NVRAM format"
        purpose: "Backup and restore operations"
        structure: "Key-value pairs suitable for nvram restore"
        
    - diagnostic_log:
        type: "Plain text"
        purpose: "Human-readable troubleshooting information"
        structure: "Timestamped entries with severity levels"


################################################################################
# SUCCESS METRICS
################################################################################

success_metrics:
  performance:
    response_time:
      target: "<2s for status check"
      measurement: "SSH command execution time"
      
    throughput:
      target: "100 routers/minute"
      python_only: "10 routers/minute"
      with_binary: "100 routers/minute"
      
  reliability:
    availability:
      target: "99.9% uptime"
      measurement: "Successful SSH connections"
      
    error_recovery:
      target: ">95% automatic recovery"
      measurement: "Errors resolved without manual intervention"
      
  quality:
    configuration_accuracy:
      target: "100% accurate configs"
      measurement: "Post-apply verification success"
      
    backup_success:
      target: ">99% successful backups"
      measurement: "Completed backup operations"
      
  domain_specific:
    ssh_efficiency:
      target: "<5 connections per task"
      measurement: "Connection reuse rate"
      
    security_compliance:
      target: "100% policy adherence"
      measurement: "Security audit pass rate"
      
    network_stability:
      target: "<0.1% config-induced outages"
      measurement: "Service disruption events"


################################################################################
# REQUIRED INFRASTRUCTURE
################################################################################

infrastructure_requirements:
  dependencies:
    system_packages:
      - "openssh-client"
      - "sshpass"
      - "expect"
      - "netcat"
      - "iputils-ping"
      
    python_packages:
      - "paramiko>=3.0.0"
      - "netmiko>=4.0.0"
      - "asyncssh>=2.13.0"
      - "pexpect>=4.8.0"
      
  storage:
    configuration_backups: "/var/lib/ddwrt/backups/"
    ssh_keys: "/etc/ddwrt/keys/"
    logs: "/var/log/ddwrt/"
    cache: "/var/cache/ddwrt/"
    
  network:
    management_vlan: required
    out_of_band: recommended
    redundant_path: recommended


################################################################################
# END DD-WRT AGENT SPECIFICATION v7.0
################################################################################
