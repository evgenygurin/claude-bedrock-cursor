# Cursor IDE Integration Guide

Complete guide for integrating Claude Code with Cursor IDE through AWS Bedrock, including installation, configuration, custom rules, and advanced workflows.

## Table of Contents

- [Overview](#overview)
- [Installation Methods](#installation-methods)
- [Configuration](#configuration)
- [Cursor Rules System](#cursor-rules-system)
- [Custom Workflows](#custom-workflows)
- [VS Code Extension](#vs-code-extension)
- [Advanced Features](#advanced-features)
- [Troubleshooting](#troubleshooting)

## Overview

### What is Cursor IDE?

Cursor is an AI-powered code editor built on VS Code, with deep integration for AI pair programming. Key features:

- **AI Chat**: Context-aware code conversations
- **Inline Completions**: Real-time code suggestions
- **Codebase Context**: AI understands your entire project
- **Custom Rules**: Define coding standards and patterns
- **VS Code Compatible**: Use existing extensions and settings

### Integration Architecture

```text
┌─────────────────┐
│   Cursor IDE    │
│   (Frontend)    │
└────────┬────────┘
         │
         │ AI Requests
         │
         ▼
┌─────────────────┐
│ Claude Bedrock  │◄─── OAuth Authentication
│   Integration   │      (Claude MAX)
└────────┬────────┘
         │
         │ Streaming
         │ + Caching
         │
         ▼
┌─────────────────┐
│  AWS Bedrock    │
│  Claude Sonnet  │
└─────────────────┘
```

### Integration Modes

This tool supports **two integration modes**:

1. **CLI Mode**: Use `claude-bedrock` CLI commands in Cursor terminal
2. **Extension Mode**: Configure Cursor to use Bedrock directly (TODO)
3. **Both Modes**: Recommended for maximum flexibility

## Installation Methods

### Method 1: Automated Installation (Recommended)

```bash
# One-command installation
claude-bedrock cursor install
```

**What This Does**:

1. ✅ Detects Cursor IDE installation path
2. ✅ Generates `.cursor/` configuration directory
3. ✅ Creates context-aware rules in `.cursor/rules/`
4. ✅ Configures Cursor settings for Bedrock
5. ✅ Sets up AI provider integration
6. ✅ Validates configuration

**Expected Output**:
```text
🎨 Installing Cursor Integration

📋 Step 1: Detect Cursor installation
✅ Cursor found at: /Applications/Cursor.app

📋 Step 2: Generate Cursor rules
✅ Created: .cursor/index.mdc
✅ Created: .cursor/rules/aws-bedrock.mdc
✅ Created: .cursor/rules/oauth-auth.mdc

📋 Step 3: Configure Cursor settings
✅ Updated: ~/.cursor/settings.json

💡 Integration Mode: both (CLI + Extension)

✨ Installation complete!
```

### Method 2: Manual Installation

**Step 1: Create Cursor Rules Directory**

```bash
# In your project root
mkdir -p .cursor/rules
```

**Step 2: Create Always-Active Rules**

```bash
# .cursor/index.mdc
cat > .cursor/index.mdc << 'EOF'
# Claude Code - Cursor Integration

## AI Provider
- Use AWS Bedrock for Claude Code models
- Model: Claude Sonnet 4 (anthropic.claude-sonnet-4-20250514-v1:0)
- Streaming enabled for better UX
- Prompt caching enabled (90% cost savings)

## Code Standards
- Python: 3.12+, type hints required, async/await preferred
- Line length: 88 characters
- Testing: pytest with 80%+ coverage
- Security: No secrets in code, use keyring for credentials

## Architecture Patterns
- OAuth2 with refresh token rotation
- Exponential backoff for AWS throttling
- Streaming responses for user-facing operations
- Pydantic for configuration validation

See `.cursor/rules/` for context-specific patterns.
EOF
```

**Step 3: Create AWS Bedrock Rules**

```bash
# .cursor/rules/aws-bedrock.mdc
cat > .cursor/rules/aws-bedrock.mdc << 'EOF'
# AWS Bedrock Implementation Patterns

Activates when: Working with Bedrock client code

## Streaming with Caching
```python
async def invoke_streaming(
    self,
    prompt: str,
    system_context: Optional[str] = None,
) -> AsyncIterator[str]:
    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": self.config.max_output_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }

    # Enable prompt caching for system context
    if system_context and self.config.enable_prompt_caching:
        body["system"] = [{
            "type": "text",
            "text": system_context,
            "cache_control": {"type": "ephemeral"}  # 90% cost savings!
        }]

    # Stream response
    response = await self.client.invoke_model_with_response_stream(
        modelId=self.config.bedrock_model_id,
        body=json.dumps(body),
    )

    async for event in response["body"]:
        chunk = json.loads(event["chunk"]["bytes"])
        if chunk["type"] == "content_block_delta":
            yield chunk["delta"]["text"]
```

## Retry Logic with Exponential Backoff
```python
async def _invoke_with_retry(self, operation, **kwargs):
    for attempt in range(self.config.max_retries):
        try:
            return await operation(**kwargs)
        except ClientError as e:
            if e.response["Error"]["Code"] == "ThrottlingException":
                if attempt < self.config.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue
            raise
```
EOF
```sql

**Step 4: Create OAuth Rules**

```bash
# .cursor/rules/oauth-auth.mdc
cat > .cursor/rules/oauth-auth.mdc << 'EOF'
# OAuth Security Patterns

Activates when: Working with authentication code

## Refresh Token Rotation
```python
async def refresh_access_token(self) -> TokenPair:
    """Refresh access token and rotate refresh token.

    SECURITY: This implements token rotation - the refresh token
    is replaced on EVERY use, preventing token reuse attacks.
    """
    current_refresh = self.storage.get_token("refresh_token")

    response = await self.http_client.post(
        f"{self.api_base}/oauth/token",
        json={
            "grant_type": "refresh_token",
            "refresh_token": current_refresh,
        }
    )

    data = response.json()

    # CRITICAL: Store NEW refresh token, invalidate old one
    self.storage.store_token("access_token", data["access_token"])
    self.storage.store_token("refresh_token", data["refresh_token"])

    return TokenPair(
        access_token=data["access_token"],
        refresh_token=data["refresh_token"],  # NEW token!
    )
```

## Secure Token Storage
```python
# ALWAYS use system keyring, NEVER environment variables
from keyring import get_password, set_password, delete_password

# Store securely
set_password("claude-bedrock-cursor", "access_token", token)

# Retrieve securely
token = get_password("claude-bedrock-cursor", "access_token")

# Delete on logout
delete_password("claude-bedrock-cursor", "access_token")
```
EOF
```text

**Step 5: Configure Cursor Settings**

```bash
# Edit Cursor settings
code ~/.cursor/settings.json  # Or use your editor

# Add/update:
{
  "claude.aiProvider": "aws-bedrock",
  "claude.bedrockRegion": "us-east-1",
  "claude.bedrockModelId": "anthropic.claude-sonnet-4-20250514-v1:0",
  "claude.enableStreaming": true,
  "claude.enablePromptCaching": true
}
```

## Configuration

### Verify Installation

```bash
# Check Cursor integration status
claude-bedrock cursor status
```

**Expected Output**:
```text
🎨 Cursor Integration Status

✅ Cursor Detected
   Version: 0.40.3
   Path: /Applications/Cursor.app
   Installation: Valid

✅ Configuration
   Settings: ~/.cursor/settings.json
   Rules: .cursor/ (3 files)
   Mode: both (CLI + Extension)

✅ Bedrock Connection
   Provider: AWS Bedrock
   Region: us-east-1
   Model: anthropic.claude-sonnet-4-20250514-v1:0
   Streaming: Enabled
   Caching: Enabled

✅ OAuth Authentication
   Status: Authenticated
   Access Token: Valid (3 minutes remaining)
   Refresh Token: Valid (6 days remaining)

✨ All systems operational!
```

### Configure Integration Mode

```bash
# Edit configuration
nano ~/.config/claude-bedrock-cursor/config.toml

[cursor]
integration_mode = "both"  # Options: "cli", "extension", "both"
```

**Integration Modes**:

- **`cli`**: Only CLI commands (`claude-bedrock` in terminal)
- **`extension`**: Only VS Code extension integration (TODO)
- **`both`**: Both CLI and extension (recommended)

### Cursor Settings Reference

```json
{
  // Claude Bedrock Integration
  "claude.aiProvider": "aws-bedrock",
  "claude.bedrockRegion": "us-east-1",
  "claude.bedrockModelId": "anthropic.claude-sonnet-4-20250514-v1:0",
  "claude.enableStreaming": true,
  "claude.enablePromptCaching": true,
  "claude.maxOutputTokens": 4096,

  // Cursor AI Settings
  "cursor.enableAI": true,
  "cursor.aiModel": "custom-bedrock",
  "cursor.codeActions": true,
  "cursor.inlineCompletions": true,

  // Editor Settings
  "editor.inlineSuggest.enabled": true,
  "editor.quickSuggestions": {
    "comments": true,
    "strings": true,
    "other": true
  }
}
```

## Cursor Rules System

### Understanding .cursor/ Directory

```text
.cursor/
├── index.mdc              # Always-active rules for all files
└── rules/                 # Context-specific rules
    ├── aws-bedrock.mdc    # Activates for Bedrock code
    ├── oauth-auth.mdc     # Activates for auth code
    ├── python.mdc         # Python-specific patterns
    └── testing.mdc        # Test writing patterns
```

**Rule Activation**:

- **index.mdc**: Always active (global context)
- **rules/*.mdc**: Activated based on file context

### Creating Custom Rules

**Example: Python Best Practices**

```bash
# .cursor/rules/python.mdc
cat > .cursor/rules/python.mdc << 'EOF'
# Python Development Patterns

Activates when: Editing .py files

## Type Hints Required
```python
# ALWAYS include type hints
def process_data(input: str, count: int = 10) -> dict[str, Any]:
    """Process data with type safety."""
    pass

# NOT ALLOWED: Missing type hints
def process_data(input, count=10):  # ❌ Missing types
    pass
```

## Async/Await Preferred
```python
# USE: Async for I/O operations
async def fetch_data(url: str) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        return response.json()

# AVOID: Sync for I/O (blocking)
def fetch_data(url: str) -> dict:  # ❌ Sync I/O
    import requests
    return requests.get(url).json()
```

## Error Handling
```python
# Specific exceptions
try:
    result = await bedrock_client.invoke(prompt)
except BedrockThrottlingError:
    await asyncio.sleep(2)
except BedrockValidationError as e:
    raise ValueError(f"Invalid request: {e}")

# NOT: Broad exception catching
try:
    result = await bedrock_client.invoke(prompt)
except Exception:  # ❌ Too broad
    pass
```
EOF
```bash

**Example: Test Writing Patterns**

```bash
# .cursor/rules/testing.mdc
cat > .cursor/rules/testing.mdc << 'EOF'
# Testing Patterns

Activates when: Editing test_*.py files

## Test Structure
```python
@pytest.mark.asyncio
async def test_function_name_scenario():
    """Test description in plain English."""
    # Arrange: Set up test data
    manager = OAuthManager()

    # Act: Perform the operation
    result = await manager.login("token")

    # Assert: Verify expectations
    assert result.access_token is not None
    assert len(result.refresh_token) > 0
```

## Mocking Best Practices
```python
# Use pytest fixtures for common mocks
@pytest.fixture
def mock_bedrock_client(mocker):
    mock = mocker.patch("boto3.client")
    mock.return_value.invoke_model_with_response_stream.return_value = {
        "body": iter([{"chunk": {"bytes": b'{"type":"content_block_delta"}'}}])
    }
    return mock

# Clean test using fixture
async def test_streaming(mock_bedrock_client):
    client = BedrockClient()
    chunks = []
    async for chunk in client.invoke_streaming("test"):
        chunks.append(chunk)
    assert len(chunks) > 0
```

## Coverage Requirements
- Unit tests: 100% for critical modules (auth, config, bedrock)
- Integration tests: 80%+ for workflows
- E2E tests: Happy path + error scenarios
EOF
```bash

### Rule Best Practices

1. **Be Specific**: Provide concrete code examples
2. **Explain Why**: Not just what, but why this pattern is better
3. **Include Anti-Patterns**: Show what NOT to do
4. **Use Comments**: Explain critical decisions inline
5. **Keep Updated**: Rules should evolve with codebase

## Custom Workflows

### Workflow 1: AI-Assisted Code Review

**Setup**:

```bash
# .cursor/rules/code-review.mdc
cat > .cursor/rules/code-review.mdc << 'EOF'
# Code Review Checklist

When reviewing code, check for:

1. **Security**
   - No secrets in code
   - Input validation present
   - Error messages don't leak sensitive info

2. **Performance**
   - Async I/O operations
   - Efficient data structures
   - No N+1 queries

3. **Testing**
   - Test coverage >80%
   - Edge cases covered
   - Mocks used appropriately

4. **Documentation**
   - Docstrings for public functions
   - Type hints present
   - README updated if needed
EOF
```

**Usage in Cursor**:

1. Open file for review
2. Cmd+L (or Ctrl+L) to open AI chat
3. Ask: "Review this code using the code-review checklist"
4. Claude will analyze code against checklist

### Workflow 2: Generate Tests from Implementation

**Setup**:

```bash
# .cursor/rules/test-generation.mdc
cat > .cursor/rules/test-generation.mdc << 'EOF'
# Test Generation Pattern

When generating tests:

1. Read implementation function
2. Identify:
   - Input types and edge cases
   - Expected outputs
   - Error conditions
3. Generate:
   - Happy path test
   - Edge case tests (empty, null, max values)
   - Error condition tests
4. Use pytest fixtures for setup
5. Aim for 100% coverage of function
EOF
```

**Usage**:

1. Select function code
2. Cmd+K (inline AI)
3. Prompt: "Generate comprehensive tests using test-generation pattern"
4. Review generated tests, refine as needed

### Workflow 3: Refactoring with Context

**Setup**: Use `.cursor/rules/refactoring.mdc` (custom)

**Usage**:

1. Select code to refactor
2. Cmd+L to chat
3. Prompt: "Refactor this following our Python patterns and async best practices"
4. Claude refactors with awareness of project standards

## VS Code Extension

### Extension Development (TODO)

**Current Status**: CLI integration complete, extension in development

**Planned Features**:

- Direct Bedrock API integration (no CLI)
- Real-time streaming completions
- Background token refresh
- Cost tracking in status bar
- Custom command palette actions

**Development Roadmap**:

1. ✅ Phase 1: CLI integration (complete)
2. 🔄 Phase 2: Extension scaffolding (in progress)
3. ⏳ Phase 3: Bedrock client in TypeScript
4. ⏳ Phase 4: OAuth flow in extension
5. ⏳ Phase 5: Cursor API integration
6. ⏳ Phase 6: VS Code Marketplace publish

### Extension Configuration (Preview)

```json
{
  "claudeBedrockCursor": {
    "aws": {
      "region": "us-east-1",
      "profile": "default"
    },
    "bedrock": {
      "modelId": "anthropic.claude-sonnet-4-20250514-v1:0",
      "enableStreaming": true,
      "enableCaching": true
    },
    "oauth": {
      "autoRefresh": true,
      "refreshThresholdMinutes": 2
    },
    "ui": {
      "showCostTracker": true,
      "showTokenCount": true
    }
  }
}
```

## Advanced Features

### Custom Commands in Cursor

**Create Custom Command**:

```json
// .vscode/tasks.json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "Test Claude Connection",
      "type": "shell",
      "command": "claude-bedrock models test",
      "group": "test",
      "presentation": {
        "reveal": "always",
        "panel": "new"
      }
    },
    {
      "label": "Check Auth Status",
      "type": "shell",
      "command": "claude-bedrock auth status",
      "group": "none",
      "presentation": {
        "reveal": "always",
        "panel": "new"
      }
    }
  ]
}
```

**Usage**: Cmd+Shift+P → "Tasks: Run Task" → Select command

### Keyboard Shortcuts

```json
// .vscode/keybindings.json
[
  {
    "key": "cmd+shift+t",
    "command": "workbench.action.tasks.runTask",
    "args": "Test Claude Connection"
  },
  {
    "key": "cmd+shift+a",
    "command": "workbench.action.tasks.runTask",
    "args": "Check Auth Status"
  }
]
```

### Context-Aware Completions

**Enable Smart Completions**:

```json
// settings.json
{
  "editor.quickSuggestions": {
    "comments": true,    // AI suggestions in comments
    "strings": true,     // AI suggestions in strings
    "other": true        // AI suggestions everywhere
  },
  "editor.suggest.preview": true,
  "editor.suggest.showMethods": true,
  "editor.suggest.showFunctions": true
}
```

### Multi-File Context

Cursor automatically includes context from:

- Current file
- Recently opened files
- Files in `.cursor/` directory
- Git history (recent changes)

**Optimize Context**:

```json
{
  "cursor.contextFiles": 10,        // Max files in context
  "cursor.contextLines": 1000,      // Max lines per file
  "cursor.includeGitHistory": true, // Include recent commits
  "cursor.includeTests": true       // Include test files
}
```

## Troubleshooting

### Common Issues

**Issue: Cursor not detecting Bedrock configuration**

**Diagnosis**:
```bash
# Check Cursor settings
cat ~/.cursor/settings.json | grep claude

# Verify .cursor/ directory exists
ls -la .cursor/

# Check rule files
ls -la .cursor/rules/
```

**Solutions**:
1. Re-run installation: `claude-bedrock cursor install`
2. Manually verify settings.json (see Configuration section)
3. Restart Cursor IDE completely
4. Check Cursor logs: Help → Toggle Developer Tools → Console

---

**Issue: Rules not activating**

**Diagnosis**:
```bash
# Verify rule file syntax
cat .cursor/rules/aws-bedrock.mdc

# Check for "Activates when:" line
grep "Activates when:" .cursor/rules/*.mdc
```

**Solutions**:
1. Ensure rule files have `.mdc` extension
2. Verify "Activates when:" header present
3. Check rule syntax matches examples
4. Reload Cursor: Cmd+Shift+P → "Reload Window"

---

**Issue: Slow AI responses**

**Possible Causes**:
1. Large codebase context (too many files)
2. Prompt caching not working
3. Network latency to Bedrock
4. AWS throttling

**Solutions**:
```bash
# 1. Reduce context files
# Edit settings.json:
{
  "cursor.contextFiles": 5,    # Reduce from 10
  "cursor.contextLines": 500    # Reduce from 1000
}

# 2. Verify caching enabled
claude-bedrock models test
# Look for "Caching: Cache hit (90% cost savings!)"

# 3. Check Bedrock latency
aws cloudwatch get-metric-statistics \
  --namespace AWS/Bedrock \
  --metric-name ModelInvocationLatency \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average

# 4. Check throttling
claude-bedrock aws validate
```

---

**Issue: Authentication errors in Cursor**

**Solutions**:
```bash
# Refresh authentication
claude-bedrock auth refresh

# Verify status
claude-bedrock auth status

# Re-login if needed
claude-bedrock auth logout
claude-bedrock auth login

# Restart Cursor after auth refresh
```

## Next Steps

### Recommended Reading

- **[OAuth Authentication Guide](./oauth-authentication.md)** - Token management
- **[Cost Optimization Guide](./cost-optimization.md)** - Reduce Bedrock costs
- **[Security Best Practices](./security-best-practices.md)** - Secure configuration
- **[Troubleshooting Guide](./troubleshooting.md)** - Common issues

### Enhancing Your Workflow

1. **Create Project-Specific Rules**: Add `.cursor/rules/` for each project
2. **Set Up Custom Commands**: Use tasks.json for common operations
3. **Configure Keyboard Shortcuts**: Speed up frequent actions
4. **Monitor Costs**: Set up CloudWatch dashboards
5. **Join Community**: Share rules and patterns with others

---

**Previous**: [← AWS Bedrock Setup](./aws-bedrock-setup.md) | **Next**: [OAuth Authentication →](./oauth-authentication.md)
