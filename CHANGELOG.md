# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned

- Cursor IDE integration (VS Code extension configuration)
- Cloudwatch metrics integration
- Performance benchmarking suite
- Interactive setup wizard
- Shell completion scripts

## [1.0.0] - TBD

### Added

- **Core Features**
  - Claude Code integration with AWS Bedrock
  - OAuth2 authentication with refresh token rotation
  - Secure credential storage using system keyring
  - Streaming responses from Bedrock with chunked output
  - Prompt caching for 90% cost reduction
  - Exponential backoff retry logic for throttling
  - Comprehensive CLI with Typer framework

- **Authentication**
  - OAuth login via `claude setup-token`
  - Automatic token refresh on expiry
  - 5-minute access tokens, 7-day refresh tokens
  - Token rotation on every refresh (security best practice)
  - Logout with complete credential cleanup

- **AWS Bedrock Integration**
  - Support for Claude Sonnet 4 models
  - Streaming API (`InvokeModelWithResponseStream`)
  - Prompt caching with ephemeral cache control
  - Configurable MAX_OUTPUT_TOKENS (minimum 4096)
  - Regional deployment support
  - IAM least-privilege policy generator

- **CLI Commands**
  - `claude-bedrock init` - Initialize configuration
  - `claude-bedrock auth login/logout/refresh/status` - Authentication
  - `claude-bedrock aws setup/validate` - AWS configuration
  - `claude-bedrock models list/test` - Model management
  - `claude-bedrock cursor install/config/status` - Cursor integration
  - `claude-bedrock status` - Overall status check

- **Configuration**
  - Pydantic-based configuration with validation
  - TOML configuration file support
  - Environment variable overrides
  - Type-safe settings management

- **Testing**
  - 134 comprehensive tests (unit, integration, e2e)
  - 80%+ code coverage requirement
  - pytest with asyncio support
  - AWS mocking with moto
  - HTTP mocking with responses
  - Complete workflow testing

- **Quality & Security**
  - Ruff linting and formatting
  - Mypy strict type checking
  - Bandit SAST scanning
  - Gitleaks secret detection
  - pip-audit dependency scanning
  - Pre-commit hooks
  - Conventional commits

- **CI/CD**
  - GitHub Actions workflows
  - Automated testing on Python 3.12+
  - Multi-OS testing (Ubuntu, macOS, Windows)
  - Security scanning pipeline
  - Automated PyPI publishing
  - GitHub Releases integration

- **Documentation**
  - Comprehensive README
  - CLAUDE.md AI memory document
  - Cursor integration rules (.cursor/)
  - API documentation
  - Setup guides
  - Troubleshooting guide

### Security

- Refresh token rotation prevents token reuse
- System keyring for encrypted storage
- Never logs sensitive tokens or credentials
- AWS IAM least-privilege policies
- Regular dependency vulnerability scanning
- Secret detection in commits

### Performance

- Prompt caching reduces costs by 90%
- Streaming for better UX
- Async/await throughout
- Reused boto3 clients
- Efficient token management

## [0.1.0] - Initial Development

### Added

- Project structure and tooling setup
- Basic authentication flow
- Initial Bedrock client implementation
- Core configuration management

---

**Legend:**

- `Added` for new features
- `Changed` for changes in existing functionality
- `Deprecated` for soon-to-be removed features
- `Removed` for now removed features
- `Fixed` for any bug fixes
- `Security` for vulnerability fixes
