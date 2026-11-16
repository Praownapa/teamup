# TeamUp backend image (FastAPI + uvicorn), built for Amazon ECS on Fargate.
#   docker build -t teamup-backend .
#   docker run -p 8000:8000 -e DATABASE_URL=postgresql://... -e AUTH_MODE=cognito ... teamup-backend
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /srv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY migrations ./migrations
COPY seed ./seed

# Run as an unprivileged user; it may only write to /srv/uploads (used when UPLOAD_MODE=local).
RUN useradd --create-home --uid 10001 app && mkdir -p /srv/uploads && chown app /srv/uploads
USER app

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health', timeout=4)"

# --proxy-headers: trust X-Forwarded-* from the load balancer in front of the container.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
