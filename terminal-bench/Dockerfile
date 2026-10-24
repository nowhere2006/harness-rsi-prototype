FROM python:3.13-slim
WORKDIR /opt/terminal-bench
RUN apt-get update \
    && apt-get install -y --no-install-recommends docker-cli docker-compose=2.26.1-4 \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.lock ./requirements.lock
RUN python -m pip install --no-cache-dir -r requirements.lock
ENTRYPOINT ["harbor"]
