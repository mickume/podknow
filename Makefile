# PodKnow Development Makefile

.PHONY: help install install-uv install-dev test lint format clean verify-deps check-platform

# Default target
help:
	@echo "PodKnow Development Commands"
	@echo ""
	@echo "Installation:"
	@echo "  install      Install PodKnow with pip"
	@echo "  install-uv   Install PodKnow with uv (faster)"
	@echo "  install-dev  Install in development mode"
	@echo ""
	@echo "Development:"
	@echo "  test         Run all tests"
	@echo "  lint         Run linting checks"
	@echo "  format       Format code with black and ruff"
	@echo "  clean        Clean build artifacts"
	@echo ""
	@echo "Platform:"
	@echo "  check-platform    Check platform and dependencies"
	@echo "  verify-deps       Verify all dependencies are installed"

# Installation targets
install:
	@echo "Installing PodKnow with pip..."
	python scripts/install.py

install-uv:
	@echo "Installing PodKnow with uv..."
	python scripts/install.py --uv

install-dev:
	@echo "Installing PodKnow in development mode..."
	pip install -e ".[dev]"

# Development targets
test:
	@echo "Running tests..."
	pytest tests/ -v --cov=podknow --cov-report=term-missing

lint:
	@echo "Running linting checks..."
	ruff check podknow/ tests/
	mypy podknow/

format:
	@echo "Formatting code..."
	black podknow/ tests/
	ruff check --fix podknow/ tests/

clean:
	@echo "Cleaning build artifacts..."
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# Platform and dependency checks
check-platform:
	@echo "Platform Information:"
	@python -c "import platform; print(f'System: {platform.system()}'); print(f'Machine: {platform.machine()}'); print(f'Python: {platform.python_version()}')"
	@echo ""
	@echo "Checking for Apple Silicon optimizations..."
	@python -c "import platform; print('Apple Silicon detected' if platform.system() == 'Darwin' and platform.machine() == 'arm64' else 'Standard platform')"

verify-deps:
	@echo "Verifying dependencies..."
	@python -c "import click; print('✓ Click available')"
	@python -c "import requests; print('✓ Requests available')"
	@python -c "import feedparser; print('✓ Feedparser available')"
	@python -c "import pydantic; print('✓ Pydantic available')"
	@python -c "import anthropic; print('✓ Anthropic available')"
	@echo "Checking audio processing dependencies..."
	@python -c "import librosa; print('✓ Librosa available')" || echo "✗ Librosa not available"
	@python -c "import platform; import sys; \
		if platform.system() == 'Darwin' and platform.machine() == 'arm64': \
			exec('try:\n    import mlx_whisper\n    print(\"✓ MLX-Whisper available\")\nexcept ImportError:\n    print(\"✗ MLX-Whisper not available\")'); \
		else: \
			exec('try:\n    import whisper\n    print(\"✓ OpenAI Whisper available\")\nexcept ImportError:\n    print(\"✗ OpenAI Whisper not available\")')"