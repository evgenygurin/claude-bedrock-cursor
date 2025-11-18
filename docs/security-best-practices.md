# Security Best Practices

Production security guidelines for Claude Bedrock Cursor integration.

## Authentication Security

### Token Management

✅ **DO**:
- Use system keyring for token storage
- Rotate refresh tokens on every use
- Set short expiry times (5 min access, 7 days refresh)
- Implement auto-refresh to minimize token lifetime
- Monitor failed authentication attempts

❌ **DON'T**:
- Store tokens in environment variables (except CI/CD)
- Write tokens to files
- Log tokens in any form
- Share tokens between users/machines
- Use same refresh token twice

### OAuth Security

```python
# Secure OAuth flow
async def login(self, oauth_token: str) -> TokenPair:
    # 1. Exchange OAuth token immediately (short-lived)
    tokens = await self.exchange_oauth_token(oauth_token)

    # 2. Store in encrypted keyring
    self.storage.store_token("access_token", tokens.access_token)
    self.storage.store_token("refresh_token", tokens.refresh_token)

    # 3. Clear OAuth token from memory
    del oauth_token

    return tokens
```

## AWS IAM Security

### Least Privilege Policy

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "BedrockInvokeOnly",
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

**Key Restrictions**:
- ✅ Specific actions only (no `bedrock:*`)
- ✅ Specific model ARN (no wildcards)
- ✅ Region restriction
- ✅ No model management permissions

### MFA for Production

```bash
# Enable MFA for AWS account
aws iam enable-mfa-device \
  --user-name claude-bedrock-user \
  --serial-number arn:aws:iam::123456789012:mfa/claude-bedrock-user \
  --authentication-code1 123456 \
  --authentication-code2 789012
```

## Data Security

### No Sensitive Data in Prompts

```python
# BAD: Sensitive data in prompt
prompt = f"Process order for customer {customer_ssn}"

# GOOD: Masked or tokenized data
customer_id = hash_ssn(customer_ssn)
prompt = f"Process order for customer {customer_id}"
```

### Audit Logging

```bash
# Enable CloudTrail for Bedrock API calls
aws cloudtrail create-trail \
  --name bedrock-audit \
  --s3-bucket-name my-audit-logs

# Enable logging
aws cloudtrail start-logging --name bedrock-audit

# Configure event selectors
aws cloudtrail put-event-selectors \
  --trail-name bedrock-audit \
  --event-selectors '[{
    "ReadWriteType": "All",
    "IncludeManagementEvents": true,
    "DataResources": [{
      "Type": "AWS::Bedrock::Model",
      "Values": ["arn:aws:bedrock:*:*:foundation-model/*"]
    }]
  }]'
```

## Network Security

### VPC Endpoints (Private Access)

```bash
# Create VPC endpoint for Bedrock
aws ec2 create-vpc-endpoint \
  --vpc-id vpc-12345678 \
  --service-name com.amazonaws.us-east-1.bedrock-runtime \
  --subnet-ids subnet-12345678 \
  --security-group-ids sg-12345678
```

**Benefits**:
- Traffic stays within AWS network
- No internet exposure
- Enhanced compliance (HIPAA, SOC 2)

### TLS/HTTPS Only

```python
# Enforce HTTPS for all API calls
async with httpx.AsyncClient(
    verify=True,  # Verify SSL certificates
    http2=True,   # Use HTTP/2 for security
) as client:
    response = await client.post(
        "https://api.claude.ai/v1/oauth/token",  # HTTPS only!
        json=payload
    )
```

## Application Security

### Input Validation

```python
from pydantic import BaseModel, Field, validator

class PromptRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=100_000)
    max_tokens: int = Field(default=4096, ge=4096, le=100_000)

    @validator("prompt")
    def validate_prompt(cls, v):
        # Prevent prompt injection
        if "<script>" in v.lower() or "javascript:" in v.lower():
            raise ValueError("Invalid prompt content")
        return v
```

### Error Handling

```python
# DON'T expose sensitive info in errors
try:
    tokens = await oauth_manager.refresh_access_token()
except Exception as e:
    # BAD: Exposes token
    raise ValueError(f"Refresh failed with token {current_token}: {e}")

    # GOOD: Generic error
    raise ValueError("Authentication refresh failed. Please re-login.")
```

## Secrets Management

### Never Commit Secrets

```bash
# .gitignore
.env
.env.local
*.pem
*.key
config.local.toml
.aws/credentials
```

### Gitleaks Configuration

```.gitleaks.toml
# Already configured in project
[allowlist]
paths = [
  "tests/",  # Test fixtures okay
]

[[rules]]
id = "aws-access-key"
description = "AWS Access Key"
regex = '''(A3T[A-Z0-9]|AKIA|AGPA|AIDA|AROA|AIPA|ANPA|ANVA|ASIA)[A-Z0-9]{16}'''

[[rules]]
id = "oauth-token"
description = "OAuth Token"
regex = '''(oauth|bearer)[\s]*[:=][\s]*['"]?([a-zA-Z0-9\-_]{20,})['"]?'''
```

## Monitoring & Alerts

### Security Monitoring

```bash
# CloudWatch alarm for auth failures
aws cloudwatch put-metric-alarm \
  --alarm-name bedrock-auth-failures \
  --metric-name 4xxError \
  --namespace AWS/Bedrock \
  --statistic Sum \
  --period 300 \
  --threshold 10 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 1
```

### Regular Security Scans

```bash
# Run security scan
make security

# Included scans:
# - Bandit (SAST)
# - Gitleaks (secrets)
# - pip-audit (dependencies)
# - Safety (vulnerability DB)
```

## Compliance

### GDPR/Privacy

- **No PII in prompts** without user consent
- **Data retention**: Cache expires in 5 minutes
- **Right to deletion**: Logout clears all tokens
- **Transparency**: Document data flows

### HIPAA (Healthcare)

- Use **VPC endpoints** (private network)
- Enable **CloudTrail** (audit logging)
- Encrypt **data at rest** (S3 for logs)
- Encrypt **data in transit** (TLS 1.2+)

### SOC 2

- **Access control**: IAM least privilege
- **Monitoring**: CloudWatch + alerts
- **Audit trails**: CloudTrail logging
- **Incident response**: Document procedures

## Incident Response

### Compromised Tokens

```bash
# 1. Immediately logout
claude-bedrock auth logout

# 2. Revoke AWS credentials
aws iam delete-access-key \
  --access-key-id AKIAI44QH8DHBEXAMPLE

# 3. Create new credentials
aws iam create-access-key --user-name claude-bedrock-user

# 4. Re-authenticate
claude setup-token
claude-bedrock auth login

# 5. Review CloudTrail logs for unauthorized access
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=Username,AttributeValue=claude-bedrock-user \
  --start-time $(date -u -d '24 hours ago' +%Y-%m-%dT%H:%M:%S) \
  --max-results 50
```

### Suspicious Activity

```bash
# Check recent Bedrock API calls
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=InvokeModel \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S)

# Look for:
# - Unusual request volume
# - Unfamiliar source IPs
# - Off-hours activity
# - Different AWS regions
```

## Security Checklist

### Development
- [ ] Secrets in .gitignore
- [ ] Pre-commit hooks enabled (gitleaks, bandit)
- [ ] Debug logging disabled in production config
- [ ] Test data doesn't contain real credentials

### Deployment
- [ ] IAM least privilege policy applied
- [ ] MFA enabled on AWS account
- [ ] CloudTrail logging enabled
- [ ] CloudWatch alarms configured
- [ ] VPC endpoints for production (if applicable)

### Operations
- [ ] Regular security scans (weekly)
- [ ] Dependency updates (monthly)
- [ ] Audit log reviews (weekly)
- [ ] Incident response plan documented
- [ ] Security training for team members

## Next Steps

- **[Troubleshooting Guide](./troubleshooting.md)** - Common issues
- **[Architecture Documentation](./architecture.md)** - System design

---

**Previous**: [← Cost Optimization](./cost-optimization.md) | **Next**: [Troubleshooting →](./troubleshooting.md)
