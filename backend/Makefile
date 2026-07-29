DB_CONTAINER = nico-robin-db
DB_IMAGE     = postgres:15-alpine
DB_PORT      = 5432

.PHONY: all db bot stop clean dev test lint check diagnose reset-db migrate

all: db migrate bot

db:
	@if docker ps --filter name=$(DB_CONTAINER) --format '{{.Names}}' | grep -q .; then \
		echo "[db] already running"; \
	else \
		echo "[db] starting PostgreSQL..."; \
		docker run -d --name $(DB_CONTAINER) \
			-e POSTGRES_USER=robin \
			-e POSTGRES_PASSWORD=password \
			-e POSTGRES_DB=robin_db \
			-p $(DB_PORT):5432 \
			$(DB_IMAGE) > /dev/null && \
		echo "[db] waiting for ready..."; \
		for i in {1..10}; do \
			if docker exec $(DB_CONTAINER) pg_isready -U robin -d robin_db >/dev/null 2>&1; then \
				echo "[db] ready"; \
				break; \
			fi; \
			sleep 1; \
		done; \
	fi

migrate: db
	@echo "[db] applying migrations..."
	@for f in migrations/*.sql; do \
		echo "[db] running $$f..."; \
		docker exec -i $(DB_CONTAINER) psql -U robin -d robin_db < $$f > /dev/null; \
	done
	@echo "[db] migrations completed."

bot: db
	@echo "[bot] starting Nico Robin..."
	@ENVIRONMENT=development cargo run --release --bin nico_robin_bot

dev: db migrate
	@echo "[dev] starting Nico Robin in development mode..."
	@ENVIRONMENT=development cargo run --bin nico_robin_bot

test:
	@echo "[test] running test suite..."
	@cargo test -- --nocapture

lint:
	@echo "[lint] running clippy and formatter..."
	@cargo clippy --all-targets --all-features -- -D warnings
	@cargo fmt -- --check

check:
	@echo "[check] cargo check..."
	@cargo check
	@$(MAKE) diagnose

diagnose:
	@echo "[diagnose] running development environment diagnostic..."
	@cargo run --bin diagnose

stop:
	@echo "[db] stopping..."
	@docker stop $(DB_CONTAINER) 2>/dev/null || true
	@docker rm $(DB_CONTAINER) 2>/dev/null || true
	@echo "[db] stopped"

reset-db: stop db migrate
	@echo "[db] reset completed."

clean: stop
	@echo "[db] removing image..."
	@docker rmi $(DB_IMAGE) 2>/dev/null || true

