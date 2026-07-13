FROM python:3.12-slim-bookworm

# Avoid interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive
ENV OLLAMA_HOST=http://ollama:11434

# Install system scanning tools + build dependencies for Go/Python tools.
# Packages that are not in Debian stable are installed from source in later steps.
RUN apt-get update && apt-get install -y --no-install-recommends \
    nmap \
    whois \
    curl \
    ca-certificates \
    dnsutils \
    iputils-ping \
    traceroute \
    openssl \
    libpcap-dev \
    libssl-dev \
    libxml2-dev \
    libxslt1-dev \
    zlib1g-dev \
    proxychains4 \
    git \
    build-essential \
    whatweb \
    libimage-exiftool-perl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Go from upstream (required for Go-based OSINT tools).
# Pinned to 1.26.5 because some tools (e.g. httpx) require go >= 1.26;
# using the newest needed version avoids repeated toolchain downloads.
ENV GOLANG_VERSION=1.26.5
ENV GOPATH=/root/go
ENV PATH=/usr/local/go/bin:${GOPATH}/bin:$PATH
RUN curl -fsSL https://go.dev/dl/go${GOLANG_VERSION}.linux-amd64.tar.gz -o /tmp/go.tgz && \
    tar -C /usr/local -xzf /tmp/go.tgz && \
    rm /tmp/go.tgz && \
    mkdir -p ${GOPATH}/bin && \
    go version

# Install Go-based OSINT tools (best-effort; image will still build if one fails)
RUN go install -v github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest || echo "subfinder install failed, skipping" && \
    go install -v github.com/owasp-amass/amass/v4/cmd/amass@latest || echo "amass install failed, skipping" && \
    go install -v github.com/projectdiscovery/httpx/cmd/httpx@latest || echo "httpx install failed, skipping" && \
    go install -v github.com/projectdiscovery/katana/cmd/katana@latest || echo "katana install failed, skipping" && \
    go install -v github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest || echo "nuclei install failed, skipping" && \
    go install -v github.com/OJ/gobuster/v3@latest || echo "gobuster install failed, skipping"

# Install additional Python OSINT tools from source/PyPI (best-effort)
RUN pip install --no-cache-dir sherlock-project || echo "sherlock install failed, skipping"
RUN git clone --depth 1 https://github.com/aboul3la/Sublist3r.git /opt/sublist3r && \
    pip install --no-cache-dir -r /opt/sublist3r/requirements.txt || echo "sublist3r requirements install failed, skipping" && \
    ln -sf /opt/sublist3r/sublist3r.py /usr/local/bin/sublist3r || true
RUN git clone --depth 1 https://github.com/laramies/theHarvester.git /opt/theHarvester && \
    pip install --no-cache-dir -r /opt/theHarvester/requirements.txt || echo "theHarvester requirements install failed, skipping" && \
    ln -sf /opt/theHarvester/theHarvester.py /usr/local/bin/theHarvester || true

# Set working directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    (pip install --no-cache-dir phoneinfoga || echo "phoneinfoga install skipped")

# Install maigret in an isolated venv to avoid aiohttp version conflicts with aiogram
RUN python -m venv /opt/maigret && \
    /opt/maigret/bin/pip install --no-cache-dir --upgrade pip && \
    (/opt/maigret/bin/pip install --no-cache-dir maigret || echo "maigret install failed, skipping") && \
    ln -sf /opt/maigret/bin/maigret /usr/local/bin/maigret || true

# Copy bot code
COPY config.py .
COPY bot.py .
COPY handlers/ ./handlers/
COPY middlewares/ ./middlewares/
COPY services/ ./services/
COPY utils/ ./utils/
COPY scripts/ ./scripts/
COPY data/ ./data/

# Create directories for results, logs, and persistent data
RUN mkdir -p /app/results /app/logs /app/data

# Run as root (required for nmap -sS SYN scans)
USER root

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python scripts/health_check.py

CMD ["python", "-u", "bot.py"]
