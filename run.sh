#!/usr/bin/env bash
# Start the dev container with GUI (Gazebo / RViz2) support.
# Usage: ./run.sh            (build the image first: docker build -t ros2-nav:jazzy .)
set -e
xhost +local:docker >/dev/null
docker run -it --rm --net=host --ipc=host --device /dev/dri \
  -e DISPLAY="$DISPLAY" -v /tmp/.X11-unix:/tmp/.X11-unix \
  -v "$PWD":/ws -w /ws -u "$(id -u):$(id -g)" \
  ros2-nav:jazzy bash
