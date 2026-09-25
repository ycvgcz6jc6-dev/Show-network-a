FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends ola python3 && rm -rf /var/lib/apt/lists/*
COPY server.py /opt/rdm-bridge/server.py
EXPOSE 8098
CMD ["python3","/opt/rdm-bridge/server.py"]
