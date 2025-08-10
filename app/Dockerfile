FROM python:3.11-slim

# Keep project root one level above the package folder so `app.main` is importable
WORKDIR /usr/src

# Install dependencies first for better layer caching
COPY ./requirements.txt /usr/src/requirements.txt
RUN pip install --no-cache-dir -r /usr/src/requirements.txt

# Copy source under /usr/src/app so module path is `app.*`
COPY . /usr/src/app

EXPOSE 8000
# Default CMD (overridden by docker-compose) — keep consistent with module path
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
