# Cost Optimization Guide

Strategies for minimizing AWS Bedrock costs while maintaining high performance and user experience.

## Cost Breakdown

### Bedrock Pricing (Claude Sonnet 4)

| Component | Cost | Notes |
|-----------|------|-------|
| Input tokens (standard) | $3.00/M tokens | What you send to Claude |
| Input tokens (cached) | $0.30/M tokens | **90% savings!** |
| Output tokens | $15.00/M tokens | What Claude generates |

**Key Insight**: Input tokens with caching cost **10x less** ($0.30 vs $3.00 per million).

## Prompt Caching (90% Savings!)

### How It Works

```python
# Without caching: $3.00/M input tokens
body = {
    "messages": [{"role": "user", "content": prompt}]
}

# With caching: $0.30/M input tokens (90% discount!)
body = {
    "system": [{
        "type": "text",
        "text": large_unchanging_context,  # e.g., codebase, standards
        "cache_control": {"type": "ephemeral"}  # CACHE THIS!
    }],
    "messages": [{"role": "user", "content": prompt}]
}
```

### Savings Example

**Scenario**: 1000 requests/day, 50K token context

| Approach | Daily Cost | Monthly Cost | Annual Cost |
|----------|------------|--------------|-------------|
| No caching | $150 | $4,500 | $54,000 |
| **With caching** | **$15.05** | **$451.50** | **$5,418** |
| **Savings** | **$134.95** | **$4,048.50** | **$48,582** |

### Best Practices

1. **Cache large, stable context** (>1024 tokens):
   - Project documentation
   - Coding standards
   - Architecture patterns
   - Common examples

2. **Don't cache frequently changing data**:
   - User-specific prompts
   - Real-time data
   - Session-specific context

3. **Cache lifetime**: 5 minutes
   - Subsequent requests within 5 min get discount
   - After 5 min, cache expires (pay full price once, then discount again)

### Configuration

```bash
# Ensure caching enabled
nano ~/.config/claude-bedrock-cursor/config.toml

[bedrock]
enable_prompt_caching = true  # Default: true (DON'T DISABLE!)
```

## Token Management

### Output Token Optimization

**Problem**: Output tokens cost $15/M (5x more than input)

**Solutions**:

1. **Precise Prompts**: Ask for concise responses
   ```python
   # Verbose: May generate 500 tokens
   "Explain how to implement OAuth in Python"

   # Concise: Generates ~200 tokens (60% cost savings)
   "Provide a minimal OAuth implementation in Python with refresh token rotation"
   ```

2. **Set MAX_OUTPUT_TOKENS wisely**:
   ```toml
   [bedrock]
   max_output_tokens = 4096  # Bedrock minimum (don't go lower!)

   # Higher values = potentially more cost
   # Lower values = risk cutting off responses
   ```

3. **Use streaming for user control**:
   ```python
   # User can stop generation early if satisfied
   async for chunk in bedrock_client.invoke_streaming(prompt):
       print(chunk, end="")
       # User hits Ctrl+C when they have enough
   ```

### Input Token Optimization

1. **Selective Context**: Include only relevant files/functions
2. **Summarization**: Summarize large docs before sending
3. **Deduplication**: Remove redundant information

## Monitoring Costs

### CloudWatch Metrics

```bash
# Get token usage for current month
aws cloudwatch get-metric-statistics \
  --namespace AWS/Bedrock \
  --metric-name InputTokens \
  --dimensions Name=ModelId,Value=anthropic.claude-sonnet-4-20250514-v1:0 \
  --start-time $(date -d "$(date +%Y-%m-01)" +%Y-%m-%dT00:00:00) \
  --end-time $(date +%Y-%m-%dT23:59:59) \
  --period 86400 \
  --statistics Sum

# Calculate cost:
# Total Input Tokens ÷ 1,000,000 × $3.00 (or $0.30 if cached)
```

### Cost Alerts

```bash
# Create SNS topic
aws sns create-topic --name bedrock-cost-alerts

# Create budget
aws budgets create-budget \
  --account-id $(aws sts get-caller-identity --query Account --output text) \
  --budget file://budget.json

# budget.json:
{
  "BudgetName": "Claude Bedrock Monthly",
  "BudgetType": "COST",
  "TimeUnit": "MONTHLY",
  "BudgetLimit": {
    "Amount": "100",
    "Unit": "USD"
  },
  "CostFilters": {
    "Service": ["Amazon Bedrock"]
  }
}
```

## Cost Estimation

### Calculate Your Costs

**Formula**:
```text
Daily Cost = (Requests × Input Tokens × Input Price) +
             (Requests × Output Tokens × Output Price)

With Caching (after first request):
Daily Cost = (Requests × Input Tokens × $0.30/M) +
             (Requests × Output Tokens × $15.00/M)
```

**Example Calculation**:
- 100 requests/day
- 10K input tokens per request (cached after first)
- 500 output tokens per request

```text
Input cost:  100 × 10,000 ÷ 1,000,000 × $0.30 = $0.30/day
Output cost: 100 × 500 ÷ 1,000,000 × $15.00 = $0.75/day
Total: $1.05/day × 30 = $31.50/month
```

### Cost Calculator Script

```python
def calculate_monthly_cost(
    requests_per_day: int,
    input_tokens_per_request: int,
    output_tokens_per_request: int,
    caching_enabled: bool = True
):
    """Calculate monthly Bedrock costs."""
    INPUT_PRICE = 0.30 if caching_enabled else 3.00  # per million
    OUTPUT_PRICE = 15.00  # per million

    daily_input = (requests_per_day * input_tokens_per_request / 1_000_000) * INPUT_PRICE
    daily_output = (requests_per_day * output_tokens_per_request / 1_000_000) * OUTPUT_PRICE

    monthly = (daily_input + daily_output) * 30

    return {
        "daily": daily_input + daily_output,
        "monthly": monthly,
        "annual": monthly * 12
    }

# Example usage
costs = calculate_monthly_cost(
    requests_per_day=100,
    input_tokens_per_request=10_000,
    output_tokens_per_request=500
)
print(f"Monthly cost: ${costs['monthly']:.2f}")
```

## Regional Optimization

### Regional Pricing

Bedrock pricing is consistent across regions, but consider:

- **Latency**: Choose region closest to users
- **Data Transfer**: Cross-region egress costs money
- **Availability**: Some regions may have higher availability

**Recommendation**: Use `us-east-1` for US users (lowest latency, highest availability).

## Next Steps

- **[Monitoring Setup](./aws-bedrock-setup.md#monitoring--logging)** - CloudWatch dashboards
- **[Security Best Practices](./security-best-practices.md)** - Production hardening
- **[Troubleshooting](./troubleshooting.md)** - Common issues

---

**Previous**: [← OAuth Authentication](./oauth-authentication.md) | **Next**: [Security Best Practices →](./security-best-practices.md)
