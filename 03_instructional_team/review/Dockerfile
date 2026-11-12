FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

RUN apt-get update && apt-get install -y --no-install-recommends build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /course
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project
COPY 02_activities/documents/ ./02_activities/documents/
COPY 03_instructional_team/review/execute_notebook.py ./execute_notebook.py
ENV PATH="/course/.venv/bin:$PATH"
WORKDIR /course/02_activities

