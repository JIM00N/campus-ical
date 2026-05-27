FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# Firefox + minimal deps for Selenium. Selenium Manager (built into selenium 4.6+)
# auto-downloads a matching geckodriver at runtime.
RUN apt-get update && apt-get install -y --no-install-recommends \
        firefox-esr \
        ca-certificates \
        fonts-noto-cjk \
        tini \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

ENV PORT=8000
EXPOSE 8000

ENTRYPOINT ["/usr/bin/tini", "--"]
# Fallback to 8000 if PORT isn't injected; exec lets signals reach uvicorn.
CMD ["sh", "-c", "echo \"starting on PORT=${PORT:-8000}\" && python -m scripts.seed_schools && exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
