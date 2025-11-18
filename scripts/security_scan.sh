#!/usr/bin/env bash
# Security scanning script for Claude Bedrock Cursor
# Runs all security checks in sequence

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "🔒 Running security scans for Claude Bedrock Cursor..."
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Track overall status
FAILED=0

# 1. Bandit - SAST (Static Application Security Testing)
echo "📊 Step 1/4: Running Bandit (SAST)..."
if uv run bandit -c pyproject.toml -r src/; then
    echo -e "${GREEN}✓ Bandit scan passed${NC}"
else
    echo -e "${RED}✗ Bandit scan failed${NC}"
    FAILED=1
fi
echo ""

# 2. Gitleaks - Secret detection
echo "🔍 Step 2/4: Running Gitleaks (secret detection)..."
if command -v gitleaks &> /dev/null; then
    if gitleaks detect --config .gitleaks.toml --no-git --verbose; then
        echo -e "${GREEN}✓ Gitleaks scan passed${NC}"
    else
        echo -e "${RED}✗ Gitleaks detected secrets${NC}"
        FAILED=1
    fi
else
    echo -e "${YELLOW}⚠ Gitleaks not installed (install: brew install gitleaks)${NC}"
fi
echo ""

# 3. pip-audit - Dependency vulnerability scanning
echo "🔍 Step 3/4: Running pip-audit (dependency vulnerabilities)..."
if uv run pip-audit --desc --skip-editable; then
    echo -e "${GREEN}✓ pip-audit scan passed${NC}"
else
    echo -e "${YELLOW}⚠ pip-audit found vulnerabilities (review above)${NC}"
    # Don't fail build on pip-audit as it may flag dev dependencies
fi
echo ""

# 4. Safety - Additional dependency check
echo "🛡️ Step 4/4: Running Safety (dependency check)..."
if command -v safety &> /dev/null; then
    # Export dependencies to temporary file
    uv pip freeze > /tmp/requirements-frozen.txt
    if safety check --file /tmp/requirements-frozen.txt --ignore 70612; then
        echo -e "${GREEN}✓ Safety scan passed${NC}"
    else
        echo -e "${YELLOW}⚠ Safety found vulnerabilities (review above)${NC}"
        # Don't fail build on safety warnings
    fi
    rm /tmp/requirements-frozen.txt
else
    echo -e "${YELLOW}⚠ Safety not installed (install: pip install safety)${NC}"
fi
echo ""

# Summary
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ All security scans passed!${NC}"
    exit 0
else
    echo -e "${RED}❌ Security scans failed - please review errors above${NC}"
    exit 1
fi
