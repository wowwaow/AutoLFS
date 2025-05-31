# Contributing to AutoLFS

First off, thank you for considering contributing to AutoLFS! It's people like you that make AutoLFS such a great tool.

## Table of Contents

1. [Code of Conduct](#code-of-conduct)
2. [Development Process](#development-process)
3. [Getting Started](#getting-started)
4. [Code Style Guidelines](#code-style-guidelines)
5. [Commit Guidelines](#commit-guidelines)
6. [Pull Request Process](#pull-request-process)
7. [Testing Guidelines](#testing-guidelines)
8. [Documentation](#documentation)

## Code of Conduct

This project and everyone participating in it is governed by our [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code.

## Development Process

### 1. Fork and Clone

1. Fork the repository on GitHub
2. Clone your fork locally:
   ```bash
   git clone https://github.com/your-username/AutoLFS.git
   cd AutoLFS
   ```
3. Add the upstream repository:
   ```bash
   git remote add upstream https://github.com/wowwaow/AutoLFS.git
   ```

### 2. Branch

1. Create a branch for your work:
   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b fix/your-bug-fix
   ```

2. Keep your branch updated:
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

## Getting Started

1. Install development dependencies:
   ```bash
   sudo apt update
   sudo apt install build-essential python3 python3-pip
   pip install -r requirements-dev.txt
   ```

2. Set up pre-commit hooks:
   ```bash
   pre-commit install
   ```

## Code Style Guidelines

### Python Code Style

- Follow PEP 8 guidelines
- Use type hints
- Maximum line length: 88 characters
- Use descriptive variable names
- Document classes and functions

### Shell Script Style

- Follow Google's Shell Style Guide
- Use shellcheck for linting
- Include error handling
- Document complex commands

### YAML/Configuration Files

- Use 2-space indentation
- Include comments for non-obvious settings
- Keep files organized by category

## Commit Guidelines

### Commit Message Format

```
type(scope): short description

[optional body]

[optional footer]
```

### Types
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

### Scope
- `core`: Core system changes
- `build`: Build system changes
- `docs`: Documentation changes
- `test`: Test-related changes
- `deps`: Dependency updates

### Examples

```
feat(core): add automatic dependency resolution

Implement smart dependency resolution for package builds.
This change allows the system to automatically determine
and install required dependencies before building packages.

Closes #123
```

## Pull Request Process

1. **Update Documentation**
   - Update README.md if needed
   - Add/update API documentation
   - Update relevant guides

2. **Run Tests**
   ```bash
   # Run unit tests
   python -m pytest tests/unit

   # Run integration tests
   python -m pytest tests/integration

   # Run system tests
   ./run_system_tests.sh
   ```

3. **Submit PR**
   - Fill out the PR template completely
   - Link related issues
   - Add labels
   - Request reviews

4. **Review Process**
   - Address review comments
   - Keep the PR updated with main
   - Squash commits when ready

## Testing Guidelines

### Required Tests

1. **Unit Tests**
   - Test individual components
   - Mock external dependencies
   - Cover edge cases

2. **Integration Tests**
   - Test component interactions
   - Verify system integration
   - Test real dependencies

3. **System Tests**
   - End-to-end testing
   - Performance testing
   - Error recovery testing

### Test Coverage

- Maintain minimum 80% code coverage
- Cover all new features
- Include regression tests

## Documentation

### Required Documentation

1. **Code Documentation**
   - Docstrings for functions/classes
   - Inline comments for complex logic
   - Type hints

2. **API Documentation**
   - Update API reference
   - Include examples
   - Document breaking changes

3. **User Documentation**
   - Update user guides
   - Add feature documentation
   - Include troubleshooting

### Documentation Style

- Use clear, concise language
- Include code examples
- Add screenshots when helpful
- Keep formatting consistent

## Release Process

1. **Version Bump**
   - Update version numbers
   - Update changelog
   - Update dependencies

2. **Testing**
   - Run full test suite
   - Perform manual testing
   - Check documentation

3. **Release**
   - Create release branch
   - Tag release
   - Update release notes

## Getting Help

- Join our discussions
- Check existing issues
- Read the documentation
- Ask in our chat channels

## Recognition

Contributors will be:
- Added to CONTRIBUTORS.md
- Mentioned in release notes
- Recognized in documentation

---

Remember: The best contribution is one that follows these guidelines and improves the project for everyone. Thank you for contributing!

