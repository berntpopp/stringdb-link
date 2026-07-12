# Security Policy

`stringdb-link` is a thin FastMCP backend in the GeneFoundry fleet. It is unauthenticated
by design and MUST be reached only through the `genefoundry-router` / reverse proxy at the
trust boundary — never published directly. Research use only; not clinical decision support.

## Reporting a vulnerability

Report suspected vulnerabilities privately to the maintainer (bernt.popp@charite.de)
rather than opening a public issue. Include reproduction steps and affected revision.

## Required repository security settings (operator follow-up)

GitHub **secret scanning** and **push protection** are repository settings, not workflow
files, so they cannot be enabled from a pull request. An operator with admin rights on the
repository must enable them:

```bash
gh api -X PATCH repos/berntpopp/stringdb-link \
  -f 'security_and_analysis[secret_scanning][status]=enabled' \
  -f 'security_and_analysis[secret_scanning_push_protection][status]=enabled'
```

Verify both are `enabled`:

```bash
gh api repos/berntpopp/stringdb-link --jq '.security_and_analysis'
```

Expected output includes:

```json
{
  "secret_scanning": { "status": "enabled" },
  "secret_scanning_push_protection": { "status": "enabled" }
}
```

Code scanning (CodeQL) is already configured for this repository via
`.github/workflows/security.yml`; this document tracks only the secret-scanning /
push-protection settings, which are the outstanding operator action.
