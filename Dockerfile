FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# System dependencies
RUN apt-get update && apt-get install -y \
    git build-essential curl wget unzip jq make \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip==23.3.1 && pip install -r requirements.txt

ARG GOLANG_VERSION=1.21.5
ENV PATH=$PATH:/usr/local/go/bin

RUN wget https://go.dev/dl/go${GOLANG_VERSION}.linux-amd64.tar.gz && \
    tar -C /usr/local -xzf go${GOLANG_VERSION}.linux-amd64.tar.gz && \
    ln -s /usr/local/go/bin/go /usr/local/bin/go && \
    go version && \
    go install github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest && \
    go install github.com/projectdiscovery/chaos-client/cmd/chaos@latest && \
    go install github.com/projectdiscovery/dnsx/cmd/dnsx@latest && \
    go install github.com/projectdiscovery/httpx/cmd/httpx@latest && \
    go install github.com/d3mondev/puredns/v2@latest && \
    go install github.com/incogbyte/shosubgo@latest && \
    rm -rf /root/go /go /usr/local/go /go${GOLANG_VERSION}.linux-amd64.tar.gz

RUN git clone https://github.com/blechschmidt/massdns.git /opt/massdns && \
    cd /opt/massdns && make && cp bin/massdns /usr/local/bin/

COPY . .

CMD ["python3", "main.py", "--help"]
