FROM pytorch/pytorch:2.7.0-cuda12.8-cudnn9-runtime

WORKDIR /app

RUN apt-get update && apt-get install -y \
  gcc \
  g++ \
  libxrender1 libxext6  \
  && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 7860

CMD ["python", "src/app.py"]