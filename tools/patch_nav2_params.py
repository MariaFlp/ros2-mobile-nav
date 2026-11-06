#!/usr/bin/env python3
"""Adapt Nav2's stock nav2_params.yaml (whatever version is installed) to this robot.

Why a patch script instead of a hand-written file: it always matches the installed Nav2 version,
changes only keys that exist, and prints exactly what it changed (documented tuning).

Usage:
  cp /opt/ros/jazzy/share/nav2_bringup/params/nav2_params.yaml src/robot_navigation/config/nav2_params.yaml
  python3 tools/patch_nav2_params.py src/robot_navigation/config/nav2_params.yaml
"""
import sys
import yaml

# ---- Robot-specific values ----
BASE_FRAME = 'base_footprint'
ROBOT_RADIUS = 0.25          # chassis 0.40 x 0.25 m -> circumscribed radius ~0.24 m
MAX_LIN = 0.4                # m/s
MAX_ANG = 1.0                # rad/s
LIN_ACC = 1.0
ANG_ACC = 2.0
LIDAR_MAX_RANGE = 12.0
# slam_toolbox's map frame originates at the robot pose when SLAM started (= spawn pose).
INITIAL_POSE = {'x': 0.0, 'y': 0.0, 'z': 0.0, 'yaw': 0.0}

path = sys.argv[1]
cfg = yaml.safe_load(open(path))
changed, skipped = [], []


def params(*names):
    node = cfg
    for n in names:
        if not isinstance(node, dict) or n not in node:
            return None
        node = node[n]
    return node.get('ros__parameters') if isinstance(node, dict) else None


def setp(label, d, key, value, add_if_missing=False):
    if d is None:
        skipped.append(f'{label}.{key}')
        return
    if key not in d:
        if add_if_missing:
            changed.append(f'{label}.{key}: (absent) -> {value!r}  [added]')
            d[key] = value
        else:
            skipped.append(f'{label}.{key}')
        return
    if d[key] != value:
        changed.append(f'{label}.{key}: {d[key]!r} -> {value!r}')
        d[key] = value


# 1) Any base_link frame reference becomes base_footprint
def walk(node, trail):
    if isinstance(node, dict):
        for k, v in node.items():
            if k in ('robot_base_frame', 'base_frame_id', 'base_frame') and v == 'base_link':
                changed.append(f"{'.'.join(trail + [k])}: 'base_link' -> {BASE_FRAME!r}")
                node[k] = BASE_FRAME
            else:
                walk(v, trail + [k])
    elif isinstance(node, list):
        for i, v in enumerate(node):
            walk(v, trail + [str(i)])


walk(cfg, [])

# 2) AMCL
amcl = params('amcl')
# The stock file ships these two commented out, so they are added when absent.
setp('amcl', amcl, 'set_initial_pose', True, add_if_missing=True)
setp('amcl', amcl, 'scan_topic', 'scan')
setp('amcl', amcl, 'laser_max_range', LIDAR_MAX_RANGE)
if amcl is not None:
    if not isinstance(amcl.get('initial_pose'), dict):
        amcl['initial_pose'] = {}
        changed.append('amcl.initial_pose: (absent) -> block added')
    for k, v in INITIAL_POSE.items():
        setp('amcl.initial_pose', amcl['initial_pose'], k, v, add_if_missing=True)

# 3) Costmaps: footprint as a circle
for name in ('local_costmap', 'global_costmap'):
    setp(name, params(name, name), 'robot_radius', ROBOT_RADIUS)

# 4) Controller speed limits (works for DWB- and MPPI-style parameter names)
ctrl = params('controller_server')
fp = ctrl.get('FollowPath') if ctrl else None
if isinstance(fp, dict):
    for key, val in {
        'max_vel_x': MAX_LIN, 'max_speed_xy': MAX_LIN, 'max_vel_theta': MAX_ANG,
        'acc_lim_x': LIN_ACC, 'acc_lim_theta': ANG_ACC,
        'decel_lim_x': -LIN_ACC, 'decel_lim_theta': -ANG_ACC,
        'vx_max': MAX_LIN, 'wz_max': MAX_ANG,
    }.items():
        if key in fp:
            setp('controller_server.FollowPath', fp, key, val)
else:
    skipped.append('controller_server.FollowPath')

# 5) Velocity smoother (x, y, theta)
vs = params('velocity_smoother')
setp('velocity_smoother', vs, 'max_velocity', [MAX_LIN, 0.0, MAX_ANG])
setp('velocity_smoother', vs, 'min_velocity', [-MAX_LIN, 0.0, -MAX_ANG])
setp('velocity_smoother', vs, 'max_accel', [LIN_ACC, 0.0, ANG_ACC])
setp('velocity_smoother', vs, 'max_decel', [-LIN_ACC, 0.0, -ANG_ACC])

header = ('# Generated from the stock nav2_bringup nav2_params.yaml by tools/patch_nav2_params.py.\n'
          '# Edit values there (or here, then document why) rather than silently drifting.\n')
with open(path, 'w') as f:
    f.write(header)
    yaml.safe_dump(cfg, f, sort_keys=False, default_flow_style=False)

print(f'Patched {path}\n\nChanged ({len(changed)}):')
for c in changed:
    print('  +', c)
print(f'\nNot present in this Nav2 version, skipped ({len(skipped)}):')
for s in skipped:
    print('  -', s)
