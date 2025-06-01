FROM redis/redis-stack:latest

RUN apt-get update && apt-get install -y \
  pip \
  libxrender1 libxext6 \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir torch==2.6.0+cpu --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir -r requirements.txt

COPY ./src ./src
ENV HF_HOME=/tmp/.cache/huggingface
ENV SENTENCE_TRANSFORMERS_HOME=/tmp/.cache/sentence_transformers

COPY redis.conf .
COPY dump.rdb /tmp
ENV REDIS_HOST=localhost
ENV REDIS_PORT=6379

CMD ["sh", "-c", "redis-server redis.conf & python3 src/app.py"]