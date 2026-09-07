# orderdesk

Order intake API with a background worker that fulfils orders. FastAPI, SQLAlchemy, Postgres.

- `POST /orders` creates an order in `pending`
- `GET /orders/{id}`, `GET /orders?status=pending`
- `GET /health`
- The worker (`python -m orderdesk.worker`) picks up pending orders and marks them `processed` or `failed`

## Running locally

You need Python 3.12 and a Postgres you can reach. Homebrew Postgres works:

```
brew services start postgresql@16
createuser orderdesk --pwprompt        # password: orderdesk
createdb orderdesk -O orderdesk
```

Then:

```
python -m venv .venv && source .venv/bin/activate
pip install -e . && pip install pytest httpx
cp .env.example .env                   # edit DATABASE_URL if yours differs
uvicorn orderdesk.api:app --reload     # API on http://127.0.0.1:8000
python -m orderdesk.worker             # in a second terminal
```

Tests need the same database:

```
pytest
```

## Deploying

There is one server, `orderdesk-prod` (Ubuntu 22.04, DigitalOcean). Deploys are done by hand. Ask Ana for SSH access.

1. `ssh deploy@orderdesk-prod`
2. `cd /srv/orderdesk && git pull origin main`
3. `source .venv/bin/activate && pip install -e .`
4. `sudo systemctl restart orderdesk-api`
5. `sudo systemctl restart orderdesk-worker` (easy to forget, then orders stay pending)
6. `curl -s localhost:8000/health` and look at `journalctl -u orderdesk-api -n 50` if it isn't `ok`

The unit files are in `deploy/`; copy them to `/etc/systemd/system/` when they change and run `systemctl daemon-reload`.

Python version on the server is whatever `apt` installed. If a deploy breaks, `git checkout` the previous commit and repeat steps 3 to 5. There is no image or artifact to roll back to.

Secrets live in `/srv/orderdesk/.env` on the server. Don't commit `.env`.
