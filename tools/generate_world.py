#!/usr/bin/env python3
"""Generate worlds/office.sdf: a 12 x 10 m two-room 'office' with doorways and obstacles.

Usage: python3 tools/generate_world.py > src/robot_gazebo/worlds/office.sdf
"""

WALL_H, WALL_T = 1.0, 0.2


def wall(name, cx, cy, length, horizontal=True):
    sx, sy = (length, WALL_T) if horizontal else (WALL_T, length)
    return box(name, cx, cy, sx, sy, WALL_H, (0.75, 0.75, 0.75))


def box(name, cx, cy, sx, sy, sz, rgb):
    r, g, b = rgb
    return f"""
    <model name="{name}">
      <static>true</static>
      <pose>{cx} {cy} {sz/2} 0 0 0</pose>
      <link name="link">
        <collision name="c"><geometry><box><size>{sx} {sy} {sz}</size></box></geometry></collision>
        <visual name="v">
          <geometry><box><size>{sx} {sy} {sz}</size></box></geometry>
          <material><ambient>{r} {g} {b} 1</ambient><diffuse>{r} {g} {b} 1</diffuse></material>
        </visual>
      </link>
    </model>"""


def cylinder(name, cx, cy, radius, height, rgb):
    r, g, b = rgb
    return f"""
    <model name="{name}">
      <static>true</static>
      <pose>{cx} {cy} {height/2} 0 0 0</pose>
      <link name="link">
        <collision name="c"><geometry><cylinder><radius>{radius}</radius><length>{height}</length></cylinder></geometry></collision>
        <visual name="v">
          <geometry><cylinder><radius>{radius}</radius><length>{height}</length></cylinder></geometry>
          <material><ambient>{r} {g} {b} 1</ambient><diffuse>{r} {g} {b} 1</diffuse></material>
        </visual>
      </link>
    </model>"""


models = [
    # Outer walls: x in [-6, 6], y in [-5, 5]
    wall("wall_north", 0, 5, 12.2), wall("wall_south", 0, -5, 12.2),
    wall("wall_east", 6, 0, 10.2, False), wall("wall_west", -6, 0, 10.2, False),
    # Central partition at x = 0 with a 2 m doorway between y = 0.5 and y = 2.5
    wall("partition_a", 0, -2.25, 5.5, False),   # y from -5 to 0.5
    wall("partition_b", 0, 3.75, 5.0, False),    # wait: see below
]
# Correct partition_b: covers y from 2.5 to 5 -> length 2.5, centre 3.75
models[-1] = wall("partition_b", 0, 3.75, 2.5, False)
models += [
    # Side wall in the east room with a 1.5 m gap between x = 4.5 and x = 6
    wall("side_wall", 3.25, -1.5, 2.5),
    # Obstacles
    box("box_1", -3, 1, 0.6, 0.6, 0.6, (0.8, 0.3, 0.2)),
    cylinder("cyl_1", -2, -3, 0.3, 0.8, (0.2, 0.6, 0.3)),
    box("box_2", 3, 3, 0.5, 1.0, 0.6, (0.8, 0.3, 0.2)),
    cylinder("cyl_2", 4, -3.5, 0.25, 0.8, (0.2, 0.6, 0.3)),
]

print(f"""<?xml version="1.0"?>
<sdf version="1.9">
  <world name="office">
    <physics name="1ms" type="ignored">
      <max_step_size>0.001</max_step_size>
      <real_time_factor>1.0</real_time_factor>
    </physics>

    <plugin filename="gz-sim-physics-system" name="gz::sim::systems::Physics"/>
    <plugin filename="gz-sim-user-commands-system" name="gz::sim::systems::UserCommands"/>
    <plugin filename="gz-sim-scene-broadcaster-system" name="gz::sim::systems::SceneBroadcaster"/>
    <plugin filename="gz-sim-sensors-system" name="gz::sim::systems::Sensors">
      <render_engine>ogre2</render_engine>
    </plugin>

    <light type="directional" name="sun">
      <cast_shadows>true</cast_shadows>
      <pose>0 0 10 0 0 0</pose>
      <diffuse>0.9 0.9 0.9 1</diffuse>
      <specular>0.2 0.2 0.2 1</specular>
      <direction>-0.5 0.1 -0.9</direction>
    </light>

    <model name="ground_plane">
      <static>true</static>
      <link name="link">
        <collision name="c">
          <geometry><plane><normal>0 0 1</normal><size>40 40</size></plane></geometry>
        </collision>
        <visual name="v">
          <geometry><plane><normal>0 0 1</normal><size>40 40</size></plane></geometry>
          <material><ambient>0.5 0.5 0.5 1</ambient><diffuse>0.5 0.5 0.5 1</diffuse></material>
        </visual>
      </link>
    </model>
{''.join(models)}
  </world>
</sdf>""")
