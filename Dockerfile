# Étape 1 : Construction des dépendances et du package
FROM python:3.11-slim as builder

WORKDIR /app

# Installe les outils de compilation nécessaires  
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 1. Copie les fichiers de configuration
COPY pyproject.toml README.md .

# 2. Copie le code source AVANT l'installation  
COPY src/ ./src/

# Crée et active l'environnement virtuel
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Installe le projet 
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

# Étape 2 : Image finale légère et sécurisée
FROM python:3.11-slim

WORKDIR /app

# Crée un utilisateur non-root pour la sécurité  
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Copie l'environnement virtuel complet  
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Crée le dossier de données et donne les permissions
RUN mkdir -p /app/data && chown -R appuser:appuser /app

# Passe à l'utilisateur non-root
USER appuser

# Expose le port
EXPOSE 8000

# Commande de démarrage avec le port dynamique de Render
CMD uvicorn cloudtrim.api.app:app --host 0.0.0.0 --port ${PORT:-8000}