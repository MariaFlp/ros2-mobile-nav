"""Run slam_toolbox (online async mapping) against the running simulation.

Terminal 1:  ros2 launch robot_gazebo sim.launch.py rviz:=false
Terminal 2:  ros2 launch robot_slam slam.launch.py
"""
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    pkg = get_package_share_directory('robot_slam')
    slam_pkg = get_package_share_directory('slam_toolbox')

    params = os.path.join(pkg, 'config', 'slam_toolbox_async.yaml')
    rviz_cfg = os.path.join(pkg, 'rviz', 'slam.rviz')

    slam = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(slam_pkg, 'launch', 'online_async_launch.py')),
        launch_arguments={
            'slam_params_file': params,
            'use_sim_time': 'true',
        }.items(),
    )

    rviz = Node(
        package='rviz2', executable='rviz2', arguments=['-d', rviz_cfg],
        parameters=[{'use_sim_time': True}], condition=IfCondition(LaunchConfiguration('rviz')),
    )

    return LaunchDescription([
        DeclareLaunchArgument('rviz', default_value='true'),
        slam, rviz,
    ])
