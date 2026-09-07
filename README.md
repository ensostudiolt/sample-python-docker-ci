# orderdesk

Order intake API with a background worker that fulfils orders. FastAPI, SQLAlchemy, Postgres.

- `POST /orders` creates an order in `pending`
- `GET /orders/{id}`, `GET /orders?status=pending`
- `GET /health` checks the database and returns the version
- The worker (`python -m orderdesk.worker`) picks up pending orders and marks them `processed` or `failed`

## Running locally

Docker is the only requirement.

```
docker compose up
```

API on http://localhost:8000, docs at `/docs`. Source is mounted, the API reloads on save. Postgres data persists in the `pgdata` volume; `docker compose down -v` wipes it.

Without Docker: `uv sync`, point `DATABASE_URL` at a Postgres, `uv run uvicorn orderdesk.api:app --reload`.

## Tests

Tests run against a real Postgres. With the compose stack up:

```
DATABASE_URL=postgresql+psycopg://orderdesk:orderdesk@localhost:5432/orderdesk uv run pytest
```

Lint and format: `uv run ruff check .` and `uv run ruff format .`.

## CI

`.github/workflows/ci.yml` runs on every pull request and on `main`:

1. `ruff check`, `ruff format --check`, `pytest` against a Postgres service container.
2. Docker image build. On `main` the image is pushed to `ghcr.io/ensostudiolt/sample-python-docker-ci`, tagged `sha-<commit>` and `latest`.

Dependencies are locked in `uv.lock` and installed with `--locked`, so CI and the image use exactly what you ran locally.

## Deploying

One Linux VPS running Docker. Everything lives in `/srv/orderdesk`: `compose.prod.yaml`, `Caddyfile`, `deploy.sh`, `rollback.sh`, and a `.env`.

**Automatic:** `.github/workflows/deploy.yml` runs after CI succeeds on `main`. It SSHes to the server and runs `deploy.sh sha-<commit>`, which pulls the image, restarts the API and worker, waits for `/health`, and rolls back on its own if the health check fails within a minute.

**By hand, or to a specific version:** in GitHub, Actions → Deploy → Run workflow, with any image tag. On the server the same thing is `./deploy.sh sha-<commit>`.

### Rollback

```
ssh deploy@your-server
cd /srv/orderdesk && ./rollback.sh            # previous tag
cd /srv/orderdesk && ./rollback.sh sha-abc123 # any tag in the registry
```

Or run the Deploy workflow with the tag you want. Database schema changes are not rolled back by either; keep migrations backward compatible for one release.

### First time on a server

```
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker deploy
sudo mkdir -p /srv/orderdesk && sudo chown deploy:deploy /srv/orderdesk
# from your machine:
scp deploy/compose.prod.yaml deploy/Caddyfile deploy/deploy.sh deploy/rollback.sh deploy@your-server:/srv/orderdesk/
```

Then on the server create `/srv/orderdesk/.env` from `deploy/.env.example` with a real `POSTGRES_PASSWORD` and, once DNS points at the server, `SITE_ADDRESS=orders.example.com` for automatic HTTPS. While the repository is private, `docker login ghcr.io` with a token that has `read:packages`.

GitHub needs four repository secrets for the Deploy workflow: `DEPLOY_HOST`, `DEPLOY_USER`, `DEPLOY_SSH_KEY` (a key that only this workflow uses; revoke it and the workflow stops), `DEPLOY_KNOWN_HOSTS` (output of `ssh-keyscan your-server`). Put them in a `production` environment so a required reviewer can be added later.

## Secrets

- Local: `.env` (ignored) or the values in `compose.yaml`.
- CI: `GITHUB_TOKEN` pushes the image; nothing else.
- Server: `/srv/orderdesk/.env`, readable by the `deploy` user only.

No secret is baked into the image. `docker history` on the published image shows only build steps.

## What changed from the hand-deploy setup

The systemd units and the "ssh in and git pull" ritual are gone. The unit of deployment is an image built once in CI from a locked dependency set, the same image runs the API and the worker, deploys are one command with a health gate, and rollback is the same command with an older tag.
