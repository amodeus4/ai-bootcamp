.PHONY: install run setup help streamlit monitoring clean

help:
	@echo "Email Agent - Available Commands:"
	@echo ""
	@echo "  make install     - Install dependencies with uv"
	@echo "  make setup       - Initialize .env file from .env.example"
	@echo "  make run         - Run the email agent (CLI mode)"
	@echo "  make streamlit   - Run the Streamlit web app"
	@echo "  make monitoring  - Run the monitoring dashboard"
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

streamlit:
	uv run streamlit run streamlit_app.py --server.port 8501

monitoring:
	uv run streamlit run monitoring_app.py --server.port 8502

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	rm -rf .cache/ 2>/dev/null || true
	rm -f email_agent_monitoring.db 2>/dev/null || true
