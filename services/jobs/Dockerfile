FROM python:3.12.13-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY pyproject.toml requirements.lock README.md ./
COPY services/api ./services/api
COPY services/backtester ./services/backtester
COPY services/data ./services/data
COPY services/extraction ./services/extraction
COPY services/jobs ./services/jobs
COPY services/mapping ./services/mapping
COPY services/research ./services/research
COPY services/risk ./services/risk

RUN python -m pip install --no-cache-dir --constraint requirements.lock .

CMD ["python", "-m", "fable5_jobs.worker"]
