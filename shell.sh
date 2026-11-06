#!/usr/bin/env bash
# Open an extra terminal inside the already-running container (started with ./run.sh).
docker exec -it -e DISPLAY="$DISPLAY" ros2-nav bash -c \
  'source /opt/ros/jazzy/setup.bash; source /ws/install/setup.bash 2>/dev/null; exec bash'
