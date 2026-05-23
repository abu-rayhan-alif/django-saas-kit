# Security Policy

## Supported versions

| Version | Supported |
|---------|-----------|
| `0.1.x` | Yes |
| `< 0.1` | No |

## Reporting a vulnerability

**Please do not open a public GitHub issue for security vulnerabilities.**

Report them through [GitHub Security Advisories](https://github.com/abu-rayhan-alif/django-saas-kit/security/advisories/new)
(Private vulnerability report). We will acknowledge receipt and work on a fix
according to severity.

If GitHub Advisories are unavailable, email the maintainers listed in the repository
profile with:

- A description of the issue and impact
- Steps to reproduce
- Affected version(s)
- Any suggested fix or mitigation

## Secure development

- Keep `SECRET_KEY` and database credentials out of version control (use `.env`)
- Run production with `DEBUG=False` and `SECURE_SSL_REDIRECT=True` behind HTTPS
- Review [CUSTOMIZATION.md](CUSTOMIZATION.md) before deploying forked code
- Follow the [Contributing guide](CONTRIBUTING.md) for dependency and CI updates
