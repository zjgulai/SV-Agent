FROM ghcr.io/astral-sh/uv:0.11.14 AS uv

FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy
WORKDIR /workspace
COPY --from=uv /uv /uvx /bin/
COPY apps/api/pyproject.toml apps/api/uv.lock apps/api/
RUN uv sync --project apps/api --frozen --no-dev --no-install-project
COPY apps/api apps/api
COPY migrations migrations
RUN uv sync --project apps/api --frozen --no-dev
RUN groupadd --system app && useradd --system --gid app --home-dir /nonexistent app \
    && chown -R app:app /workspace
ENV PATH="/workspace/apps/api/.venv/bin:${PATH}"
USER app
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--app-dir", "apps/api", "--host", "0.0.0.0", "--port", "8000"]
