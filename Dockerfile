FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    wget \
    unzip \
    libnss3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    libxshmfence1 \
    libglib2.0-0 \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && playwright install chromium \
    && playwright install-deps chromium

RUN python -c "\
import os, urllib.request, zipfile; \
url = 'https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip'; \
zip_path = '/app/vosk-model.zip'; \
urllib.request.urlretrieve(url, zip_path); \
zf = zipfile.ZipFile(zip_path, 'r'); \
extracted = zf.namelist()[0].split('/')[0]; \
zf.extractall('/app'); \
zf.close(); \
os.rename(f'/app/{extracted}', '/app/vosk-model'); \
os.remove(zip_path); \
print('Vosk model installed')"

COPY captcha_solver.py api_client.py data_exporter.py BusinessSearchScraper.py main.py ./

VOLUME /app/output

ENTRYPOINT ["python", "main.py"]
CMD ["tech"]
