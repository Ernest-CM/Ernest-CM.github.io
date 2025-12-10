.PHONY: start stop test clean logs migrate shell

start:
	docker-compose up -d
	@echo "Waiting for services to be ready..."
	@sleep 5
	docker-compose exec app alembic upgrade head
	@echo "Services started. API available at http://localhost:8000"

stop:
	docker-compose down

test:
	docker-compose exec app pytest -v

test-local:
	pytest -v

clean:
	docker-compose down -v
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete

logs:
	docker-compose logs -f app

migrate:
	docker-compose exec app alembic upgrade head

shell:
	docker-compose exec app python

worker-logs:
	docker-compose logs -f worker
