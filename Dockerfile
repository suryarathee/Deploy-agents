FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1
WORKDIR /app

# install supervisor for process management
RUN apt-get update \
 && apt-get install -y --no-install-recommends supervisor \
 && rm -rf /var/lib/apt/lists/*

# copy project
COPY . /app

# Install Python deps
RUN if [ -f "requirements.txt" ]; then \
      pip install --no-cache-dir -r requirements.txt ; \
    else \
      pip install --no-cache-dir fastapi "uvicorn[standard]" requests pyyaml ; \
      # try installing google-adk CLI package if available
      pip install --no-cache-dir google-adk || true ; \
    fi

# ✅ THE FIX: We added 'stdout_logfile_maxbytes=0' and 'stderr_logfile_maxbytes=0' to all sections.
# This prevents Supervisor from trying to "seek" or rotate the Docker log stream.
RUN mkdir -p /var/log/supervisor \
 && printf "[supervisord]\nnodaemon=true\nlogfile=/var/log/supervisor/supervisord.log\npidfile=/var/run/supervisord.pid\n\n[program:adk]\ncommand=adk api_server --port 8085\ndirectory=/app\nautostart=true\nautorestart=true\nstdout_logfile=/dev/fd/1\nstdout_logfile_maxbytes=0\nstderr_logfile=/dev/fd/2\nstderr_logfile_maxbytes=0\n\n[program:fastapi]\ncommand=uvicorn main:app --host 0.0.0.0 --port 8082\ndirectory=/app\nautostart=true\nautorestart=true\nstdout_logfile=/dev/fd/1\nstdout_logfile_maxbytes=0\nstderr_logfile=/dev/fd/2\nstderr_logfile_maxbytes=0\n" > /etc/supervisord.conf

EXPOSE 8082 8085

CMD ["supervisord", "-c", "/etc/supervisord.conf"]