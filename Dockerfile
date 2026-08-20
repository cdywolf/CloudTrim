# Étape 1 : Build des dépendances
FROM python:3.11-slim as builder

WORKDIR /app

# Installe les outils de build
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copie les fichiers de dépendances
COPY pyproject.toml .

# Installe les dépendances dans un dossier virtuel
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

# Étape 2 : Image finale légère
FROM python:3.11-slim

WORKDIR /app

# Crée un utilisateur non-root pour la sécurité
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Copie l'environnement virtuel depuis le builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copie le code source (cela inclut DÉJÀ les dossiers templates et static)
COPY src/ ./src/

# Crée le dossier data et donne les permissions à l'utilisateur non-root
RUN mkdir -p /app/data && chown -R appuser:appuser /app

# Change vers l'utilisateur non-root
USER appuser

# Expose le port
EXPOSE 8000

# Commande de démarrage
CMD ["uvicorn", "cloudtrim.api.app:app", "--host", "0.0.0.0", "--port", "8000"]