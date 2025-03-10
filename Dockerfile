FROM python:3.10-slim

# Environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git curl wget build-essential jq \
    && rm -rf /var/lib/apt/lists/*

# Install Go (required for subfinder, chaos, dnsx, httpx)
RUN wget https://go.dev/dl/go1.21.1.linux-amd64.tar.gz && \
    tar -C /usr/local -xzf go1.21.1.linux-amd64.tar.gz && \
    rm go1.21.1.linux-amd64.tar.gz

ENV PATH="/usr/local/go/bin:${PATH}"
ENV GOPATH="/go"
ENV PATH="$GOPATH/bin:$PATH"

# Install external tools
RUN go install github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest
RUN go install github.com/projectdiscovery/chaos-client/cmd/chaos@latest
RUN go install github.com/projectdiscovery/dnsx/cmd/dnsx@latest
RUN go install github.com/projectdiscovery/httpx/cmd/httpx@latest
RUN go install github.com/incogbyte/shosubgo@latest

# Install massdns
RUN git clone https://github.com/blechschmidt/massdns.git /opt/massdns && \
    make -C /opt/massdns && \
    cp /opt/massdns/bin/massdns /usr/local/bin/ && \
    rm -rf /opt/massdns

# Set working directory
WORKDIR /app

# Copy project files
COPY . /app

# Install Python requirements
RUN pip install --no-cache-dir -r requirements.txt

# Default entrypoint
ENTRYPOINT ["python", "main.py"]
