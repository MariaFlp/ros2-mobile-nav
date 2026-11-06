"""Pure-Python mission logic (no ROS imports) so it can be unit-tested anywhere."""
import math
from collections import deque
from dataclasses import dataclass

import yaml


@dataclass(frozen=True)
class Station:
    name: str
    x: float
    y: float
    yaw: float


@dataclass(frozen=True)
class DeliveryRequest:
    destination: str
    requested_at: float  # seconds on the node clock (simulation time in the sim)


def yaw_to_quaternion(yaw):
    """Return (z, w) of a yaw-only quaternion."""
    return math.sin(yaw / 2.0), math.cos(yaw / 2.0)


def load_stations(path):
    """Read stations.yaml and return (dock_name, {name: Station})."""
    with open(path) as f:
        data = yaml.safe_load(f)
    stations = {
        s['name']: Station(s['name'], float(s['x']), float(s['y']), float(s['yaw']))
        for s in data['stations']
    }
    dock = data['dock']
    if dock not in stations:
        raise ValueError(f"dock '{dock}' is not listed in stations")
    return dock, stations


class DeliveryQueue:
    """First-come-first-served queue of delivery requests with validation."""

    def __init__(self, stations, dock):
        self.stations = stations
        self.dock = dock
        self._items = deque()

    def request(self, destination, now):
        """Return (True, queue_position) if accepted, or (False, reason) if rejected."""
        destination = destination.strip()
        if destination == self.dock:
            return False, f"'{destination}' is the dock, nothing to deliver there"
        if destination not in self.stations:
            known = ', '.join(sorted(n for n in self.stations if n != self.dock))
            return False, f"unknown destination '{destination}' (known: {known})"
        self._items.append(DeliveryRequest(destination, now))
        return True, len(self._items)

    def take_batch(self, capacity):
        """Remove and return up to `capacity` requests, oldest first."""
        batch = []
        while self._items and len(batch) < capacity:
            batch.append(self._items.popleft())
        return batch

    def __len__(self):
        return len(self._items)
