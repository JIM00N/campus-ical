FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# Firefox + minimal deps for Selenium.
RUN apt-get update && apt-get install -y --no-install-recommends \
        firefox-esr \
        ca-certificates \
        curl \
        fonts-noto-cjk \
        tini \
    && rm -rf /var/lib/apt/lists/*

# geckodriver: Selenium Manager (4.6+) can auto-provision a driver on amd64,
# but NOT on linux/aarch64 (Apple Silicon mac mini host) — it raises
# "Unsupported platform/architecture combination". Install it explicitly for
# the build arch so the crawler can skip Selenium Manager (see app/crawlers/gachon.py).
ARG TARGETARCH
ARG GECKODRIVER_VERSION=0.36.0
RUN set -eux; \
    case "${TARGETARCH}" in \
        amd64) gd_arch=linux64 ;; \
        arm64) gd_arch=linux-aarch64 ;; \
        *) echo "unsupported TARGETARCH: ${TARGETARCH}" >&2; exit 1 ;; \
    esac; \
    curl -fsSL -o /tmp/geckodriver.tar.gz \
        "https://github.com/mozilla/geckodriver/releases/download/v${GECKODRIVER_VERSION}/geckodriver-v${GECKODRIVER_VERSION}-${gd_arch}.tar.gz"; \
    tar -xzf /tmp/geckodriver.tar.gz -C /usr/local/bin; \
    chmod +x /usr/local/bin/geckodriver; \
    rm /tmp/geckodriver.tar.gz; \
    /usr/local/bin/geckodriver --version

# Let the crawler reach Firefox + geckodriver without invoking Selenium Manager.
ENV FIREFOX_BIN=/usr/bin/firefox-esr \
    GECKODRIVER_BIN=/usr/local/bin/geckodriver

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

ENV PORT=8000
EXPOSE 8000

ENTRYPOINT ["/usr/bin/tini", "--"]
# Fallback to 8000 if PORT isn't injected; exec lets signals reach uvicorn.
CMD ["sh", "-c", "echo \"starting on PORT=${PORT:-8000}\" && python -m scripts.seed_schools && exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
