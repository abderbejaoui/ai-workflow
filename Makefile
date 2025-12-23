.PHONY: help install test validate run interactive clean docs

help:
	@echo "AI Workflow Orchestrator - Available Commands"
	@echo "=============================================="
	@echo ""
	@echo "Setup:"
	@echo "  make install      Install dependencies"
	@echo "  make setup        Copy environment template"
	@echo ""
	@echo "Testing:"
	@echo "  make test         Run example tests"
	@echo "  make validate     Run validation suite"
	@echo ""
	@echo "Running:"
	@echo "  make run          Single query with mock data"
	@echo "  make interactive  Interactive mode with mock data"
	@echo "  make demo         Run demo queries"
	@echo ""
	@echo "Utilities:"
	@echo "  make visualize    Show workflow structure"
	@echo "  make clean        Remove cache files"
	@echo "  make docs         Open documentation"
	@echo ""

install:
	@echo "Installing dependencies..."
	pip install -r requirements.txt
	@echo "✓ Dependencies installed"

setup:
	@echo "Setting up environment..."
	@if [ ! -f .env ]; then \
		cp env.template .env; \
		echo "✓ Created .env file - please add your API keys"; \
	else \
		echo "⚠ .env already exists - skipping"; \
	fi

test:
	@echo "Running example tests..."
	python examples.py

validate:
	@echo "Running validation suite..."
	python validate.py

run:
	@echo "Running single query with mock data..."
	python main.py --mock --query "Show me all customers"

interactive:
	@echo "Starting interactive mode..."
	python main.py --mock --interactive

demo:
	@echo "Running demo queries..."
	@echo ""
	@echo "1. Conversation query:"
	python main.py --mock --query "Hello!"
	@echo ""
	@echo "2. Data query:"
	python main.py --mock --query "Show me all customers"
	@echo ""
	@echo "3. Ambiguous query:"
	python main.py --mock --query "Show me that thing"

visualize:
	@echo "Workflow structure:"
	python visualize.py

clean:
	@echo "Cleaning cache files..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@echo "✓ Cache cleaned"

docs:
	@echo "Documentation files:"
	@echo "  - README.md           : User guide"
	@echo "  - QUICKSTART.md       : Quick start guide"
	@echo "  - ARCHITECTURE.md     : Technical documentation"
	@echo "  - PROJECTSUMMARY.md   : Project summary"
	@echo ""
	@echo "Opening README.md..."
	@if command -v open > /dev/null; then \
		open README.md; \
	elif command -v xdg-open > /dev/null; then \
		xdg-open README.md; \
	else \
		cat README.md; \
	fi

# Quick start for new users
quickstart: setup install
	@echo ""
	@echo "================================================"
	@echo "Quick Start Complete!"
	@echo "================================================"
	@echo ""
	@echo "Next steps:"
	@echo "  1. Add your OPENAI_API_KEY to .env file"
	@echo "  2. Run: make interactive"
	@echo ""
	@echo "Or read: QUICKSTART.md for detailed instructions"
	@echo ""

