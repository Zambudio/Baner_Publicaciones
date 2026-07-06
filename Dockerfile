# Imagen oficial con Chromium y todas las dependencias de sistema ya resueltas
# para linux/amd64 (compatible con Synology DS224+, Container Manager).
FROM mcr.microsoft.com/playwright/python:v1.48.0-jammy

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY banner_engine/ banner_engine/
COPY templates/ templates/
COPY static/ static/

RUN mkdir -p /app/output /app/examples

ENTRYPOINT ["python", "-m", "banner_engine.cli"]
CMD ["examples/offer_data.json", "output/offer_banner.png"]
