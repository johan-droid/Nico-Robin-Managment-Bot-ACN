# Root-level Dockerfile that builds from the backend directory
# The bot runs in long-polling mode (no HTTP server)

FROM rust:1.88-slim-bookworm AS builder
WORKDIR /app

# Copy the backend source
COPY backend/ .

# Build the release binary
RUN cargo build --release --bin nico_robin_bot

FROM debian:bookworm-slim AS runtime
WORKDIR /app

# Install runtime dependencies: ca-certificates for HTTPS and openssl for SSL libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    openssl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /app/target/release/nico_robin_bot /app/nico_robin_bot
RUN chmod +x /app/nico_robin_bot

# RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
# USER appuser

EXPOSE 8000

# No HEALTHCHECK - the bot uses long polling (no HTTP server)
# Render will keep the container alive as long as the process runs

CMD ["/bin/sh", "-c", "/app/nico_robin_bot"]