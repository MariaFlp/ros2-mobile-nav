import math
import os

import pytest

from robot_missions.mission_logic import (
    DeliveryQueue, Station, load_stations, yaw_to_quaternion)

STATIONS = {
    'pharmacy': Station('pharmacy', 0.0, 0.0, 0.0),
    'lab': Station('lab', 1.0, -1.0, 3.14),
    'ward_a': Station('ward_a', 7.5, 1.0, 0.0),
}


def make_queue():
    return DeliveryQueue(STATIONS, 'pharmacy')


def test_accepts_known_destination_and_reports_position():
    q = make_queue()
    assert q.request('lab', 1.0) == (True, 1)
    assert q.request('ward_a', 2.0) == (True, 2)
    assert len(q) == 2


def test_rejects_unknown_destination():
    q = make_queue()
    ok, reason = q.request('cafeteria', 0.0)
    assert not ok
    assert 'unknown destination' in reason
    assert 'lab' in reason and 'ward_a' in reason
    assert len(q) == 0


def test_rejects_the_dock():
    q = make_queue()
    ok, reason = q.request('pharmacy', 0.0)
    assert not ok
    assert 'dock' in reason


def test_strips_whitespace():
    q = make_queue()
    assert q.request('  lab \n', 0.0)[0]


def test_batch_is_fifo_and_limited_by_capacity():
    q = make_queue()
    for i, name in enumerate(['lab', 'ward_a', 'lab', 'ward_a']):
        q.request(name, float(i))
    first = q.take_batch(3)
    assert [r.destination for r in first] == ['lab', 'ward_a', 'lab']
    assert [r.requested_at for r in first] == [0.0, 1.0, 2.0]
    second = q.take_batch(3)
    assert [r.destination for r in second] == ['ward_a']
    assert q.take_batch(3) == []


def test_quaternion_is_unit_length():
    for yaw in (-3.0, 0.0, 1.57, 3.14):
        z, w = yaw_to_quaternion(yaw)
        assert math.isclose(z * z + w * w, 1.0, abs_tol=1e-9)


def test_bundled_stations_file_is_valid():
    path = os.path.join(os.path.dirname(__file__), '..', 'config', 'stations.yaml')
    dock, stations = load_stations(path)
    assert dock in stations
    assert len(stations) >= 2


def test_dock_must_be_a_listed_station(tmp_path):
    bad = tmp_path / 'bad.yaml'
    bad.write_text('dock: nowhere\nstations:\n  - {name: lab, x: 0, y: 0, yaw: 0}\n')
    with pytest.raises(ValueError):
        load_stations(str(bad))
