FROM python:3.9-slim-bullseye

RUN apt-get update \
    && apt-get install -y \
    --no-install-recommends \
    --no-install-suggests \
    build-essential ffmpeg \
    pkg-config \
    && pip install --no-cache-dir --upgrade pip

RUN pip3 install flask mysql-connector-python

WORKDIR /app
COPY ./requirements.txt /app
RUN pip install --no-cache-dir --requirement /app/requirements.txt
COPY . /app

CMD ["python3", "consumer.py"]