.PHONY: help build up down seed panel consensus sign publish test clean logs

help: ## Show this help message
	@echo "Truce Development Commands"
	@echo "========================="
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

build: ## Build all Docker images
	docker-compose build

up: ## Start all services
	docker-compose up -d
	@echo "🚀 Services starting..."
	@echo "   Web UI: http://localhost:3000"
	@echo "   API: http://localhost:8000"
	@echo "   Fuseki (optional): http://localhost:3030"
	@echo ""
	@echo "Run 'make seed' to load demo data"

down: ## Stop all services
	docker-compose down

seed: ## Seed demo data for Canadian violent crime claim
	@echo "🌱 Seeding Canadian violent crime demo..."
	cd apps/adjudicator && python -m truce_adjudicator.scripts.seed
	@echo "✅ Demo data loaded!"
	@echo "   Claim Card: http://localhost:3000/claim/violent-crime-canada"
	@echo "   Consensus Board: http://localhost:3000/consensus/canada-crime"

panel: ## Run model panel evaluation on existing claims
	@echo "🤖 Running model panel evaluation..."
	@echo "Panel evaluation available via API - use 'make seed' first to create demo data"

consensus: ## Seed additional consensus statements
	@echo "💭 Adding consensus statements..."
	@echo "Additional consensus statements can be added via API - see documentation"

sign: ## Create verifiable credential for claims
	@echo "🔐 Creating verifiable credentials..."
	@echo "VC signing functionality available but requires keys - see documentation"

publish: ## Create static site with replay bundles
	@echo "📦 Creating publication bundle..."
	@echo "Replay bundles available via API - see /replay/{claim_id}.jsonl endpoint"

dev: ## Start development environment
	docker-compose up --build

logs: ## Show logs from all services
	docker-compose logs -f

logs-web: ## Show web service logs
	docker-compose logs -f web

logs-api: ## Show adjudicator API logs  
	docker-compose logs -f adjudicator

test: ## Run tests
	cd apps/adjudicator && python -m pytest tests/
	cd apps/web && npm test

clean: ## Clean up Docker resources
	docker-compose down -v
	docker system prune -f

install: ## Install dependencies locally (for development)
	cd apps/web && npm install
	cd apps/adjudicator && pip install -e .

format: ## Format code
	cd apps/adjudicator && black . && isort .
	cd apps/web && npm run lint

demo: build up seed ## Full demo setup (build + up + seed)
	@echo ""
	@echo "🎉 Truce demo is ready!"
	@echo "   Claim Card: http://localhost:3000/claim/violent-crime-canada"  
	@echo "   Consensus Board: http://localhost:3000/consensus/canada-crime"
	@echo "   API: http://localhost:8000"
	@echo ""
	@echo "Next steps:"
	@echo "  - View the claim evaluation and evidence"
	@echo "  - Vote on consensus statements"
	@echo "  - Download replay bundle for reproducibility"
