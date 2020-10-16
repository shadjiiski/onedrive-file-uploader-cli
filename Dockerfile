FROM python:3.9.0-alpine3.12
COPY src/ /app/
RUN apk add --no-cache \
        gcc \
        musl-dev \
        libressl-dev \
        libffi-dev && \
    pip install --no-cache-dir -r /app/requirements.txt && \
    apk del \
        gcc \
        musl-dev \
        libressl-dev \
        libffi-dev
WORKDIR /data
ENTRYPOINT ["python", "/app/onedrive_uploader.py"]
CMD ["--help"]
