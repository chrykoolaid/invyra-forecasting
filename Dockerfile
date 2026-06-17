FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    INVYRA_FORECASTING_HOST=0.0.0.0 \
    INVYRA_FORECASTING_PORT=8000

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src

RUN pip install --upgrade pip \
    && pip install -e '.[api]'

EXPOSE 8000

CMD ["sh", "-c", "uvicorn invyra_forecasting.api.app:app --host ${INVYRA_FORECASTING_HOST:-0.0.0.0} --port ${PORT:-${INVYRA_FORECASTING_PORT:-8000}}"]
