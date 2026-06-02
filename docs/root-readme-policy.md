# Root README Audience And Redaction Rules

## Decision

The repository-root `README.md` is `mixed/public-safe`.

It should help maintainers and outside readers, but every line must be written as if it will be publicly visible. This is the default for this repository because the GitHub repository is currently public, the root README is published through package metadata in `pyproject.toml`, and the repository does not contain a separate internal-only documentation path for maintainer operations.

## Repository Signals Behind This Decision

- GitHub reports the repository visibility as `PUBLIC`.
- `README.md` already uses public-safe product language and `localhost` examples rather than internal environment details.
- `.env.example` only exposes local development placeholders and generic environment variable names.
- The repository has a `LICENSE` file, but no `CONTRIBUTING.md`, no `.github/` issue or support templates, and no documented internal-only contributor workflow.
- Recent pull request activity is maintainer-driven, so the root README should stay safe for both maintainers and external readers without promising an internal support model.

## Allow In The Root README

- Public service summaries and feature descriptions.
- Local development commands such as `uv sync`, `docker compose up`, `uv run alembic upgrade head`, and `uv run serve`.
- `localhost` or loopback URLs used for local setup, API docs, or health checks.
- Public API paths and example requests that only target local development endpoints.
- Generic environment variable names already present in `.env.example`, without real secret values.
- High-level architecture statements such as FastAPI, PostgreSQL, Alembic, and versioned API routing.
- Public repository metadata such as the license, package name, and public GitHub location.
- Neutral contribution wording such as `open a pull request` or `contact the maintainers`.

## Do Not Put In The Root README

- Private URLs, internal domains, hostnames, VPN addresses, or non-public dashboards.
- Credentials, tokens, API keys, cookies, connection strings for shared environments, or secret values copied from `.env`.
- Cloud account IDs, project IDs, bucket names, queue names, cluster names, database names, or other identifiable infrastructure labels outside local development defaults.
- Internal support channels, private email aliases, Slack channels, pager rotations, or escalation paths.
- Asana, Jira, incident, or other internal work-tracking links.
- Deployment, rollback, access approval, on-call, or incident response procedures.
- Production or staging topology, private service dependencies, network layout, or SSO/VPN instructions.
- Admin-only or staff-only endpoints, back-office tools, seed data with real people, or customer-specific examples.

## Approved Replacement Wording

Use these high-level substitutions when the README needs to acknowledge internal context without exposing it:

- `contact the maintainers` instead of naming a private Slack channel or internal email list
- `deployment is handled separately from this repository` instead of describing deploy or rollback steps
- `non-development environments` instead of naming staging, production, or internal hostnames
- `configured via environment variables or deployment-time secret management` instead of naming secret stores or real values
- `internal operational procedures are documented separately` instead of linking to runbooks, incident docs, or support systems

## Reviewer Checklist

- The root README audience is stated or implied as `mixed/public-safe`, not internal-only.
- Every literal URL in `README.md` is either public or points to `localhost`.
- The README only uses generic configuration names and local example values.
- No deny-list items appear in new prose, commands, screenshots, or copied examples.
- Any required reference to private operations uses the approved high-level wording above.
