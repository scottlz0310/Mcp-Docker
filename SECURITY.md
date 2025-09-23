# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.x.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

We take the security of MCP Docker Environment seriously. If you discover a security vulnerability, please follow these steps:

### 1. **DO NOT** create a public GitHub issue

### 2. Report privately via GitHub Security Advisories
- Go to the [Security tab](https://github.com/scottlz0310/Mcp-Docker/security/advisories)
- Click "Report a vulnerability"
- Provide detailed information about the vulnerability

### 3. Email reporting (alternative)
- Email: security@example.com
- Include "MCP-Docker Security" in the subject line
- Provide detailed information about the vulnerability

## What to Include in Your Report

Please include the following information:
- Description of the vulnerability
- Steps to reproduce the issue
- Potential impact
- Suggested fix (if available)
- Your contact information

## Response Timeline

- **Initial Response**: Within 48 hours
- **Status Update**: Within 7 days
- **Fix Timeline**: Depends on severity
  - Critical: Within 24-48 hours
  - High: Within 1 week
  - Medium: Within 2 weeks
  - Low: Within 1 month

## Security Measures

### Container Security
- Non-root user execution
- Minimal base images (Alpine Linux)
- Regular security updates
- Vulnerability scanning with Trivy

### Code Security
- CodeQL static analysis
- Dependency vulnerability scanning
- Secret scanning
- Automated security updates via Dependabot

### CI/CD Security
- Signed commits (recommended)
- Branch protection rules
- Required status checks
- Automated security testing

## Security Best Practices

### For Users
1. Always use the latest version
2. Regularly update dependencies
3. Use environment variables for secrets
4. Never commit sensitive information
5. Enable Docker security features

### For Contributors
1. Follow secure coding practices
2. Run security tests before submitting PRs
3. Use signed commits
4. Report security issues responsibly

## Acknowledgments

We appreciate the security research community and will acknowledge researchers who responsibly disclose vulnerabilities.

## Contact

For security-related questions or concerns:
- GitHub Security Advisories (preferred)
- Email: security@example.com
- Maintainer: @scottlz0310
