# Troubleshooting Guide

Common issues and solutions for Claude Bedrock Cursor integration.

## Authentication Issues

### "OAuth token invalid or expired"

**Symptoms**: Login fails immediately after pasting OAuth token

**Causes**:
- OAuth token expired (short-lived, ~5 minutes)
- Token copied incorrectly (extra spaces, truncation)
- Using old token from previous session

**Solutions**:
```bash
# 1. Get fresh OAuth token
claude setup-token

# 2. Login immediately (within 5 minutes)
claude-bedrock auth login

# 3. Verify authentication
claude-bedrock auth status
```

**Prevention**: Use OAuth token within 5 minutes of generation.

---

### "Refresh token expired"

**Symptoms**: `auth status` shows "Refresh token expired"

**Cause**: Haven't used tool in 7+ days

**Solution**:
```bash
# Complete re-authentication
claude-bedrock auth logout
claude setup-token
claude-bedrock auth login
```

**Prevention**: Use tool at least once per week.

---

### "Keyring backend not found"

**Symptoms**: "Failed to store token: No keyring backend available"

**Platform-Specific Solutions**:

**macOS**:
```bash
# Keychain should work by default
# Verify:
security find-generic-password -s "claude-bedrock-cursor" 2>/dev/null || echo "No tokens stored"
```

**Linux (Ubuntu/Debian)**:
```bash
# Install gnome-keyring
sudo apt update
sudo apt install gnome-keyring libsecret-tools

# Start gnome-keyring daemon
eval $(gnome-keyring-daemon --start)
export $(gnome-keyring-daemon --start)

# Test
secret-tool store --label="Test" service test username test
```

**Linux (Fedora)**:
```bash
sudo dnf install gnome-keyring libsecret

# Start daemon
eval $(gnome-keyring-daemon --start)
```

**Windows**: Credential Manager works by default, no action needed.

---

### "Auto-refresh not working"

**Diagnosis**:
```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
claude-bedrock auth status

# Look for refresh attempts in output
# Should see: "Auto-refresh triggered"
```

**Solutions**:

1. **Verify configuration**:
```bash
cat ~/.config/claude-bedrock-cursor/config.toml

# Should have:
[oauth]
auto_refresh = true
refresh_threshold_minutes = 2
```

2. **Manual refresh test**:
```bash
claude-bedrock auth refresh
# If this works, auto-refresh should work too
```

3. **Check token expiry**:
```bash
claude-bedrock auth status
# Access token should show "expires in X minutes"
# If already expired, auto-refresh may have failed
```

## AWS Bedrock Issues

### "AccessDeniedException: User is not authorized"

**Symptoms**: API calls fail with 403 Forbidden

**Diagnosis**:
```bash
# Check IAM permissions
aws iam get-user-policy \
  --user-name claude-bedrock-user \
  --policy-name ClaudeBedrockCursorAccess

# Verify model access
aws bedrock get-foundation-model \
  --model-identifier anthropic.claude-sonnet-4-20250514-v1:0 \
  --region us-east-1
```

**Solutions**:

1. **Apply IAM policy**:
```bash
# Generate policy
claude-bedrock aws setup

# Create and attach
aws iam create-policy \
  --policy-name ClaudeBedrockCursorAccess \
  --policy-document file://~/.config/claude-bedrock-cursor/iam-policy.json

aws iam attach-user-policy \
  --user-name claude-bedrock-user \
  --policy-arn arn:aws:iam::YOUR_ACCOUNT_ID:policy/ClaudeBedrockCursorAccess
```

2. **Request model access**:
   - Go to AWS Console → Bedrock → Model access
   - Select region (us-east-1)
   - Request access to Claude Sonnet 4
   - Wait for approval (usually instant)

3. **Verify region**:
```bash
# Ensure config matches policy
cat ~/.config/claude-bedrock-cursor/config.toml | grep region
# Should be us-east-1 or other supported region
```

---

### "ThrottlingException: Rate exceeded"

**Symptoms**: Requests fail with "Rate exceeded" error

**Diagnosis**:
```bash
# Check throttling metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/Bedrock \
  --metric-name Throttles \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Sum \
  --region us-east-1
```

**Solutions**:

1. **Exponential backoff** (already implemented):
```python
# Client automatically retries with backoff
# Wait: 1s, 2s, 4s, 8s, etc.
```

2. **Request quota increase**:
```bash
# Via AWS Support Console
# Service: Amazon Bedrock
# Quota: Invocations per minute
# Desired value: XXX (justify with usage patterns)
```

3. **Spread across regions**:
```bash
# Use multiple regions for load balancing
# us-east-1, us-west-2, eu-west-1
```

---

### "ValidationException: MAX_OUTPUT_TOKENS must be at least 4096"

**Symptoms**: API calls fail with token validation error

**Solution**:
```bash
# Edit configuration
nano ~/.config/claude-bedrock-cursor/config.toml

# Ensure minimum value:
[bedrock]
max_output_tokens = 4096  # DON'T GO LOWER!
```

**Explanation**: Bedrock enforces minimum 4096 tokens to prevent "burndown throttling".

---

### "Prompt caching not working"

**Symptoms**: No cost savings, all requests charged at full price

**Diagnosis**:
```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
claude-bedrock models test

# Look for:
# - "cache_control" in request body
# - "Cache hit" or "Cache miss" in response
```

**Solutions**:

1. **Verify configuration**:
```bash
cat ~/.config/claude-bedrock-cursor/config.toml

[bedrock]
enable_prompt_caching = true  # Must be true!
```

2. **Ensure large enough context**:
```python
# Caching benefits contexts >1024 tokens
# Small contexts (<1024 tokens) won't cache
```

3. **Check cache expiry**:
```text
Cache lifetime: 5 minutes
- First request: Cache miss (full price)
- Within 5 min: Cache hit (90% discount)
- After 5 min: Cache expired (full price again)
```

4. **Verify cache_control in request**:
```bash
# Debug output should show:
{
  "system": [{
    "type": "text",
    "text": "...",
    "cache_control": {"type": "ephemeral"}  # THIS MUST BE PRESENT!
  }]
}
```

## Cursor IDE Issues

### "Cursor not detecting Bedrock configuration"

**Diagnosis**:
```bash
# Check integration status
claude-bedrock cursor status

# Verify files exist
ls -la .cursor/
ls -la ~/.cursor/settings.json
```

**Solutions**:

1. **Re-run installation**:
```bash
claude-bedrock cursor install

# Verify files created:
# - .cursor/index.mdc
# - .cursor/rules/
# - ~/.cursor/settings.json
```

2. **Manual verification**:
```bash
# Check settings
cat ~/.cursor/settings.json | grep claude

# Should contain:
# "claude.aiProvider": "aws-bedrock"
# "claude.bedrockModelId": "anthropic.claude-sonnet-4-20250514-v1:0"
```

3. **Restart Cursor**:
```bash
# Completely quit and restart Cursor IDE
# Cmd+Q (macOS) or Alt+F4 (Windows/Linux)
# Then reopen
```

---

### "Cursor rules not activating"

**Diagnosis**:
```bash
# Verify rule file syntax
cat .cursor/rules/aws-bedrock.mdc

# Check for required header
grep "Activates when:" .cursor/rules/*.mdc
```

**Solutions**:

1. **Verify file extension**: Must be `.mdc` (not `.md`)
2. **Check "Activates when:" header**: Required for context activation
3. **Reload Cursor window**: Cmd+Shift+P → "Reload Window"

---

### "Slow AI responses in Cursor"

**Diagnosis**:
```bash
# Check CloudWatch metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/Bedrock \
  --metric-name ModelInvocationLatency \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average \
  --region us-east-1
```

**Solutions**:

1. **Reduce context size**:
```json
// settings.json
{
  "cursor.contextFiles": 5,     // Reduce from default 10
  "cursor.contextLines": 500     // Reduce from default 1000
}
```

2. **Verify caching**:
```bash
claude-bedrock models test
# Should show "Cache hit" for repeated requests
```

3. **Check network latency**:
```bash
# Ping Bedrock endpoint
ping bedrock-runtime.us-east-1.amazonaws.com
# Should be <100ms for good performance
```

4. **Use closer region**:
```bash
# If in Europe, use eu-west-1 instead of us-east-1
nano ~/.config/claude-bedrock-cursor/config.toml

[aws]
region = "eu-west-1"  # Closer region
```

## Configuration Issues

### "Config file not found"

**Symptoms**: `claude-bedrock init` needed but not run

**Solution**:
```bash
# Initialize configuration
claude-bedrock init

# Verify created
ls -la ~/.config/claude-bedrock-cursor/config.toml
```

---

### "Invalid configuration value"

**Diagnosis**:
```bash
# Check configuration syntax
cat ~/.config/claude-bedrock-cursor/config.toml

# Look for:
# - Typos in section names
# - Invalid TOML syntax
# - Out-of-range values
```

**Solution**:
```bash
# Backup current config
cp ~/.config/claude-bedrock-cursor/config.toml \
   ~/.config/claude-bedrock-cursor/config.toml.backup

# Re-initialize with defaults
claude-bedrock init --force

# Manually merge your custom settings back
```

## Testing & Debugging

### Enable Debug Logging

```bash
# Temporary (current session)
export LOG_LEVEL=DEBUG
claude-bedrock status

# Permanent
echo 'export LOG_LEVEL=DEBUG' >> ~/.bashrc  # or ~/.zshrc
source ~/.bashrc
```

### Run Comprehensive Tests

```bash
# Test authentication
claude-bedrock auth status

# Test AWS Bedrock
claude-bedrock aws validate

# Test model invocation
claude-bedrock models test

# Test Cursor integration
claude-bedrock cursor status

# Overall status
claude-bedrock status
```

### View Logs

```bash
# macOS
tail -f ~/Library/Logs/claude-bedrock-cursor/app.log

# Linux
tail -f ~/.local/share/claude-bedrock-cursor/logs/app.log

# Windows
type %LOCALAPPDATA%\claude-bedrock-cursor\logs\app.log
```

## Getting Help

### Before Opening an Issue

1. ✅ Run `claude-bedrock status` and share output
2. ✅ Enable debug logging and reproduce issue
3. ✅ Check this troubleshooting guide
4. ✅ Search existing GitHub issues
5. ✅ Collect relevant logs (sanitize tokens!)

### Where to Get Help

- **GitHub Issues**: [github.com/yourusername/claude-bedrock-cursor/issues](https://github.com/yourusername/claude-bedrock-cursor/issues)
- **Discussions**: [github.com/yourusername/claude-bedrock-cursor/discussions](https://github.com/yourusername/claude-bedrock-cursor/discussions)
- **Documentation**: [Full docs](https://github.com/yourusername/claude-bedrock-cursor/tree/main/docs)

### Issue Template

```markdown
**Description**: [Brief description of the issue]

**Environment**:
- OS: [macOS 14.1 / Ubuntu 22.04 / Windows 11]
- Python version: [3.12.1]
- Tool version: [1.0.0]

**Steps to Reproduce**:
1. Run command X
2. See error Y

**Expected Behavior**: [What should happen]

**Actual Behavior**: [What actually happens]

**Logs**: (Run with `LOG_LEVEL=DEBUG`)
```
[Paste sanitized logs here]
```text

**Additional Context**: [Any other relevant information]
```

---

**Previous**: [← Security Best Practices](./security-best-practices.md) | **Next**: [Architecture →](./architecture.md)
