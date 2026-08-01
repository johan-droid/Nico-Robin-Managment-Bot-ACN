FROM rust:1.88-slim-bookworm AS builder
WORKDIR /app
COPY backend/ .

RUN apt-get update && apt-get install -y --no-install-recommends \
    pkg-config \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

RUN cargo build --release --bin nico_robin_bot --bin migrate

FROM debian:bookworm-slim AS runtime
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    openssl \
    && rm -rf /var/lib/apt/lists/* \
    && echo "precedence ::ffff:0:0/96  100" >> /etc/gai.conf

RUN groupadd -r appuser && useradd -r -g appuser -u 1000 -m appuser

COPY --from=builder /app/target/release/nico_robin_bot /app/
COPY --from=builder /app/target/release/migrate /app/
COPY --from=builder /app/migrations/ /app/migrations/

RUN chmod +x /app/nico_robin_bot /app/migrate && chown -R appuser:appuser /app

RUN printf '#!/bin/sh\nset -e\necho "Running database migrations..."\n/app/migrate\necho "Starting bot..."\nexec /app/nico_robin_bot\n' > /app/entrypoint.sh && \
    chmod +x /app/entrypoint.sh && chown appuser:appuser /app/entrypoint.sh

USER appuser

ENTRYPOINT ["/app/entrypoint.sh"]
