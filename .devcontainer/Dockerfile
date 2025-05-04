# ... existing code ...
FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependencies list and install
COPY requirements.txt /tmp/reqs.txt
RUN pip install --no-cache-dir -r requirements.txt

# (Optional) Ensure transformers is installed, if not in requirements.txt
RUN pip install --no-cache-dir transformers

# Non-root user (good practice)
RUN useradd -ms /bin/bash devuser
USER devuser
WORKDIR /workspace