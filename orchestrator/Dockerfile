FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential cmake ffmpeg alsa-utils wget && \
    rm -rf /var/lib/apt/lists/*

# Piper TTS (binario ARM64 para Raspberry Pi 4)
RUN wget -q https://github.com/rhasspy/piper/releases/latest/download/piper_linux_aarch64.tar.gz \
    -O /tmp/piper.tar.gz && \
    tar -xzf /tmp/piper.tar.gz -C /opt && rm /tmp/piper.tar.gz
ENV PATH="/opt/piper:${PATH}"

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

CMD ["python", "main.py"]
