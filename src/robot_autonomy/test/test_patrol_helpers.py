import math

from robot_autonomy.patrol import yaw_to_quaternion


def test_zero_yaw_is_identity():
    z, w = yaw_to_quaternion(0.0)
    assert z == 0.0
    assert w == 1.0


def test_half_turn():
    z, w = yaw_to_quaternion(math.pi)
    assert abs(z - 1.0) < 1e-9
    assert abs(w) < 1e-9


def test_quaternion_is_unit_length():
    for yaw in (-3.0, -1.0, 0.3, 1.57, 2.9):
        z, w = yaw_to_quaternion(yaw)
        assert abs(z * z + w * w - 1.0) < 1e-9
