FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
WORKDIR /app

# 1. Install Supervisor (Process Manager)
RUN apt-get update \
 && apt-get install -y --no-install-recommends supervisor curl \
 && rm -rf /var/lib/apt/lists/*

# Install uv (provides the uvx command used by the MCP toolset)
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# 2. Copy project files
COPY . /app

# 3. Install Python Dependencies
# We use Python 3.11 and strictly require google-adk to ensure it installs correctly.
RUN pip install --no-cache-dir fastapi "uvicorn[standard]" requests pyyaml google-adk

# 4. Create Supervisor Configuration
# This runs BOTH the ADK Agent (port 8085) and FastAPI (port 8082) inside one container.
# We also set logfile_maxbytes=0 to prevent Docker logging errors.
RUN mkdir -p /var/log/supervisor \
 && printf "[supervisord]\nnodaemon=true\nlogfile=/var/log/supervisor/supervisord.log\npidfile=/var/run/supervisord.pid\n\n[program:adk]\ncommand=adk api_server --port 8085\ndirectory=/app\nautostart=true\nautorestart=true\nstdout_logfile=/dev/fd/1\nstdout_logfile_maxbytes=0\nstderr_logfile=/dev/fd/2\nstderr_logfile_maxbytes=0\n\n[program:fastapi]\ncommand=uvicorn main:app --host 0.0.0.0 --port 8082\ndirectory=/app\nautostart=true\nautorestart=true\nstdout_logfile=/dev/fd/1\nstdout_logfile_maxbytes=0\nstderr_logfile=/dev/fd/2\nstderr_logfile_maxbytes=0\n" > /etc/supervisord.conf

# 5. Expose ports
EXPOSE 8082 8085

# 6. Start Supervisor
CMD ["supervisord", "-c", "/etc/supervisord.conf"]