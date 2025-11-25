.PHONY: install run setup help

help:
	@echo "Email Agent - Available Commands:"
	@echo ""
	@echo "  make install     - Install dependencies with uv"
	@echo "  make setup       - Initialize .env file from .env.example"
	@echo "  make run         - Run the email agent"
	@echo "  make clean       - Clean cache and __pycache__ files"
	@echo ""

install:
	uv sync

setup:
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "✓ Created .env file from .env.example"; \
		echo "⚠️  Please update .env with your configuration"; \
	else \
		echo "ℹ️  .env already exists"; \
	fi

run:
	uv run main.py

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	rm -rf .cache/ 2>/dev/null || true
