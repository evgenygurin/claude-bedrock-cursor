# Architecture Documentation

Technical architecture and design decisions for Claude Bedrock Cursor integration.

## System Overview

```text
┌─────────────────────────────────────────────────────────────┐
│                      Cursor IDE                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ AI Chat UI   │  │ Inline Code  │  │ .cursor/     │      │
│  │              │  │ Completions  │  │ Rules        │      │
│  └──────┬───────┘  └──────┬───────┘  └──────────────┘      │
│         │                  │                                 │
│         └──────────────────┼─────────────────────────────────┘
│                            │
│                            │ User Prompts
│                            ▼
┌─────────────────────────────────────────────────────────────┐
│              Claude Bedrock Cursor CLI Tool                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ CLI          │  │ OAuth        │  │ Bedrock      │      │
│  │ (Typer)      │  │ Manager      │  │ Client       │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
│         │                  │                  │              │
│         └──────────────────┼──────────────────┘              │
│                            │                                 │
└────────────────────────────┼─────────────────────────────────┘
                             │
                             │ Access Token
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                    OAuth Authentication                      │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Claude Code MAX Subscription                          │   │
│  │ - OAuth Token Generation                              │   │
│  │ - Access Token (5 min)                                │   │
│  │ - Refresh Token Rotation (7 days)                     │   │
│  └─────────────────────┬────────────────────────────────┘   │
└────────────────────────┼─────────────────────────────────────┘
                         │
                         │ Authenticated Requests
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                     AWS Bedrock                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Claude Sonnet 4 Model                                 │   │
│  │ - Streaming Responses                                 │   │
│  │ - Prompt Caching (90% cost savings)                   │   │
│  │ - Exponential Backoff Retry                           │   │
│  └─────────────────────┬────────────────────────────────┘   │
└────────────────────────┼─────────────────────────────────────┘
                         │
                         │ Streaming Response
                         ▼
                   [User Sees Result]
```

## Core Components

### 1. CLI Layer (`cli.py`)

**Purpose**: User-facing command-line interface

**Technology**: Typer (FastAPI-style CLI framework)

**Key Features**:
- Type-safe command definitions
- Automatic help generation
- Rich terminal output (colors, progress bars)
- Subcommand organization

**Commands**:
```python
app = typer.Typer()

@app.command()
def init():
    """Initialize configuration."""

@app.command()
def auth():
    """Authentication commands (login, logout, refresh, status)."""

@app.command()
def aws():
    """AWS Bedrock commands (setup, validate)."""

@app.command()
def cursor():
    """Cursor IDE integration (install, config, status)."""
```

**Design Decision**: Typer chosen for:
- Modern Python (3.12+) type hints
- Minimal boilerplate
- Excellent developer experience
- Built-in validation

### 2. Configuration Layer (`config.py`)

**Purpose**: Type-safe configuration management

**Technology**: Pydantic + TOML

**Schema**:
```python
class Config(BaseSettings):
    # AWS Configuration
    aws_region: str = "us-east-1"
    aws_profile: str = "default"

    # Bedrock Configuration
    bedrock_model_id: str = "anthropic.claude-sonnet-4-20250514-v1:0"
    max_output_tokens: int = Field(default=4096, ge=4096)
    max_thinking_tokens: int = 1024
    enable_prompt_caching: bool = True
    enable_streaming: bool = True

    # OAuth Configuration
    auto_refresh: bool = True
    refresh_threshold_minutes: int = 2

    # Cursor Configuration
    integration_mode: str = "both"  # cli, extension, both

    # Validation
    @validator("max_output_tokens")
    def validate_tokens(cls, v):
        if v < 4096:
            raise ValueError("Must be >= 4096 (Bedrock minimum)")
        return v
```

**Design Decision**: Pydantic for:
- Runtime validation
- Environment variable support
- Type safety
- Automatic documentation

### 3. Authentication Layer (`auth/`)

**Components**:
- `oauth.py`: OAuth2 manager with token rotation
- `storage.py`: Secure keyring storage

**OAuth Flow**:
```python
class OAuthManager:
    async def login(self, oauth_token: str) -> TokenPair:
        """Exchange OAuth token for access + refresh tokens."""
        # 1. Exchange OAuth token
        tokens = await self._exchange_oauth_token(oauth_token)

        # 2. Store securely
        self.storage.store_token("access_token", tokens.access_token)
        self.storage.store_token("refresh_token", tokens.refresh_token)

        return tokens

    async def refresh_access_token(self) -> TokenPair:
        """Refresh access token and ROTATE refresh token."""
        current_refresh = self.storage.get_token("refresh_token")

        # Exchange for NEW tokens
        tokens = await self._refresh_token(current_refresh)

        # Store NEW refresh token (rotation!)
        self.storage.store_token("access_token", tokens.access_token)
        self.storage.store_token("refresh_token", tokens.refresh_token)

        # Old refresh token is now INVALID
        return tokens
```

**Design Decision**: Refresh token rotation for security
- OWASP recommendation
- Prevents token reuse attacks
- Limits exposure window

### 4. Bedrock Client Layer (`bedrock/client.py`)

**Purpose**: AWS Bedrock API interaction

**Technology**: boto3 with async wrapper

**Key Features**:
- Streaming responses (better UX)
- Prompt caching (90% cost savings)
- Exponential backoff retry
- Metrics tracking

**Implementation**:
```python
class BedrockClient:
    async def invoke_streaming(
        self,
        prompt: str,
        system_context: Optional[str] = None,
    ) -> AsyncIterator[str]:
        """Stream response from Bedrock with caching."""

        # Build request body
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": self.config.max_output_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }

        # Enable prompt caching for large context
        if system_context and self.config.enable_prompt_caching:
            body["system"] = [{
                "type": "text",
                "text": system_context,
                "cache_control": {"type": "ephemeral"}  # 90% savings!
            }]

        # Invoke with retry logic
        response = await self._invoke_with_retry(
            self.client.invoke_model_with_response_stream,
            modelId=self.config.bedrock_model_id,
            body=json.dumps(body),
        )

        # Stream chunks
        async for event in response["body"]:
            chunk = json.loads(event["chunk"]["bytes"])
            if chunk["type"] == "content_block_delta":
                yield chunk["delta"]["text"]
```

**Design Decisions**:
- **Streaming**: Better UX, allows user to see progress
- **Async**: Non-blocking I/O, faster for concurrent requests
- **Retry Logic**: Handle AWS throttling gracefully
- **Caching**: Massive cost savings for repeated context

### 5. Storage Layer (`auth/storage.py`)

**Purpose**: Secure credential storage

**Technology**: Python keyring (OS-level encryption)

**Platform Support**:
- macOS: Keychain
- Linux: Secret Service API / gnome-keyring
- Windows: Windows Credential Manager

**Interface**:
```python
class SecureTokenStorage:
    SERVICE_NAME = "claude-bedrock-cursor"

    def store_token(self, token_type: str, token: str) -> None:
        """Store token in OS keyring."""
        keyring.set_password(self.SERVICE_NAME, token_type, token)

    def get_token(self, token_type: str) -> Optional[str]:
        """Retrieve token from OS keyring."""
        return keyring.get_password(self.SERVICE_NAME, token_type)

    def delete_token(self, token_type: str) -> None:
        """Delete token from OS keyring."""
        keyring.delete_password(self.SERVICE_NAME, token_type)
```

**Design Decision**: OS keyring over environment variables
- Encrypted at rest
- OS-level security
- No file exposure
- Cross-platform support

## Data Flow

### Successful Request Flow

```text
1. User: "Explain this code"
   ↓
2. Cursor IDE: Send prompt to CLI
   ↓
3. CLI: Check auth status
   ↓
4. OAuth Manager:
   - Get access token from keyring
   - Check expiry (< 2 min?)
   - Auto-refresh if needed
   ↓
5. Bedrock Client:
   - Build request body
   - Add cache_control for context
   - Invoke streaming API
   ↓
6. AWS Bedrock:
   - Check prompt cache (90% discount if hit)
   - Generate response
   - Stream chunks
   ↓
7. Bedrock Client:
   - Yield chunks as they arrive
   ↓
8. CLI: Display streamed response
   ↓
9. Cursor IDE: Show result to user
```

### Token Refresh Flow

```text
1. Access token expires in 1 minute
   ↓
2. Next API call triggers auto-refresh:
   ↓
3. OAuth Manager:
   - Get current refresh token from keyring
   - Call OAuth API with refresh_grant
   ↓
4. OAuth API:
   - Validate refresh token
   - Generate NEW access token (5 min)
   - Generate NEW refresh token (7 days)
   - Invalidate OLD refresh token
   ↓
5. OAuth Manager:
   - Store NEW access token
   - Store NEW refresh token
   - Delete OLD refresh token from memory
   ↓
6. Proceed with API call using new access token
```

## Design Patterns

### 1. Async/Await Throughout

**Rationale**: All I/O operations are async for performance

```python
# OAuth API calls
async def login(oauth_token: str) -> TokenPair

# AWS Bedrock calls
async def invoke_streaming(prompt: str) -> AsyncIterator[str]

# HTTP client
async with httpx.AsyncClient() as client:
    response = await client.post(url, json=data)
```

**Benefits**:
- Non-blocking I/O
- Concurrent request handling
- Better resource utilization

### 2. Exponential Backoff Retry

**Rationale**: AWS Bedrock has rate limits

```python
async def _invoke_with_retry(self, operation, **kwargs):
    for attempt in range(max_retries):
        try:
            return await operation(**kwargs)
        except ClientError as e:
            if e.response["Error"]["Code"] == "ThrottlingException":
                if attempt < max_retries - 1:
                    # Exponential backoff: 1s, 2s, 4s, 8s
                    await asyncio.sleep(2 ** attempt)
                    continue
            raise
```

**Benefits**:
- Graceful handling of throttling
- Automatic recovery
- User doesn't see failures

### 3. Type Safety with Pydantic

**Rationale**: Catch errors early, better IDE support

```python
class TokenPair(BaseModel):
    access_token: str = Field(..., min_length=20)
    refresh_token: str = Field(..., min_length=20)
    expires_in: int = Field(default=300, ge=0)

# Usage:
tokens = TokenPair(**response.json())  # Validates automatically
```

**Benefits**:
- Runtime validation
- Better IDE autocomplete
- Self-documenting code

### 4. Decorator Pattern for Auth

**Rationale**: Simplify authentication logic

```python
def requires_auth(func):
    """Decorator: Auto-refresh tokens if expired."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Check token expiry
        if oauth_manager.needs_refresh():
            await oauth_manager.refresh_access_token()

        # Proceed with function
        return await func(*args, **kwargs)

    return wrapper

@requires_auth
async def call_bedrock_api():
    # Function always has valid token
    pass
```

## Technology Choices

### Python 3.12+

**Why**:
- Modern type hints (PEP 585, 604)
- Performance improvements
- Better async support

### Typer

**Why**:
- Type-safe CLI framework
- Minimal boilerplate
- Excellent DX

**Alternatives Considered**:
- Click: More verbose, less type-safe
- argparse: Stdlib but tedious

### Pydantic

**Why**:
- Runtime validation
- Environment variable support
- Type safety

**Alternatives Considered**:
- dataclasses: No validation
- attrs: Less feature-rich

### boto3

**Why**:
- Official AWS SDK
- Comprehensive Bedrock support
- Well-documented

**Alternatives Considered**:
- aioboto3: Added complexity, minimal benefit

### keyring

**Why**:
- Cross-platform
- OS-level encryption
- Standard Python library

**Alternatives Considered**:
- python-jose: JWE encryption (more complex)
- Environment variables: Less secure

## Scalability Considerations

### Concurrent Requests

Current architecture supports concurrent requests:

```python
# Multiple requests in parallel
tasks = [
    bedrock_client.invoke_streaming(prompt1),
    bedrock_client.invoke_streaming(prompt2),
    bedrock_client.invoke_streaming(prompt3),
]
results = await asyncio.gather(*tasks)
```

**Limitations**:
- AWS Bedrock rate limits (per account)
- OAuth token refresh (single refresh token)

### Caching Strategy

**Prompt Cache**: 5-minute TTL
- First request: Cache miss (full cost)
- Subsequent requests: Cache hit (90% discount)
- After 5 min: Cache expires

**Token Cache**: In-memory
- Access token: Cached until < 2 min expiry
- Refresh token: Retrieved from keyring as needed

## Security Architecture

### Defense in Depth

1. **Transport**: HTTPS/TLS 1.2+
2. **Storage**: OS-level keyring encryption
3. **Tokens**: Short expiry (5 min access, rotation on refresh)
4. **IAM**: Least privilege policies
5. **Logging**: No sensitive data in logs
6. **Validation**: Pydantic input validation

### Threat Model

**Protected Against**:
- ✅ Token theft from logs
- ✅ Token reuse attacks
- ✅ Long-term credential exposure
- ✅ Prompt injection (input validation)

**Requires External Controls**:
- Compromised keyring (OS security)
- MITM attacks (certificate validation)
- Phishing (user education)

## Future Enhancements

### Phase 2: VS Code Extension

- Direct Bedrock integration (no CLI)
- Real-time inline completions
- Cost tracking in status bar

### Phase 3: Advanced Features

- Multi-model support (Opus, Haiku)
- Custom inference profiles
- Local caching layer
- Response streaming with SSE

### Phase 4: Enterprise Features

- Team authentication (SSO)
- Shared prompt libraries
- Usage analytics dashboard
- Policy enforcement

---

**Previous**: [← Troubleshooting](./troubleshooting.md)
