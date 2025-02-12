from typing import NamedTuple
from tello.generic import RotationVector, Vector, TemperatureRange


class TelloState(NamedTuple):
    attitude: RotationVector
    velocity: Vector[int]
    temperature: TemperatureRange
    timeOfFlight: int
    height: int
    battery: int
    barometer: float
    time: int
    acceleration: Vector[float]

    def __str__(self):
        return f"""velocity: {str(self.velocity)}, acceleration: {str(self.acceleration)}, attitude: {str(self.attitude)}
time of flight: {self.timeOfFlight}, height: {self.height}
temperature: {str(self.temperature)}
battery: {self.battery}, barometer: {self.barometer}, time: {self.time}"""
