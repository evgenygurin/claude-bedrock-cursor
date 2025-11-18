# OAuth Authentication Guide

Comprehensive guide for OAuth2 authentication with Claude MAX subscription, including token lifecycle, security patterns, and troubleshooting.

## Overview

This integration uses **OAuth2 with refresh token rotation** for secure authentication with Claude Code API through your Claude MAX subscription.

### Key Security Features

- ✅ **Refresh Token Rotation**: New refresh token on every use (prevents token reuse attacks)
- ✅ **System Keyring Storage**: OS-level encrypted credential storage
- ✅ **Auto-Refresh**: Automatic access token renewal before expiration
- ✅ **No Token Logging**: Tokens never logged or exposed in errors
- ✅ **Short-Lived Access Tokens**: 5-minute lifetime reduces exposure window

## Token Lifecycle

### Access Token

- **Lifetime**: 5 minutes
- **Purpose**: Authenticate API requests to Claude Code
- **Storage**: System keyring (encrypted)
- **Auto-Refresh**: Automatically refreshed when expired or within 2 minutes of expiry

### Refresh Token

- **Lifetime**: 7 days
- **Purpose**: Obtain new access tokens
- **Storage**: System keyring (encrypted)
- **Security**: Rotated (replaced) on EVERY use
- **Invalidation**: Old refresh token becomes invalid after rotation

### Token Flow Diagram

```text
Initial Login:
OAuth Token → Exchange → Access Token (5 min)
                      └→ Refresh Token (7 days)
                                          ↓
                                   [System Keyring]

Token Refresh (automatic every ~3-4 minutes):
Current Refresh Token → API → New Access Token (5 min)
                          └→ New Refresh Token (7 days)
                                          ↓
                              Old Refresh Token INVALIDATED
```

## Authentication Commands

### Login

```bash
# Step 1: Get OAuth token from Claude Code
claude setup-token

# Step 2: Login with OAuth token
claude-bedrock auth login

# Expected flow:
# 1. Paste OAuth token when prompted
# 2. Tool exchanges for access + refresh tokens
# 3. Tokens stored securely in system keyring
# 4. Success confirmation
```

### Status Check

```bash
# Check authentication status
claude-bedrock auth status

# Output shows:
# - Authentication status (✅ Authenticated / ❌ Not authenticated)
# - Access token expiry time
# - Refresh token expiry time
# - Auto-refresh status
```

### Manual Refresh

```bash
# Manually refresh access token (usually automatic)
claude-bedrock auth refresh

# Use cases:
# - Testing refresh flow
# - Forcing new tokens
# - Debugging auth issues
```

### Logout

```bash
# Logout and clear all tokens
claude-bedrock auth logout

# What this does:
# - Deletes access token from keyring
# - Deletes refresh token from keyring
# - Confirms successful cleanup
```

## Security Patterns

### Token Rotation Implementation

```python
async def refresh_access_token(self) -> TokenPair:
    """Refresh access token and rotate refresh token.

    SECURITY: Implements token rotation - refresh token is replaced
    on EVERY use, preventing token reuse attacks.
    """
    # Get current refresh token
    current_refresh = self.storage.get_token("refresh_token")

    # Exchange for new tokens
    response = await self.http_client.post(
        f"{self.api_base}/oauth/token",
        json={
            "grant_type": "refresh_token",
            "refresh_token": current_refresh,
        }
    )

    data = response.json()

    # Store NEW tokens, invalidating old refresh token
    self.storage.store_token("access_token", data["access_token"])
    self.storage.store_token("refresh_token", data["refresh_token"])

    # Old refresh token is now INVALID
    return TokenPair(
        access_token=data["access_token"],
        refresh_token=data["refresh_token"],  # NEW!
    )
```

### Secure Storage with Keyring

```python
from keyring import get_password, set_password, delete_password

class SecureTokenStorage:
    SERVICE_NAME = "claude-bedrock-cursor"

    def store_token(self, token_type: str, token: str) -> None:
        """Store token securely in system keyring."""
        set_password(self.SERVICE_NAME, token_type, token)

    def get_token(self, token_type: str) -> Optional[str]:
        """Retrieve token from system keyring."""
        return get_password(self.SERVICE_NAME, token_type)

    def delete_token(self, token_type: str) -> None:
        """Delete token from system keyring."""
        try:
            delete_password(self.SERVICE_NAME, token_type)
        except Exception:
            pass  # Token might not exist

# Platform-specific storage:
# - macOS: Keychain
# - Linux: Secret Service API / gnome-keyring
# - Windows: Windows Credential Manager
```

### Auto-Refresh Logic

```python
@requires_auth
async def call_api(access_token: str):
    """Decorator automatically refreshes on 401 Unauthorized."""
    try:
        return await make_request(access_token)
    except UnauthorizedError:
        # Auto-refresh and retry once
        new_token = await oauth_manager.refresh_access_token()
        return await make_request(new_token.access_token)
```

## Troubleshooting

### "OAuth token invalid or expired"

**Cause**: OAuth tokens from `claude setup-token` expire quickly (minutes).

**Solution**:
```bash
# Get fresh OAuth token
claude setup-token

# Login immediately
claude-bedrock auth login
```

**Prevention**: Use OAuth token within 5 minutes of generation.

---

### "Refresh token expired"

**Cause**: Haven't used the tool in 7+ days, refresh token expired.

**Solution**:
```bash
# Re-authenticate completely
claude-bedrock auth logout
claude setup-token
claude-bedrock auth login
```

**Prevention**: Use tool at least once per week to keep refresh token active.

---

### "Keyring backend not found"

**Cause**: System keyring not available on Linux/macOS.

**macOS Solution**:
```bash
# Keychain should work by default
# Verify:
security find-generic-password -s "claude-bedrock-cursor"
```

**Linux Solution**:
```bash
# Install gnome-keyring or kwallet
sudo apt install gnome-keyring  # Ubuntu/Debian
sudo dnf install gnome-keyring  # Fedora

# Or use secret-tool
sudo apt install libsecret-tools
```

**Windows Solution**:
Windows Credential Manager works by default, no action needed.

---

### "Auto-refresh not working"

**Diagnosis**:
```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
claude-bedrock auth status

# Check logs for auto-refresh attempts
```

**Solution**:
```bash
# Manually refresh to test
claude-bedrock auth refresh

# If manual works but auto doesn't:
# Check configuration:
cat ~/.config/claude-bedrock-cursor/config.toml

# Ensure auto-refresh enabled (default):
[oauth]
auto_refresh = true
refresh_threshold_minutes = 2
```

## Best Practices

### Development

1. **Use `auth status` regularly**: Monitor token health
2. **Enable debug logging**: `export LOG_LEVEL=DEBUG` for troubleshooting
3. **Test token rotation**: Run `auth refresh` manually to verify
4. **Never commit tokens**: Tokens stored in keyring, not in files

### Production

1. **Monitor token expiry**: Set up alerts for refresh failures
2. **Implement retry logic**: Handle transient auth errors
3. **Log auth events**: Audit successful/failed authentications
4. **Rotate credentials regularly**: Re-login monthly for security

### CI/CD

For automated environments without keyring:

```bash
# Use environment variables as fallback
export CLAUDE_ACCESS_TOKEN="..."
export CLAUDE_REFRESH_TOKEN="..."

# Tool detects env vars when keyring unavailable
claude-bedrock auth status
```

## Security Considerations

### What We Do

✅ **Token Rotation**: New refresh token on every use
✅ **Encrypted Storage**: OS-level keyring encryption
✅ **Short Expiry**: 5-minute access tokens
✅ **No Logging**: Tokens never logged
✅ **Secure Transmission**: HTTPS only

### What We Don't Do

❌ **No Token Caching**: Don't store in memory longer than needed
❌ **No File Storage**: Never write tokens to files
❌ **No Environment Variables**: Only use for CI/CD if needed
❌ **No Token Sharing**: Each user/machine has own tokens

### Threat Model

**Protected Against**:
- Token theft from logs ✅
- Token reuse attacks ✅
- Long-term token exposure ✅
- Credential leakage in files ✅

**Not Protected Against**:
- Compromised system keyring (requires OS-level access)
- Man-in-the-middle attacks (use HTTPS, verify certificates)
- Phishing for OAuth tokens (user education)

## Advanced Configuration

### Custom OAuth Endpoints

```bash
# Edit config for custom Claude Code deployments
nano ~/.config/claude-bedrock-cursor/config.toml

[oauth]
api_base = "https://api.claude.ai/v1"  # Default
oauth_endpoint = "/oauth/token"
token_refresh_threshold_minutes = 2
auto_refresh = true
```

### Multiple Profiles

```bash
# Create profile-specific config
mkdir -p ~/.config/claude-bedrock-cursor/profiles/
cp ~/.config/claude-bedrock-cursor/config.toml \
   ~/.config/claude-bedrock-cursor/profiles/production.toml

# Use specific profile
export CLAUDE_BEDROCK_PROFILE=production
claude-bedrock auth login
```

### Programmatic Authentication

```python
from claude_bedrock_cursor.auth import OAuthManager

async def authenticate():
    manager = OAuthManager()

    # Login with OAuth token
    tokens = await manager.login(oauth_token="...")

    # Access token ready to use
    print(f"Access token: {tokens.access_token}")

    # Auto-refresh will happen automatically
    # when token expires or is within threshold
```

## Next Steps

- **[Cost Optimization](./cost-optimization.md)** - Reduce Bedrock costs
- **[Security Best Practices](./security-best-practices.md)** - Production hardening
- **[Troubleshooting](./troubleshooting.md)** - Common issues

---

**Previous**: [← Cursor Integration](./cursor-integration.md) | **Next**: [Cost Optimization →](./cost-optimization.md)
