# syntax=docker/dockerfile:1.7
# Two stages: build the virtualenv with uv from the lockfile, then copy only the
# result into a slim runtime image that runs as a non-root user.

FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:0.11.2 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0

WORKDIR /app

# Dependencies first so this layer is cached until the lockfile changes.
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-install-project

# Then the project itself.
COPY README.md ./
COPY src ./src
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev


FROM python:3.12-slim AS runtime

RUN groupadd --system app && useradd --system --gid app --home-dir /app --shell /usr/sbin/nologin app

WORKDIR /app
COPY --from=builder --chown=app:app /app /app

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

USER app
EXPOSE 8000

# No curl in the image; the check uses the interpreter that is already there.
HEALTHCHECK --interval=15s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import sys, urllib.request; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2).status == 200 else 1)"

CMD ["uvicorn", "orderdesk.api:app", "--host", "0.0.0.0", "--port", "8000"]
