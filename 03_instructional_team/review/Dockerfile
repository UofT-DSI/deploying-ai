FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

RUN apt-get update && apt-get install -y --no-install-recommends build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /course
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project
COPY 02_activities/documents/ ./02_activities/documents/
COPY 05_src/utils/ ./05_src/utils/
COPY 03_instructional_team/review/course_workspace.py ./course_workspace.py
COPY 03_instructional_team/review/execute_notebook.py ./execute_notebook.py
COPY 03_instructional_team/review/execute_chat.py ./execute_chat.py
ENV PATH="/course/.venv/bin:$PATH"
ENV PYTHONPATH="/course/05_src"
WORKDIR /course/02_activities

