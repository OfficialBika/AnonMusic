FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DENO_INSTALL=/usr/local/deno \
    UV_PROJECT_ENVIRONMENT=/opt/venv
ENV PATH="/usr/local/deno/bin:/root/.local/bin:/opt/venv/bin:${PATH}"

WORKDIR /app

RUN apt-get update -y \
    && apt-get install -y --no-install-recommends ffmpeg curl unzip ca-certificates \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && curl -fsSL https://deno.land/install.sh | sh \
    && mv /root/.deno /usr/local/deno \
    && curl -Ls https://astral.sh/uv/install.sh | sh

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY . .
RUN useradd --system --create-home --home-dir /home/anonmusic anonmusic \
    && mkdir -p /app/cache /app/downloads /app/anony/cookies /app/migration_backups \
    && chown -R anonmusic:anonmusic /app /opt/venv /usr/local/deno

USER anonmusic
HEALTHCHECK --interval=60s --timeout=5s --start-period=90s --retries=3 \
    CMD python -c "import os,sys; sys.exit(0 if os.path.exists('/app/log.txt') else 1)" || exit 1

CMD ["bash", "start"]
