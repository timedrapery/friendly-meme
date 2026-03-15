# Security Policy

## Supported versions

Only the latest release on the `main` branch receives security fixes.

## Reporting a vulnerability

Please **do not** open a public GitHub issue for security vulnerabilities.

Instead, report them privately by emailing the maintainers or using
[GitHub's private vulnerability reporting](https://docs.github.com/en/code-security/security-advisories/guidance-on-reporting-and-writing/privately-reporting-a-security-vulnerability)
for this repository.

Include as much detail as you can:

- A description of the vulnerability and its potential impact
- Steps to reproduce or a minimal proof-of-concept
- Affected versions (if known)

We aim to acknowledge reports within **72 hours** and provide a fix or
mitigation plan within **14 days** for confirmed vulnerabilities.

## Scope

The main attack surface of this project is network access: the lexicon loader
fetches JSON from `raw.githubusercontent.com` and the GitHub API.  Concerns
relevant to this project include:

- Malformed or malicious JSON served from the upstream data source
- GITHUB_TOKEN leakage through logs or error messages
- Cache-file path traversal issues

Issues in the [timedrapery/shiny-adventure](https://github.com/timedrapery/shiny-adventure)
lexicon data repository should be reported there.
