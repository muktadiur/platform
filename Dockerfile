FROM python:3.11-slim as builder

RUN apt-get update && apt-get install -y \
    gcc \
    libffi-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /usr/src/app

COPY requirements.txt .
RUN pip install --upgrade pip && pip install --target=/usr/src/app/site-packages -r requirements.txt

COPY . .

# Copy everything from builder stage
FROM python:3.11-slim as runner
COPY --from=builder /usr/src/app /usr/src/app
COPY --from=builder /usr/src/app/site-packages /usr/local/lib/python3.11/site-packages

WORKDIR /usr/src/app

# RUN ./setup.sh

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

