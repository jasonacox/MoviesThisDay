#!/bin/bash

# Listen on this port
PORT=8080
VERSION=0.1.14
PKL_ZIP_URL="https://moviesthisday.s3.us-east-1.amazonaws.com/movies_by_day.pkl.zip"
MOVIE_DB_DIR="$(pwd)/movie_db"

# Download movies_by_day.pkl
echo "Downloading movies_by_day.pkl..."
mkdir -p "$MOVIE_DB_DIR"
curl -fL "$PKL_ZIP_URL" -o "$MOVIE_DB_DIR/movies_by_day.pkl.zip" || { echo "Download failed."; exit 1; }
unzip -o "$MOVIE_DB_DIR/movies_by_day.pkl.zip" -d "$MOVIE_DB_DIR" || { echo "Extraction failed."; exit 1; }
rm -f "$MOVIE_DB_DIR/movies_by_day.pkl.zip"
echo "Download complete."

# Remove any existing container with the same name
if [ "$(docker ps -aq -f name=moviesthisday)" ]; then
    docker rm -f moviesthisday
fi

# Run MoviesThisDay Container with healthcheck
echo "Starting MoviesThisDay Container..."
docker run -d \
  --name moviesthisday \
  -p $PORT:8000 \
  --restart unless-stopped \
  --health-cmd="wget --spider -q http://127.0.0.1:8000/ping || exit 1" \
  --health-interval=30s \
  --health-timeout=10s \
  --health-retries=3 \
  -e TZ=America/Los_Angeles \
  --log-opt max-size=10m \
  --log-opt max-file=3 \
  -v "$MOVIE_DB_DIR:/app/movie_db" \
  jasonacox/moviesthisday:$VERSION

# Check if the container is running
if [ "$(docker ps -q -f name=moviesthisday)" ]; then
    echo "Running."
    # Show logs
    echo "Displaying logs for the container (^C to exit):"
    echo ""
    docker logs moviesthisday -f
else
    echo "Failed to start the container."
fi
