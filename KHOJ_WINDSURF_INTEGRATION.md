# Khoj + Windsurf Integration Guide

## Overview
Khoj provides local RAG (Retrieval-Augmented Generation) for your codebase. This guide shows how to wire it into Windsurf for enhanced context.

## Architecture

```
Windsurf → Proxy (9999/443) → Codeium API
                ↓
            Khoj (42110) ← Workspace Index
```

The proxy intercepts completion requests and can inject Khoj context before sending to upstream.

## Setup

### 1. Start Khoj
```bash
./hg_start.sh
# Select option 4 (Start services)
# Khoj will start automatically via Docker
```

### 2. Verify Khoj is Running
```bash
curl http://127.0.0.1:42110/api/health
# Should return: {"detail":"OK"}
```

### 3. Index Your Workspace
Khoj auto-indexes on startup, but you can manually trigger:
```bash
curl -X POST http://127.0.0.1:9999/hg/khoj/reindex
```

## Integration Methods

### Method 1: Automatic Context Injection (Recommended)

The proxy automatically injects Khoj context into completion requests when relevant.

**How it works:**
1. Proxy intercepts completion request
2. Extracts query from messages
3. Queries Khoj for relevant code snippets
4. Injects top-K results into system prompt
5. Forwards enhanced request to Codeium

**Configuration** (in `src/proxy.py`):
```python
# Enable Khoj injection
KHOJ_ENABLED = True
KHOJ_TOP_K = 5  # Number of snippets to inject
```

### Method 2: Manual Khoj Queries

Query Khoj directly from terminal:
```bash
# Search codebase
curl "http://127.0.0.1:42110/api/search?q=authentication+logic&n=5"

# Chat with Khoj
curl -X POST http://127.0.0.1:42110/api/chat \
  -H "Content-Type: application/json" \
  -d '{"q": "How does the proxy handle key rotation?"}'
```

### Method 3: Windsurf Extension (Future)

Create a Windsurf extension that:
1. Adds "Ask Khoj" command to context menu
2. Queries Khoj API directly
3. Displays results in sidebar

## Khoj API Endpoints

### Search
```
GET /api/search?q=<query>&n=<results>
```
Returns relevant code snippets from indexed workspace.

### Chat
```
POST /api/chat
Body: {"q": "your question"}
```
Interactive chat with RAG context.

### Health
```
GET /api/health
```
Returns `{"detail":"OK"}` if healthy.

### Reindex
```
POST /api/update
```
Triggers full workspace reindex.

## Proxy Integration Points

### 1. Context Injection Hook
Located in `src/proxy.py` → `proxy_request()`:

```python
# Before forwarding to upstream
if KHOJ_ENABLED and "messages" in raw_body_json:
    query = extract_query(raw_body_json["messages"])
    khoj_context = await query_khoj(query, top_k=KHOJ_TOP_K)
    
    # Inject into system message
    for msg in raw_body_json["messages"]:
        if msg.get("role") == "system":
            msg["content"] = khoj_context + "\n\n" + msg["content"]
            break
```

### 2. Khoj Status Endpoint
```
GET http://127.0.0.1:9999/hg/khoj/status
```
Returns:
```json
{
  "enabled": true,
  "search_count": 42,
  "injection_count": 15,
  "top_k": 5
}
```

### 3. Reindex Trigger
```
POST http://127.0.0.1:9999/hg/khoj/reindex
```
Triggers Khoj to reindex the workspace.

## Dashboard Integration

The dashboard shows Khoj status in real-time:
- **Enabled**: Green if Khoj is responding
- **Searches**: Total search queries
- **Injections**: Number of context injections
- **Top-K**: Configured snippet count

Press `L` in dashboard to view Khoj logs.

## Best Practices

### 1. Keep Index Fresh
Reindex after major code changes:
```bash
curl -X POST http://127.0.0.1:9999/hg/khoj/reindex
```

### 2. Tune Top-K
- **Low (3-5)**: Fast, focused context
- **High (10-15)**: Comprehensive but slower

Adjust in `src/proxy.py`:
```python
KHOJ_TOP_K = 5  # Your preferred value
```

### 3. Monitor Injection Rate
Check dashboard "Injections" counter. If too high, Khoj may be over-triggering.

### 4. Exclude Large Files
Add to Khoj config (if needed):
```yaml
# ~/.khoj/khoj.yml
content-type:
  org:
    input-filter: ["*.org"]
  markdown:
    input-filter: ["*.md"]
  # Exclude large generated files
  plaintext:
    input-filter: ["!node_modules/**", "!dist/**", "!*.min.js"]
```

## Troubleshooting

### Khoj Not Starting
```bash
# Check Docker containers
docker ps | grep khoj

# View logs
docker logs khoj
docker logs khoj-pg

# Restart
docker stop khoj khoj-pg
./hg_start.sh  # Select option 4
```

### Context Not Injecting
1. Check proxy logs: `tail -f logs/proxy.log`
2. Verify `KHOJ_ENABLED = True` in `src/proxy.py`
3. Test Khoj directly: `curl http://127.0.0.1:42110/api/health`

### Slow Completions
- Reduce `KHOJ_TOP_K` to 3
- Check Khoj response time: `curl -w "@-" http://127.0.0.1:42110/api/search?q=test`
- Consider indexing only key directories

### Index Out of Date
```bash
# Force full reindex
curl -X POST http://127.0.0.1:42110/api/update
```

## Advanced: Custom Khoj Queries

### Semantic Code Search
```python
import requests

def search_codebase(query, n=5):
    r = requests.get(
        "http://127.0.0.1:42110/api/search",
        params={"q": query, "n": n}
    )
    return r.json()

# Example
results = search_codebase("authentication middleware", n=10)
for hit in results:
    print(f"{hit['file']}:{hit['line']} - {hit['snippet']}")
```

### Chat with Context
```python
def ask_khoj(question):
    r = requests.post(
        "http://127.0.0.1:42110/api/chat",
        json={"q": question}
    )
    return r.json()["response"]

# Example
answer = ask_khoj("How does the proxy handle rate limiting?")
print(answer)
```

## Performance Metrics

Monitor via dashboard or API:
```bash
curl http://127.0.0.1:9999/hg/telemetry | jq '.khoj'
```

Expected metrics:
- **Search latency**: <100ms for small codebases
- **Index size**: ~10MB per 1000 files
- **Memory usage**: ~500MB (Khoj container)

## Next Steps

1. **Enable auto-injection**: Set `KHOJ_ENABLED = True` in proxy
2. **Tune Top-K**: Start with 5, adjust based on quality
3. **Monitor dashboard**: Watch injection count and search latency
4. **Reindex regularly**: After major commits or refactors
5. **Experiment**: Try different queries to see what Khoj finds

## Resources

- Khoj docs: https://docs.khoj.dev
- Khoj API: http://127.0.0.1:42110/docs (when running)
- Dashboard: Press `6` in `hg_start.sh` menu
