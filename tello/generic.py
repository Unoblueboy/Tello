from typing import NamedTuple, TypeVar, Generic
from threading import Thread, Event

T = TypeVar("T")


class Vector(NamedTuple, Generic[T]):
    x: T
    y: T
    z: T

    def __str__(self):
        return f"({self.x}, {self.y}, {self.z})"


class RotationVector(NamedTuple):
    pitch: float
    roll: float
    yaw: float

    def __str__(self):
        return f"({self.pitch}, {self.roll}, {self.yaw})"


class TemperatureRange(NamedTuple):
    min: int
    max: int

    def __str__(self):
        return f"{self.min} - {self.max}"
