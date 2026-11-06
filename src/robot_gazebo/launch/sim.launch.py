"""Start Gazebo with the office world, spawn the robot, bridge topics, optionally open RViz2.

  ros2 launch robot_gazebo sim.launch.py
  ros2 launch robot_gazebo sim.launch.py x:=-4.0 y:=0.0 yaw:=0.0 rviz:=false
"""
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    gz_pkg = get_package_share_directory('robot_gazebo')
    desc_pkg = get_package_share_directory('robot_description')
    ros_gz_sim = get_package_share_directory('ros_gz_sim')

    xacro_file = os.path.join(desc_pkg, 'urdf', 'diffbot.urdf.xacro')
    default_world = os.path.join(gz_pkg, 'worlds', 'office.sdf')
    bridge_cfg = os.path.join(gz_pkg, 'config', 'bridge.yaml')
    rviz_cfg = os.path.join(gz_pkg, 'rviz', 'sim.rviz')

    world = LaunchConfiguration('world')
    rviz = LaunchConfiguration('rviz')

    robot_description = ParameterValue(Command(['xacro ', xacro_file]), value_type=str)

    gz_sim = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(ros_gz_sim, 'launch', 'gz_sim.launch.py')),
        launch_arguments={'gz_args': ['-r ', world]}.items(),
    )

    rsp = Node(
        package='robot_state_publisher', executable='robot_state_publisher',
        parameters=[{'robot_description': robot_description, 'use_sim_time': True}],
    )

    spawn = Node(
        package='ros_gz_sim', executable='create',
        arguments=['-topic', 'robot_description', '-name', 'diffbot',
                   '-x', LaunchConfiguration('x'), '-y', LaunchConfiguration('y'),
                   '-z', '0.1', '-Y', LaunchConfiguration('yaw')],
        output='screen',
    )

    bridge = Node(
        package='ros_gz_bridge', executable='parameter_bridge',
        parameters=[{'config_file': bridge_cfg, 'use_sim_time': True}],
        output='screen',
    )

    rviz_node = Node(
        package='rviz2', executable='rviz2', arguments=['-d', rviz_cfg],
        parameters=[{'use_sim_time': True}], condition=IfCondition(rviz),
    )

    return LaunchDescription([
        DeclareLaunchArgument('world', default_value=default_world),
        DeclareLaunchArgument('x', default_value='-4.0'),
        DeclareLaunchArgument('y', default_value='0.0'),
        DeclareLaunchArgument('yaw', default_value='0.0'),
        DeclareLaunchArgument('rviz', default_value='true'),
        gz_sim, rsp, spawn, bridge, rviz_node,
    ])
