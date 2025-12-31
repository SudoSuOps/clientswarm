# SwarmOS Backend Makefile
# 
# Commands:
#   make install    - Install dependencies
#   make dev        - Run development stack
#   make bee1       - Run Bee-1 only
#   make bee2       - Run Bee-2 worker
#   make test       - Run tests
#   make clean      - Clean up

.PHONY: install dev bee1 bee2 test clean docker-up docker-down

# =============================================================================
# Development
# =============================================================================

install:
	pip install -r bee1/requirements.txt
	pip install -r bee2/requirements.txt

dev: docker-up
	@echo "✓ SwarmOS dev stack running"
	@echo "  Bee-1 API: http://localhost:8000"
	@echo "  Redis: localhost:6379"
	@echo "  IPFS: http://localhost:5001"

bee1:
	cd bee1 && python -m api.main

bee2:
	cd bee2 && python -m worker.main

# =============================================================================
# Docker
# =============================================================================

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f

docker-build:
	docker-compose build

# =============================================================================
# Database
# =============================================================================

db-init:
	cd bee1 && alembic upgrade head

db-migrate:
	cd bee1 && alembic revision --autogenerate -m "$(msg)"

# =============================================================================
# Testing
# =============================================================================

test:
	pytest tests/ -v

test-api:
	@echo "Testing Bee-1 API..."
	curl -s http://localhost:8000/health | jq .
	curl -s http://localhost:8000/api/v1/status | jq .

test-submit:
	@echo "Submitting test job..."
	curl -s -X POST http://localhost:8000/api/v1/jobs \
		-H "Content-Type: application/json" \
		-d '{"job_type":"spine_mri","dicom_ref":"ipfs://QmTest","client_ens":"xyzclinic.clientswarm.eth","timestamp":'$$(date +%s)',"nonce":"test123","signature":"0x..."}' | jq .

# =============================================================================
# Cleanup
# =============================================================================

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache
	rm -rf data/*.db

# =============================================================================
# Production
# =============================================================================

prod-build:
	docker-compose -f docker-compose.prod.yml build

prod-up:
	docker-compose -f docker-compose.prod.yml up -d

prod-down:
	docker-compose -f docker-compose.prod.yml down
