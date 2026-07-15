# Dockerfile optimisé pour Railway
FROM python:3.11-slim

WORKDIR /app

# Installer les dépendances
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copier le code source
COPY . .

# Railway injecte automatiquement la variable PORT
CMD ["python", "-u", "services/process_supervisor.py"]
