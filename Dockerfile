FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app app
COPY data data
COPY static static
RUN useradd --create-home appuser && mkdir /state && chown appuser /state
USER appuser
ENV DATABASE_PATH=/state/fielddesk.db
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
