.PHONY: test frontend verify lint format install-hooks

test:
	./run_all_tests.sh

frontend:
	./run_all_frontend_checks.sh

verify: test frontend
	cd .. && python3 tools/verify_portfolio.py

lint:
	flake8 . --max-line-length=120

format:
	black .

install-hooks:
	pip install pre-commit black flake8
	pre-commit install
