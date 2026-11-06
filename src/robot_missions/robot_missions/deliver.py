#!/usr/bin/env python3
"""Command-line client: request one or more deliveries from the running mission manager.

  ros2 run robot_missions deliver ward_a
  ros2 run robot_missions deliver ward_a lab ward_b
"""
import sys
import time

import rclpy
from rclpy.utilities import remove_ros_args
from std_msgs.msg import String

LISTEN_S = 3.0


def main(argv=None):
    argv = sys.argv if argv is None else argv
    destinations = remove_ros_args(argv)[1:]
    if not destinations:
        print('usage: ros2 run robot_missions deliver <destination> [<destination> ...]')
        return 1

    rclpy.init(args=argv)
    node = rclpy.create_node('delivery_client')
    pub = node.create_publisher(String, 'delivery_request', 10)
    node.create_subscription(String, 'delivery_status', lambda m: print(f'  {m.data}'), 10)

    deadline = time.time() + 10.0
    while pub.get_subscription_count() == 0 and time.time() < deadline:
        rclpy.spin_once(node, timeout_sec=0.1)
    if pub.get_subscription_count() == 0:
        print('No mission manager is listening on /delivery_request. Is it running?')
        node.destroy_node()
        rclpy.shutdown()
        return 1

    for d in destinations:
        print(f'requesting delivery to {d}')
        pub.publish(String(data=d))
    end = time.time() + LISTEN_S
    while time.time() < end:
        rclpy.spin_once(node, timeout_sec=0.1)

    node.destroy_node()
    rclpy.shutdown()
    return 0


if __name__ == '__main__':
    sys.exit(main())
