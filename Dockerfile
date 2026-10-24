FROM docker:29.2.1-cli@sha256:cab69e2d0a1a2ea9a1ce1060252f439e83483ae41ec09317aecb33b08a0656a5 AS dockercli
FROM python:3.11-slim-bookworm@sha256:f06d01d4ba3f8ad5af45a3ec87df19c1d317d8e8961edc0fabda61811af6f7cf

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    MSWEA_SILENT_STARTUP=1 \
    MSWEA_GLOBAL_CONFIG_DIR=/workspace/.cache/mini \
    HF_HOME=/workspace/.cache/huggingface

RUN apt-get update && apt-get install -y --no-install-recommends bash git ca-certificates \
    && rm -rf /var/lib/apt/lists/*
COPY --from=dockercli /usr/local/bin/docker /usr/local/bin/docker
COPY --from=dockercli /usr/local/libexec/docker/cli-plugins/docker-buildx /usr/local/libexec/docker/cli-plugins/docker-buildx
WORKDIR /workspace
COPY requirements-bootstrap.txt requirements.lock /tmp/
COPY mini-swe-agent /workspace/mini-swe-agent
RUN pip install --no-cache-dir -c /tmp/requirements.lock -e /workspace/mini-swe-agent -r /tmp/requirements-bootstrap.txt \
    && pip check
CMD ["sleep", "infinity"]
