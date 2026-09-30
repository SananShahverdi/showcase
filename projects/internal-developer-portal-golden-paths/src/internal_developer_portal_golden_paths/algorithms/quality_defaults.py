class QualityDefaults:
    @staticmethod
    def get_dockerfile(lang: str, command: str | None = None) -> str:
        if lang == "python":
            run = command or '["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]'
            return f"""FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN addgroup --system app && adduser --system --ingroup app app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY --chown=app:app . .
USER app
CMD {run}
"""
        if lang == "node":
            return """FROM node:22-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install --omit=dev
COPY --chown=node:node . .
USER node
CMD ["npm", "start"]
"""
        return ""

    @staticmethod
    def get_docker_compose(service_name: str, port: str | None = None) -> str:
        ports = f'\n    ports:\n      - "{port}:{port}"' if port else ""
        return f"""services:
  {service_name}:
    build: .{ports}
    environment:
      OTEL_SERVICE_NAME: {service_name}
"""

    @staticmethod
    def get_ci_config(lang: str) -> str:
        setup = """      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install -r requirements.txt
      - run: python -m compileall .
      - run: pytest -q
""" if lang == "python" else """      - uses: actions/setup-node@v4
        with:
          node-version: '22'
      - run: npm install
      - run: npm test
"""
        return f"""name: CI
on:
  pull_request:
  push:
    branches: [main]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
{setup}"""

    @staticmethod
    def metadata(name: str, owner: str, component_type: str) -> str:
        return f"""apiVersion: backstage.io/v1alpha1
kind: Component
metadata:
  name: {name}
spec:
  type: {component_type}
  lifecycle: experimental
  owner: {owner}
"""
