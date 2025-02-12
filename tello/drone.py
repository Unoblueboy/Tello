import socket
import threading
import logging
import av
import numpy as np

from queue import Queue

from tello.exception import TelloException
from tello.state import TelloState
from tello.generic import TemperatureRange, RotationVector, Vector

# Setup logging
formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")

# Setup State Logger for State Thread
state_handler = logging.FileHandler(f"{__name__}.state.log")
state_handler.setFormatter(formatter)

state_logger = logging.getLogger(f"{__name__}.state")
state_logger.addHandler(state_handler)

# Setup Stream Logger for Stream Thread
stream_handler = logging.FileHandler(f"{__name__}.stream.log")
stream_handler.setFormatter(formatter)

stream_logger = logging.getLogger(f"{__name__}.stream")
stream_logger.addHandler(stream_handler)

# Client Logger for calls using client socket
client_logger = logging.getLogger(f"{__name__}.client")

# General Logger for everything else
general_logger = logging.getLogger(__name__)


class TelloDrone:
    """Class representing the Tello drone"""

    DRONE_ADDRESS = ("192.168.10.1", 8889)
    BASE_TIMEOUT = 1.0

    def __init__(self):
        # Setup client socket for issuing and receicing commands
        self._client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._client_socket.bind(("0.0.0.0", 9000))
        self._client_socket.settimeout(TelloDrone.BASE_TIMEOUT)

        self._client_socket_lock = threading.Lock()

        # Setup a thread and socket to constantly receive full Tello State
        self.state_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.state_socket.bind(("0.0.0.0", 8890))

        self.state_thread = threading.Thread(
            target=self._state_thread_function, daemon=True
        )
        self.state_lock = threading.Lock()

        # set state variable to None
        self._state = None

        # Setup thread for constantly receiving video stream
        self._stream_queue = Queue(maxsize=0)

        self.stream_thread = StreamThread(("0.0.0.0", 11111), self._stream_queue)
        self.stream_lock = threading.Lock()

        # Start Listening Threads
        self.state_thread.start()

    @property
    def state(self):
        """The state of the Tello drone"""
        with self.state_lock:
            return self._state

    @state.setter
    def state(self, value: TelloState):
        with self.state_lock:
            self._state = value

    @property
    def next_frame(self):
        """The next frame retrieved from the Tello drone"""
        next_frame = self._stream_queue.get(block=True)
        self._stream_queue.task_done()
        return next_frame

    @property
    def speed(self):
        """Get current speed (cm/s)"""
        general_logger.info("Get speed")
        byte_data = self._simple_client_socket_caller("speed?")
        stripped_data = byte_data.strip()
        return float(stripped_data)

    @property
    def battery(self):
        """Get current battery percentage"""
        return float(self._simple_client_socket_caller("battery?"))

    @property
    def time(self):
        """Get current fly time (s)"""
        byte_data = self._simple_client_socket_caller("time?")
        stripped_data = byte_data.strip()
        return int(stripped_data[:-1])

    @property
    def height(self):
        """Get height (cm)"""
        byte_data = self._simple_client_socket_caller("height?")
        stripped_data = byte_data.strip()
        return int(stripped_data[:-2])

    @property
    def temperature(self):
        """Get temperature range (°C)"""
        byte_data = self._simple_client_socket_caller("temp?")
        stripped_data = byte_data.strip()
        split_data = stripped_data.split(b"~")
        return TemperatureRange(int(split_data[0]), int(split_data[1][:-1]))

    @property
    def attitude(self):
        """Get IMU attitude data: roll, pitch, yaw"""
        byte_data = self._simple_client_socket_caller("attitude?")
        stripped_data = byte_data.strip()
        split_data = stripped_data.split(b";")
        return RotationVector(
            float(split_data[0][6:]), float(split_data[1][5:]), float(split_data[2][4:])
        )

    @property
    def barometer(self):
        """Get barometer value"""
        return float(self._simple_client_socket_caller("baro?"))

    @property
    def acceleration(self):
        """Get IMU angular acceleration data (0.001g)"""
        byte_data = self._simple_client_socket_caller("acceleration?")
        stripped_data = byte_data.strip()
        split_data = stripped_data.split(b";")
        return Vector[float](
            float(split_data[0][4:]), float(split_data[1][4:]), float(split_data[2][4:])
        )

    @property
    def time_of_flight(self):
        """Get Distance value from TOF (mm)"""
        byte_data = self._simple_client_socket_caller("tof?")
        stripped_data = byte_data.strip()
        return float(stripped_data[:-2])

    @property
    def wifi(self):
        """Get Wi-Fi signal to noise ratio (SNR)"""
        return int(self._simple_client_socket_caller("wifi?"))

    def _simple_client_socket_caller(
        self, command: str, bufsize: int = 2048, timeout=None
    ):
        with self._client_socket_lock:
            byte_command = command.encode(encoding="utf8")
            if timeout is not None:
                self._client_socket.settimeout(timeout)
            self._client_socket.sendto(byte_command, TelloDrone.DRONE_ADDRESS)
            byte_data = self._client_socket.recv(bufsize)
            if timeout is not None:
                self._client_socket.settimeout(TelloDrone.BASE_TIMEOUT)
            return byte_data

    def _generic_client_socket_caller(
        self,
        command: str,
        bufsize: int = 2048,
        timeout: int = None,
        tries: int = 1,
        throw_exception: bool = True,
    ):
        try_num = 1
        while try_num <= tries:
            try:
                byte_data = self._simple_client_socket_caller(command, bufsize, timeout)
                print(command, byte_data)
                stripped_data = byte_data.strip()
                if stripped_data == b"ok":
                    return True
                elif throw_exception:
                    str_exception = stripped_data.decode(encoding="utf-8")
                    raise TelloException(str_exception, command)

            except Exception as exc:
                if throw_exception and try_num == tries:
                    raise exc
                elif try_num == tries:
                    return False
            try_num += 1
        return False

    def command(self):
        """Enter SDK Mode"""
        return self._generic_client_socket_caller("command")

    def takeoff(self, throw_exception=True):
        """Tello auto takeoff"""
        return self._generic_client_socket_caller(
            "takeoff", throw_exception=throw_exception, timeout=20.0
        )

    def land(self, throw_exception=True):
        """Tello auto land"""
        return self._generic_client_socket_caller(
            "land", throw_exception=throw_exception, timeout=7.0
        )

    def stream_on(self):
        """Set video stream on"""
        self._generic_client_socket_caller(f"streamon")
        self.stream_thread.start()

    def stream_off(self):
        """Set video stream off"""
        self._generic_client_socket_caller(f"streamoff")
        self.stream_thread.stop()

    def emergency(self):
        """Stop all motors immediately"""
        return self._generic_client_socket_caller(f"emergency", timeout=20.0)

    def up(self, x: int):
        """Tello fly up with distance x cm, x: 20-500"""
        return self._generic_client_socket_caller(f"up {x}", timeout=20.0)

    def down(self, x: int):
        """Tello fly down with distance x cm, x: 20-500"""
        return self._generic_client_socket_caller(f"down {x}", timeout=20.0)

    def left(self, x: int):
        """Tello fly left with distance x cm, x: 20-500"""
        return self._generic_client_socket_caller(f"left {x}", timeout=20.0)

    def right(self, x: int):
        """Tello fly right with distance x cm, x: 20-500"""
        return self._generic_client_socket_caller(f"right {x}", timeout=20.0)

    def forward(self, x: int):
        """Tello fly forward with distance x cm, x: 20-500"""
        return self._generic_client_socket_caller(f"forward {x}", timeout=20.0)

    def back(self, x: int):
        """Tello fly back with distance x cm, x: 20-500"""
        return self._generic_client_socket_caller(f"back {x}", timeout=20.0)

    def clockwise(self, x: int):
        """Tello rotate x degrees clockwise, x: 1-3600"""
        # set timeout to be (10 + (degrees rotated / 6)) seconds
        return self._generic_client_socket_caller(f"cw {x}", timeout=10 + x / 6)

    def counterclockwise(self, x: int):
        """Tello rotate x degrees counterclockwise, x: 1-3600"""
        # set timeout to be (10 + (degrees rotated / 6)) seconds
        return self._generic_client_socket_caller(f"ccw {x}", timeout=10 + x / 6)

    def go(self, location: Vector[int], speed: int):
        """Tello fly to location at speed (cm/s)

        location.x, location.y, location.z: 20-500
        speed: 10-100"""
        return self._generic_client_socket_caller(
            f"go {location.x} {location.y} {location.z} {speed}", timeout=120
        )

    def curve(
        self,
        location1: Vector[int],
        location2: Vector[int],
        speed: int,
        throw_exception=False,
    ):
        """Tello fly a curve defined by the current and two given coordinates with speed (cm/s)
        If the arc radius is not within the range of 0.5-10 meters, it responses false

        location1.x, location1.y, location1.z: 20-500
        location2.x, location2.y, location2.z: 20-500
        speed: 10-60
        x/y/z can't be between -20 – 20 at the same time."""

        return self._generic_client_socket_caller(
            f"curve {location1.x} {location1.y} {location1.z} {location2.x} {location2.y} {location2.z} {speed}",
            throw_exception=throw_exception,
        )

    def set_speed(self, x: int):
        """set speed to x cm/s, x: 10-100"""
        return self._generic_client_socket_caller(f"speed {x}")

    def rc(self, channel1: int, channel2: int, channel3: int, channel4: int):
        """Send RC control via four channels.

        channel1: left/right (-100~100)
        channel2: forward/backward (-100~100)
        channel3: up/down (-100~100)
        channel4: yaw (-100~100)"""
        return self._generic_client_socket_caller(
            f"rc {channel1} {channel2} {channel3} {channel4}"
        )

    def set_wifi(self, ssid: str, password: str):
        """Set Wi-Fi with SSID password"""
        return self._generic_client_socket_caller(f"wifi {ssid} {password}")

    def _state_thread_function(self):
        state_logger.info("StreamThread run started")
        while True:
            try:
                data = self.state_socket.recv(2048)
                state_logger.debug(f"Byte data: {data}")
                string_data = data.decode(encoding="utf-8").strip()
                split_data = string_data.split(";")
                self.state = TelloState(
                    RotationVector(
                        float(split_data[0][6:]),
                        float(split_data[1][5:]),
                        float(split_data[2][4:]),
                    ),
                    Vector[int](
                        int(split_data[3][4:]),
                        int(split_data[4][4:]),
                        int(split_data[5][4:]),
                    ),
                    TemperatureRange(int(split_data[6][6:]), int(split_data[7][6:])),
                    int(split_data[8][4:]),
                    int(split_data[9][2:]),
                    int(split_data[10][4:]),
                    float(split_data[11][5:]),
                    int(split_data[12][5:]),
                    Vector[float](
                        float(split_data[13][4:]),
                        float(split_data[14][4:]),
                        float(split_data[15][4:]),
                    ),
                )
                state_logger.debug(repr(self.state))
            except Exception as e:
                state_logger.exception(e)


class StreamThread(threading.Thread):
    """Thread class with a stop() method. The thread itself has to check
    regularly for the stopped() condition."""

    def __init__(self, address, queue):
        super().__init__(daemon=True)
        self._stop_event = threading.Event()
        self.address = address
        self.queue = queue

    def stop(self):
        stream_logger.info("StreamThread.stop called")
        self._stop_event.set()

    def stopped(self):
        return self._stop_event.is_set()

    def run(self):
        stream_logger.info("StreamThread run started")

        container = av.open(f"udp://{self.address[0]}:{self.address[1]}")

        for frame in container.decode(video=0):
            if self.stopped():
                stream_logger.info("StreamThread run stopped")
                break
            try:
                stream_logger.debug(np.array(frame.to_image()))
                self.queue.put(np.array(frame.to_image()))
            except Exception as e:
                stream_logger.exception(e)

        stream_logger.info("No More Frames Processed")
        av.close()
