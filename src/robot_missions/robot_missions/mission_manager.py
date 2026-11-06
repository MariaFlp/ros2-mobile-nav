#!/usr/bin/env python3
"""Indoor delivery mission manager.

Requests arrive on /delivery_request (std_msgs/String, one destination name each). While the robot
sits at the dock it loads up to --capacity queued requests, visits the destinations in order
(waiting --unload-time at each), then returns to the dock. A failed leg is retried once.
Status messages go to /delivery_status; every delivery is appended to a CSV file.

  ros2 run robot_missions mission_manager --ros-args -p use_sim_time:=true
  ros2 run robot_missions deliver ward_a lab

Requires the simulation and `ros2 launch robot_navigation navigation.launch.py` to be running.
"""
import argparse
import csv
import os
import sys

import rclpy
from ament_index_python.packages import get_package_share_directory
from geometry_msgs.msg import PoseStamped
from nav2_simple_commander.robot_navigator import BasicNavigator, TaskResult
from rclpy.node import Node
from rclpy.utilities import remove_ros_args
from std_msgs.msg import String

from robot_missions.mission_logic import DeliveryQueue, load_stations, yaw_to_quaternion

LEG_TIMEOUT_S = 150.0
MAX_ATTEMPTS = 2  # first try plus one retry


class MissionManager(Node):
    def __init__(self, queue):
        super().__init__('mission_manager')
        self.queue = queue
        self.status_pub = self.create_publisher(String, 'delivery_status', 10)
        self.create_subscription(String, 'delivery_request', self.on_request, 10)

    def now_s(self):
        return self.get_clock().now().nanoseconds / 1e9

    def say(self, text):
        self.get_logger().info(text)
        self.status_pub.publish(String(data=text))

    def on_request(self, msg):
        accepted, info = self.queue.request(msg.data, self.now_s())
        if accepted:
            self.say(f'accepted {msg.data.strip()} (queue length {info})')
        else:
            self.say(f'rejected: {info}')


def make_pose(navigator, station):
    pose = PoseStamped()
    pose.header.frame_id = 'map'
    # Zero stamp means 'latest'; the navigator's own clock can lag behind simulation time here.
    pose.pose.position.x = station.x
    pose.pose.position.y = station.y
    pose.pose.orientation.z, pose.pose.orientation.w = yaw_to_quaternion(station.yaw)
    return pose


def wait(manager, seconds):
    """Wait on the node clock while still receiving new requests."""
    start = manager.now_s()
    while rclpy.ok() and manager.now_s() - start < seconds:
        rclpy.spin_once(manager, timeout_sec=0.1)


def drive_to(navigator, manager, station):
    """Send one goal and wait. Returns (succeeded, duration_s, recoveries)."""
    start = manager.now_s()
    navigator.goToPose(make_pose(navigator, station))
    recoveries = 0
    while not navigator.isTaskComplete():
        rclpy.spin_once(manager, timeout_sec=0.0)  # keep accepting requests while driving
        feedback = navigator.getFeedback()
        if feedback:
            recoveries = max(recoveries, feedback.number_of_recoveries)
        if manager.now_s() - start > LEG_TIMEOUT_S:
            navigator.cancelTask()
    duration = manager.now_s() - start
    return navigator.getResult() == TaskResult.SUCCEEDED, duration, recoveries


def drive_with_retry(navigator, manager, station):
    """Try a leg up to MAX_ATTEMPTS times. Returns (succeeded, attempts, total_s, recoveries)."""
    total, recoveries = 0.0, 0
    for attempt in range(1, MAX_ATTEMPTS + 1):
        ok, duration, rec = drive_to(navigator, manager, station)
        total += duration
        recoveries += rec
        if ok:
            return True, attempt, total, recoveries
        manager.say(f'attempt {attempt} to reach {station.name} failed')
        wait(manager, 3.0)  # short pause before retrying
    return False, MAX_ATTEMPTS, total, recoveries


def parse_args(argv):
    default_cfg = os.path.join(
        get_package_share_directory('robot_missions'), 'config', 'stations.yaml')
    p = argparse.ArgumentParser(description='Indoor delivery mission manager')
    p.add_argument('--stations', default=default_cfg)
    p.add_argument('--capacity', type=int, default=3, help='deliveries per trip')
    p.add_argument('--load-time', type=float, default=3.0, help='seconds spent loading at the dock')
    p.add_argument('--unload-time', type=float, default=5.0, help='seconds spent unloading at a stop')
    p.add_argument('--log', default='results/deliveries.csv')
    return p.parse_args(remove_ros_args(argv)[1:])


def write_rows(path, rows):
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    new_file = not os.path.exists(path)
    with open(path, 'a', newline='') as f:
        writer = csv.writer(f)
        if new_file:
            writer.writerow(['trip', 'destination', 'result', 'attempts', 'drive_s',
                             'recoveries', 'request_to_delivery_s'])
        writer.writerows(rows)


def main(argv=None):
    argv = sys.argv if argv is None else argv
    args = parse_args(argv)
    dock_name, stations = load_stations(args.stations)
    dock = stations[dock_name]

    rclpy.init(args=argv)
    queue = DeliveryQueue(stations, dock_name)
    manager = MissionManager(queue)
    navigator = BasicNavigator()
    navigator.waitUntilNav2Active()
    manager.say(f'ready at {dock_name}; waiting for delivery requests on /delivery_request')

    trip = 0
    try:
        while rclpy.ok():
            rclpy.spin_once(manager, timeout_sec=0.2)
            if len(queue) == 0:
                continue

            trip += 1
            manager.say(f'trip {trip}: loading at {dock_name}')
            wait(manager, args.load_time)
            batch = queue.take_batch(args.capacity)
            manager.say(f'trip {trip}: carrying {len(batch)} item(s): '
                        + ', '.join(r.destination for r in batch))

            rows = []
            for item in batch:
                station = stations[item.destination]
                manager.say(f'trip {trip}: delivering to {item.destination}')
                ok, attempts, drive_s, rec = drive_with_retry(navigator, manager, station)
                latency = manager.now_s() - item.requested_at
                if ok:
                    manager.say(f'delivered {item.destination} in {drive_s:.0f} s')
                    wait(manager, args.unload_time)
                else:
                    manager.say(f'FAILED to deliver to {item.destination}')
                rows.append([trip, item.destination, 'delivered' if ok else 'failed',
                             attempts, f'{drive_s:.1f}', rec, f'{latency:.1f}'])

            manager.say(f'trip {trip}: returning to {dock_name}')
            ok, _, _, _ = drive_with_retry(navigator, manager, dock)
            manager.say(f'idle at {dock_name}' if ok else f'could not return to {dock_name}')
            write_rows(args.log, rows)
    except KeyboardInterrupt:
        manager.say('interrupted, cancelling the current goal')
        navigator.cancelTask()
    finally:
        navigator.destroy_node()
        manager.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
