# 1. Use an official, stable, and lightweight Python runtime
FROM python:3.12-slim

# 2. Set the working directory inside the container
WORKDIR /code

# 3. Install system dependencies required for building certain Python packages
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 4. Copy requirements file and install dependencies
COPY ./requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /code/requirements.txt

# 5. Copy the rest of the application code into the container
COPY . /code

# 6. Create the ChromaDB directory and grant full read/write permissions
RUN mkdir -p /code/chroma_db && chmod -R 777 /code

# 7. Expose and run the FastAPI app on port 7860 (Hugging Face default port)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]