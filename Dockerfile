# Use Playwright base to include Chromium deps
FROM mcr.microsoft.com/playwright/python:v1.47.0-jammy

WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt \
    && python -m playwright install --with-deps chromium

COPY . .

EXPOSE 8080
CMD ["uvicorn", "src.iva.server:app", "--host", "0.0.0.0", "--port", "8080"]
