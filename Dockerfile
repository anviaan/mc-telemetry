FROM python:3.12-alpine

WORKDIR /app

COPY requirements.txt .

RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

ENV MYSQL_HOST="host.docker.internal"

CMD ["python3", "-m", "flask", "run", "--host=0.0.0.0"]
