# Setup Guide - Claude Bedrock Cursor Integration

Comprehensive step-by-step guide for installing and configuring Claude Code integration with Cursor IDE through AWS Bedrock.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Initial Configuration](#initial-configuration)
- [OAuth Authentication](#oauth-authentication)
- [AWS Bedrock Setup](#aws-bedrock-setup)
- [Cursor IDE Integration](#cursor-ide-integration)
- [First Query](#first-query)
- [Verification](#verification)
- [Next Steps](#next-steps)

## Prerequisites

### Required

1. **Python 3.12 or higher**
   ```bash
   python3 --version  # Should show 3.12.x or higher
   ```

   **Installation**:
   - macOS: `brew install python@3.12`
   - Ubuntu: `sudo apt install python3.12`
   - Windows: Download from [python.org](https://www.python.org/downloads/)

2. **Claude MAX Subscription**
   - Required for OAuth authentication
   - Sign up at [claude.ai](https://claude.ai/)
   - Verify subscription status in account settings

3. **AWS Account with Bedrock Access**
   - AWS account with active credentials
   - Bedrock service enabled in your region
   - IAM permissions to invoke models

4. **Cursor IDE**
   - Download from [cursor.sh](https://cursor.sh/)
   - Latest version recommended (0.40+)

### Optional (Recommended)

- **uv package manager** (10x faster than pip):
  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```

- **AWS CLI** (for easier credential setup):
  ```bash
  # macOS
  brew install awscli

  # Ubuntu
  sudo apt install awscli

  # Windows
  # Download MSI from https://aws.amazon.com/cli/
  ```

## Installation

### Method 1: Using uv (Recommended)

```bash
# Install the package
uv pip install claude-bedrock-cursor

# Verify installation
claude-bedrock --version
```

### Method 2: Using pip

```bash
# Install the package
pip install claude-bedrock-cursor

# Verify installation
claude-bedrock --version
```

### Method 3: From Source (Development)

```bash
# Clone the repository
git clone https://github.com/yourusername/claude-bedrock-cursor.git
cd claude-bedrock-cursor

# Install with uv
uv sync --all-extras

# Or with pip
pip install -e ".[dev]"

# Verify installation
claude-bedrock --version
```

## Initial Configuration

### Step 1: Initialize Configuration

```bash
# Run initialization wizard
claude-bedrock init
```

**Expected Output**:
```text
🚀 Initializing Claude Bedrock Cursor integration...

📝 Creating configuration file at: ~/.config/claude-bedrock-cursor/config.toml
✅ Configuration file created

🔧 Setting up directories...
✅ Created: ~/.config/claude-bedrock-cursor/
✅ Created: ~/.local/share/claude-bedrock-cursor/

📋 Next steps:
   1. Run 'claude-bedrock auth login' to authenticate
   2. Run 'claude-bedrock aws setup' to configure AWS
   3. Run 'claude-bedrock cursor install' to integrate with Cursor

✨ Initialization complete!
```

### Step 2: Review Configuration

```bash
# View current configuration
cat ~/.config/claude-bedrock-cursor/config.toml
```

**Default Configuration**:
```toml
[aws]
region = "us-east-1"
profile = "default"

[bedrock]
model_id = "anthropic.claude-sonnet-4-20250514-v1:0"
max_output_tokens = 4096
max_thinking_tokens = 1024
enable_prompt_caching = true
enable_streaming = true

[cursor]
integration_mode = "both"  # cli, extension, or both

[logging]
level = "INFO"
```

**Configuration Customization**:

Edit the file to customize settings:
```bash
# Use your preferred editor
nano ~/.config/claude-bedrock-cursor/config.toml
# or
code ~/.config/claude-bedrock-cursor/config.toml
```

**Common Customizations**:
- `aws.region`: Change to your preferred AWS region
- `bedrock.model_id`: Switch between Claude models
- `logging.level`: Set to "DEBUG" for troubleshooting

## OAuth Authentication

### Step 1: Get OAuth Token from Claude Code

```bash
# Run Claude Code's token setup command
claude setup-token
```

**Expected Flow**:
1. Browser window opens to claude.ai
2. Login with your Claude MAX account
3. Authorize the application
4. Copy the generated token
5. Token is automatically saved

**Important Notes**:
- ⏰ OAuth tokens expire after a short time (use immediately)
- 🔒 Never share your OAuth token
- ✨ This token is exchanged for long-lived access/refresh tokens

### Step 2: Login with OAuth Token

```bash
# Login using the OAuth token
claude-bedrock auth login
```

**Expected Output**:
```bash
🔐 Claude Bedrock Cursor - OAuth Login

📋 Step 1: Get OAuth token
   Run: claude setup-token

📋 Step 2: Paste the token below

Enter OAuth token: [paste token here]

🔄 Exchanging OAuth token for access tokens...
✅ Successfully authenticated!

📊 Token Information:
   Access Token: Expires in 5 minutes
   Refresh Token: Valid for 7 days

💾 Tokens securely stored in system keyring
✨ Login complete!
```

### Step 3: Verify Authentication

```bash
# Check authentication status
claude-bedrock auth status
```

**Expected Output**:
```bash
🔐 Authentication Status

✅ Authenticated
   Access Token: Valid (expires in 4 minutes)
   Refresh Token: Valid (expires in 6 days, 23 hours)

🔄 Auto-refresh: Enabled
   Next refresh: In 3 minutes

✨ All systems operational
```

**Token Lifecycle**:
- **Access Token**: 5-minute lifespan, used for API requests
- **Refresh Token**: 7-day lifespan, rotated on every use (security best practice)
- **Auto-refresh**: Automatically refreshes access token when expired

## AWS Bedrock Setup

### Step 1: Configure AWS Credentials

**Method 1: Using AWS CLI (Recommended)**:
```bash
# Configure AWS credentials
aws configure

# Enter when prompted:
# AWS Access Key ID: [your-access-key]
# AWS Secret Access Key: [your-secret-key]
# Default region name: us-east-1
# Default output format: json
```

**Method 2: Manual Configuration**:
```bash
# Create credentials file
mkdir -p ~/.aws
cat > ~/.aws/credentials << EOF
[default]
aws_access_key_id = YOUR_ACCESS_KEY
aws_secret_access_key = YOUR_SECRET_KEY
EOF

# Create config file
cat > ~/.aws/config << EOF
[default]
region = us-east-1
output = json
EOF
```

### Step 2: Run AWS Setup Wizard

```bash
# Interactive AWS setup
claude-bedrock aws setup
```

**Expected Flow**:
```bash
🔧 AWS Bedrock Setup

📋 Step 1: Verify AWS credentials
✅ AWS credentials found (profile: default)

📋 Step 2: Check AWS Bedrock access
🔍 Testing connection to Bedrock...
✅ Bedrock accessible in us-east-1

📋 Step 3: Verify Claude model availability
🔍 Checking model: anthropic.claude-sonnet-4-20250514-v1:0
✅ Model available and ready

📋 Step 4: Generate IAM policy (least privilege)
📄 IAM Policy generated at: ~/.config/claude-bedrock-cursor/iam-policy.json

💡 Recommendation:
   Review the IAM policy and apply it to your AWS user/role
   for production deployments.

✨ AWS setup complete!
```

### Step 3: Validate Bedrock Configuration

```bash
# Validate AWS Bedrock setup
claude-bedrock aws validate
```

**Expected Output**:
```text
✅ AWS Configuration Valid

Region: us-east-1
Profile: default
Bedrock Endpoint: bedrock-runtime.us-east-1.amazonaws.com

✅ Model Access Valid

Model ID: anthropic.claude-sonnet-4-20250514-v1:0
Model Status: ACTIVE
Streaming: Supported
Prompt Caching: Supported

✅ IAM Permissions Valid

- bedrock:InvokeModel: ✓
- bedrock:InvokeModelWithResponseStream: ✓

✨ All validations passed!
```

### Step 4: Apply IAM Policy (Production)

**For Production Environments**:

1. **View Generated Policy**:
   ```bash
   cat ~/.config/claude-bedrock-cursor/iam-policy.json
   ```

2. **Apply via AWS Console**:
   - Go to IAM → Policies → Create Policy
   - Paste JSON content
   - Name: `ClaudeBedrockCursorAccess`
   - Attach to your IAM user/role

3. **Or Apply via CLI**:
   ```bash
   aws iam create-policy \
     --policy-name ClaudeBedrockCursorAccess \
     --policy-document file://~/.config/claude-bedrock-cursor/iam-policy.json

   # Attach to user
   aws iam attach-user-policy \
     --user-name YOUR_USERNAME \
     --policy-arn arn:aws:iam::YOUR_ACCOUNT_ID:policy/ClaudeBedrockCursorAccess
   ```

## Cursor IDE Integration

### Step 1: Install Cursor Integration

```bash
# Install Cursor integration
claude-bedrock cursor install
```

**Expected Output**:
```text
🎨 Installing Cursor Integration

📋 Step 1: Detect Cursor installation
✅ Cursor found at: /Applications/Cursor.app

📋 Step 2: Generate Cursor rules
✅ Created: /path/to/project/.cursor/index.mdc
✅ Created: /path/to/project/.cursor/rules/aws-bedrock.mdc
✅ Created: /path/to/project/.cursor/rules/oauth-auth.mdc

📋 Step 3: Configure Cursor settings
✅ Updated: ~/.cursor/settings.json

💡 Configuration:
   - AI Provider: AWS Bedrock
   - Model: Claude Sonnet 4
   - Streaming: Enabled
   - Caching: Enabled

✨ Cursor integration complete!
```

### Step 2: Verify Cursor Configuration

```bash
# Check Cursor integration status
claude-bedrock cursor status
```

**Expected Output**:
```bash
🎨 Cursor Integration Status

✅ Cursor Detected
   Version: 0.40.3
   Path: /Applications/Cursor.app

✅ Configuration Valid
   Settings: ~/.cursor/settings.json
   Rules: .cursor/ (3 files)

✅ Bedrock Connection
   Provider: AWS Bedrock
   Model: anthropic.claude-sonnet-4-20250514-v1:0
   Streaming: Enabled

✨ Cursor ready for Claude Code!
```

### Step 3: Test in Cursor IDE

1. **Open Cursor IDE**
2. **Open any project**
3. **Open Cursor AI panel** (Cmd+L or Ctrl+L)
4. **Test query**: "Hello, can you verify the Bedrock connection?"
5. **Expected**: Response streaming from Claude via Bedrock

## First Query

### Test via CLI

```bash
# Test basic model invocation
claude-bedrock models test
```

**Expected Output**:
```text
🧪 Testing Claude Sonnet 4 Model

📤 Sending test prompt...
Prompt: "Hello! Please respond with a brief greeting to confirm the connection."

📥 Response:
───────────────────────────────────────────────────────
Hello! Connection confirmed. I'm Claude, running on AWS Bedrock
through your integration. The streaming and prompt caching are
working correctly. How can I assist you today?
───────────────────────────────────────────────────────

✅ Model test successful!

📊 Metrics:
   Response Time: 1.2s
   Tokens Used: 47
   Streaming: Enabled
   Caching: Used (90% cost savings!)

✨ Test complete!
```

### Test via Cursor

1. **Open Cursor**
2. **Open Cursor AI** (Cmd+L / Ctrl+L)
3. **Enter**: "Write a simple Python hello world function"
4. **Verify**:
   - Response streams in real-time
   - Code suggestions appear
   - No authentication errors

## Verification

### Run Complete Status Check

```bash
# Check overall system status
claude-bedrock status
```

**Expected Output**:
```text
🚀 Claude Bedrock Cursor - System Status

✅ Authentication
   Status: Authenticated
   Access Token: Valid (4 minutes remaining)
   Refresh Token: Valid (6 days remaining)

✅ AWS Bedrock
   Region: us-east-1
   Model: anthropic.claude-sonnet-4-20250514-v1:0
   Connection: Active
   Streaming: Enabled
   Caching: Enabled

✅ Cursor IDE
   Installed: Yes
   Configured: Yes
   Integration: Active

✅ Configuration
   Config File: ~/.config/claude-bedrock-cursor/config.toml
   Valid: Yes

📊 Cost Optimization
   Prompt Caching: Enabled (90% savings)
   Streaming: Enabled (better UX)
   Token Limit: 4096 (optimized)

✨ All systems operational!
```

### Verify Key Features

**1. Authentication Auto-Refresh**:
```bash
# Wait for access token to expire (5 minutes)
# Then run:
claude-bedrock auth status

# Should show new access token automatically
```

**2. Prompt Caching**:
```bash
# Run same query twice
claude-bedrock models test

# Second run should show:
# "Caching: Cache hit (90% cost savings!)"
```

**3. Streaming**:
```bash
# In Cursor AI panel, watch response stream in real-time
# Should see word-by-word output, not all at once
```

## Next Steps

### Recommended Reading

1. **[AWS Bedrock Setup Guide](./aws-bedrock-setup.md)**
   - Detailed AWS configuration
   - Regional deployment
   - Cost optimization strategies

2. **[OAuth Authentication Guide](./oauth-authentication.md)**
   - Token lifecycle management
   - Security best practices
   - Troubleshooting auth issues

3. **[Cursor Integration Guide](./cursor-integration.md)**
   - Advanced Cursor configuration
   - Custom rules and templates
   - Extension development

4. **[Cost Optimization Guide](./cost-optimization.md)**
   - Prompt caching strategies
   - Token usage optimization
   - CloudWatch monitoring

5. **[Security Best Practices](./security-best-practices.md)**
   - Token security
   - IAM hardening
   - Audit logging

### Common Next Actions

**For Development**:
```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
claude-bedrock status

# Monitor costs
# Set up CloudWatch dashboard (see cost-optimization.md)
```

**For Production**:
```bash
# Apply IAM least-privilege policy
# (See IAM policy generation in aws-bedrock-setup.md)

# Set up monitoring
# (See monitoring setup in cost-optimization.md)

# Configure log aggregation
# (See logging configuration in security-best-practices.md)
```

## Troubleshooting

### Common Issues

**Issue: "OAuth token invalid or expired"**

**Solution**:
```bash
# Get fresh token
claude setup-token

# Re-login
claude-bedrock auth login
```

**Issue: "AWS credentials not found"**

**Solution**:
```bash
# Configure AWS CLI
aws configure

# Or manually create ~/.aws/credentials
```

**Issue: "Bedrock model not available"**

**Solution**:
1. Verify region supports Claude models: `us-east-1`, `us-west-2`
2. Check model availability:
   ```bash
   aws bedrock list-foundation-models \
     --region us-east-1 \
     --by-provider anthropic
   ```
3. Request model access in AWS Console

**Issue: "Cursor not detecting Bedrock"**

**Solution**:
```bash
# Re-run installation
claude-bedrock cursor install

# Restart Cursor IDE completely
```

For more troubleshooting: [docs/troubleshooting.md](./troubleshooting.md)

## Getting Help

- **Issues**: [GitHub Issues](https://github.com/yourusername/claude-bedrock-cursor/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/claude-bedrock-cursor/discussions)
- **Documentation**: [docs/](https://github.com/yourusername/claude-bedrock-cursor/tree/main/docs)
- **Email**: support@example.com

---

**Next**: [AWS Bedrock Setup →](./aws-bedrock-setup.md)
