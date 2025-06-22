#!/bin/bash

# Listen on this port
PORT=8000

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
  --health-cmd="curl -f http://localhost:$PORT/ping || exit 1" \
  --health-interval=30s \
  --health-timeout=10s \
  --health-retries=3 \
  -e TZ=America/Los_Angeles \
  --log-opt max-size=10m \
  --log-opt max-file=3 \
  jasonacox/moviesthisday:latest

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
