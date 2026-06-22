FROM python:3.12-slim
# slim reduces image size by excluding many unnecessary system tools

# stops Python from egenrating .pyc cbytecode cached files and __pycache__ directories. Keep Docker container cleaner
ENV PYTHONDONTWRITEBYTECODE=1
# send output directly to teh terminal; logs appear immediately
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# --no-cache-dir prevents pip from keeping downloaded installation files, reducing teh final Docker image size

COPY . .
# copies teh resty of your project into /app
# first . means teh local project directory. Teh second . means /app inside teh image

CMD ["sh", "-c", "alembic upgrade head && uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
# updates the db schema to teh newest Alembic migration
# start fast api



# RUN: runs once while building teh Docker image
# CMD: runs whenever a container is started from that image