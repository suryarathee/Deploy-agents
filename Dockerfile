
FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1
WORKDIR /app

# install supervisor for process management
RUN apt-get update \
 && apt-get install -y --no-install-recommends supervisor \
 && rm -rf /var/lib/apt/lists/*

# copy project (main.py at repo root, agent/ package present)
COPY . /app

# Install Python deps:
# - if you provide requirements.txt, it will be used
# - otherwise install common defaults (fastapi, uvicorn, requests, pyyaml)
RUN if [ -f "requirements.txt" ]; then \
      pip install --no-cache-dir -r requirements.txt ; \
    else \
      pip install --no-cache-dir fastapi "uvicorn[standard]" requests pyyaml ; \
      # try installing google-adk CLI package if available (non-fatal if missing)
      pip install --no-cache-dir google-adk || true ; \
    fi

# Create supervisor config to run both the ADK server and FastAPI
RUN mkdir -p /var/log/supervisor \
 && printf "[supervisord]\nnodaemon=true\n\n[program:adk]\ncommand=adk api_server --port 8085\ndirectory=/app\nautostart=true\nautorestart=true\nstdout_logfile=/dev/fd/1\nstderr_logfile=/dev/fd/2\n\n[program:fastapi]\ncommand=uvicorn main:app --host 0.0.0.0 --port 8082\ndirectory=/app\nautostart=true\nautorestart=true\nstdout_logfile=/dev/fd/1\nstderr_logfile=/dev/fd/2\n" > /etc/supervisord.conf

EXPOSE 8082 8085

CMD ["supervisord", "-c", "/etc/supervisord.conf"]
