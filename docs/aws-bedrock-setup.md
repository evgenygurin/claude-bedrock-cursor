# AWS Bedrock Setup Guide

Comprehensive guide for configuring AWS Bedrock to work with Claude Code models, including IAM permissions, regional deployment, cost optimization, and monitoring.

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [AWS Account Setup](#aws-account-setup)
- [Regional Deployment](#regional-deployment)
- [Model Access](#model-access)
- [IAM Configuration](#iam-configuration)
- [Cost Optimization](#cost-optimization)
- [Monitoring & Logging](#monitoring--logging)
- [Advanced Configuration](#advanced-configuration)
- [Troubleshooting](#troubleshooting)

## Overview

### What is AWS Bedrock?

AWS Bedrock is a fully managed service that provides access to foundation models from leading AI companies through a single API. It offers:

- **Serverless architecture** - No infrastructure management
- **Pay-per-use pricing** - Only pay for tokens consumed
- **Enterprise security** - AWS-level encryption and compliance
- **Streaming responses** - Better user experience
- **Prompt caching** - Up to 90% cost reduction

### Why Use Bedrock for Claude Code?

1. **Cost Control**: Precise usage tracking and budgeting
2. **Security**: Enterprise-grade data protection
3. **Scalability**: Handles any workload without infrastructure
4. **Compliance**: HIPAA, SOC 2, GDPR ready
5. **Integration**: Works seamlessly with AWS ecosystem

## Prerequisites

### Required AWS Services

- ✅ **AWS Account** with active billing
- ✅ **IAM user/role** with programmatic access
- ✅ **Bedrock service** enabled in chosen region
- ✅ **CloudWatch** for monitoring (optional but recommended)
- ✅ **CloudTrail** for audit logging (recommended for production)

### Required Tools

```bash
# AWS CLI (v2 recommended)
aws --version  # Should show 2.x.x

# Python 3.12+
python3 --version

# Claude Bedrock Cursor tool
claude-bedrock --version
```

## AWS Account Setup

### Step 1: Create IAM User (if needed)

**Option A: AWS Console**

1. Go to IAM → Users → Create User
2. **User name**: `claude-bedrock-user`
3. **Access type**: Programmatic access
4. **Attach policies**: (temporary, will refine later)
   - `AmazonBedrockFullAccess` (start broad, then narrow)
5. **Save credentials**: Download CSV with access keys

**Option B: AWS CLI**

```bash
# Create IAM user
aws iam create-user --user-name claude-bedrock-user

# Create access key
aws iam create-access-key --user-name claude-bedrock-user

# Attach temporary policy
aws iam attach-user-policy \
  --user-name claude-bedrock-user \
  --policy-arn arn:aws:iam::aws:policy/AmazonBedrockFullAccess
```

### Step 2: Configure AWS Credentials

**Method 1: AWS CLI Configuration**

```bash
# Configure credentials
aws configure --profile claude-bedrock

# Enter when prompted:
# AWS Access Key ID: AKIAIOSFODNN7EXAMPLE
# AWS Secret Access Key: wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
# Default region name: us-east-1
# Default output format: json
```

**Method 2: Environment Variables**

```bash
# Add to ~/.bashrc or ~/.zshrc
export AWS_PROFILE=claude-bedrock
export AWS_REGION=us-east-1
export AWS_DEFAULT_REGION=us-east-1
```

**Method 3: Configuration Files**

```bash
# ~/.aws/credentials
[claude-bedrock]
aws_access_key_id = AKIAIOSFODNN7EXAMPLE
aws_secret_access_key = wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY

# ~/.aws/config
[profile claude-bedrock]
region = us-east-1
output = json
```

### Step 3: Verify AWS Access

```bash
# Test basic AWS access
aws sts get-caller-identity --profile claude-bedrock

# Expected output:
{
    "UserId": "AIDAI23HXS…",
    "Account": "123456789012",
    "Arn": "arn:aws:iam::123456789012:user/claude-bedrock-user"
}
```

## Regional Deployment

### Supported Regions for Claude Models

| Region Code    | Region Name           | Claude Models Available |
|----------------|-----------------------|-------------------------|
| `us-east-1`    | US East (N. Virginia) | ✅ All models           |
| `us-west-2`    | US West (Oregon)      | ✅ All models           |
| `eu-west-1`    | Europe (Ireland)      | ✅ All models           |
| `ap-southeast-1` | Asia Pacific (Singapore) | ✅ All models      |
| `ap-northeast-1` | Asia Pacific (Tokyo) | ✅ Most models         |

**Recommendation**: Use `us-east-1` for maximum model availability and lowest latency (for US users).

### Check Model Availability

```bash
# List available Claude models in a region
aws bedrock list-foundation-models \
  --region us-east-1 \
  --by-provider anthropic \
  --query 'modelSummaries[].modelId' \
  --output table

# Expected output:
------------------------------------------------------
|            ListFoundationModels                     |
+----------------------------------------------------+
|  anthropic.claude-3-5-sonnet-20240620-v1:0        |
|  anthropic.claude-3-opus-20240229-v1:0             |
|  anthropic.claude-3-sonnet-20240229-v1:0           |
|  anthropic.claude-sonnet-4-20250514-v1:0           | ← Latest!
+----------------------------------------------------+
```

### Configure Region in Tool

```bash
# Edit configuration
nano ~/.config/claude-bedrock-cursor/config.toml

# Update region
[aws]
region = "us-east-1"  # Change to your preferred region
```

## Model Access

### Request Model Access

**Important**: Bedrock requires explicit model access grants.

**Step 1: Check Current Access**

```bash
# Use claude-bedrock tool
claude-bedrock aws validate

# Or check directly
aws bedrock get-foundation-model \
  --model-identifier anthropic.claude-sonnet-4-20250514-v1:0 \
  --region us-east-1
```

**Step 2: Request Access (if needed)**

1. **Via AWS Console**:
   - Go to Bedrock → Model access
   - Select region (top-right corner)
   - Click "Modify model access"
   - Check "Anthropic - Claude Sonnet 4"
   - Submit request

2. **Access typically granted**:
   - **Instantly** for most accounts
   - **1-2 business days** for new accounts
   - **Manual review** for high-risk regions

**Step 3: Verify Access Granted**

```bash
# Check model status
aws bedrock get-foundation-model \
  --model-identifier anthropic.claude-sonnet-4-20250514-v1:0 \
  --region us-east-1

# Look for:
# "modelLifecycle": {
#     "status": "ACTIVE"
# }
```

### Available Claude Models

| Model ID                                      | Name             | Use Case                 | Cost  |
|-----------------------------------------------|------------------|--------------------------|-------|
| `anthropic.claude-sonnet-4-20250514-v1:0`     | Claude Sonnet 4  | Best balance (recommended) | $$   |
| `anthropic.claude-3-5-sonnet-20240620-v1:0`  | Claude 3.5 Sonnet | Fast, cost-effective     | $    |
| `anthropic.claude-3-opus-20240229-v1:0`       | Claude 3 Opus    | Highest capability       | $$$  |
| `anthropic.claude-3-sonnet-20240229-v1:0`     | Claude 3 Sonnet  | Legacy version           | $    |

**Recommendation**: Use **Claude Sonnet 4** for best balance of capability, speed, and cost.

## IAM Configuration

### Least Privilege Policy

The tool automatically generates a minimal IAM policy. Here's the structure:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "BedrockInvokeModel",
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ],
      "Resource": [
        "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-sonnet-4-20250514-v1:0"
      ],
      "Condition": {
        "StringEquals": {
          "aws:RequestedRegion": ["us-east-1"]
        }
      }
    }
  ]
}
```

**Key Security Features**:

- ✅ **Specific actions only**: Only model invocation, no model management
- ✅ **Resource restriction**: Only Claude models, specific version
- ✅ **Region restriction**: Only allowed regions
- ✅ **No wildcard permissions**: Explicit resource ARNs

### Generate and Apply IAM Policy

**Step 1: Generate Policy**

```bash
# Generate IAM policy with tool
claude-bedrock aws setup

# Policy saved to:
# ~/.config/claude-bedrock-cursor/iam-policy.json
```

**Step 2: Review Policy**

```bash
# View generated policy
cat ~/.config/claude-bedrock-cursor/iam-policy.json

# Customize if needed (e.g., add multiple regions)
nano ~/.config/claude-bedrock-cursor/iam-policy.json
```

**Step 3: Create IAM Policy**

```bash
# Create policy in AWS
aws iam create-policy \
  --policy-name ClaudeBedrockCursorAccess \
  --policy-document file://~/.config/claude-bedrock-cursor/iam-policy.json \
  --description "Least privilege access for Claude Bedrock Cursor integration"

# Save the policy ARN from output:
# "Arn": "arn:aws:iam::123456789012:policy/ClaudeBedrockCursorAccess"
```

**Step 4: Attach Policy to User/Role**

```bash
# For IAM User
aws iam attach-user-policy \
  --user-name claude-bedrock-user \
  --policy-arn arn:aws:iam::123456789012:policy/ClaudeBedrockCursorAccess

# For IAM Role (e.g., EC2 instance role)
aws iam attach-role-policy \
  --role-name MyEC2Role \
  --policy-arn arn:aws:iam::123456789012:policy/ClaudeBedrockCursorAccess
```

**Step 5: Remove Broad Permissions**

```bash
# Remove temporary full access policy
aws iam detach-user-policy \
  --user-name claude-bedrock-user \
  --policy-arn arn:aws:iam::aws:policy/AmazonBedrockFullAccess
```

### Multi-Region Setup

For multi-region deployments:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "BedrockMultiRegion",
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ],
      "Resource": [
        "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-*",
        "arn:aws:bedrock:us-west-2::foundation-model/anthropic.claude-*",
        "arn:aws:bedrock:eu-west-1::foundation-model/anthropic.claude-*"
      ],
      "Condition": {
        "StringEquals": {
          "aws:RequestedRegion": [
            "us-east-1",
            "us-west-2",
            "eu-west-1"
          ]
        }
      }
    }
  ]
}
```

## Cost Optimization

### Understanding Bedrock Pricing

**Input Tokens** (what you send):
- Claude Sonnet 4: **$3.00 per million tokens**
- With caching: **$0.30 per million tokens** (90% savings!)

**Output Tokens** (what Claude generates):
- Claude Sonnet 4: **$15.00 per million tokens**
- No caching for output tokens

### Enable Prompt Caching

**Configuration**:

```bash
# Edit config
nano ~/.config/claude-bedrock-cursor/config.toml

# Ensure caching is enabled
[bedrock]
enable_prompt_caching = true  # Default: true (don't disable!)
```

**How It Works**:

```python
# Large, unchanging context (e.g., codebase context)
system_context = """
[Large context about your codebase, coding standards, etc.]
This content rarely changes but is sent with every request.
"""

# Bedrock request with caching
body = {
    "system": [
        {
            "type": "text",
            "text": system_context,
            "cache_control": {"type": "ephemeral"}  # CACHE THIS!
        }
    ],
    "messages": [...]
}

# Result:
# - First request: Full cost ($3.00/M tokens)
# - Subsequent requests: 90% discount ($0.30/M tokens)
# - Cache lifetime: 5 minutes
```

**Savings Example**:

| Scenario | Without Caching | With Caching | Savings |
|----------|----------------|--------------|---------|
| 1000 requests/day with 50K token context | $150/day | $15.05/day | **90%** |
| Monthly cost | $4,500 | $451.50 | **$4,048.50** |

### Set Up Cost Alerts

**Step 1: Create SNS Topic**

```bash
# Create topic for alerts
aws sns create-topic \
  --name bedrock-cost-alerts \
  --region us-east-1

# Subscribe your email
aws sns subscribe \
  --topic-arn arn:aws:sns:us-east-1:123456789012:bedrock-cost-alerts \
  --protocol email \
  --notification-endpoint your-email@example.com
```

**Step 2: Create Budget**

```bash
# Create budget via AWS Console:
# 1. Go to AWS Budgets
# 2. Create budget
# 3. Name: "Claude Bedrock Monthly"
# 4. Period: Monthly
# 5. Budget amount: $100 (adjust to your needs)
# 6. Alerts:
#    - 50% threshold → SNS notification
#    - 80% threshold → SNS notification
#    - 100% threshold → SNS notification + potential action
```

**Step 3: Monitor Usage**

```bash
# View current month costs
aws ce get-cost-and-usage \
  --time-period Start=$(date -d "1 month ago" +%Y-%m-01),End=$(date +%Y-%m-%d) \
  --granularity MONTHLY \
  --metrics BlendedCost \
  --filter file://bedrock-filter.json

# bedrock-filter.json:
{
  "Dimensions": {
    "Key": "SERVICE",
    "Values": ["Amazon Bedrock"]
  }
}
```

## Monitoring & Logging

### CloudWatch Metrics

**Enable Bedrock Metrics** (automatic):

```bash
# View invocation count
aws cloudwatch get-metric-statistics \
  --namespace AWS/Bedrock \
  --metric-name Invocations \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Sum \
  --region us-east-1

# View input token count
aws cloudwatch get-metric-statistics \
  --namespace AWS/Bedrock \
  --metric-name InputTokens \
  --dimensions Name=ModelId,Value=anthropic.claude-sonnet-4-20250514-v1:0 \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Sum \
  --region us-east-1
```

**Available Metrics**:

- `Invocations` - Total API calls
- `InputTokens` - Tokens sent to model
- `OutputTokens` - Tokens generated by model
- `Throttles` - Rate limit hits
- `ModelInvocationLatency` - Response time
- `ClientErrors` - 4xx errors
- `ServerErrors` - 5xx errors

### CloudWatch Dashboard

Create a monitoring dashboard:

```bash
# dashboard.json
{
  "widgets": [
    {
      "type": "metric",
      "properties": {
        "metrics": [
          ["AWS/Bedrock", "Invocations"],
          [".", "InputTokens"],
          [".", "OutputTokens"]
        ],
        "period": 300,
        "stat": "Sum",
        "region": "us-east-1",
        "title": "Bedrock Usage"
      }
    }
  ]
}

# Create dashboard
aws cloudwatch put-dashboard \
  --dashboard-name ClaudeBedrockMonitoring \
  --dashboard-body file://dashboard.json
```

### CloudTrail Logging

**Enable CloudTrail** (for audit compliance):

```bash
# Create S3 bucket for logs
aws s3 mb s3://my-bedrock-cloudtrail-logs-123456

# Enable CloudTrail
aws cloudtrail create-trail \
  --name bedrock-audit-trail \
  --s3-bucket-name my-bedrock-cloudtrail-logs-123456

# Start logging
aws cloudtrail start-logging --name bedrock-audit-trail

# Configure to log Bedrock events
aws cloudtrail put-event-selectors \
  --trail-name bedrock-audit-trail \
  --event-selectors file://event-selectors.json

# event-selectors.json:
{
  "EventSelectors": [
    {
      "ReadWriteType": "All",
      "IncludeManagementEvents": true,
      "DataResources": [
        {
          "Type": "AWS::Bedrock::Model",
          "Values": ["arn:aws:bedrock:*:*:foundation-model/*"]
        }
      ]
    }
  ]
}
```

## Advanced Configuration

### Inference Profiles

Use cross-region inference for higher availability:

```bash
# Create cross-region inference profile
aws bedrock create-inference-profile \
  --inference-profile-name claude-sonnet-4-multi-region \
  --model-source '{
    "copyFrom": "anthropic.claude-sonnet-4-20250514-v1:0"
  }' \
  --region us-east-1
```

### Custom Model Configuration

```bash
# Edit config for advanced settings
nano ~/.config/claude-bedrock-cursor/config.toml

[bedrock]
model_id = "anthropic.claude-sonnet-4-20250514-v1:0"
max_output_tokens = 4096  # Bedrock minimum (don't go lower!)
max_thinking_tokens = 1024  # For Claude's reasoning
temperature = 1.0  # Default: balanced creativity
top_p = 0.999  # Default: full sampling range
top_k = 250  # Default: diverse token selection

# Advanced settings
enable_prompt_caching = true
enable_streaming = true
retry_max_attempts = 3
retry_backoff_base = 2
timeout_seconds = 300
```

### VPC Endpoint (Private Access)

For enhanced security, use VPC endpoints:

```bash
# Create VPC endpoint for Bedrock
aws ec2 create-vpc-endpoint \
  --vpc-id vpc-12345678 \
  --service-name com.amazonaws.us-east-1.bedrock-runtime \
  --subnet-ids subnet-12345678 subnet-87654321 \
  --security-group-ids sg-12345678

# Update config to use VPC endpoint
[aws]
use_vpc_endpoint = true
vpc_endpoint_url = "https://vpce-12345678-abcd.bedrock-runtime.us-east-1.vpce.amazonaws.com"
```

## Troubleshooting

### Common Issues

**Issue: "AccessDeniedException: User is not authorized"**

**Diagnosis**:
```bash
# Check IAM permissions
aws iam get-user-policy \
  --user-name claude-bedrock-user \
  --policy-name ClaudeBedrockCursorAccess

# Verify model access
aws bedrock get-foundation-model \
  --model-identifier anthropic.claude-sonnet-4-20250514-v1:0
```

**Solutions**:
1. Ensure IAM policy includes `bedrock:InvokeModel` action
2. Verify resource ARN matches model ID
3. Check region restrictions in policy
4. Confirm model access granted in Bedrock console

---

**Issue: "ThrottlingException: Rate exceeded"**

**Diagnosis**:
```bash
# Check CloudWatch for throttling metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/Bedrock \
  --metric-name Throttles \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Sum
```

**Solutions**:
1. Implement exponential backoff (already in client)
2. Request quota increase via AWS Support
3. Spread requests across multiple regions
4. Use inference profiles for load balancing

---

**Issue: "ValidationException: MAX_OUTPUT_TOKENS too low"**

**Solution**:
```bash
# Bedrock requires minimum 4096 tokens
# Edit config:
nano ~/.config/claude-bedrock-cursor/config.toml

[bedrock]
max_output_tokens = 4096  # Don't go lower than this!
```

---

**Issue: Prompt caching not working**

**Diagnosis**:
```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
claude-bedrock models test

# Look for cache hit/miss in logs
```

**Solutions**:
1. Ensure `cache_control` field in system message
2. Cache lifetime is 5 minutes (may have expired)
3. Context must be >1024 tokens to benefit
4. Verify `enable_prompt_caching = true` in config

## Next Steps

### Recommended Reading

- **[Cost Optimization Guide](./cost-optimization.md)** - Deep dive into cost savings
- **[Monitoring & Observability](./cost-optimization.md#monitoring)** - CloudWatch dashboards
- **[Security Best Practices](./security-best-practices.md)** - Production hardening
- **[Troubleshooting Guide](./troubleshooting.md)** - Common issues and solutions

### Production Checklist

- [ ] Apply least-privilege IAM policy
- [ ] Enable CloudWatch monitoring
- [ ] Set up cost alerts and budgets
- [ ] Enable CloudTrail for audit logging
- [ ] Configure VPC endpoints (if required)
- [ ] Test failover to secondary region
- [ ] Document disaster recovery procedures
- [ ] Set up automated backups of configurations

---

**Previous**: [← Setup Guide](./setup-guide.md) | **Next**: [Cursor Integration Guide →](./cursor-integration.md)
