FROM python:3.12-slim

# Install system scanning tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    nmap \
    whois \
    curl \
    ca-certificates \
    dnsutils \
    sublist3r \
    iputils-ping \
    traceroute \
    openssl \
    libpcap-dev \
    proxychains4 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy bot code
COPY config.py .
COPY bot.py .
COPY handlers/ ./handlers/
COPY middlewares/ ./middlewares/
COPY services/ ./services/
COPY utils/ ./utils/
COPY scripts/ ./scripts/

# Create directories for results and logs
RUN mkdir -p /app/results /app/logs

# Run as root (required for nmap -sS SYN scans)
USER root

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python scripts/health_check.py

CMD ["python", "-u", "bot.py"]
