FROM python:3.11-slim AS base

ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1

# Install helm CLI — auto-detect CPU architecture (amd64 or arm64)
RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends curl git ca-certificates tar gzip; \
    ARCH=$(dpkg --print-architecture); \
    case "$ARCH" in \
      amd64)   HELM_ARCH="amd64" ;; \
      arm64)   HELM_ARCH="arm64" ;; \
      armhf)   HELM_ARCH="arm" ;; \
      *)       echo "Unsupported arch: $ARCH" && exit 1 ;; \
    esac; \
    curl -fsSL "https://get.helm.sh/helm-v3.16.0-linux-${HELM_ARCH}.tar.gz" | tar xz; \
    mv "linux-${HELM_ARCH}/helm" /usr/local/bin/helm; \
    rm -rf "linux-${HELM_ARCH}"; \
    helm version; \
    apt-get clean; rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy BOTH pyproject.toml AND src/ before pip install -e .
# setuptools needs the package directory present during the editable install.
COPY pyproject.toml ./
COPY src ./src

RUN pip install --upgrade pip && pip install -e .

RUN mkdir -p /var/cache/helm

EXPOSE 8000
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
