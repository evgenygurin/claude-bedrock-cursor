# Claude Code + AWS Bedrock + Cursor IDE Integration

⚡ **Production-ready integration** of Claude Code with Cursor IDE through AWS Bedrock, featuring OAuth authentication, cost optimization, and comprehensive testing.

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Type checked: mypy](https://img.shields.io/badge/type%20checked-mypy-blue.svg)](http://mypy-lang.org/)

## ✨ Features

- ✅ **OAuth2 Authentication** - Secure authentication using Claude Code MAX subscription (no API keys needed)
- ✅ **AWS Bedrock Integration** - Streaming responses with automatic retry logic
- ✅ **Prompt Caching** - 90% cost reduction for repeated contexts
- ✅ **Dual Cursor Integration** - CLI in terminal + VS Code extension support
- ✅ **Security Hardened** - System keyring for credentials, IAM least privilege
- ✅ **Comprehensive Testing** - 80%+ coverage with unit, integration, and e2e tests
- ✅ **Production-Ready CI/CD** - GitHub Actions for testing, security scanning, and deployment
- ✅ **Cost Monitoring** - CloudWatch integration for usage tracking
- ✅ **Developer-Friendly** - Modern Python tooling (uv, ruff, Typer)

## 🚀 Quick Start (5 Minutes)

### Prerequisites

- Python 3.12+ installed
- Claude Code MAX subscription
- AWS account with Bedrock access
- Cursor IDE installed

### Installation

```bash
# Clone repository
git clone https://github.com/evgenygurin/claude-bedrock-cursor.git
cd claude-bedrock-cursor

# Install with uv (recommended)
pip install uv
uv sync

# Or install with pip
pip install -e .

# Or install from PyPI (when published)
pip install claude-bedrock-cursor
```

### Configuration

```bash
# 1. Initialize configuration
claude-bedrock init

# 2. Login with Claude MAX subscription
claude-bedrock auth login

# 3. Setup AWS Bedrock
claude-bedrock aws setup

# 4. Install in Cursor IDE
claude-bedrock cursor install

# 5. Verify everything works
claude-bedrock status
```

**That's it!** 🎉 You can now use Claude Code in Cursor with AWS Bedrock.

## 📋 Available Commands

### Authentication

```bash
claude-bedrock auth login        # OAuth login with Claude MAX
claude-bedrock auth logout       # Logout and clear tokens
claude-bedrock auth refresh      # Manually refresh access token
claude-bedrock auth status       # Show authentication status
```

### AWS Bedrock

```bash
claude-bedrock aws setup         # Interactive AWS setup
claude-bedrock aws validate      # Validate Bedrock access
claude-bedrock models list       # List available Claude models
claude-bedrock models test       # Test model invocation
```

### Cursor IDE

```bash
claude-bedrock cursor install    # Install in Cursor (CLI + Extension)
claude-bedrock cursor config     # Configure Cursor settings
claude-bedrock cursor status     # Show integration status
```

### Management

```bash
claude-bedrock init              # Initialize project
claude-bedrock configure         # Interactive configuration
claude-bedrock status            # Show overall status
claude-bedrock health            # Run health check
claude-bedrock cost estimate     # Estimate monthly costs
```

## 🏗️ Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│                      Cursor IDE                              │
│  ┌────────────────┐              ┌──────────────────────┐   │
│  │  CLI Terminal  │              │  VS Code Extension   │   │
│  │  claude-bedrock│              │  Claude Code Ext     │   │
│  └────────┬───────┘              └──────────┬───────────┘   │
└───────────┼─────────────────────────────────┼───────────────┘
            │                                  │
            │         ┌────────────────────────┴──────┐
            │         │  claude-bedrock-cursor CLI    │
            │         │  ┌──────────────────────────┐ │
            └─────────┼──│  OAuth Manager           │ │
                      │  │  (Token Rotation)        │ │
                      │  └──────────────────────────┘ │
                      │  ┌──────────────────────────┐ │
                      │  │  Bedrock Client          │ │
                      │  │  (Streaming + Caching)   │ │
                      │  └──────────────────────────┘ │
                      │  ┌──────────────────────────┐ │
                      │  │  Secure Storage          │ │
                      │  │  (System Keyring)        │ │
                      │  └──────────────────────────┘ │
                      └───────────┬──────────────────┘
                                  │
                      ┌───────────▼──────────────────┐
                      │   AWS Bedrock                │
                      │   Claude Models              │
                      │   (Sonnet, Haiku, Opus)      │
                      └──────────────────────────────┘
```

## 💰 Cost Optimization

### Prompt Caching (90% Savings!)

```python
# Automatically enabled for system prompts
# Cache large, unchanging context:
# - Project documentation
# - Code guidelines
# - Architectural context

# Example: 10,000 token system prompt
# First request: $0.03 (full price)
# Cached requests: $0.003 (90% off!)
```

### Model Selection

| Model | Cost | Use Case |
|-------|------|----------|
| Claude 3.5 Haiku | $1/MTok | Simple tasks, code formatting |
| Claude Sonnet 4 | $3/MTok | **Default** - Balanced performance |
| Claude Opus 4 | $15/MTok | Complex reasoning, critical tasks |

### Monitoring

```bash
# Check current month costs
claude-bedrock cost estimate

# View CloudWatch metrics
# - Token usage
# - Cache hit rate
# - Request counts
```

## 🔐 Security

### OAuth Token Storage

- ✅ **System Keyring** - Encrypted storage (Keychain on macOS, Credential Manager on Windows)
- ✅ **Token Rotation** - Refresh tokens rotated on every use
- ✅ **Short-lived Tokens** - Access tokens expire in 5 minutes
- ✅ **No Plain Text** - Tokens never stored in files or environment variables

### AWS IAM

- ✅ **Least Privilege** - Minimal required permissions
- ✅ **Region Restrictions** - Limit to specific AWS regions
- ✅ **Model Restrictions** - Restrict to specific Claude models
- ✅ **Condition Keys** - Fine-grained access control

### Code Security

- ✅ **Secret Scanning** - Gitleaks in CI/CD
- ✅ **Dependency Scanning** - pip-audit for vulnerabilities
- ✅ **SAST** - Bandit static analysis
- ✅ **Type Safety** - Strict mypy checking

## 🧪 Development

### Setup Development Environment

```bash
# Clone and install
git clone https://github.com/your-org/claude-bedrock-cursor.git
cd claude-bedrock-cursor

# Install with dev dependencies
make dev

# Install pre-commit hooks
make pre-commit
```

### Run Tests

```bash
# All tests
make test

# Unit tests only
make test-unit

# Integration tests
make test-integration

# E2E tests
make test-e2e

# With coverage report
make test  # Opens htmlcov/index.html
```

### Code Quality

```bash
# Format code
make format

# Lint code
make lint

# Type check
mypy src/

# All quality checks
make quality

# Security scan
make security
```

### Available Make Commands

```bash
make help          # Show all commands
make dev           # Setup dev environment
make test          # Run tests
make lint          # Lint code
make format        # Format code
make quality       # All quality checks
make security      # Security scanning
make build         # Build package
make clean         # Clean artifacts
```

## 📚 Documentation

- [Setup Guide](docs/setup-guide.md) - Detailed installation instructions
- [AWS Bedrock Setup](docs/aws-bedrock-setup.md) - AWS configuration
- [Cursor Integration](docs/cursor-integration.md) - Cursor IDE integration
- [OAuth Authentication](docs/oauth-authentication.md) - Authentication details
- [Cost Optimization](docs/cost-optimization.md) - Save money on API costs
- [Security Best Practices](docs/security-best-practices.md) - Security hardening
- [Troubleshooting](docs/troubleshooting.md) - Common issues and solutions
- [Architecture](docs/architecture.md) - Technical architecture
- [API Reference](docs/api-reference.md) - API documentation

## 🤝 Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details.

### Development Workflow

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests and quality checks (`make all`)
5. Commit your changes (`git commit -m 'feat: add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [AWS Bedrock](https://aws.amazon.com/bedrock/) - Claude model hosting
- [Anthropic](https://www.anthropic.com/) - Claude AI models
- [Cursor](https://cursor.com/) - AI-powered code editor
- [Typer](https://typer.tiangolo.com/) - Modern CLI framework
- [steve-code](https://github.com/StoliRocks/steve-code) - Architecture inspiration
- [AWS Solutions Library](https://github.com/aws-solutions-library-samples/guidance-for-claude-code-with-amazon-bedrock) - Enterprise patterns

## 🐛 Issues

Found a bug? Have a feature request? Please open an issue on [GitHub Issues](https://github.com/your-org/claude-bedrock-cursor/issues).

## 📧 Contact

- **Project Lead**: [Your Name](mailto:your@email.com)
- **Documentation**: [https://github.com/your-org/claude-bedrock-cursor/docs](https://github.com/your-org/claude-bedrock-cursor/docs)
- **Discussions**: [GitHub Discussions](https://github.com/your-org/claude-bedrock-cursor/discussions)

---

**Built with ❤️ by the Claude Code community**

**Powered by**: AWS Bedrock · Anthropic Claude · Cursor IDE · Python 3.12+
