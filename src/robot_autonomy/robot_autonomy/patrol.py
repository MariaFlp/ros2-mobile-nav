#!/usr/bin/env python3
"""Drive the robot through a list of map-frame waypoints using Nav2, and log each goal.

  ros2 run robot_autonomy patrol --ros-args -p use_sim_time:=true
  ros2 run robot_autonomy patrol --loops 3 --log results/patrol_log.csv --ros-args -p use_sim_time:=true

Requires the simulation and `ros2 launch robot_navigation navigation.launch.py` to be running.
"""
import argparse
import csv
import math
import os
import sys

import rclpy
import yaml
from ament_index_python.packages import get_package_share_directory
from geometry_msgs.msg import PoseStamped
from nav2_simple_commander.robot_navigator import BasicNavigator, TaskResult
from rclpy.utilities import remove_ros_args

GOAL_TIMEOUT_S = 120.0


def yaw_to_quaternion(yaw):
    """Return (z, w) of a yaw-only quaternion."""
    return math.sin(yaw / 2.0), math.cos(yaw / 2.0)


def make_pose(navigator, x, y, yaw):
    pose = PoseStamped()
    pose.header.frame_id = 'map'
    pose.header.stamp = navigator.get_clock().now().to_msg()
    pose.pose.position.x = float(x)
    pose.pose.position.y = float(y)
    pose.pose.orientation.z, pose.pose.orientation.w = yaw_to_quaternion(float(yaw))
    return pose


def parse_args(argv):
    default_wp = os.path.join(
        get_package_share_directory('robot_autonomy'), 'config', 'waypoints.yaml')
    p = argparse.ArgumentParser(description='Nav2 waypoint patrol')
    p.add_argument('--waypoints', default=default_wp, help='YAML file with a waypoints list')
    p.add_argument('--loops', type=int, default=1, help='how many times to run the route')
    p.add_argument('--log', default='results/patrol_log.csv', help='CSV file for per-goal results')
    return p.parse_args(remove_ros_args(argv)[1:])


def go_to(navigator, name, pose):
    """Send one goal, wait for it, return (result, duration_s, recoveries)."""
    start = navigator.get_clock().now()
    navigator.goToPose(pose)
    recoveries = 0
    last_print = start
    while not navigator.isTaskComplete():
        feedback = navigator.getFeedback()
        now = navigator.get_clock().now()
        elapsed = (now - start).nanoseconds / 1e9
        if feedback:
            recoveries = max(recoveries, feedback.number_of_recoveries)
            if (now - last_print).nanoseconds / 1e9 >= 2.0:
                print(f'  [{name}] {feedback.distance_remaining:.2f} m remaining, '
                      f'{elapsed:.0f} s elapsed')
                last_print = now
        if elapsed > GOAL_TIMEOUT_S:
            print(f'  [{name}] timeout after {GOAL_TIMEOUT_S:.0f} s, cancelling')
            navigator.cancelTask()
    duration = (navigator.get_clock().now() - start).nanoseconds / 1e9
    return navigator.getResult(), duration, recoveries


def main(argv=None):
    argv = sys.argv if argv is None else argv
    args = parse_args(argv)

    with open(args.waypoints) as f:
        waypoints = yaml.safe_load(f)['waypoints']

    rclpy.init(args=argv)
    navigator = BasicNavigator()
    navigator.waitUntilNav2Active()

    rows = []
    try:
        for loop in range(1, args.loops + 1):
            print(f'=== Loop {loop}/{args.loops} ===')
            for wp in waypoints:
                print(f"-> {wp['name']} ({wp['x']}, {wp['y']})")
                pose = make_pose(navigator, wp['x'], wp['y'], wp['yaw'])
                result, duration, recoveries = go_to(navigator, wp['name'], pose)
                outcome = {TaskResult.SUCCEEDED: 'succeeded',
                           TaskResult.CANCELED: 'canceled',
                           TaskResult.FAILED: 'failed'}.get(result, 'unknown')
                print(f'   {outcome} in {duration:.1f} s ({recoveries} recoveries)')
                rows.append([loop, wp['name'], outcome, f'{duration:.1f}', recoveries])
    except KeyboardInterrupt:
        print('Interrupted, cancelling the current goal')
        navigator.cancelTask()
    finally:
        if rows:
            os.makedirs(os.path.dirname(args.log) or '.', exist_ok=True)
            new_file = not os.path.exists(args.log)
            with open(args.log, 'a', newline='') as f:
                writer = csv.writer(f)
                if new_file:
                    writer.writerow(['loop', 'waypoint', 'result', 'duration_s', 'recoveries'])
                writer.writerows(rows)
            ok = sum(1 for r in rows if r[2] == 'succeeded')
            print(f'\nSummary: {ok}/{len(rows)} goals succeeded. Log: {args.log}')
        navigator.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
