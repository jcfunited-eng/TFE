FROM python:3.11-slim-bookworm

ARG TARGETARCH

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        bash \
        bubblewrap \
        build-essential \
        ca-certificates \
        curl \
        espeak-ng \
        ffmpeg \
        git \
        jq \
        nodejs \
        npm \
        openssh-client \
        procps \
        ripgrep \
        tar \
        unzip \
        util-linux \
        zip \
    && case "${TARGETARCH}" in \
        amd64) aws_arch="x86_64"; session_arch="64bit" ;; \
        arm64) aws_arch="aarch64"; session_arch="arm64" ;; \
        *) echo "unsupported development-container architecture: ${TARGETARCH}" >&2; exit 1 ;; \
       esac \
    && curl -fsSLo /tmp/awscliv2.zip \
        "https://awscli.amazonaws.com/awscli-exe-linux-${aws_arch}.zip" \
    && unzip -q /tmp/awscliv2.zip -d /tmp \
    && /tmp/aws/install \
    && curl -fsSLo /tmp/session-manager-plugin.deb \
        "https://s3.amazonaws.com/session-manager-downloads/plugin/latest/ubuntu_${session_arch}/session-manager-plugin.deb" \
    && apt-get install -y --no-install-recommends /tmp/session-manager-plugin.deb \
    && rm -rf \
        /tmp/aws \
        /tmp/awscliv2.zip \
        /tmp/session-manager-plugin.deb \
        /var/lib/apt/lists/*

ENV CARGO_HOME=/usr/local/cargo
ENV RUSTUP_HOME=/usr/local/rustup
ENV PATH=/usr/local/cargo/bin:${PATH}

# The mounted workspace is disposable-container independent. Install the
# complete production and verification toolchain into the image so a rebuild
# cannot remove Codex's ability to test, build, or deploy Guala.
RUN curl --proto '=https' --tlsv1.2 -fsS https://sh.rustup.rs \
        | sh -s -- -y --profile minimal --default-toolchain stable \
    && pip install --no-cache-dir \
        boto3 \
        cryptography \
        fastapi \
        httpx \
        ijson==3.4.0.post0 \
        maturin \
        numpy \
        pandas \
        pillow \
        pillow-heif \
        pyarrow \
        pymupdf \
        pytest \
        pytest-asyncio \
        python-flint==0.9.0 \
        python-multipart \
        scipy \
        uvicorn \
        websockets
