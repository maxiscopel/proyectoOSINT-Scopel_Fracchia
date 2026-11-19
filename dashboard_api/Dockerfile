FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 NLTK_DATA=/opt/nltk_data PIPELINE_DIR=/pipeline
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && python -c "import nltk; nltk.download('vader_lexicon', download_dir='/opt/nltk_data')"

COPY *.py ./
# Los scripts del pipeline (osint_pipeline.py) se montan en /pipeline (solo lectura)
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
