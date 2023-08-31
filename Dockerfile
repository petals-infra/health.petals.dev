FROM python:3.10-slim-bullseye

ARG MODEL_ID

WORKDIR /usr/src/app/

COPY requirements.txt ./

RUN pip install --no-cache-dir -r ./requirements.txt --upgrade pip

CMD flask run --host=0.0.0.0 --port=5000