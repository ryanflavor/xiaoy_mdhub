# Contributing to Market Data Hub

Thank you for your interest in contributing to the Local High-Availability Market Data Hub! This document provides guidelines and instructions for contributing to this project.

## 📋 Table of Contents

- [Development Setup](#development-setup)
- [Coding Standards](#coding-standards)
- [Development Workflow](#development-workflow)
- [Testing Guidelines](#testing-guidelines)
- [Documentation](#documentation)
- [Pull Request Process](#pull-request-process)
- [Security Guidelines](#security-guidelines)

## 🛠️ Development Setup

### Prerequisites

Ensure you have the following installed:
- **Node.js** 18+ and npm 8+
- **Python** 3.12+
- **Docker** and Docker Compose
- **Git**

### Initial Setup

1. **Fork and clone the repository**
   ```bash
   git clone https://github.com/YOUR_USERNAME/xiaoy_mdhub.git
   cd xiaoy_mdhub
   ```

2. **Install all dependencies**
   ```bash
   npm run install:all
   ```

3. **Set up pre-commit hooks**
   ```bash
   # Install pre-commit (Python)
   pip install pre-commit
   pre-commit install
   ```

4. **Start development environment**
   ```bash
   docker-compose up -d mysql mongodb redis
   npm run dev
   ```

## 📐 Coding Standards

### TypeScript/JavaScript

- **Formatting**: Prettier with 2-space indentation
- **Linting**: ESLint with strict TypeScript rules
- **Naming**: camelCase for variables/functions, PascalCase for components/types
- **Imports**: Absolute imports using `@/` prefix

**Example**:
```typescript
// Good
import { Gateway } from '@xiaoy-mdhub/shared-types';
import { useGatewayStore } from '@/store';

interface GatewayProps {
  gateway: Gateway;
  onUpdate: (gateway: Gateway) => void;
}

export function GatewayCard({ gateway, onUpdate }: GatewayProps) {
  // Component implementation
}
```

### Python

- **Formatting**: Black with 88-character line length
- **Import sorting**: isort
- **Type hints**: Required for all function signatures
- **Docstrings**: Google-style docstrings for all public functions

**Example**:
```python
from typing import List, Optional
from pydantic import BaseModel

class MarketDataAccount(BaseModel):
    """Market data account configuration.
    
    Args:
        id: Unique account identifier
        gateway_type: Type of market data gateway
        settings: Account connection settings
    """
    id: str
    gateway_type: str
    settings: dict
    
async def get_account(account_id: str) -> Optional[MarketDataAccount]:
    """Retrieve a market data account by ID.
    
    Args:
        account_id: The unique identifier for the account
        
    Returns:
        The account if found, None otherwise
        
    Raises:
        DatabaseError: If database connection fails
    """
    # Implementation
```

### File Organization

- **Components**: One component per file, export as default
- **Types**: Shared types in `packages/shared-types/`
- **Utils**: Pure functions in dedicated utility files
- **Constants**: Uppercase with descriptive names

## 🔄 Development Workflow

### Story-Driven Development

All development work must start with a user story:

1. **Check existing stories** in `docs/stories/`
2. **Create new story** if needed using the story template
3. **Get story approval** from Product Owner
4. **Implement story** following acceptance criteria
5. **Update story status** as you progress

### Branch Strategy

- **main**: Production-ready code
- **develop**: Integration branch for features
- **feature/story-X-Y**: Feature branches for specific stories
- **hotfix/**: Critical production fixes

### Commit Messages

Use conventional commits format:

```
type(scope): description

[optional body]

[optional footer]
```

**Types**: feat, fix, docs, style, refactor, test, chore

**Examples**:
```
feat(api): add gateway health monitoring endpoint

- Implement /api/gateways/{id}/health endpoint
- Add health check service for CTP/SOPT gateways
- Include heartbeat validation for canary contracts

Closes #123
```

## 🧪 Testing Guidelines

### Test Structure

- **Unit Tests**: Test individual functions/components
- **Integration Tests**: Test interactions between modules
- **E2E Tests**: Test complete user workflows

### Backend Testing

```python
# apps/api/tests/test_gateway_service.py
import pytest
from app.services.gateway_service import GatewayService

@pytest.fixture
def gateway_service():
    return GatewayService()

async def test_get_gateway_health(gateway_service):
    """Test gateway health check functionality."""
    # Arrange
    gateway_id = "test-gateway-1"
    
    # Act
    health = await gateway_service.check_health(gateway_id)
    
    # Assert
    assert health.gateway_id == gateway_id
    assert health.is_healthy is not None
```

### Frontend Testing

```typescript
// apps/web/src/components/__tests__/GatewayCard.test.tsx
import { render, screen } from '@testing-library/react';
import { GatewayCard } from '../GatewayCard';

const mockGateway = {
  id: 'test-1',
  name: 'Test Gateway',
  status: 'HEALTHY' as const,
  // ... other properties
};

describe('GatewayCard', () => {
  it('displays gateway status correctly', () => {
    render(<GatewayCard gateway={mockGateway} onUpdate={() => {}} />);
    
    expect(screen.getByText('Test Gateway')).toBeInTheDocument();
    expect(screen.getByText('HEALTHY')).toBeInTheDocument();
  });
});
```

### Running Tests

```bash
# All tests
npm run test

# Backend tests only
cd apps/api && python -m pytest

# Frontend tests only
cd apps/web && npm test

# With coverage
npm run test:coverage
```

## 📚 Documentation

### Code Documentation

- **README**: Update for significant changes
- **API Docs**: Auto-generated from FastAPI docstrings
- **Type Definitions**: Document complex types with JSDoc
- **Architecture**: Update docs/architecture/ for structural changes

### Documentation Standards

- **Clear headings** with consistent formatting
- **Code examples** for all public APIs
- **Links** to related documentation
- **Version information** for breaking changes

## 🔍 Pull Request Process

### Before Submitting

1. **Ensure all tests pass**
   ```bash
   npm run test
   npm run lint
   npm run type-check
   ```

2. **Update documentation** if needed

3. **Add/update tests** for new functionality

4. **Follow story acceptance criteria**

### PR Template

```markdown
## Story Reference
- Story: [Story X.Y: Description](link-to-story)
- Epic: Epic X - Name

## Changes Made
- [ ] Feature implementation
- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] Acceptance criteria met

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed

## Screenshots (if applicable)
[Add screenshots for UI changes]

## Notes
[Any additional context or considerations]
```

### Review Process

1. **Automated checks** must pass (CI/CD)
2. **Code review** by at least one team member
3. **Story validation** by Product Owner (if applicable)
4. **Merge approval** by maintainer

## 🔒 Security Guidelines

### Sensitive Information

- **Never commit secrets** (API keys, passwords, tokens)
- **Use environment variables** for configuration
- **Encrypt sensitive data** at rest and in transit

### Trading Data Security

- **Account credentials** must be encrypted
- **API access** requires authentication
- **Audit logging** for all account changes
- **Rate limiting** on API endpoints

### Security Checklist

- [ ] No secrets in code or comments
- [ ] Input validation on all endpoints
- [ ] Proper error handling (no data leaks)
- [ ] Authentication/authorization implemented
- [ ] SQL injection prevention
- [ ] XSS protection in frontend

## 🐛 Bug Reports

When reporting bugs, include:

1. **Environment details** (OS, Python/Node versions, etc.)
2. **Steps to reproduce** the issue
3. **Expected vs actual behavior**
4. **Error messages** and stack traces
5. **Log files** if relevant

## 🚀 Feature Requests

For new features:

1. **Check existing stories** and issues first
2. **Provide business justification** for the feature
3. **Include user story format** (As a... I want... So that...)
4. **Consider architectural impact**

## 📞 Getting Help

- **Documentation**: Check docs/ directory first
- **Issues**: Search existing GitHub issues
- **Discussion**: Use GitHub Discussions for questions
- **Email**: ryanflavor@163.com for urgent matters

---

## 🙏 Recognition

Contributors will be acknowledged in:
- **CONTRIBUTORS.md** file
- **Release notes** for significant contributions
- **Architecture documentation** for design contributions

Thank you for contributing to reliable quantitative trading infrastructure! 🚀