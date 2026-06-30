# Stage 1: Compilación de dependencias
FROM python:3.12-slim AS builder

WORKDIR /build

# Instalar herramientas básicas de compilación
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Compilar wheels de python en un directorio temporal para celeridad y tamaño
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Stage 2: Runtime de producción de alta seguridad
FROM python:3.12-slim AS runner

WORKDIR /app

# Instalar librerías runtime necesarias (como libpq para PostgreSQL)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copiar dependencias pre-instaladas del builder
COPY --from=builder /install /usr/local

# Copiar el código del proyecto
COPY . .

# Principio de Privilegio Mínimo: Ejecutar la intranet bajo un usuario no-root por ciberseguridad
RUN groupadd -g 10001 intranetgroup && \
    useradd -u 10000 -g intranetgroup -s /bin/sh intranetuser && \
    chown -R intranetuser:intranetgroup /app

USER intranetuser

EXPOSE 8000

ENV PORT=8000
ENV PYTHONUNBUFFERED=1

CMD ["python", "run.py"]
