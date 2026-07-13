FROM python:3.12.13-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY pyproject.toml requirements.lock README.md ./
COPY services/api ./services/api
COPY services/jobs ./services/jobs

RUN python -m pip install --no-cache-dir --constraint requirements.lock .

EXPOSE 8000

CMD ["uvicorn", "fable5_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
