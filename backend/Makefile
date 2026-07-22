DB_CONTAINER = nico-robin-db
DB_IMAGE     = postgres:15-alpine
DB_PORT      = 5432

.PHONY: all db bot stop clean

all: db bot

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
		sleep 5; \
		echo "[db] ready"; \
	fi

bot: db
	@echo "[bot] starting Nico Robin..."
	@cargo run

stop:
	@echo "[db] stopping..."
	@docker stop $(DB_CONTAINER) 2>/dev/null || true
	@docker rm $(DB_CONTAINER) 2>/dev/null || true
	@echo "[db] stopped"

clean: stop
	@echo "[db] removing image..."
	@docker rmi $(DB_IMAGE) 2>/dev/null || true
