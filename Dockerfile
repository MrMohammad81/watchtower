# Use official Python image
FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    build-essential \
    curl \
    wget \
    unzip \
    jq \
    make \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Install Go (for subfinder, chaos, httpx, dnsx, puredns, shosubgo)
ENV GOLANG_VERSION=1.21.5
RUN wget https://go.dev/dl/go${GOLANG_VERSION}.linux-amd64.tar.gz && \
    rm -rf /usr/local/go && \
    tar -C /usr/local -xzf go${GOLANG_VERSION}.linux-amd64.tar.gz && \
    ln -s /usr/local/go/bin/go /usr/local/bin/go && \
    go version

# Set Go env
ENV PATH=$PATH:/usr/local/go/bin

# Install subfinder
RUN go install github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest

# Install chaos
RUN go install github.com/projectdiscovery/chaos-client/cmd/chaos@latest

# Install dnsx
RUN go install github.com/projectdiscovery/dnsx/cmd/dnsx@latest

# Install httpx
RUN go install github.com/projectdiscovery/httpx/cmd/httpx@latest

# Install puredns
RUN go install github.com/d3mondev/puredns/v2@latest

# Install shosubgo 
RUN go install github.com/incogbyte/shosubgo@latest

# Install massdns
RUN git clone https://github.com/blechschmidt/massdns.git /opt/massdns && \
    cd /opt/massdns && make && \
    cp /opt/massdns/bin/massdns /usr/local/bin/

# Copy source code
COPY . .

# Expose 
# EXPOSE 8000

# Default command 
CMD ["python3", "main.py", "--help"]
