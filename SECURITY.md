# Security Policy

## Supported Versions

We release patches for security vulnerabilities. Currently supported versions:

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Reporting a Vulnerability

**Please do not report security vulnerabilities through public GitHub issues.**

Instead, please report them via email to: **security@dweepbot.dev**

You should receive a response within 48 hours. If for some reason you do not, please follow up via email to ensure we received your original message.

Please include the following information:

- Type of issue (e.g., buffer overflow, SQL injection, cross-site scripting, etc.)
- Full paths of source file(s) related to the manifestation of the issue
- The location of the affected source code (tag/branch/commit or direct URL)
- Any special configuration required to reproduce the issue
- Step-by-step instructions to reproduce the issue
- Proof-of-concept or exploit code (if possible)
- Impact of the issue, including how an attacker might exploit it

This information will help us triage your report more quickly.

## Security Best Practices

When using DweepBot Pro:

### 1. API Keys
- **Never commit API keys** to version control
- Store API keys in `.env` file (which is gitignored)
- Use environment variables for sensitive data
- Rotate API keys regularly

### 2. Code Execution
- **Be cautious with code execution features** - they pose security risks
- Set `SANDBOX_MODE=true` in production
- Limit `ALLOWED_PACKAGES` to necessary packages only
- Set appropriate `CODE_EXEC_TIMEOUT` values
- Consider disabling code execution in production with `ENABLE_CODE_EXEC=false`

### 3. File Operations
- Limit file operations to specific directories
- Use `ALLOWED_FILE_OPS` to restrict operations
- Never allow write access to system directories
- Validate file paths before operations

### 4. Network Security
- Enable rate limiting with `ENABLE_RATE_LIMITING=true`
- Set appropriate `RATE_LIMIT` values
- Use HTTPS for all API calls
- Validate and sanitize all user inputs

### 5. Dependencies
- Keep dependencies up to date
- Run `pip list --outdated` regularly
- Use `pip-audit` to check for known vulnerabilities
- Pin dependency versions in production

### 6. Docker Security
- Run containers as non-root user (already configured)
- Use minimal base images
- Scan images for vulnerabilities
- Keep Docker images updated

### 7. Data Protection
- Enable encryption at rest for sensitive data
- Use secure communication channels
- Implement proper access controls
- Follow data retention policies

## Security Features

DweepBot Pro includes several security features:

- **Sandboxed code execution** (when enabled)
- **Rate limiting** to prevent abuse
- **Input validation** for all user inputs
- **Secure credential management** via environment variables
- **Limited file system access**
- **Package restrictions** for code execution

## Known Security Considerations

### Code Execution Risk
The code execution feature (`ENABLE_CODE_EXEC=true`) can be dangerous if not properly secured:
- Only enable in trusted environments
- Always use sandbox mode in production
- Regularly audit executed code logs
- Consider using a separate, isolated environment for code execution

### LLM Prompt Injection
As with all LLM-based systems, DweepBot Pro may be susceptible to prompt injection attacks:
- Validate and sanitize user inputs
- Implement input filtering for known patterns
- Monitor for unusual behavior
- Set appropriate context limits

## Disclosure Policy

When we receive a security bug report, we will:

1. Confirm the problem and determine affected versions
2. Audit code to find any similar problems
3. Prepare fixes for all supported versions
4. Release new security patch versions

## Comments on this Policy

If you have suggestions on how this process could be improved, please submit a pull request.

## Credits

We would like to publicly thank the following individuals for responsibly disclosing security vulnerabilities:

- (No vulnerabilities reported yet)

---

Last updated: January 26, 2025
