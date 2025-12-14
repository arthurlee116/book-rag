ARG PYTHON_BASE_IMAGE=docker.m.daocloud.io/library/python:3.12-slim
FROM ${PYTHON_BASE_IMAGE}

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DEFAULT_TIMEOUT=60

# Use a fast PyPI mirror by default (common fix for flaky/blocked pypi access).
# Override at build time with: --build-arg PIP_INDEX_URL=...
ARG PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
ARG PIP_TRUSTED_HOST=pypi.tuna.tsinghua.edu.cn

WORKDIR /app

# faiss-cpu wheels rely on OpenMP on Debian (libgomp1).
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./requirements.txt
RUN pip install -i ${PIP_INDEX_URL} --trusted-host ${PIP_TRUSTED_HOST} --retries 5 -r requirements.txt

# Copy sources so the image works even without bind mounts.
COPY . /app

EXPOSE 8000
