# KP14 v2 Architecture Baseline

**Generated:** 2026-03-28T14:20:13.008946

## Current Pipeline

### Static Analysis
- PE/ELF structure analysis
- Code disassembly
- String extraction
- Import/export analysis

### Dynamic Analysis (BLACKROOM)
- Sandbox execution
- API call tracing
- Network activity monitoring
- Registry/file operations

### AI-Assisted Analysis
- Behavior detection
- Pattern recognition
- Threat scoring

### Reporting
- Forensic reports
- STIX/Caldera export
- YARA rule generation

## Current Limitations

- No behavioral sequencing (temporal chains)
- Limited MBC depth
- No Caldera export automation
- Limited similarity clustering
