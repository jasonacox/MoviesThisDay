# Dockerfile for MoviesThisDay
FROM python:3.10-alpine

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Copy requirements and install
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt


# Copy application code
COPY app.py ./
COPY templates/ ./templates/
COPY static/ ./static/
COPY logging.conf ./

# Copy database archive (if missing, will be downloaded at runtime)
# COPY movie_db/movies_by_day.pkl.zip ./movie_db/movies_by_day.pkl.zip

# Expose port
EXPOSE 8000

# Create mount point for movie_db (for persistent data)
VOLUME ["/app/movie_db"]

# Download data if missing (handled by app.py at runtime)

# Start the FastAPI app with uvicorn
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--log-config", "logging.conf"]

# To build the Docker image, run:
# docker build -t moviesthisday .

# To run the Docker container, use:
# docker run -d -p 8000:8000 --name moviesthisday moviesthisday
