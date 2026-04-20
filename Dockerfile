FROM python:3.11-slim

WORKDIR /app

# Projeto usa apenas biblioteca padrão para os testes.
COPY . /app

CMD ["python", "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py", "-v"]
