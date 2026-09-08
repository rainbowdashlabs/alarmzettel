# Stage 1: frontend dependencies, cached until package.json changes
FROM node:24-alpine AS frontend-deps
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

# Stage 2: build the frontend
FROM frontend-deps AS frontend-build
COPY frontend/ ./
RUN npm run build

# Stage 3: the renderer. typst ships a static binary, so it is fetched once and copied in.
FROM debian:trixie-slim AS typst
ARG TYPST_VERSION=v0.14.2
ARG TARGETARCH=amd64
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates curl xz-utils \
 && rm -rf /var/lib/apt/lists/*
RUN case "$TARGETARCH" in \
      amd64) ZIEL=x86_64-unknown-linux-musl ;; \
      arm64) ZIEL=aarch64-unknown-linux-musl ;; \
      *) echo "nicht unterstützte Architektur: $TARGETARCH" >&2; exit 1 ;; \
    esac \
 && curl -fsSL "https://github.com/typst/typst/releases/download/${TYPST_VERSION}/typst-${ZIEL}.tar.xz" \
    | tar -xJ --strip-components=1 -C /usr/local/bin "typst-${ZIEL}/typst" \
 && typst --version

# Stage 4: everything the app needs to run except the app itself. The dev compose file stops
# here and mounts the sources, so it gets the same python and the same typst.
FROM python:3.14-slim AS runtime
WORKDIR /app
COPY --from=typst /usr/local/bin/typst /usr/local/bin/typst
RUN pip install --no-cache-dir pipenv
COPY backend/Pipfile backend/Pipfile.lock ./
RUN pipenv sync --system && pip uninstall -y pipenv

# Stage 5: the image that runs
FROM runtime AS production
LABEL org.opencontainers.image.title="Alarmzettel" \
      org.opencontainers.image.description="Berlin fire brigade alarm slips, rendered with Typst" \
      org.opencontainers.image.source="https://github.com/rainbowdashlabs/alarmzettel" \
      org.opencontainers.image.licenses="AGPL-3.0-or-later"
WORKDIR /app

COPY backend/src/ ./src/
COPY --from=frontend-build /app/dist ./static/

# The fonts travel with the image, so a render never depends on what the host has installed.
# /data is where shared working sets and the downloaded address list live, and is the only thing
# that outlives the container. The address list is fetched on first start, not shipped.
ENV FREIGABE_VERZEICHNIS=/data/freigaben \
    ADRESSEN_DATEI=/data/adressen.sqlite
RUN mkdir -p src/render/tmp /data/freigaben && chmod 1777 src/render/tmp \
 && useradd --system --uid 10001 alarmzettel \
 && chown -R alarmzettel:alarmzettel /app /data
USER alarmzettel
VOLUME ["/data"]

EXPOSE 8000
# --proxy-headers so the share link is built with the scheme and host the client actually used;
# without it a deployment behind TLS hands out http:// links to itself.
CMD ["uvicorn", "--app-dir", "src", "main:app", "--host", "0.0.0.0", "--port", "8000", \
     "--proxy-headers", "--forwarded-allow-ips", "*"]

HEALTHCHECK --start-period=10s --interval=30s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')" || exit 1
