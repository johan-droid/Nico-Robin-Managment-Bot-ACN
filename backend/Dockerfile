FROM rust:1.88-slim-bookworm AS builder
WORKDIR /app

COPY . .
RUN cargo build --release --bin nico_robin_bot

FROM debian:bookworm-slim AS runtime
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd -r appuser && useradd -r -g appuser -u 1000 -m appuser

COPY --from=builder /app/target/release/nico_robin_bot /app/nico_robin_bot
RUN chmod +x /app/nico_robin_bot && chown appuser:appuser /app/nico_robin_bot

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://127.0.0.1:8000/health || exit 1

CMD ["/app/nico_robin_bot"]

