from setuptools import find_packages, setup

package_name = 'robot_autonomy'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/config', ['config/waypoints.yaml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='mfilip',
    maintainer_email='82089636+MariaFlp@users.noreply.github.com',
    description='Waypoint patrol mission on top of Nav2',
    license='Apache-2.0',
    entry_points={
        'console_scripts': [
            'patrol = robot_autonomy.patrol:main',
        ],
    },
)
