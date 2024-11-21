FROM ubuntu:20.04

ARG WORKING_DIR=/app
WORKDIR $WORKING_DIR

RUN apt-get update \
    && apt-get install -y --no-install-recommends python3-pip \
    && pip3 install --default-timeout=1000 --upgrade pip

RUN apt-get install --no-install-recommends -y \
    python3-dev \
    python3-venv \
    python3-setuptools \
    nano \
    vim \
    curl \
    ca-certificates

COPY src $WORKING_DIR
COPY requirements.txt /requirements.txt

RUN pip3 install --default-timeout=1000 --no-cache-dir -r /requirements.txt \
    --trusted-host pypi.org --trusted-host pypi.python.org  --trusted-host files.pythonhosted.org

RUN apt-get autoclean && apt-get clean && apt-get autoremove


ENV PYTHONPATH=$WORKING_DIR \
    LC_ALL=C.UTF-8 \
    LANG=C.UTF-8

CMD python3 main.py

# docker build -t mygraphql .