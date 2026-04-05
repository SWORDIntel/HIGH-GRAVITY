# 🎤 VOICE SYSTEM TOGGLE GUIDE

## ⚡ QUICK COMMANDS

```bash
# Enable voice system
voice-toggle on

# Disable voice system  
voice-toggle off

# Check status
voice-toggle status

# Quick minimal setup
voice-toggle quick
```

## 🎯 HOW IT WORKS

### **Enable Voice System:**
```bash
voice-toggle on
```
**What happens:**
- ✅ Enables voice command processing
- ✅ Adds voice shortcuts to terminal
- ✅ Makes `claude-voice`, `claude-say` commands available
- ✅ Voice system auto-starts on terminal sessions

### **Disable Voice System:**
```bash
voice-toggle off
```
**What happens:**
- 🔇 Disables voice command processing
- 🔇 Voice shortcuts become inactive (but remain in bashrc)
- 🔇 `claude-voice` commands show "disabled" message
- ✅ Stops any running voice processes

### **Check Status:**
```bash
voice-toggle status
```
**Shows:**
- Current voice system status (enabled/disabled)
- Available commands when enabled
- Usage examples and help

### **Quick Setup:**
```bash
voice-toggle quick
```
**Creates:**
- Minimal voice system with simple `voice` command
- No external dependencies required
- Basic agent routing based on keywords

## 🎛️ VOICE SYSTEM STATES

### **🟢 ENABLED State**
When voice system is **ON**:

```bash
# These commands work:
claude-voice                    # Interactive voice interface
claude-voice-help              # Show examples
claude-say "plan my project"   # Quick voice command
voice "design API"             # Quick command (after quick setup)

# Voice commands process normally:
🎤 Processing: 'Claude, ask director to plan deployment' 
🎯 Routing to DIRECTOR: plan deployment
✅ DIRECTOR executed successfully
```

### **🔴 DISABLED State** 
When voice system is **OFF**:

```bash
# These commands show disabled message:
claude-voice
# Output: 🔇 Voice system disabled. Enable with: voice-toggle on

claude-say "test"
# Output: 🔇 Voice system disabled. Enable with: voice-toggle on
```

## 🔧 CONFIGURATION FILES

The toggle system manages these files:

| File | Purpose |
|------|---------|
| `voice_config.json` | Voice system configuration and enable/disable state |
| `voice_shortcuts_managed.sh` | Bash shortcuts that respect enable/disable state |
| `.voice_system.pid` | Process tracking for running voice interfaces |

## 💡 USAGE SCENARIOS

### **Scenario 1: Enable for Project Work**
```bash
# Starting a project session
voice-toggle on
claude-say "Claude, ask director to plan sprint"
claude-say "Have security audit the codebase"  
claude-say "Tell architect to design the database"
```

### **Scenario 2: Disable for Quiet Work**
```bash
# Need to focus without voice prompts
voice-toggle off

# Voice commands now inactive
claude-say "test"  # Shows disabled message
```

### **Scenario 3: Quick Check and Re-enable**
```bash
# Check what's available
voice-toggle status

# Re-enable if needed
voice-toggle on
```

### **Scenario 4: Minimal Setup for Simple Use**
```bash
# Just want basic voice routing
voice-toggle quick

# Now use simple command
voice "plan my project"      # Routes to DIRECTOR
voice "check security"       # Routes to SECURITY  
voice "design architecture"  # Routes to ARCHITECT
```

## 🎯 TOGGLE BEHAVIOR

### **Smart Command Behavior:**
- **When ENABLED:** Voice commands execute normally
- **When DISABLED:** Voice commands show helpful disable message
- **Commands persist:** Shortcuts remain in bashrc but check enable state

### **Process Management:**
- **Enable:** Adds shortcuts, sets config to enabled
- **Disable:** Updates config, stops running processes
- **Status:** Shows current state and available commands

### **Configuration Persistence:**
- Settings saved in `voice_config.json`
- Bashrc shortcuts added once, check config each time
- Easy to toggle without removing/re-adding shortcuts

## 🔄 INTEGRATION WITH AUTO-BOOT

The voice toggle works seamlessly with the auto-boot system:

1. **Claude Code starts** → Agents auto-load (always)
2. **Voice system checks config** → Enables/disables based on toggle setting  
3. **Commands available** → Only when voice system is enabled

## 🎉 BENEFITS

✅ **Easy Control:** Simple on/off commands  
✅ **Persistent Settings:** Remembers your preference  
✅ **Clean Disable:** No error messages, just helpful info  
✅ **Quick Enable:** Instant activation when needed  
✅ **Process Safe:** Properly stops/starts voice processes  
✅ **Configuration Safe:** Doesn't break existing setup  

**Perfect for switching between voice-enabled and quiet work modes!** 🎤🔇