# Bullish Breakout Scanner -- API
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Dependencies first so they stay cached when only app code changes.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY export_scan.py ./

# Price/info cache lives here (config.py puts it one level above app/).
# docker-compose mounts a named volume over it so a cold scan happens once,
# not on every container restart.
RUN mkdir -p /app/.cache /app/exports

# Run as a non-root user; it needs write access to the cache and exports dirs.
RUN useradd --create-home --uid 10001 scanner \
 && chown -R scanner:scanner /app
USER scanner

EXPOSE 8000

# 0.0.0.0, not the 127.0.0.1 default -- otherwise the port is unreachable
# from outside the container.
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# python:3.12-slim ships no curl, so probe with the stdlib instead.
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
  CMD ["python", "-c", "import sys,urllib.request; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=5).status == 200 else 1)"]
