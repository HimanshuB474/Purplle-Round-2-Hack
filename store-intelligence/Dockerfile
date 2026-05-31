FROM python:3.11-slim



WORKDIR /app



# No apt-get — keeps image small and avoids Docker Desktop disk issues on Windows

COPY requirements-api.txt .

RUN pip install --no-cache-dir -r requirements-api.txt



COPY app/ ./app/

COPY data/ ./data/



EXPOSE 8000



HEALTHCHECK --interval=30s --timeout=5s --retries=3 \

  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)"]



CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

