#!/bin/bash

USERNAME=mrgreen1337

set -e  # exit on any command failure

echo "Building linux/amd64 images in parallel..."

# Start builds in background and capture PIDs directly
docker build --platform=linux/amd64 -t $USERNAME/alloy-web:latest ./web &
web_pid=$!

docker build --platform=linux/amd64 -t $USERNAME/alloy-backend:latest ./backend &
backend_pid=$!

# Store PIDs in array
build_pids=($web_pid $backend_pid)

# Wait for builds and check status
for pid in "${build_pids[@]}"; do
  if ! wait "$pid"; then
    echo "Build failed for PID $pid"
    exit 1
  fi
done

echo "Building finished successfully."

echo "Pushing images to Docker Hub in parallel..."

# Start pushes in background and capture PIDs directly
docker push $USERNAME/alloy-web:latest &
web_push_pid=$!

docker push $USERNAME/alloy-backend:latest &
backend_push_pid=$!

# Store PIDs in array
push_pids=($web_push_pid $backend_push_pid)

# Wait for pushes and check status
for pid in "${push_pids[@]}"; do
  if ! wait "$pid"; then
    echo "Push failed for PID $pid"
    exit 1
  fi
done

echo "All images pushed successfully."

docker build --platform=linux/amd64 \
  --build-arg NEXT_PUBLIC_API_URL="https://alloy-backend-527185366316.europe-west1.run.app" \    
  -t mrgreen1337/alloy-web:latest \
  ./web \
  --no-cache