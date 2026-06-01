FROM python:3.11-slim



WORKDIR /app



# No apt-get — keeps image small and avoids Docker Desktop disk issues on Windows

COPY requirements-api.txt .

RUN pip install --no-cache-dir -r requirements-api.txt



COPY app/ ./app/

COPY dashboard/ ./dashboard/

COPY data/ ./data/

COPY scripts/start.sh ./scripts/start.sh

RUN chmod +x ./scripts/start.sh

EXPOSE 8000



HEALTHCHECK --interval=30s --timeout=5s --retries=3 \

  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)"]



CMD ["./scripts/start.sh"]

