FROM docker.m.daocloud.io/ubuntu:22.04

# Set working directory
WORKDIR /app

# Install system dependencies
# For PDF processing, we need poppler utilities
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    poppler-utils \
    libreoffice \
    libreoffice-calc \
    python3-uno \
    fonts-wqy-microhei fonts-wqy-zenhei fonts-noto-cjk \
    python3-pip \
    python3-venv \
    python3-dev \
    build-essential \
    procps \
    locales \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
RUN pip3 install --no-cache-dir requests python-docx pdf2image pandas openpyxl docxtpl pillow minio fastapi uvicorn -i https://mirrors.aliyun.com/pypi/simple

RUN sed -i 's/# zh_CN.UTF-8 UTF-8/zh_CN.UTF-8 UTF-8/' /etc/locale.gen \
 && locale-gen zh_CN.UTF-8

ENV LANG=zh_CN.UTF-8
ENV LC_ALL=zh_CN.UTF-8
# Copy application code
COPY . .

# Expose port for API mode
EXPOSE 8000

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Default command to run the application in CLI mode
ENTRYPOINT ["/entrypoint.sh"]
